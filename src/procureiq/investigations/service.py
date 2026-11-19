"""Transactional investigation use cases. No HTTP or Streamlit dependencies."""
from contextlib import contextmanager
from dataclasses import asdict
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from procureiq.opportunity_model import OpportunityConfig
from procureiq.opportunities import TYPES
from procureiq.source_basis import fingerprint
from . import repository as repo
from .reviews import resolve,find_review,review_key,summary,context
from .domain import InvestigationError,transition,meaningful,Status


class InvestigationService:
    def __init__(self,engine,config=None):
        self.engine=engine
        self.config=config or OpportunityConfig()

    @contextmanager
    def read(self):
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
            conn.exec_driver_sql('SET TRANSACTION READ ONLY')
            conn.exec_driver_sql("SET LOCAL statement_timeout='30s'")
            yield conn

    @staticmethod
    def page(offset,limit):
        if type(offset) is not int or offset<0 or offset>1000000 or type(limit) is not int or not 1<=limit<=100:
            raise InvestigationError('invalid_pagination','Use offset 0–1000000 and limit 1–100.',422)

    @staticmethod
    def annotate(case,version):
        case['basis_matches_current_source']=case['source_fingerprint']==version
        # Large per-row quality flags remain frozen in storage, not in detail responses.
        if 'review_snapshot' in case:
            case['review_snapshot'].get('metrics',{}).pop('source_flags',None)
        return case

    def health(self):
        with self.read() as conn:
            conn.execute(text('SELECT 1 FROM procureiq_app.schema_migration LIMIT 1'))
        return dict(status='ok',service='procureiq_investigations',mode='local_single_analyst')

    def reviews(self,filters=None,kind=None,minimum=Decimal('0'),offset=0,limit=50,review_id=None):
        self.page(offset,limit)
        if kind is not None and kind not in TYPES:raise InvestigationError('invalid_input','Unknown detector type.',422)
        minimum=Decimal(str(minimum))
        if not minimum.is_finite() or not 0<=minimum<=100:raise InvestigationError('invalid_input','Minimum priority must be 0–100.',422)
        with self.read() as conn:
            result,basis,token=resolve(conn,filters,self.config)
            items=[find_review(result,review_id)] if review_id else [o for o in result['opportunities'] if (kind is None or o['opportunity_type']==kind) and o['scoring']['priority_score']>=minimum]
            cases=repo.existing(conn,[review_key(i,basis) for i in items])
            summaries=[]
            for item in items[offset:offset+limit] if not review_id else items:
                out=summary(item)
                out.update(review_basis_key=review_key(item,basis),existing_case=cases.get(review_key(item,basis)))
                if review_id:
                    out.update({k:item[k] for k in ('scoring','business_interpretation','next_investigation_step','caveats','exposure_definition')})
                    out['metrics']={k:v for k,v in item['metrics'].items() if k!='source_flags'}
                summaries.append(out)
            qualified=sum(result['qualified_before_cap'].values());exported=len(result['opportunities'])
            return dict(items=summaries,total=len(items),offset=offset,limit=limit,basis=basis,basis_token=token,
                qualified_count=qualified,exported_count=exported,deferred_count=qualified-exported,
                counts_by_type=result['counts_by_type'],qualified_by_type=result['qualified_before_cap'])

    def create(self,review_id,filters,basis_token,title,objective):
        if not isinstance(title,str) or not 3<=len(title.strip())<=240 or not meaningful(objective):
            raise InvestigationError('invalid_input','Provide a title (3–240 characters) and meaningful objective (10–4000 characters).',422)
        # A conflicting INSERT in repeatable-read can raise 40001. Retry the entire
        # transaction, re-resolve the basis, then return the committed existing case.
        for attempt in range(3):
            try:
                return self._create(review_id,filters,basis_token,title.strip(),objective.strip())
            except DBAPIError as exc:
                if getattr(exc.orig,'sqlstate',None)!='40001':raise
                if attempt==2:raise InvestigationError('concurrent_change','Concurrent changes prevented creation. Refresh and retry.') from exc

    def _create(self,review_id,filters,basis_token,title,objective):
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
            conn.exec_driver_sql("SET LOCAL lock_timeout='10s'")
            conn.exec_driver_sql("SET LOCAL statement_timeout='30s'")
            # Acquire before the first MVCC read. SHARE blocks source activation,
            # ingestion and analytical migration writes until this case commits.
            conn.exec_driver_sql('LOCK TABLE procureiq.source_file, procureiq.schema_migration IN SHARE MODE')
            basis,token=context(conn,filters,self.config)
            if basis_token!=token:raise InvestigationError('stale_review_basis','Source, policy or filters changed. Refresh the review list before creating a case.')
            result,basis,token=resolve(conn,filters,self.config)
            item=find_review(result,review_id);key=review_key(item,basis)
            case_id=repo.insert_case(conn,item,basis,key,title,objective,asdict(self.config))
            created=case_id is not None
            if created:
                repo.insert_evidence(conn,case_id,item)
                repo.event(conn,case_id,'CASE_CREATED',None,'OPEN',None,dict(review_basis_key=key,row_version=1,origin='flagged_exported_review'))
            else:case_id=repo.existing(conn,[key])[key]['case_id']
            case=self.annotate(repo.get_case(conn,case_id),basis['source_fingerprint'])
            return dict(created=created,case=case)

    def get(self,case_id):
        with self.read() as conn:
            case=self.annotate(repo.get_case(conn,case_id),fingerprint(conn))
            case['work_counts']={r[0]:r[1] for r in conn.execute(text('SELECT kind,count(*) FROM procureiq_app.case_entry WHERE case_id=:id AND NOT deleted GROUP BY kind'),dict(id=case_id))}
            case['work_counts']['bookmarks']=conn.execute(text('SELECT count(*) FROM procureiq_app.case_bookmark WHERE case_id=:id AND active'),dict(id=case_id)).scalar_one()
            return case

    def cases(self,status=None,offset=0,limit=50):
        self.page(offset,limit)
        if status is not None and status not in {x.value for x in Status}:raise InvestigationError('invalid_input','Unknown case status.',422)
        with self.read() as conn:
            output=repo.list_cases(conn,status,offset,limit);version=fingerprint(conn)
            output['items']=[self.annotate(c,version) for c in output['items']]
            return output

    def evidence(self,case_id,classification='primary',offset=0,limit=50,filters=None):
        self.page(offset,limit)
        if classification not in ('primary','contextual'):raise InvestigationError('invalid_input','Unknown evidence classification.',422)
        with self.read() as conn:
            case=repo.get_case(conn,case_id,detail=False)
            output=repo.evidence(conn,case,classification,offset,limit,filters)
            output['basis_matches_current_source']=case['source_fingerprint']==fingerprint(conn)
            return output

    def activity(self,case_id,offset=0,limit=50,kind=None):
        self.page(offset,limit)
        with self.read() as conn:return repo.activity(conn,case_id,offset,limit,kind)

    def status(self,case_id,new,expected_version,reason=None,disposition=None):
        if type(expected_version) is not int or expected_version<1:raise InvestigationError('invalid_input','Expected version must be a positive integer.',422)
        with self.engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL lock_timeout='10s'")
            old=repo.get_case(conn,case_id,lock=True,detail=False)
            if old['row_version']!=expected_version:raise InvestigationError('case_version_conflict','Case changed since it was read. Refresh before retrying.')
            transition(old['status'],new,reason,disposition)
            conn.execute(text('''UPDATE procureiq_app.investigation_case SET status=:new,row_version=row_version+1,updated_at=now(),
              reviewed_at=CASE WHEN :new='REVIEWED' THEN now() WHEN :reopen THEN NULL ELSE reviewed_at END,
              closed_at=CASE WHEN :new='CLOSED' THEN now() ELSE NULL END,
              disposition=:disposition,closure_explanation=CASE WHEN :new='CLOSED' THEN :reason ELSE NULL END
              WHERE case_id=:id'''),dict(new=new,reopen=old['status']=='CLOSED',disposition=disposition,reason=reason,id=case_id))
            repo.event(conn,case_id,'CASE_REOPENED' if old['status']=='CLOSED' else 'STATUS_CHANGED',old['status'],new,reason,
                dict(row_version=expected_version+1,disposition=disposition,previous_disposition=old['disposition']))
            return self.annotate(repo.get_case(conn,case_id),fingerprint(conn))
