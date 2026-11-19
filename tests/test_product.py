from decimal import Decimal as D
from types import SimpleNamespace
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from test_database import db,ROOT
from test_opportunities import radar_data
from test_investigations import investigation,request_for
from procureiq.investigations.work import CaseWork
from procureiq.api.work_routes import Entry
from procureiq.api.app import create_app
from procureiq.investigations.domain import InvestigationError
from procureiq.product.optimization import OptimizationInput,solve
from procureiq.product.pipeline import Pipeline

def model(**kw):
    return OptimizationInput(title='Independent fixture',units='equivalent units',assumption_note='Synthetic commercial assumptions only.',demand='100',candidates=[dict(name='A',unit_cost='10',capacity='60'),dict(name='B',unit_cost='20',capacity='100')],**kw)
def test_milp_independent_cost_capacity_dependency():
    r=solve(model());assert r['status']=='optimal';assert D(r['objective_gbp'])==D('1400');assert [D(x['allocation']) for x in r['allocations']]==[D(60),D(40)]
    r=solve(model(dependency_pct='50'));assert D(r['objective_gbp'])==D('1500');assert [D(x['allocation']) for x in r['allocations']]==[D(50),D(50)]
def test_milp_fixed_costs_and_selection():
    m=model();m.candidates[0].fixed_cost=D(1000);r=solve(m);assert D(r['objective_gbp'])==D(2000);assert r['allocations'][0]['selected'] is False
    r=solve(model(max_suppliers=1));assert D(r['objective_gbp'])==D(2000)
def test_milp_eligibility_infeasible_zero_invalid():
    m=model();m.candidates[1].eligible=False;assert solve(m)['status']=='infeasible'
    assert solve(model(dependency_pct='40'))['status']=='infeasible'
    with pytest.raises(ValueError):OptimizationInput(**(model().model_dump()|{'demand':'0'}))
    with pytest.raises(ValueError):model(min_suppliers=3,max_suppliers=1)
def test_milp_nonoptimal(monkeypatch):
    import procureiq.product.optimization as module
    monkeypatch.setattr(module,'milp',lambda *a,**k:SimpleNamespace(status=1,x=None))
    r=solve(model());assert r['status']=='limit_reached' and not r['feasible'] and r['objective_gbp'] is None

def test_work_persistence_conflicts_citations_audit(investigation):
    svc,_=investigation;c=svc.create(**request_for(svc))['case'];cid=c['case_id'];w=CaseWork(svc.engine)
    assert w.bookmark(cid,'primary',1,True)['changed'];assert not w.bookmark(cid,'primary',1,True)['changed']
    with pytest.raises(InvestigationError):w.bookmark(cid,'primary',999999,True)
    e=w.save(cid,Entry(kind='finding',title='Evidence finding',content='Observed source lines require contractual validation.',citations=[dict(classification='primary',ordinal=1)]))
    assert w.list(cid)['items'][0]['citations']==[dict(classification='primary',ordinal=1)]
    with pytest.raises(InvestigationError,match='changed'):w.save(cid,Entry(kind='finding',title='Edited finding',content='This is an updated observation.',expected_version=9),e['entry_id'])
    w.save(cid,Entry(kind='finding',title='Edited finding',content='This is an updated observation.',expected_version=1),e['entry_id'])
    w.save(cid,Entry(kind='finding',title='Edited finding',content='This is an updated observation.',expected_version=2,deleted=True),e['entry_id'])
    assert not w.list(cid)['items']
    events=svc.activity(cid)['items'];assert [x['event_type'] for x in events][-3:]==['FINDING_CREATED','FINDING_UPDATED','FINDING_DELETED']
    assert events[-1]['details']['before']['content']=='This is an updated observation.'

def test_work_event_rollback(investigation,monkeypatch):
    svc,_=investigation;cid=svc.create(**request_for(svc))['case']['case_id']
    from procureiq.investigations import repository
    monkeypatch.setattr(repository,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('failure')))
    with pytest.raises(RuntimeError):CaseWork(svc.engine).save(cid,Entry(kind='note',title='Test note',content='Meaningful observation to be rolled back.'))
    assert not CaseWork(svc.engine).list(cid)['items']

def test_product_api_precision_pagination_validation(investigation):
    svc,root=investigation
    with TestClient(create_app(svc.engine,root=root)) as client:
        r=client.get('/api/v1/spend/summary');assert r.status_code==200,r.text
        assert isinstance(r.json()['overview'][0]['positive_gbp'],str)
        tx=client.get('/api/v1/spend/transactions?limit=2').json();assert len(tx['items'])==2
        assert client.get('/api/v1/spend/transactions?limit=101').status_code==422
        assert client.post('/api/v1/operations/registrations',json={'manifest_name':'../secret.json'}).status_code==422
        assert client.post('/api/v1/operations/runs',json={'operation':'activate','source_file_id':1}).status_code==422
        r=client.post('/api/v1/strategy/optimization/runs',json={'assumptions':model().model_dump(mode='json')});assert r.status_code==201,r.text
        saved=r.json();assert client.get('/api/v1/strategy/optimization/runs/'+str(saved['run_id'])).json()['result']==saved['result']

