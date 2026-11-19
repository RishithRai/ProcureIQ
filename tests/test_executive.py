"""Independent selection fixtures and real PostgreSQL/UI/presentation acceptance."""
from copy import deepcopy
from decimal import Decimal as D
from io import BytesIO
import json
import pytest
from pptx import Presentation
from streamlit.testing.v1 import AppTest
from test_database import db,ROOT
from test_opportunities import write_source,radar_data
from procureiq.ingestion import load
from procureiq.executive import recommend,compatible_scenario,THEMES,export_default
from procureiq.executive_presentation import presentation_bytes,TITLES
from procureiq.ui.service import DashboardService,SourceChanged
from procureiq.scenario_basis import database_baseline,manual_baseline
from procureiq.scenario_io import document,export_json,load_json
from procureiq.financial_model import illustrative


def candidate(ident,kind,score,amount,refs):
    return dict(opportunity_id=ident,opportunity_type=kind,scoring={'priority_score':D(score)},positive_exposure_gbp=D(amount),
        scope={'expense_type':ident},evidence_summary='Observed fixture',metrics={'count':len(refs)},
        source_references=[dict(sha256='a'*64,source_record_number=r) for r in refs],context_source_references=[],
        exposure_definition='Distinct positive rows',business_interpretation='Review this evidence',caveats=['No savings claim'])


def test_selection_diversity_overlap_and_order():
    items=[candidate('f','purchasing_fragmentation','99','1000',[1,2,3]),
           candidate('f2','purchasing_fragmentation','98','2000',[7]),
           candidate('c','supplier_concentration','97','500',[1,2,3]),
           candidate('c2','supplier_concentration','96','400',[4,5]),
           candidate('p','payment_pattern','90','300',[1,2,3]),
           candidate('q','data_quality','70','100',[3,4])]
    out=recommend(items)
    assert [r['opportunity_ids'][0] for r in out]==['f','c2','p','q']
    assert len({r['opportunity_type'] for r in out})==4
    assert out[0]['priority_score']==99
    assert out[0]['overlaps'][0]==dict(opportunity_id='p',shared_primary_rows=3)
    assert recommend(list(reversed(items)))==out
    assert len({r['reference'] for r in out})==4
    assert out[0]['source_references']==items[0]['source_references']
    assert all(r['recommended_action'] and r['evidence_required'] and r['caveats'] for r in out)
    assert recommend([])==[]


def test_materiality_and_identifier_break_ties():
    items=[candidate('z','data_quality','50','10',[1]),candidate('b','data_quality','50','20',[2]),candidate('a','data_quality','50','20',[3])]
    assert recommend(items)[0]['opportunity_ids']==['a']


def test_service_filters_empty_and_source_change(db,tmp_path):
    write_source(db,tmp_path,'2025-04',[('Type','A','1000','Area','a'),('Other','B','250','Else','b'),('Type','A','-50','Area','c')])
    s=DashboardService(db);v=s.version()
    b=s.executive({'expense_type':'Type'},v)
    assert b['overview']['positive_gbp']==1000 and b['overview']['net_gbp']==950
    assert b['overview']['credit_gbp']==50 and b['overview']['record_count']==2
    assert b['counts']==dict(qualified=0,exported=0,deferred=0)
    assert b['recommendations']==[]
    empty=s.executive({'expense_type':'Missing'},v)
    assert empty['overview']['record_count']==0 and empty['findings']==[]
    assert len(Presentation(BytesIO(presentation_bytes(empty))).slides)==5
    write_source(db,tmp_path,'2025-05',[('Type','A','100','Area','d')])
    with pytest.raises(SourceChanged):s.executive({},v)


def test_scenario_scope_and_stale_rejection(db,tmp_path):
    write_source(db,tmp_path,'2025-04',[('Type','A','1000','Area','a'),('Other','B','250','Else','b')])
    s=DashboardService(db);v=s.version();brief=s.executive({},v)
    doc=document(database_baseline(s,{},v,category='Type'),illustrative())
    assert compatible_scenario(s,brief,doc)['outputs']['Base']['net_benefit_gbp']==D('-149998.00')
    with pytest.raises(ValueError,match='category'):compatible_scenario(s,s.executive({'expense_type':'Other'},v),doc)
    with pytest.raises(ValueError,match='filters'):compatible_scenario(s,s.executive({'expense_area':'Else'},v),doc)
    manual=document(manual_baseline('1000','2025-04-01','2025-04-01','Manual'),illustrative())
    with pytest.raises(ValueError):compatible_scenario(s,brief,manual)
    stale=deepcopy(doc);stale['baseline']['source_fingerprint']='f'*64
    with pytest.raises(ValueError,match='stale'):compatible_scenario(s,brief,stale)
    with pytest.raises(ValueError):presentation_bytes(brief,stale)
    forged=deepcopy(doc);forged['baseline']['scope']='Changed'
    with pytest.raises(ValueError,match='evidence'):compatible_scenario(s,brief,forged)
    changed=deepcopy(doc);changed['outputs']['Base']['net_benefit_gbp']='999999'
    with pytest.raises(ValueError):compatible_scenario(s,brief,changed)


