"""Synthetic rule expectations and isolated PostgreSQL/source-line verification."""
import copy
import csv
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from pathlib import Path
import pytest
from sqlalchemy import text
from test_database import db, ROOT
from procureiq.acquisition import digest
from procureiq.ingestion import load_file, load
from procureiq.opportunity_model import OpportunityConfig, score, load_config
from procureiq.opportunity_data import retrieve
from procureiq.opportunity_detectors import category_detectors, payment_detector, quality_detector
from procureiq.opportunities import detect, verify_result, canonical
from procureiq.opportunity_reporting import export
from procureiq.analytics import verify_analytics


def write_source(db, root, month, entries, filename=None, active=True):
    raw = root/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    path = raw/(filename or month+'.csv')
    with path.open('w',newline='') as f:
        w = csv.writer(f)
        w.writerow(['Department family','Entity','Date','Expense type','Expense area','Supplier','Transaction number','Amount','Description','Supplier Postcode'])
        for category,supplier,amount,area,txn in entries:
            w.writerow(['HMRC','HMRC',date.fromisoformat(month+'-01').strftime('%d/%m/%Y'),category,area,supplier,txn,amount,'Synthetic test','SW1'])
    receipt = dict(reporting_month=month,filename=path.name,url='https://example.invalid/'+path.name,
                   sha256=digest(path.read_bytes()),size_bytes=path.stat().st_size,
                   downloaded_at='2026-10-15T00:00:00+00:00',status='verified')
    load_file(db,root,receipt,activate_initial=active)


@pytest.fixture
def radar_data(db,tmp_path):
    for month in range(4,11):
        entries = [
            ('Recurring','One','1000000','North','rec'),
            ('Small','Tiny','100','North','tiny'),
            ('Spike','Spike supplier', '5000000' if month==10 else '1000000','North','spike'),
            ('Credit','Credit supplier','1000000','North','credit'),
            ('Zeros','Zero supplier','5000000' if month==10 else '0','North','zeros'),
            ('Quality','Alias Ltd','20000','North','dup'),('Quality','Alias Ltd','20000','North','dup'),
            ('Quality','Alias Ltd.','20000','South','alias'),
            ('Split','Split supplier','10000','North','split'),('Split','Split supplier','20000','South','split'),
            ('Unknown','Unknown','0','North','unknown'),
        ]
        entries += [('Fragment',f'Supplier {i}','100000',f'Area {i%4}',f'frag{i}') for i in range(12)]
        if month==4:
            entries += [('Sparse','One off','20000000','North','sparse')]
        if month==10:
            entries += [('Credit','Credit supplier','-2000000','North','credit_note')]
        write_source(db,tmp_path,f'2025-{month:02}',entries)
    write_source(db,tmp_path,'2025-04',[('Inactive','Not selected','999999999','North','inactive')],filename='inactive.csv',active=False)
    with db.connect() as conn:
        data = retrieve(conn)
    return db,tmp_path,data


def test_score_exact_weights_and_bounds():
    s = score(D('50000000'),D('0.4'),D('0.75'),OpportunityConfig())
    assert s['weighted_points']=={'materiality':D('22.5'),'signal':D('14'),'evidence':D('15')}
    assert s['priority_score']==D('51.5')
    assert score(D('10000000000'),D('2'),D('2'),OpportunityConfig())['priority_score']==100
    assert score(D('0'),D('-1'),D('-1'),OpportunityConfig())['priority_score']==0
    with pytest.raises(ValueError):score(D('-1'),D('1'),D('1'),OpportunityConfig())
    with pytest.raises(ValueError):score(D('1'),D('NaN'),D('1'),OpportunityConfig())


@pytest.mark.parametrize('changes', [dict(materiality_weight=D('0.9')),dict(min_mapping=D('1.1')),dict(history_months=2),
    dict(max_per_type=0),dict(max_per_type=True),dict(payment_min_gbp=D('0')),dict(credit_ratio=D('0')),
    dict(materiality_reference_gbp=D('NaN')),dict(concentration_hhi=D('10001'))])
def test_config_validation(changes):
    with pytest.raises(ValueError):OpportunityConfig(**changes)


def test_config_file_decimal_and_unknown_fields(tmp_path):
    p=tmp_path/'config.json';p.write_text('{"category_min_gbp": "1000000", "min_mapping": 0.97}')
    assert load_config(p).category_min_gbp==D('1000000') and load_config(p).min_mapping==D('0.97')
    p.write_text('{"unknown":1}')
    with pytest.raises(ValueError):load_config(p)