def test_pipeline_incremental_idempotency_and_retries(investigation):
    svc,root=investigation;p=Pipeline(svc.engine,root)
    import json
    with svc.engine.connect() as c:
        source=c.execute(text('SELECT * FROM procureiq.source_file ORDER BY file_id LIMIT 1')).mappings().one()
    receipt=dict(filename=source['filename'],reporting_month=str(source['reporting_month'])[:7],sha256=source['sha256'],size_bytes=source['size_bytes'],url=source['source_url'],status='verified',downloaded_at=source['acquired_at'].isoformat() if source['acquired_at'] else None)
    (root/'manifests').mkdir(exist_ok=True)
    (root/'manifests/download_manifest.json').write_text(json.dumps([receipt]))
    reg=p.register('download_manifest.json');assert p.register('download_manifest.json')['registration_id']==reg['registration_id']
    run=p.enqueue('ingest',reg['registration_id']);assert p.execute_next()
    with svc.engine.connect() as c:
        assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=run['run_id'])).scalar()=='succeeded'
        before=c.execute(text('SELECT count(*) FROM procureiq.raw_spend_row')).scalar()
    p.enqueue('ingest',reg['registration_id']);p.execute_next()
    with svc.engine.connect() as c:assert c.execute(text('SELECT count(*) FROM procureiq.raw_spend_row')).scalar()==before
    # Controlled receipt tampering fails without a source write; restore bytes then retry.
    path=root/'manifests/download_manifest.json';original=path.read_bytes();path.write_bytes(original+b' ')
    failed=p.enqueue('ingest',reg['registration_id']);p.execute_next();path.write_bytes(original)
    with svc.engine.connect() as c:assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=failed['run_id'])).scalar()=='failed'
    retried=p.retry(failed['run_id']);p.execute_next()
    with svc.engine.connect() as c:assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=retried['run_id'])).scalar()=='succeeded'

def test_milp_minimum_maximum_single_supplier_and_incumbent(monkeypatch):
    m=model();m.candidates[1].minimum=D(55)
    assert D(solve(m)['objective_gbp'])==D(1550)
    m=model();m.candidates[0].maximum=D(20)
    assert D(solve(m)['objective_gbp'])==D(1800)
    m=model();m.candidates=m.candidates[1:]
    assert D(solve(m)['objective_gbp'])==D(2000)
    import numpy as np
    import procureiq.product.optimization as module
    monkeypatch.setattr(module,'milp',lambda *a,**k:SimpleNamespace(status=1,x=np.array([60,40,1,1]),mip_gap=.2))
    r=solve(model());assert r['status']=='feasible_not_proven_optimal' and r['feasible']
    monkeypatch.setattr(module,'milp',lambda *a,**k:SimpleNamespace(status=0,x=np.array([80,20,1,1])))
    assert solve(model())['status']=='failed_validation'

def test_product_scenario_reports_and_quality_contracts(investigation):
    svc,root=investigation
    with TestClient(create_app(svc.engine,root=root)) as c:
        assert c.get('/api/v1/operations/quality?limit=2').status_code==200
        assert c.post('/api/v1/strategy/calculate',json={'baseline':{},'scenarios':{}}).status_code==422
        baseline=c.post('/api/v1/strategy/baseline',json={'kind':'manual','amount':'1000000','start_month':'2025-01-01','end_month':'2025-12-01','scope':'Independent hypothetical model'}).json()
        assumptions=dict(addressable_pct='40',adoption_pct='50',improvement_pct='10',implementation_cost='10000',operating_cost='5000')
        r=c.post('/api/v1/strategy/calculate',json={'baseline':baseline,'scenarios':{n:assumptions for n in ('Conservative','Base','Ambitious')}})
        assert r.status_code==200,r.text
        doc=r.json()['document'];assert doc['outputs']['Base']['net_benefit_gbp']=='5000.00'
        assert c.post('/api/v1/strategy/import',json={'document':doc}).status_code==200
        workbook=c.post('/api/v1/strategy/excel',json={'document':doc});assert workbook.content[:2]==b'PK'
        # Manual scenarios are deliberately incompatible with a database executive brief.
        assert c.post('/api/v1/reports/preview',json={'scenario':doc}).status_code==422
        brief=c.post('/api/v1/reports/preview',json={});assert brief.status_code==200,brief.text
        assert c.post('/api/v1/reports/download/pptx',json={}).content[:2]==b'PK'
        assert c.post('/api/v1/operations/runs',json={'operation':'activate','confirm_activation':True,'source_file_id':999999,'expected_fingerprint':'a'*64}).status_code==422

