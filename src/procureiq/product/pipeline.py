"""Durable local queue. One advisory-locked worker; controlled receipts only."""
import json
import re
import time
from hashlib import sha256
from pathlib import Path
from threading import Event,Thread
from sqlalchemy import text
from procureiq.ingestion import prepare,load_file,activate,LOCK
from procureiq.opportunities import canonical
from procureiq.source_basis import fingerprint
from procureiq.investigations.domain import InvestigationError
WORKER_LOCK=7102026030

class Pipeline:
    def __init__(self,engine,root):self.engine=engine;self.root=Path(root).resolve();self.stop=Event();self.thread=None
    def manifest(self,name):
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.json',name):raise ValueError('Invalid manifest name')
        path=(self.root/'manifests'/name).resolve()
        if path.parent!=(self.root/'manifests').resolve():raise ValueError('Manifest must be controlled local file')
        data=path.read_bytes()
        if len(data)>2_000_000:raise ValueError('Manifest too large')
        receipts=json.loads(data)
        if not isinstance(receipts,list) or not 1<=len(receipts)<=120:raise ValueError('Receipt list required')
        for r in receipts:
            if not isinstance(r,dict) or not {'filename','reporting_month','sha256','size_bytes','url','status'}<=set(r):raise ValueError('Receipt fields missing')
            raw=(self.root/'data/raw'/r['filename']).resolve()
            if raw.parent!=(self.root/'data/raw').resolve():raise ValueError('Source must remain in controlled data/raw')
            if r['status'] not in ('downloaded','verified'):raise ValueError('Verified acquisition receipt required')
        if len({(r['reporting_month'],r['sha256']) for r in receipts})!=len(receipts):raise ValueError('Duplicate month/hash receipts')
        return sha256(data).hexdigest(),receipts
    def discover(self):
        result=[]
        for p in sorted((self.root/'manifests').glob('*.json')):
            try:digest,receipts=self.manifest(p.name)
            except (ValueError,KeyError,TypeError,OSError):continue
            result.append(dict(name=p.name,sha256=digest,source_count=len(receipts)))
        return result
    def register(self,name):
        digest,receipts=self.manifest(name)
        with self.engine.begin() as c:
            c.execute(text('INSERT INTO procureiq_app.source_registration(manifest_name,manifest_sha256,receipts) VALUES(:name,:hash,CAST(:receipts AS jsonb)) ON CONFLICT DO NOTHING'),dict(name=name,hash=digest,receipts=canonical(receipts)))
            return dict(c.execute(text('SELECT * FROM procureiq_app.source_registration WHERE manifest_name=:name AND manifest_sha256=:hash'),dict(name=name,hash=digest)).mappings().one())
    def enqueue(self,operation,registration_id=None,source_file_id=None,expected=None,retry_of=None):
        with self.engine.begin() as c:
            c.execute(text('SELECT pg_advisory_xact_lock(:key)'),dict(key=WORKER_LOCK+1))
            if c.execute(text("SELECT count(*) FROM procureiq_app.pipeline_run WHERE status IN ('queued','running')")).scalar_one()>=8:raise InvestigationError('queue_full','Local queue is full. Wait for existing operations.',409)
            if operation=='ingest' and not registration_id:raise ValueError('Source registration required')
            if operation=='activate' and (not source_file_id or not expected):raise ValueError('Activation needs source identity and reviewed basis')
            if source_file_id and not c.execute(text('SELECT 1 FROM procureiq.source_file WHERE file_id=:id'),dict(id=source_file_id)).scalar():raise ValueError('Source version not found')
            if registration_id and not c.execute(text('SELECT 1 FROM procureiq_app.source_registration WHERE registration_id=:id'),dict(id=registration_id)).scalar():raise ValueError('Registration not found')
            return dict(c.execute(text('''INSERT INTO procureiq_app.pipeline_run(operation,registration_id,source_file_id,expected_fingerprint,retry_of)
              VALUES(:op,:reg,:file,:basis,:retry) RETURNING *'''),dict(op=operation,reg=registration_id,file=source_file_id,basis=expected,retry=retry_of)).mappings().one())
    def retry(self,run_id):
        with self.engine.connect() as c:r=c.execute(text('SELECT * FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=run_id)).mappings().first()
        if not r or r['status'] not in ('failed','interrupted'):raise InvestigationError('retry_not_allowed','Only failed/interrupted runs can be retried.')
        if r['operation']=='activate':raise InvestigationError('review_required','Activation requires a new explicit review and confirmation.')
        return self.enqueue(r['operation'],r['registration_id'],retry_of=run_id)
    def start(self):
        self.thread=Thread(target=self.loop,name='procureiq-local-pipeline',daemon=True);self.thread.start()
    def close(self):self.stop.set();self.thread.join(timeout=35) if self.thread else None
    def loop(self):
        while not self.stop.is_set():
            try:
                with self.engine.connect() as lock:
                    acquired=lock.execute(text('SELECT pg_try_advisory_lock(:key)'),dict(key=WORKER_LOCK)).scalar();lock.commit()
                    if acquired:
                        try:
                            # Holding exclusive worker lock proves no prior worker remains alive.
                            with self.engine.begin() as c:
                                c.execute(text("UPDATE procureiq_app.pipeline_stage SET status='interrupted',finished_at=now() WHERE status='running'"))
                                c.execute(text("UPDATE procureiq_app.pipeline_run SET status='interrupted',finished_at=now(),error_code='worker_interrupted',error_summary='Worker stopped before completion; retry revalidates prior committed files.' WHERE status='running'"))
                            while not self.stop.is_set() and self.execute_next():pass
                        finally:lock.execute(text('SELECT pg_advisory_unlock(:key)'),dict(key=WORKER_LOCK));lock.commit()
            except Exception:
                # No fabricated success; durable active stages are recovered on next lock acquisition.
                import logging
                logging.getLogger(__name__).warning('Local pipeline worker unavailable; durable queue retained.')
            self.stop.wait(1)
    def stage(self,run_id,name,fn):
        with self.engine.begin() as c:
            c.execute(text('UPDATE procureiq_app.pipeline_run SET current_stage=:name WHERE run_id=:id'),dict(id=run_id,name=name))
            c.execute(text("INSERT INTO procureiq_app.pipeline_stage(run_id,name,status) VALUES(:id,:name,'running')"),dict(id=run_id,name=name))
        start=time.monotonic()
        try:result=fn();status='succeeded'
        except Exception:
            with self.engine.begin() as c:c.execute(text("UPDATE procureiq_app.pipeline_stage SET status='failed',finished_at=now(),duration_ms=:ms WHERE run_id=:id AND name=:name"),dict(id=run_id,name=name,ms=str((time.monotonic()-start)*1000)))
            raise
        with self.engine.begin() as c:c.execute(text('UPDATE procureiq_app.pipeline_stage SET status=:status,finished_at=now(),duration_ms=:ms,output=CAST(:out AS jsonb) WHERE run_id=:id AND name=:name'),dict(id=run_id,name=name,status=status,ms=str((time.monotonic()-start)*1000),out=canonical(result)))
        return result
    def execute_next(self):
        with self.engine.begin() as c:
            r=c.execute(text("SELECT * FROM procureiq_app.pipeline_run WHERE status='queued' ORDER BY run_id LIMIT 1 FOR UPDATE SKIP LOCKED")).mappings().first()
            if not r:return False
            r=dict(r);c.execute(text("UPDATE procureiq_app.pipeline_run SET status='running',started_at=now() WHERE run_id=:id"),dict(id=r['run_id']))
        try:
            self.execute(r)
            with self.engine.begin() as c:c.execute(text("UPDATE procureiq_app.pipeline_run SET status='succeeded',finished_at=now() WHERE run_id=:id"),dict(id=r['run_id']))
        except Exception as exc:
            code='validation_failed' if isinstance(exc,(ValueError,InvestigationError)) else 'operation_failed'
            summary='Stage failed validation or execution. Inspect the failed stage; check controlled receipts, file hashes and local service availability before retrying.'
            if isinstance(exc,ValueError):
                message=str(exc).lower()
                if 'manifest changed' in message:code='receipt_changed';summary='Registered receipt bytes changed. Restore the registered version or register a new receipt before ingestion.'
                elif 'contract failed' in message:code='schema_contract';summary='A source is missing required columns or contains ragged records. Correct the controlled source receipt before ingestion.'
                elif 'hash' in message or 'checksum' in message or 'size' in message:code='source_identity';summary='Source bytes do not match their receipt hash or size. Reacquire and register verified bytes.'
                elif 'fingerprint' in message or 'source changed' in message:code='stale_source';summary='Active source selection changed since review. Inspect the current sources and explicitly confirm activation again.' 
            # Controlled summary; never arbitrary DB/server exception text.
            with self.engine.begin() as c:c.execute(text("UPDATE procureiq_app.pipeline_run SET status='failed',finished_at=now(),error_code=:code,error_summary=:summary WHERE run_id=:id"),dict(id=r['run_id'],code=code,summary=summary))
        return True
    def execute(self,run):
        rid=run['run_id'];stage=lambda n,f:self.stage(rid,n,f)
        if run['operation']=='ingest':
            with self.engine.connect() as c:reg=c.execute(text('SELECT * FROM procureiq_app.source_registration WHERE registration_id=:id'),dict(id=run['registration_id'])).mappings().one()
            def receipt_check():
                digest,receipts=self.manifest(reg['manifest_name'])
                if digest!=reg['manifest_sha256'] or canonical(receipts)!=canonical(reg['receipts']):raise ValueError('Manifest changed; register a new version')
                return dict(manifest=reg['manifest_name'],sha256=digest,sources=len(receipts))
            stage('source_validation',receipt_check)
            def profile():
                summaries=[]
                for receipt in reg['receipts']:
                    rows,issues,summary=prepare(self.root,receipt)
                    fatal=[x for x in issues if x['code']=='ragged_row' or x['code']=='schema_drift' and x.get('missing')]
                    if fatal:raise ValueError('Required-column/rectangular-record contract failed')
                    summaries.append(dict(file=receipt['filename'],sha256=receipt['sha256'],rows=len(rows),quality_issue_count=len(issues),summary=summary))
                return summaries
            stage('parsing_and_contracts',profile)
            # Every version is inactive on first import; already-loaded selections are preserved.
            loaded=stage('incremental_ingestion',lambda:[load_file(self.engine,self.root,r,activate_initial=False) for r in reg['receipts']])
            stage('reconciliation_and_quality',lambda:[load_file(self.engine,self.root,r,activate_initial=False) for r in reg['receipts']])
            stage('activation_readiness',lambda:dict(files=loaded,automatic_activation=False,requires_explicit_confirmation=True))
        elif run['operation']=='activate':
            with self.engine.connect() as c:
                source=dict(c.execute(text('SELECT * FROM procureiq.source_file WHERE file_id=:id'),dict(id=run['source_file_id'])).mappings().one())
            def activate_checked():
                activate(self.engine,self.root,str(source['reporting_month'])[:7],source['sha256'],expected_fingerprint=run['expected_fingerprint'])
                return dict(file_id=source['file_id'],sha256=source['sha256'])
            stage('explicit_activation',activate_checked)

        else:
            from procureiq.reconciliation import verify
            stage('frozen_source_reconciliation',lambda:verify(self.engine,self.root,write_reports=False))
        from procureiq.analytics import verify_analytics
        def analytical():
            with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as c,c.begin():
                c.exec_driver_sql('SET TRANSACTION READ ONLY');return verify_analytics(c)
        stage('downstream_analytics',analytical)