def test_four_detectors_positive_negative_safeguards(radar_data):
    _,_,data=radar_data
    cfg=OpportunityConfig()
    result=detect(data,cfg)
    assert verify_result(data,result,cfg)['passed']
    candidates=result['opportunities']
    assert all(result['counts_by_type'][kind]>0 for kind in result['counts_by_type'])
    concentration=[c for c in candidates if c['opportunity_type']=='supplier_concentration']
    assert any(c['scope']['expense_type']=='Recurring' for c in concentration)
    assert not any(c['scope']['expense_type'] in ('Small','Sparse','Zeros') for c in concentration)
    assert any(r['scope'].get('expense_type')=='Sparse' and r['reason']=='insufficient_recurring_activity' for r in result['rejections'])
    assert any(c['scope']['expense_type']=='Fragment' for c in candidates if c['opportunity_type']=='purchasing_fragmentation')
    assert not any(c['scope']['expense_type']=='Recurring' for c in candidates if c['opportunity_type']=='purchasing_fragmentation')
    for c in concentration:
        assert 'does not establish inefficient procurement' in c['business_interpretation']
        assert any('may be appropriate' in caveat for caveat in c['caveats'])
    patterns=[c for c in candidates if c['opportunity_type']=='payment_pattern']
    spike=next(c for c in patterns if c['scope']['expense_type']=='Spike')
    assert spike['positive_exposure_gbp']==D('11000000')
    assert spike['metrics']['prior_median_gbp']==1000000 and spike['metrics']['prior_mad_gbp']==0
    assert 'historical_positive_spike' in spike['metrics']['triggers']
    credit=next(c for c in patterns if c['scope']['expense_type']=='Credit')
    assert credit['metrics']['current_credit_gbp']==2000000 and credit['positive_exposure_gbp']==7000000
    assert credit['metrics']['triggers']==['material_credit_activity']
    assert not any(c['scope']['expense_type'] in ('Zeros','Recurring','Small','Sparse') for c in patterns)
    assert any(r['reason']=='sparse_prior_activity' for r in result['rejections'])


def test_quality_union_repeated_only_aliases_and_unknown(radar_data):
    _,_,data=radar_data
    result=detect(data)
    quality=[c for c in result['opportunities'] if c['opportunity_type']=='data_quality']
    q=next(c for c in quality if c['scope']['expense_type']=='Quality')
    assert q['metrics']['affected_rows']==21
    assert q['metrics']['flag_counts']['exact_duplicate_candidate']==14
    assert q['metrics']['flag_counts']['supplier_alias_candidate']==21
    assert q['positive_exposure_gbp']==420000
    assert len(q['source_references'])==21
    assert not any(c['scope']['expense_type']=='Split' for c in quality)
    missing=next(c for c in quality if c['scope']['expense_type']=='Unknown')
    assert missing['positive_exposure_gbp']==0 and missing['metrics']['missing_or_unresolved_rows']==7
    assert missing['scoring']['components']['materiality']==0
    assert any(r['reason']=='repeated_identifier_alone_not_an_error' for r in result['rejections'])


def test_filters_stability_references_caps_and_no_mutation(radar_data):
    db,_,data=radar_data
    result=detect(data)
    assert canonical(result)==canonical(detect(data))
    assert 'Inactive' not in {c['scope'].get('expense_type') for c in result['opportunities']}
    reduced=detect(data,replace(OpportunityConfig(),max_per_type=1))
    assert max(reduced['counts_by_type'].values())==1
    assert 'output_cap_after_scoring' in reduced['rejection_counts']
    sid=next(r['supplier_id'] for r in data['lines'] if r['expense_type']=='Recurring')
    with db.connect() as conn:
        before=[tuple(r) for r in conn.execute(text('SELECT * FROM procureiq.monthly_reconciliation ORDER BY reporting_month'))]
        selected=retrieve(conn,{'supplier_id':sid})
        filtered=detect(selected)
        assert filtered['counts_by_type']['supplier_concentration']==0
        assert filtered['rejection_counts']['disabled_supplier_filtered_population']>0
        assert verify_result(selected,filtered,OpportunityConfig())['passed']
        narrow=detect(retrieve(conn,{'start_month':'2025-10','end_month':'2025-10','expense_type':'Spike'}))
        assert narrow['counts_by_type']['payment_pattern']==0
        for f in ({'expense_area':'North'}, {'entity':'missing'}, {'expense_type':'absent'}, {'expense_type':"'; DROP TABLE supplier; --"}):
            d=retrieve(conn,f);r=detect(d);assert verify_result(d,r,OpportunityConfig())['passed']
        after=[tuple(r) for r in conn.execute(text('SELECT * FROM procureiq.monthly_reconciliation ORDER BY reporting_month'))]
        assert before==after
        assert verify_analytics(conn)['passed']
    changed=copy.deepcopy(result)
    changed['opportunities'][0]['source_references'][0]['sha256']='f'*64
    with pytest.raises(ValueError,match='evidence resolves'):verify_result(data,changed,OpportunityConfig())
    changed=copy.deepcopy(result);changed['opportunities'][0]['positive_exposure_gbp']+=D('0.01')
    with pytest.raises(ValueError,match='exposure'):verify_result(data,changed,OpportunityConfig())