def test_bookmark_removal_keeps_finding_citations_and_closed_guard(investigation):
    svc,_=investigation;cid=svc.create(**request_for(svc))['case']['case_id'];w=CaseWork(svc.engine)
    w.bookmark(cid,'primary',1,True)
    w.save(cid,Entry(kind='finding',title='Cited observation',content='This remains an analyst interpretation.',citations=[dict(classification='primary',ordinal=1)]))
    w.bookmark(cid,'primary',1,False)
    assert w.bookmarks(cid)['total']==0 and w.list(cid)['items'][0]['citations']
    prior=w.list(cid)['items'][0]
    w.save(cid,Entry(kind='finding',title='Revised cited observation',content='Retain historical citations after bookmark removal.',expected_version=1,citations=prior['citations']),prior['entry_id'])
    with pytest.raises(ValueError):Entry(kind='note',title='Title',content='abc       ')
    for version,status in enumerate(('INVESTIGATING','REVIEWED','CLOSED'),1):
        svc.status(cid,status,version,'Local test lifecycle verification.', 'INSUFFICIENT_EVIDENCE' if status=='CLOSED' else None)
    with pytest.raises(InvestigationError,match='Reopen'):w.save(cid,Entry(kind='note',title='Closed note',content='This write must be rejected.'))

def test_pipeline_revision_activation_stale_guard_and_contract(investigation):
    import json,hashlib
    from procureiq.source_basis import fingerprint
    svc,root=investigation;p=Pipeline(svc.engine,root)
    with svc.engine.connect() as c:
        source=dict(c.execute(text('SELECT * FROM procureiq.source_file ORDER BY file_id LIMIT 1')).mappings().one());basis=fingerprint(c)
    raw=root/'data/raw'/source['filename'];rev=raw.with_name('pipeline_revision.csv')
    rev.write_bytes(raw.read_bytes().replace(b'One',b'Revised One'))
    assert rev.read_bytes()!=raw.read_bytes()
    receipt=dict(filename=rev.name,reporting_month=str(source['reporting_month'])[:7],sha256=hashlib.sha256(rev.read_bytes()).hexdigest(),size_bytes=rev.stat().st_size,url=source['source_url'],status='verified',downloaded_at=source['acquired_at'].isoformat())
    (root/'manifests').mkdir(exist_ok=True);(root/'manifests/revision.json').write_text(json.dumps([receipt]))
    reg=p.register('revision.json');p.enqueue('ingest',reg['registration_id']);p.execute_next()
    with svc.engine.connect() as c:
        version=c.execute(text('SELECT * FROM procureiq.source_file WHERE sha256=:hash'),dict(hash=receipt['sha256'])).mappings().one()
        assert not version['active'] and fingerprint(c)==basis
    stale=p.enqueue('activate',source_file_id=version['file_id'],expected='0'*64);p.execute_next()
    with svc.engine.connect() as c:
        assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=stale['run_id'])).scalar()=='failed'
        assert fingerprint(c)==basis
    p.enqueue('activate',source_file_id=version['file_id'],expected=basis);p.execute_next()
    with svc.engine.connect() as c:
        assert fingerprint(c)!=basis
        assert c.execute(text('SELECT active FROM procureiq.source_file WHERE file_id=:id'),dict(id=version['file_id'])).scalar()
        assert c.execute(text('SELECT count(*) FROM procureiq.raw_spend_row WHERE file_id=:id'),dict(id=source['file_id'])).scalar()>0
    # Hash-correct but missing required column fails before ingestion.
    bad=raw.with_name('bad_contract.csv');bad.write_text('Supplier,Amount\nExample,100\n')
    receipt.update(filename=bad.name,sha256=hashlib.sha256(bad.read_bytes()).hexdigest(),size_bytes=bad.stat().st_size)
    (root/'manifests/bad.json').write_text(json.dumps([receipt]));reg=p.register('bad.json');r=p.enqueue('ingest',reg['registration_id']);p.execute_next()
    with svc.engine.connect() as c:
        assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=r['run_id'])).scalar()=='failed'
        assert not c.execute(text('SELECT 1 FROM procureiq.source_file WHERE sha256=:hash'),dict(hash=receipt['sha256'])).scalar()

def test_pipeline_worker_recovers_orphan_and_queue_limit(investigation,monkeypatch):
    svc,root=investigation;p=Pipeline(svc.engine,root)
    orphan=p.enqueue('verify')
    with svc.engine.begin() as c:
        c.execute(text("UPDATE procureiq_app.pipeline_run SET status='running' WHERE run_id=:id"),dict(id=orphan['run_id']))
        c.execute(text("INSERT INTO procureiq_app.pipeline_stage(run_id,name,status) VALUES(:id,'simulated_interruption','running')"),dict(id=orphan['run_id']))
    def finish():p.stop.set();return False
    monkeypatch.setattr(p,'execute_next',finish);p.loop()
    with svc.engine.connect() as c:
        assert c.execute(text('SELECT status FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=orphan['run_id'])).scalar()=='interrupted'
        assert c.execute(text('SELECT status FROM procureiq_app.pipeline_stage WHERE run_id=:id'),dict(id=orphan['run_id'])).scalar()=='interrupted'
    for _ in range(8):p.enqueue('verify')
    with pytest.raises(InvestigationError,match='full'):p.enqueue('verify')
