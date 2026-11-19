"""Investigation V1: guarded PostgreSQL, independent lifecycle and HTTP acceptance."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Lock
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import json
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_database import db,ROOT
from test_opportunities import radar_data,write_source
from procureiq.ingestion import load,activate
from procureiq.source_basis import fingerprint
from procureiq.opportunity_data import retrieve
from procureiq.opportunities import detect,canonical
from procureiq.opportunity_model import OpportunityConfig
from procureiq.investigations.migrations import initialize_app
from procureiq.investigations.service import InvestigationService
from procureiq.investigations.domain import InvestigationError
from procureiq.investigations import repository as repo
from procureiq.api.app import create_app


@pytest.fixture
def investigation(radar_data):
    engine,root,_=radar_data
    initialize_app(engine,ROOT)
    return InvestigationService(engine),root


def request_for(svc,filters=None):
    r=svc.reviews(filters)
    return dict(review_id=r['items'][0]['opportunity_id'],filters=filters or {},basis_token=r['basis_token'],
                title='Synthetic investigation',objective='Validate synthetic source evidence and contract assumptions.')


def count(svc,table):
    with svc.engine.connect() as c:return c.execute(text('SELECT count(*) FROM procureiq_app.'+table)).scalar_one()


def test_app_migrations_reruns_checksums_and_source_preservation(db,tmp_path):
    with db.connect() as conn:before=fingerprint(conn)
    initialize_app(db,ROOT);initialize_app(db,ROOT)
    with db.connect() as conn:
        assert fingerprint(conn)==before
        assert conn.execute(text('SELECT count(*) FROM procureiq_app.schema_migration')).scalar()==len(list((ROOT/'sql/app').glob('[0-9]*.sql')))
        assert conn.execute(text('SELECT count(*) FROM procureiq.schema_migration')).scalar()==3
    (tmp_path/'sql/app').mkdir(parents=True)
    (tmp_path/'sql/app/001_investigations.sql').write_text('SELECT 1;')
    with pytest.raises(ValueError,match='changed'):initialize_app(db,tmp_path)


def test_create_dedupe_snapshot_counts_and_database_constraints(investigation):
    s,_=investigation;req=request_for(s)
    with s.engine.connect() as c:before=fingerprint(c)
    a=s.create(**req);b=s.create(**dict(req,title='Replacement title'))
    assert a['created'] and not b['created']
    assert a['case']['case_id']==b['case']['case_id']
    assert b['case']['title']=='Synthetic investigation' and b['case']['status']=='OPEN'
    assert b['case']['case_reference'].startswith('PIQ-')
    cid=a['case']['case_id']
    assert count(s,'investigation_case')==1 and count(s,'case_event')==1
    event=s.activity(cid)['items'][0]
    assert event['event_type']=='CASE_CREATED' and event['actor']=='local_application' and event['new_status']=='OPEN'
    assert s.reviews()['items'][0]['existing_case']['case_id']==cid
    assert s.evidence(cid)['total']==a['case']['primary_count']
    with s.engine.connect() as c:assert fingerprint(c)==before
    for sql in ["UPDATE procureiq_app.case_event SET reason='altered'", "DELETE FROM procureiq_app.case_event", "DELETE FROM procureiq_app.case_evidence", "UPDATE procureiq_app.investigation_case SET original_score=1", "UPDATE procureiq_app.investigation_case SET status='INVALID'"]:
        with pytest.raises(DBAPIError),s.engine.begin() as c:c.exec_driver_sql(sql)
    # INSERT directly proves uniqueness independently of service check paths.
    with pytest.raises(DBAPIError),s.engine.begin() as c:
        c.exec_driver_sql('''INSERT INTO procureiq_app.investigation_case (title,objective,opportunity_id,opportunity_type,original_score,
          review_snapshot,rule_version,configuration,configuration_identity,reporting_filters,source_fingerprint,review_basis_key,primary_count,contextual_count)
          SELECT title,objective,opportunity_id,opportunity_type,original_score,review_snapshot,rule_version,configuration,
          configuration_identity,reporting_filters,source_fingerprint,review_basis_key,primary_count,contextual_count FROM procureiq_app.investigation_case''')


def test_concurrent_create_and_status(investigation,monkeypatch):
    s,_=investigation;req=request_for(s)
    original=repo.insert_case;barrier=Barrier(2);guard=Lock();attempts=0
    def simultaneous_insert(*args,**kwargs):
        nonlocal attempts
        with guard:
            attempts+=1
            wait=attempts<=2
        if wait:barrier.wait(timeout=10)
        return original(*args,**kwargs)
    monkeypatch.setattr(repo,'insert_case',simultaneous_insert)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:s.create(**req),range(2)))
    assert sum(r['created'] for r in results)==1
    assert count(s,'investigation_case')==1 and count(s,'case_event')==1
    cid=results[0]['case']['case_id']
    def update(_):
        try:return s.status(cid,'INVESTIGATING',1)
        except InvestigationError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(update,range(2)))
    assert sum(isinstance(r,dict) for r in results)==1
    assert 'case_version_conflict' in results and s.activity(cid)['total']==2


def test_creation_and_event_failures_rollback(investigation,monkeypatch):
    s,_=investigation;req=request_for(s)
    original=repo.insert_evidence
    def fail(conn,cid,item):
        original(conn,cid,item)
        raise RuntimeError('synthetic insertion failure')
    monkeypatch.setattr(repo,'insert_evidence',fail)
    with pytest.raises(RuntimeError):s.create(**req)
    assert all(count(s,t)==0 for t in ('investigation_case','case_evidence','case_event'))
    monkeypatch.setattr(repo,'insert_evidence',original)
    case=s.create(**req)['case']
    def fail_event(*args,**kwargs):raise RuntimeError('synthetic event failure')
    monkeypatch.setattr(repo,'event',fail_event)
    with pytest.raises(RuntimeError):s.status(case['case_id'],'INVESTIGATING',1)
    assert s.get(case['case_id'])['status']=='OPEN' and s.activity(case['case_id'])['total']==1


def test_server_evidence_validation_rollback(investigation,monkeypatch):
    import procureiq.investigations.service as module
    s,_=investigation;req=request_for(s);original=module.resolve
    def forged(*args):
        result,basis,token=original(*args)
        item=next(o for o in result['opportunities'] if o['opportunity_id']==req['review_id'])
        item['source_references'][0]['sha256']='f'*64
        return result,basis,token
    monkeypatch.setattr(module,'resolve',forged)
    with pytest.raises(InvestigationError,match='lineage'):s.create(**req)
    assert count(s,'investigation_case')==0


def test_stale_unknown_deferred_and_policy_basis(investigation):
    s,_=investigation;req=request_for(s)
    with pytest.raises(InvestigationError) as e:s.create(**dict(req,basis_token='f'*64))
    assert e.value.code=='stale_review_basis'
    with pytest.raises(InvestigationError) as e:s.create(**dict(req,review_id='opp_'+'0'*24))
    assert e.value.code=='review_not_found'
    capped=InvestigationService(s.engine,replace(s.config,max_per_type=1))
    with pytest.raises(InvestigationError) as e:capped.create(**req)
    assert e.value.code=='stale_review_basis'
    with s.read() as c:result=detect(retrieve(c),capped.config)
    deferred=next(r['opportunity_id'] for r in result['rejections'] if r.get('reason')=='output_cap_after_scoring')
    req2=request_for(capped)
    with pytest.raises(InvestigationError) as e:capped.create(**dict(req2,review_id=deferred))
    assert e.value.code=='review_not_eligible'
    first=s.create(**req)['case'];second=capped.create(**req2)['case']
    assert first['review_basis_key']!=second['review_basis_key']
    assert count(s,'investigation_case')==2


def test_workflow_close_reopen_and_history(investigation):
    s,_=investigation;req=request_for(s);c=s.create(**req)['case'];cid=c['case_id']
    for status in ('REVIEWED','CLOSED','OPEN','INVALID'):
        with pytest.raises(InvestigationError):s.status(cid,status,1)
    c=s.status(cid,'INVESTIGATING',1);assert c['row_version']==2
    c=s.status(cid,'REVIEWED',2);assert c['reviewed_at']
    for reason,disposition in [(None,None),('too short','NO_ACTIONABLE_FINDING'),('............','NO_ACTIONABLE_FINDING'),('Meaningful explanation','MADE_UP')]:
        with pytest.raises(InvestigationError):s.status(cid,'CLOSED',3,reason,disposition)
    c=s.status(cid,'CLOSED',3,'Synthetic review has insufficient contractual evidence.','INSUFFICIENT_EVIDENCE')
    assert c['closed_at'] and c['disposition']=='INSUFFICIENT_EVIDENCE'
    assert s.create(**req)['case']['status']=='CLOSED'
    assert s.get(cid)['status']=='CLOSED' and s.activity(cid)['total']==4
    with pytest.raises(InvestigationError):s.status(cid,'INVESTIGATING',4)
    c=s.status(cid,'INVESTIGATING',4,'Additional supporting invoices have become available.')
    assert c['status']=='INVESTIGATING' and c['closed_at'] is None and c['disposition'] is None
    events=s.activity(cid)['items']
    assert [x['new_status'] for x in events]==['OPEN','INVESTIGATING','REVIEWED','CLOSED','INVESTIGATING']
    assert events[-1]['details']['previous_disposition']=='INSUFFICIENT_EVIDENCE'


def test_historical_sources_paging_and_integrity(investigation):
    s,root=investigation;req=request_for(s);case=s.create(**req)['case'];cid=case['case_id']
    before=s.evidence(cid,limit=100)
    assert len({(x['file_sha256'],x['source_record_number']) for x in before['items']})==len(before['items'])
    with s.engine.connect() as c:
        sha=c.execute(text("SELECT sha256 FROM procureiq.source_file WHERE filename='inactive.csv'")).scalar_one()
    activate(s.engine,root,'2025-04',sha)
    historical=s.evidence(cid,limit=100)
    assert not historical['basis_matches_current_source']
    assert [r['source_values'] for r in historical['items']]==[r['source_values'] for r in before['items']]
    assert s.get(cid)['original_score']==case['original_score']
    with pytest.raises(InvestigationError):s.create(**req)
    new=s.create(**request_for(s))['case'];assert new['case_id']!=cid
    # Missing historical source simulation only in the guarded test database.
    # Remove the test FK and disable the application immutability trigger to emulate external corruption.
    with s.engine.begin() as c:
        c.exec_driver_sql('ALTER TABLE procureiq_app.case_evidence DROP CONSTRAINT case_evidence_raw_row_id_fkey')
        c.exec_driver_sql('ALTER TABLE procureiq_app.case_evidence DISABLE TRIGGER immutable_case_evidence')
        c.execute(text('UPDATE procureiq_app.case_evidence SET raw_row_id=999999999 WHERE case_id=:id AND ordinal=1'),dict(id=cid))
    with pytest.raises(InvestigationError) as e:s.evidence(cid)
    assert e.value.code=='evidence_integrity'


def test_contextual_evidence_and_bounded_pages(investigation):
    s,root=investigation
    write_source(s.engine,root,'2025-11',[('QualityOther','Alias Ltd','20000','North','extra')])
    reviews=s.reviews(kind='data_quality')['items']
    item=next(x for x in reviews if x['contextual_count']>0)
    req=request_for(s);req['review_id']=item['opportunity_id']
    c=s.create(**req)['case'];cid=c['case_id']
    for kind,key in [('primary','primary_count'),('contextual','contextual_count')]:
        records=[]
        for offset in range(0,c[key],2):records+=s.evidence(cid,kind,offset,2)['items']
        assert [r['ordinal'] for r in records]==list(range(1,c[key]+1))
        assert len({r['raw_row_id'] for r in records})==c[key]
    assert s.activity(cid,0,1)['total']==1
    with pytest.raises(InvestigationError):s.evidence(cid,limit=101)


def test_http_contract_cors_errors_and_serialization(investigation):
    s,_=investigation
    with TestClient(create_app(s.engine),raise_server_exceptions=False) as client:
        assert client.get('/api/v1/health').status_code==200
        assert client.get('/docs').status_code==200 and client.get('/openapi.json').status_code==200
        response=client.get('/api/v1/investigations/reviews');assert response.status_code==200,response.text
        data=response.json();assert isinstance(data['items'][0]['priority_score'],str)
        req=request_for(s)
        a=client.post('/api/v1/investigations/cases',json=req);assert a.status_code==201,a.text
        case=a.json()['case'];cid=case['case_id']
        assert client.post('/api/v1/investigations/cases',json=req).status_code==200
        assert client.post('/api/v1/investigations/cases',json=dict(req,source_references=[])).status_code==422
        assert client.post('/api/v1/investigations/cases',json=dict(req,basis_token='f'*64)).status_code==409
        assert client.post('/api/v1/investigations/cases',json=dict(req,review_id='opp_'+'0'*24)).status_code==404
        for route in ['cases','reviews']:
            assert client.get('/api/v1/investigations/'+route,params={'limit':101}).status_code==422
        assert client.get('/api/v1/investigations/cases/999999').status_code==404
        assert client.get('/api/v1/investigations/cases',params={'status':'WRONG'}).status_code==422
        assert client.get('/api/v1/investigations/reviews',params={'start_month':'2025-99'}).status_code==422
        filtered=client.get('/api/v1/investigations/reviews',params={'detector_type':'supplier_concentration','minimum_priority':'0','expense_type':'Recurring'})
        assert filtered.status_code==200,filtered.text
        assert all(x['opportunity_type']=='supplier_concentration' for x in filtered.json()['items'])
        assert client.get('/api/v1/investigations/reviews',params={'expense_type':"x'; DROP TABLE source_file;--"}).json()['total']==0
        detail=client.get('/api/v1/investigations/reviews/'+req['review_id']);assert detail.status_code==200
        assert 'source_references' not in detail.json()['items'][0]
        ev=client.get(f'/api/v1/investigations/cases/{cid}/evidence',params={'limit':2});assert len(ev.json()['items'])<=2
        bad=client.patch(f'/api/v1/investigations/cases/{cid}/status',json={'status':'CLOSED','expected_version':1});assert bad.status_code==409
        good=client.patch(f'/api/v1/investigations/cases/{cid}/status',json={'status':'INVESTIGATING','expected_version':1});assert good.status_code==200
        assert client.patch(f'/api/v1/investigations/cases/{cid}/status',json={'status':'REVIEWED','expected_version':1}).status_code==409
        assert client.get(f'/api/v1/investigations/cases/{cid}/activity').json()['total']==2
        assert client.options('/api/v1/investigations/cases',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'}).headers['access-control-allow-origin']=='http://localhost:5173'
        denied=client.options('/api/v1/investigations/cases',headers={'Origin':'https://untrusted.invalid','Access-Control-Request-Method':'POST'})
        assert denied.status_code==400 and 'access-control-allow-origin' not in denied.headers
        assert client.post('/api/v1/investigations/cases',content=b'x'*17000).status_code==413


def test_sanitized_service_failure(db,monkeypatch):
    initialize_app(db,ROOT)
    with TestClient(create_app(db),raise_server_exceptions=False) as client:
        def fail():raise DBAPIError('secret_sql',{},RuntimeError('secret_password postgres://private'),False)
        monkeypatch.setattr(client.app.state.service,'health',fail)
        result=client.get('/api/v1/health')
        assert result.status_code==503 and 'secret' not in result.text and 'postgres://' not in result.text


def test_actual_6497_evidence_snapshot_and_regressions(db):
    load(db,ROOT)
    with db.connect() as c:before=fingerprint(c)
    initialize_app(db,ROOT);s=InvestigationService(db)
    reviews=s.reviews();assert (reviews['qualified_count'],reviews['exported_count'],reviews['deferred_count'])==(112,34,78)
    req=request_for(s);case=s.create(**req)['case'];cid=case['case_id']
    assert case['primary_count']==6497
    seen=[]
    for offset in range(0,6497,100):
        page=s.evidence(cid,offset=offset,limit=100)
        assert len(page['items'])<=100 and page['total']==6497
        seen.extend(r['raw_row_id'] for r in page['items'])
    assert len(seen)==len(set(seen))==6497
    with TestClient(create_app(db)) as client:
        payload=client.get(f'/api/v1/investigations/cases/{cid}/evidence').json()
        assert len(payload['items'])==50 and payload['total']==6497
    with db.connect() as c:
        assert fingerprint(c)==before
        from procureiq.queries import query
        row=query(c,'overview')[0]
        assert (row['record_count'],row['supplier_count'])==(12973,456)
        assert (row['positive_gbp'],row['credit_gbp'],row['net_gbp'])==(D('2499145830.48'),D('30802967.80'),D('2468342862.68'))
    assert s.reviews()['items'][0]['priority_score']==reviews['items'][0]['priority_score']


def test_source_activation_cannot_interleave_with_creation(investigation,monkeypatch):
    s,_=investigation;req=request_for(s);original=repo.insert_evidence
    def locked(conn,cid,item):
        # Separate transaction cannot change source selection until creation commits.
        with pytest.raises(DBAPIError) as error,s.engine.begin() as other:
            other.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
            other.exec_driver_sql('UPDATE procureiq.source_file SET active=active')
        assert getattr(error.value.orig,'sqlstate',None)=='55P03'
        original(conn,cid,item)
    monkeypatch.setattr(repo,'insert_evidence',locked)
    created=s.create(**req)
    assert created['case']['basis_matches_current_source']


def test_exact_filters_case_pagination_and_unknown_http_fields(investigation):
    s,_=investigation
    one=s.create(**request_for(s))['case']
    two=s.create(**request_for(s,{'expense_type':'Recurring'}))['case']
    assert one['review_basis_key']!=two['review_basis_key']
    assert s.cases(limit=1)['items'][0]['case_id']==one['case_id']
    assert s.cases(offset=1,limit=1)['items'][0]['case_id']==two['case_id']
    s.status(one['case_id'],'INVESTIGATING',1)
    assert s.cases(status='OPEN')['total']==1
    with TestClient(create_app(s.engine)) as client:
        assert client.get('/api/v1/investigations/reviews',params={'expense_typo':'Recurring'}).status_code==422
        assert client.get('/api/v1/investigations/reviews',params={'expense_type':' Recurring '}).json()['total']==0
        bounded=client.get('/api/v1/investigations/reviews',params={'start_month':'2025-04','end_month':'2025-10'}).json()
        echoed=dict(request_for(s),review_id=bounded['items'][0]['opportunity_id'],basis_token=bounded['basis_token'],filters=bounded['basis']['filters'])
        assert echoed['filters']['start_month']=='2025-04-01'
        created=client.post('/api/v1/investigations/cases',json=echoed)
        assert created.status_code==201,created.text
        assert client.post('/api/v1/investigations/cases',json=echoed).status_code==200
        assert client.post('/api/v1/investigations/cases',json=dict(request_for(s),priority_score='100')).status_code==422
        assert client.patch(f"/api/v1/investigations/cases/{one['case_id']}/status",json={'status':'REVIEWED','expected_version':True}).status_code==422