def slide_text(slide):
    chunks=[]
    for shape in slide.shapes:
        if shape.has_text_frame:chunks.append(shape.text)
        if shape.has_table:chunks.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return '\n'.join(chunks)


def test_actual_default_deck_and_evidence(db,tmp_path):
    load(db,ROOT);s=DashboardService(db);v=s.version();b=s.executive({},v)
    assert b['overview']['positive_gbp']==D('2499145830.48')
    assert b['overview']['credit_gbp']==D('30802967.80')
    assert b['overview']['net_gbp']==D('2468342862.68')
    assert b['overview']['record_count']==12973 and b['overview']['supplier_count']==456
    assert b['counts']==dict(qualified=112,exported=34,deferred=78)
    assert len(b['recommendations'])==4
    assert set(r['opportunity_type'] for r in b['recommendations'])==set(THEMES)
    assert b['analytics']['suppliers'][0]['positive_gbp']==D('410066806.54')
    for r in b['recommendations']:
        evidence=s.evidence({},v,r['opportunity_ids'][0])
        assert evidence['total']==len(r['source_references'])
        assert evidence['rows'][0]['sha256']==r['source_references'][0]['sha256']
    result=export_default(s,tmp_path)
    deck=Presentation(result['presentation']);assert len(deck.slides)==5
    assert round(deck.slide_width/deck.slide_height,5)==round(16/9,5)
    texts=[slide_text(x) for x in deck.slides]
    assert all(t.startswith(title) for t,title in zip(texts,TITLES))
    assert all('Apr 2025 – Mar 2026' in t and 'HMRC spending-over-£25,000' in t for t in texts)
    assert '£2,499,145,830.48' in texts[0] and '12,973' in texts[0]
    assert '112 qualified' in texts[2] and '34 exported' in texts[2] and '78 deferred' in texts[2]
    for value in ['£721,458,382.18','20% / 25% / 1%','20% / 50% / 2%','20% / 75% / 3%','£100,000.00','£50,000.00','£210,729.19','£1,292,916.76','£3,096,562.72']:
        assert value in texts[3]
    assert 'not predicted or realized savings' in texts[3]
    assert sum(shape.has_chart for shape in deck.slides[1].shapes)==2
    frozen=json.load(open(result['evidence']));assert frozen['brief']['source_fingerprint']==v
    # Contextual export must not silently insert the default illustration.
    filtered=s.executive({'expense_type':'Physical Hosting and Infrastructure'},v)
    context=Presentation(BytesIO(presentation_bytes(filtered)))
    assert '£73,702,602.00' in slide_text(context.slides[0])
    assert 'No matching scenario' in slide_text(context.slides[3])
    assert '£1,292,916.76' not in slide_text(context.slides[3])


def test_brief_apptest_navigation_and_explicit_scenario(db,tmp_path,monkeypatch):
    write_source(db,tmp_path,'2025-04',[('Type','A','1000000','Area','a'),('Other','B','200','Else','b')])
    monkeypatch.setenv('DATABASE_URL',db.url.render_as_string(hide_password=False))
    at=AppTest.from_file(str(ROOT/'src/procureiq/ui/app.py'),default_timeout=40).run()
    at.radio(key='navigation').set_value('Executive Brief').run()
    assert not at.exception and not at.error
    assert any('No valid matching scenario' in x.value for x in at.info)
    at.radio(key='navigation').set_value('Financial Scenario Lab').run()
    next(b for b in at.button if b.label=='Use selected baseline').click().run()
    next(b for b in at.button if b.label.startswith('Load illustrative')).click().run()
    at.radio(key='navigation').set_value('Executive Brief').run()
    assert len(at.checkbox)==1 and not at.checkbox[0].value
    at.checkbox[0].check().run();assert any('Hypothetical financial illustration' in w.value for w in at.warning)
    next(b for b in at.button if b.label=='Prepare executive PowerPoint').click().run()
    assert not at.exception and not at.error
    at.selectbox(key='filter_expense_type').set_value('Other').run()
    assert not any(c.value for c in at.checkbox)
    assert any('filters' in w.value or 'category' in w.value for w in at.warning)
    at.radio(key='navigation').set_value('Financial Scenario Lab').run()
    assert at.session_state['_scenario_drafts']['Base']['adoption_pct']=='50'
    at.radio(key='navigation').set_value('Executive Brief').run()
    write_source(db,tmp_path,'2025-05',[('Type','A','100','Area','c')])
    at.run();assert any('stale' in w.value for w in at.warning)
    assert not at.exception