def test_missing_coverage_and_insufficient_mapping(radar_data):
    _,_,data=radar_data
    missing=copy.deepcopy(data);missing['calendar'][2]['source_available']=False
    assert payment_detector(missing,OpportunityConfig())[0]==[]
    assert any(r['reason']=='missing_source_period' for r in payment_detector(missing,OpportunityConfig())[1])
    lowmap=copy.deepcopy(data)
    for cat in lowmap['categories']:cat['mapping_coverage_pct']=D('90')
    candidates,rejected=category_detectors(lowmap,OpportunityConfig())
    assert candidates==[]
    assert any(r['reason']=='insufficient_supplier_mapping' for r in rejected)


def test_payment_march_context_and_mad_nonzero(db,tmp_path):
    months=['2025-09','2025-10','2025-11','2025-12','2026-01','2026-02','2026-03']
    for month,amount in zip(months,['1000000','1100000','900000','1200000','800000','1000000','6000000']):
        write_source(db,tmp_path,month,[('Spike','Supplier',amount,'North','one')])
    with db.connect() as conn:data=retrieve(conn)
    candidates,_=payment_detector(data,OpportunityConfig())
    assert len(candidates)==1
    c=candidates[0]
    assert c.metrics['prior_median_gbp']==1000000 and c.metrics['prior_mad_gbp']==100000
    assert c.metrics['deviation_in_mad_units']==50
    assert c.evidence==D('0.75') and c.metrics['march_year_end_context']


def test_repeated_identifier_context_and_quality_minimum(db,tmp_path):
    write_source(db,tmp_path,'2025-04',[('Shared','A','20000','North','same'),('Shared','B','20000','North','same'),
                                     ('Tiny','A','1','North','tiny'),('Tiny','A','1','North','tiny')])
    with db.connect() as conn:data=retrieve(conn)
    candidates,rejected=quality_detector(data,OpportunityConfig())
    assert len(candidates)==1 and candidates[0].scope['expense_type']=='Shared'
    assert candidates[0].metrics['flag_counts']['identifier_context_review']==2
    assert any(r['reason']=='below_quality_materiality' for r in rejected)


def test_export_lossless_nested_evidence_and_empty_header(radar_data,tmp_path):
    _,_,data=radar_data
    result=detect(data);result['verification']=verify_result(data,result,OpportunityConfig())
    directory=export(tmp_path,result,tmp_path/'export')
    document=json.loads((directory/'opportunities.json').read_text())
    with (directory/'opportunities.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(document['opportunities'])
    assert D(rows[0]['positive_exposure_gbp'])==result['opportunities'][0]['positive_exposure_gbp']
    assert json.loads(rows[0]['source_references'])==document['opportunities'][0]['source_references']
    assert json.loads(rows[0]['scoring'])==document['opportunities'][0]['scoring']
    empty=copy.deepcopy(data);empty.update(lines=[],by_category={},categories=[],category_suppliers=[],issues=[],alias_candidates=[])
    r=detect(empty);r['verification']=verify_result(empty,r,OpportunityConfig())
    path=export(tmp_path,r,tmp_path/'empty')
    assert 'opportunity_id' in (path/'opportunities.csv').read_text().splitlines()[0]


def test_actual_hmrc_radar_preserves_analytics(db):
    load(db,ROOT)
    with db.connect() as conn:
        before=verify_analytics(conn)
        data=retrieve(conn)
        result=detect(data)
        assert verify_result(data,result,OpportunityConfig())['passed']
        assert result['population']['record_count']==12973
        assert result['population']['net_gbp']==D('2468342862.68')
        assert set(result['counts_by_type'])=={'supplier_concentration','purchasing_fragmentation','payment_pattern','data_quality'}
        assert all(0<n<=10 for n in result['counts_by_type'].values())
        after=verify_analytics(conn)
        assert before==after
