"""Namespace isolation and historical exploration use the guarded test DB."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from decimal import Decimal
import shutil
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from test_database import db, ROOT
from test_opportunities import radar_data
from test_investigations import investigation, request_for
from procureiq.investigations.namespace import current_namespace
from procureiq.investigations.migrations import initialize_app
from procureiq.investigations.service import InvestigationService
from procureiq.investigations.work import CaseWork
from procureiq.api.work_routes import Entry
from procureiq.api.app import create_app
from procureiq.investigations.domain import InvestigationError

@contextmanager
def mode(name):
    token=current_namespace.set(name)
    try:yield
    finally:current_namespace.reset(token)

def test_namespaces_coexist_and_independently_deduplicate(investigation):
    svc,_=investigation;req=request_for(svc)
    normal=svc.create(**req)['case']
    with mode('DEMO'):
        assert svc.cases()['total']==0
        assert not svc.reviews()['items'][0]['existing_case']
        demo=svc.create(**req)['case']
        assert not svc.create(**req)['created']
        assert svc.cases()['total']==1
        assert svc.reviews()['items'][0]['existing_case']['case_id']==demo['case_id']
        with pytest.raises(InvestigationError,match='other workspace'):svc.get(normal['case_id'])
        with pytest.raises(InvestigationError):CaseWork(svc.engine).bookmark(normal['case_id'],'primary',1,True)
    assert demo['case_id']!=normal['case_id']
    assert svc.cases()['total']==1
    assert not svc.create(**req)['created']
    with pytest.raises(InvestigationError):svc.evidence(demo['case_id'])

def test_demo_concurrent_creation(investigation):
    svc,_=investigation;req=request_for(svc)
    def create(_):
        with mode('DEMO'):return svc.create(**req)
    with ThreadPoolExecutor(max_workers=2) as p:results=list(p.map(create,range(2)))
    assert sum(r['created'] for r in results)==1
    assert results[0]['case']['case_id']==results[1]['case']['case_id']
    assert svc.create(**req)['created']

def test_legacy_demo_migration_preserves_every_relationship(radar_data,tmp_path):
    engine,_,_=radar_data
    old=tmp_path/'sql/app';old.mkdir(parents=True)
    for p in (ROOT/'sql/app').glob('00[123]_*.sql'):shutil.copy(p,old/p.name)
    initialize_app(engine,tmp_path)
    # Populate the pre-namespace schema through SQL, preserving a real frozen basis.
    with engine.begin() as c:
        c.execute(text("""INSERT INTO procureiq_app.investigation_case(title,objective,opportunity_id,opportunity_type,original_score,review_snapshot,rule_version,configuration,configuration_identity,reporting_filters,source_fingerprint,review_basis_key,primary_count,contextual_count)
        VALUES('[LOCAL DEMO] migration fixture','Original objective stays exactly the same','opp_fixture','data_quality',50,'{}','v1','{}',:hash,'{}',:hash,:hash,0,0)"""),dict(hash='a'*64))
        c.execute(text("INSERT INTO procureiq_app.case_event(case_id,event_type,new_status,details) VALUES(1,'CASE_CREATED','OPEN','{}')"))
        before=dict(c.execute(text('SELECT * FROM procureiq_app.investigation_case')).mappings().one())
        events=[dict(r) for r in c.execute(text('SELECT * FROM procureiq_app.case_event')).mappings()]
    initialize_app(engine,ROOT);initialize_app(engine,ROOT)
    with engine.connect() as c:
        after=dict(c.execute(text('SELECT * FROM procureiq_app.investigation_case')).mappings().one())
        assert after.pop('namespace')=='DEMO';assert after==before
        assert [dict(r) for r in c.execute(text('SELECT * FROM procureiq_app.case_event')).mappings()]==events

def test_historical_filters_counts_summary_and_navigation(investigation):
    svc,_=investigation;cid=svc.create(**request_for(svc))['case']['case_id']
    allrows=[]
    for offset in range(0,svc.evidence(cid)['total'],100):allrows+=svc.evidence(cid,offset=offset,limit=100)['items']
    first=allrows[0];supplier=first['source_values']['Supplier']
    expected=[r for r in allrows if r['source_values']['Supplier']==supplier]
    filtered=svc.evidence(cid,filters=dict(supplier=supplier),limit=1)
    assert filtered['total']==len(expected)
    assert filtered['summary']['composition']['positive_gbp']==sum(max(r['amount_gbp'] or Decimal(0),Decimal(0)) for r in expected)
    for i,r in enumerate(expected[:4]):assert svc.evidence(cid,offset=i,limit=1,filters=dict(supplier=supplier))['items'][0]['raw_row_id']==r['raw_row_id']
    assert svc.evidence(cid,filters=dict(search="' OR 1=1 --"))['total']==0
    amount=first['amount_gbp'];assert all(r['amount_gbp']>=amount for r in svc.evidence(cid,filters=dict(minimum_amount=amount))['items'])
    w=CaseWork(svc.engine);w.bookmark(cid,'primary',first['ordinal'],True)
    assert svc.evidence(cid,limit=1)['items'][0]['bookmarked']
    entry=w.save(cid,Entry(kind='finding',title='Preliminary observation',content='Original observation preserved.',sections=dict(assessment='',next_step='Review contract terms.'),citations=[dict(classification='primary',ordinal=first['ordinal'])]))
    assert entry['sections']['next_step']=='Review contract terms.'
    assert w.bookmarks(cid)['items'][0]['source_values']==first['source_values']

def test_http_mode_and_quality_pagination(investigation):
    svc,root=investigation;req=request_for(svc)
    with TestClient(create_app(svc.engine,root=root,workers=False)) as client:
        a=client.post('/api/v1/investigations/cases',json=req).json()['case']
        demo={'X-Investigation-Namespace':'DEMO'}
        b=client.post('/api/v1/investigations/cases',json=req,headers=demo).json()['case']
        assert a['case_id']!=b['case_id']
        assert client.get(f"/api/v1/investigations/cases/{b['case_id']}").status_code==409
        assert client.get('/api/v1/command',headers=demo).json()['case_counts']=={'OPEN':1}
        assert client.post('/api/v1/reports/preview',json={'case_ids':[b['case_id']]}).status_code==409
        q=client.get('/api/v1/operations/quality?limit=1').json()
        seen=[]
        for i in range(q['total']):seen.extend(x['issue_id'] for x in client.get(f'/api/v1/operations/quality?limit=1&offset={i}').json()['items'])
        assert len(set(seen))==q['total']
        assert sum(g['count'] for g in q['groups'])==q['all_total']
        assert client.get('/api/v1/operations/quality?search=not-a-real-issue').json()['total']==0

def test_filtered_history_survives_activation(investigation):
    from procureiq.ingestion import activate
    svc,root=investigation;case=svc.create(**request_for(svc))['case'];cid=case['case_id']
    first=svc.evidence(cid)['items'][0];filters={'supplier':first['source_values']['Supplier']}
    before=svc.evidence(cid,filters=filters)
    with svc.engine.connect() as c:sha=c.execute(text("SELECT sha256 FROM procureiq.source_file WHERE filename='inactive.csv'")).scalar_one()
    activate(svc.engine,root,'2025-04',sha)
    after=svc.evidence(cid,filters=filters)
    assert before['summary']==after['summary'] and before['total']==after['total']
    assert [(r['raw_row_id'],r['file_sha256'],r['source_values']) for r in before['items']]==[(r['raw_row_id'],r['file_sha256'],r['source_values']) for r in after['items']]
    assert not after['basis_matches_current_source']

def test_report_dynamic_slides_and_stale_content_guard(investigation):
    svc,root=investigation;case=svc.create(**request_for(svc))['case'];cid=case['case_id']
    with TestClient(create_app(svc.engine,root=root,workers=False)) as client:
        body={'case_ids':[cid]}
        preview=client.post('/api/v1/reports/preview',json=body);assert preview.status_code==200,preview.text
        data=preview.json();assert len(data['presentation']['slides'])==5
        assert all(slide['shapes'] for slide in data['presentation']['slides'])
        pinned=body|{'expected_content_hash':data['brief']['content_hash']}
        deck=client.post('/api/v1/reports/download/pptx',json=pinned);assert deck.status_code==200
        from io import BytesIO
        from pptx import Presentation
        prs=Presentation(BytesIO(deck.content));assert len(prs.slides)==5
        assert data['presentation']['slides'][0]['shapes'][0]['text']==prs.slides[0].shapes[0].text
        CaseWork(svc.engine).save(cid,Entry(kind='finding',title='New observation',content='Changed report content requires another preview.'))
        assert client.post('/api/v1/reports/download/pptx',json=pinned).status_code==409
        excluded=client.post('/api/v1/reports/preview',json=body|{'include_insights':False,'include_recommendations':False,'include_findings':False}).json()
        assert excluded['brief']['findings']==[] and excluded['brief']['recommendations']==[]
        assert excluded['brief']['investigation_context'][0]['findings']==[]
