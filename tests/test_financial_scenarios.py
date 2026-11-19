"""Independent numerical fixtures, provenance controls, UI and workbook checks."""
import json
from dataclasses import replace
from decimal import Decimal as D
from io import BytesIO
import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
from sqlalchemy import text
from test_database import db,ROOT
from test_opportunities import write_source,radar_data
from procureiq.financial_model import Assumptions,calculate,comparison,sensitivity,break_even,illustrative,NAMES
from procureiq.scenario_basis import database_baseline,manual_baseline,period_label,opportunity_request,is_stale,refresh_baseline
from procureiq.scenario_io import document,export_json,load_json,validate_database_claim
from procureiq.scenario_excel import workbook_bytes
from procureiq.ui.service import DashboardService
from procureiq.opportunities import detect
from procureiq.ingestion import load


def sample():return Assumptions(D('40'),D('50'),D('10'),D('10000'),D('5000'))


def test_exact_math_and_no_intermediate_rounding():
    r=calculate(D('1000000'),sample())
    assert r==dict(addressable_gbp=D('400000.00'),affected_gbp=D('200000.00'),gross_benefit_gbp=D('20000.00'),
        implementation_cost_gbp=D('10000'),operating_cost_gbp=D('5000'),total_costs_gbp=D('15000.00'),net_benefit_gbp=D('5000.00'),roi_pct=D('33.3333'))
    r=calculate(D('.05'),Assumptions(D('50'),D('50'),D('100')))
    assert (r['addressable_gbp'],r['affected_gbp'],r['gross_benefit_gbp'])==(D('.03'),D('.01'),D('.01'))
    assert calculate(D('.01'),Assumptions(D('100'),D('100'),D('50')))['gross_benefit_gbp']==D('.01')


def test_zero_boundaries_negative_and_independent_cases():
    assert calculate('100',Assumptions())['roi_pct'] is None
    r=calculate('100',Assumptions(implementation_cost=D('10')))
    assert r['net_benefit_gbp']==-10 and r['roi_pct']==-100
    r=calculate('100',Assumptions(D('100'),D('100'),D('100')))
    assert r['gross_benefit_gbp']==100 and r['roi_pct'] is None
    cases={n:Assumptions() for n in NAMES};cases['Base']=sample()
    result=comparison('1000000',cases)
    assert result['Base']['net_benefit_gbp']==5000 and result['Conservative']['gross_benefit_gbp']==0
    with pytest.raises(ValueError):comparison('1',{'Base':sample()})


@pytest.mark.parametrize('field,value',[('addressable_pct','-1'),('adoption_pct','100.01'),('improvement_pct','NaN'),
    ('implementation_cost','-1'),('operating_cost','Infinity'),('operating_cost','0.001'),('adoption_pct',1.1),
    ('addressable_pct',True),('improvement_pct','0.00001'),('operating_cost','1000000000000')])
def test_invalid_assumptions(field,value):
    with pytest.raises(ValueError):Assumptions(**{field:value})


@pytest.mark.parametrize('value',['-1','NaN','0.001',True,1.2])
def test_invalid_baseline(value):
    with pytest.raises(ValueError):calculate(value,Assumptions())


def test_sensitivity_and_break_even_known_grid():
    a=Assumptions(D('50'),D('100'),D('5'),D('20'),D('5'))
    rows=sensitivity('1000',a,[D('0'),D('50'),D('100')],[D('0'),D('5'),D('10')])
    assert [r['net_benefit_gbp'] for r in rows]==[D('-25'),D('-25'),D('-25'),D('-25'),D('-12.50'),D('0'),D('-25'),D('0'),D('25')]
    assert break_even('1000',a)['improvement_pct']==5
    assert break_even('1000',a,D('0'))['improvement_pct'] is None
    assert break_even('0',Assumptions())['improvement_pct']==0
    assert not break_even('1',a)['feasible']
    increased=replace(a,operating_cost=D('15'))
    assert sensitivity('1000',increased,[D('100')],[D('5')])[0]['net_benefit_gbp']==-10
    with pytest.raises(ValueError):sensitivity('1',a,[],[D('1')])


def test_periods_json_roundtrip_and_tampering():
    assert period_label('2025-04-01','2026-03-01').startswith('12-month same-period')
    assert period_label('2025-07-01','2025-08-01').startswith('2-month same-period')
    with pytest.raises(ValueError):period_label('2026-03-01','2025-04-01')
    b=manual_baseline('1000000','2025-04-01','2026-03-01','User test pool')
    cases={n:sample() for n in NAMES};doc=document(b,cases)
    roundtrip,again=load_json(export_json(doc))
    assert roundtrip['baseline']['kind']=='manual' and again==cases
    assert roundtrip['outputs']['Base']['net_benefit_gbp']==5000
    raw=json.loads(export_json(doc));raw['outputs']['Base']['net_benefit_gbp']='999999'
    with pytest.raises(ValueError,match='disagree'):load_json(json.dumps(raw))
    raw=json.loads(export_json(doc));raw['baseline']['source_fingerprint']='f'*64
    with pytest.raises(ValueError):load_json(json.dumps(raw))
    raw=json.loads(export_json(doc));raw['model_version']='unknown'
    with pytest.raises(ValueError):load_json(json.dumps(raw))


def test_database_basis_and_version_review(db,tmp_path):
    write_source(db,tmp_path,'2025-04',[('Type','A','1000','Area','a'),('Type','A','-100','Area','b')])
    svc=DashboardService(db);v=svc.version();b=database_baseline(svc,{},v,'Type')
    assert b['amount_gbp']==1000 and b['population']['net_gbp']==900 and b['population']['record_count']==2
    assert b['period_label'].startswith('1-month same-period')
    doc=document(b,illustrative());decoded,_=load_json(export_json(doc));validate_database_claim(svc,decoded['baseline'],v)
    forged=dict(b,amount_gbp=D('2000'),population=dict(b['population'],positive_gbp=D('2000'),net_gbp=D('1900')))
    with pytest.raises(ValueError):validate_database_claim(svc,forged,v)
    write_source(db,tmp_path,'2025-05',[('Type','A','2000','Area','c')])
    new=svc.version();assert is_stale(b,new)
    fresh=refresh_baseline(svc,b,new)
    assert fresh['amount_gbp']==3000 and b['amount_gbp']==1000
    assert not is_stale(manual_baseline('1','2025-04-01','2025-04-01','Manual'),new)
    with pytest.raises(ValueError):database_baseline(svc,{'expense_type':'Different'},new,'Type')


def test_opportunity_single_pool_safeguards(radar_data):
    engine,_,data=radar_data;svc=DashboardService(engine);v=svc.version()
    for item in detect(data)['opportunities']:
        request=opportunity_request(item,{},v)
        if item['opportunity_type'] in ('payment_pattern','data_quality'):
            assert not request['eligible'] and request['category'] is None
            assert 'positive_exposure_gbp' not in request
        else:
            assert request['eligible']
            b=database_baseline(svc,{},v,request['category'],origin=request)
            assert b['scope']==item['scope']['expense_type']
    with pytest.raises(ValueError):database_baseline(svc,{},v,['Type','Other'])


def test_workbook_formulas_cached_results_and_input_validation():
    b=manual_baseline('1000000','2025-04-01','2026-03-01','Independent fixture')
    cases={n:sample() for n in NAMES};cases['Conservative']=Assumptions()
    payload=workbook_bytes(document(b,cases))
    formula=load_workbook(BytesIO(payload),data_only=False)
    cache=load_workbook(BytesIO(payload),data_only=True)
    assert formula.sheetnames==['Model Inputs','Scenario Comparison','Sensitivity Analysis','Methodology & Limitations']
    ws=formula['Scenario Comparison']
    assert "'Model Inputs'!D17" in ws['D7'].value
    assert 'ROUND(D13-D20,2)' in ws['D21'].value
    assert 'IF(D20>0' in ws['D22'].value and 'n.a.' in ws['D22'].value
    assert cache['Scenario Comparison']['D21'].value==5000
    assert cache['Scenario Comparison']['C22'].value=='n.a.'
    assert cache['Scenario Comparison']['D22'].value==pytest.approx(.333333)
    assert 'SUM($C$7:$D$7)' in formula['Sensitivity Analysis']['C9'].value
    assert len(formula['Sensitivity Analysis'].conditional_formatting)>0
    assert formula['Model Inputs']['D17'].protection.locked is False
    assert formula['Model Inputs'].data_validations.count>0
    assert formula.calculation.fullCalcOnLoad
    # Cached values are checked here, not falsely described as evaluated Excel formulas.


def test_lab_apptest_persistence_and_stale_baseline(db,tmp_path,monkeypatch):
    write_source(db,tmp_path,'2025-04',[('Type','A','1000000','Area','a')])
    monkeypatch.setenv('DATABASE_URL',db.url.render_as_string(hide_password=False))
    at=AppTest.from_file(str(ROOT/'src/procureiq/ui/app.py'),default_timeout=40).run()
    at.radio(key='navigation').set_value('Financial Scenario Lab').run()
    assert not at.exception and not at.error
    next(b for b in at.button if b.label=='Use selected baseline').click().run()
    assert any(m.value=='Unavailable — zero costs' for m in at.metric)
    epoch=at.session_state['_scenario_epoch']
    for field,value in [('addressable_pct',40),('adoption_pct',50),('improvement_pct',10)]:
        at.number_input(key=f'scenario_edit_{epoch}_Base_{field}').set_value(float(value)).run()
    for field,value in [('implementation_cost','10000'),('operating_cost','5000')]:
        at.text_input(key=f'scenario_edit_{epoch}_Base_{field}').set_value(value).run()
    assert any(m.label=='Net hypothetical benefit' and m.value=='£5,000.00' for m in at.metric)
    at.radio(key='navigation').set_value('Spend Overview').run()
    at.radio(key='navigation').set_value('Financial Scenario Lab').run()
    assert at.number_input(key=f'scenario_edit_{epoch}_Base_addressable_pct').value==40
    assert any(m.value=='£5,000.00' for m in at.metric)
    write_source(db,tmp_path,'2025-05',[('Type','A','2000000','Area','b')])
    at.run();assert any('stale' in e.value for e in at.error)
    assert not any(m.label=='Net hypothetical benefit' for m in at.metric)
    next(b for b in at.button if b.label=='Review complete — use current source version').click().run()
    assert not at.exception and not at.error
    assert any(m.value=='£45,000.00' for m in at.metric)


def test_actual_baseline_unchanged(db):
    load(db,ROOT);svc=DashboardService(db);b=database_baseline(svc,{},svc.version())
    assert b['amount_gbp']==D('2499145830.48')
    assert b['population']['record_count']==12973
    assert b['population']['credit_gbp']==D('30802967.80')
    assert b['population']['net_gbp']==D('2468342862.68')
    partial=database_baseline(svc,{'start_month':'2025-07','end_month':'2025-08'},svc.version())
    decoded,_=load_json(export_json(document(partial,illustrative())))
    validate_database_claim(svc,decoded['baseline'],svc.version())
    assert partial['period_label'].startswith('2-month same-period')
