"""Dashboard acceptance: exact backend parity, pagination, caching and UI behavior."""
import json
from datetime import date
from decimal import Decimal as D
from unittest.mock import patch
import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest
from test_database import db, fixture_source, ROOT
from test_opportunities import radar_data, write_source
from procureiq.ingestion import load_file, load
from procureiq.queries import query
from procureiq.opportunities import detect
from procureiq.opportunity_data import retrieve
from procureiq.ui.service import DashboardService, SourceChanged, cache_key
from procureiq.ui.formatting import ALL,money,reset_filters,selected_filters,csv_bytes
from procureiq.ui import charts

APP=str(ROOT/'src/procureiq/ui/app.py')


def test_exact_format_reset_and_chart_units():
    assert money(D('2499145830.48'))=='£2,499,145,830.48'
    assert money(None)=='Not available'
    state={'filter_supplier':2,'detail_supplier':2,'table_page':4,'navigation':'Opportunity Radar','_source_version':'v'}
    reset_filters(state)
    assert state=={'filter_supplier':ALL,'navigation':'Opportunity Radar','_source_version':'v'}
    months=[date(2025,4,1),date(2025,5,1)]
    assert selected_filters({'months':months},tuple(months))['start_month'] is None
    assert selected_filters({'months':months},(months[0],months[0]))['end_month']==months[0]
    with pytest.raises(ValueError):selected_filters({'months':months},(months[1],months[0]))
    assert b'100.01' in csv_bytes([{'amount':D('100.01')}])
    fig=charts.bar([{'name':'A','hhi':D('10000')}],'name','hhi',unit='HHI')
    assert fig.layout.xaxis.title.text=='HHI'
    assert charts.trend([]).data[0].y==()


def test_adapters_filter_denominators_and_readonly(db,fixture_source):
    root,_,receipt=fixture_source;load_file(db,root,receipt,activate_initial=True)
    svc=DashboardService(db);v=svc.version()
    data=svc.analytics({},v,('overview','suppliers','concentration','category_suppliers'))
    assert data['overview'][0]['positive_gbp']==D('112.60')
    assert data['overview'][0]['net_gbp']==D('112.40')
    assert data['concentration'][0]['unresolved_positive_gbp']==D('2.50')
    assert data['suppliers'][-1]['cumulative_resolved_pct']==100
    assert data['suppliers'][0]['share_all_positive_pct']<data['suppliers'][0]['share_resolved_positive_pct']
    sid=data['suppliers'][0]['supplier_id']
    single=svc.analytics({'supplier_id':sid},v,('concentration',))['concentration'][0]
    assert single['hhi']==10000 and data['concentration'][0]['hhi']<10000
    assert set(svc.aliases({},v,sid))=={' Acme  LTD ','ACME LTD'}
    assert svc.analytics({'expense_type':"'; DROP SCHEMA procureiq; --"},v,('overview',))['overview']==[]
    for filters in ({'expense_area':'Area'},{'entity':'HMRC'},{'expense_type':'Type'},
                    {'start_month':'2025-04','end_month':'2025-04'},{'supplier_id':sid}):
        with db.connect() as conn: expected=query(conn,'overview',filters)
        assert svc.analytics(filters,v,('overview',))['overview']==expected
    with svc.snapshot(v) as (conn,_):
        assert conn.execute(text('SHOW transaction_read_only')).scalar_one()=='on'


def test_radar_parity_cache_and_complete_evidence(radar_data):
    engine,_,source=radar_data
    svc=DashboardService(engine);v=svc.version()
    expected=detect(source)
    with patch('procureiq.ui.service.detect',wraps=detect) as call:
        result=svc.opportunities({},v)
        svc.opportunities({},v)
        assert call.call_count==1
    assert [o['opportunity_id'] for o in result['opportunities']]==[o['opportunity_id'] for o in expected['opportunities']]
    assert result['qualified_before_cap']==expected['qualified_before_cap']
    assert 'total_exposure' not in result  # overlapping opportunities deliberately have no additive portfolio total
    assert all('source_references' not in o and 'source_flags' not in o['metrics'] for o in result['opportunities'])
    item=next(o for o in result['opportunities'] if o['primary_count']>50)
    first=svc.evidence({},v,item['opportunity_id'],page=1)
    second=svc.evidence({},v,item['opportunity_id'],page=2)
    assert len(first['rows'])==50
    assert not {r['raw_row_id'] for r in first['rows']} & {r['raw_row_id'] for r in second['rows']}
    full=json.loads(svc.evidence_download({},v,item['opportunity_id']))
    assert len(full['source_references_details'])==item['primary_count']
    assert {r['raw_row_id'] for r in full['source_references_details']}=={r['raw_row_id'] for r in full['source_references']}
    assert all(r['filename'] and len(r['sha256'])==64 and r['source_record_number']>0 for r in first['rows'])
    with pytest.raises(ValueError):svc.evidence({},v,item['opportunity_id'],page=0)
    sid=next(r['supplier_id'] for r in source['lines'] if r['supplier_id'])
    assert svc.opportunities({'supplier_id':sid},v)['counts_by_type']['supplier_concentration']==0


def test_source_switch_invalidates_cached_results(db,tmp_path):
    write_source(db,tmp_path,'2025-04',[('Type','A','10','Area','1')])
    svc=DashboardService(db);old=svc.version()
    assert svc.analytics({},old,('overview',))['overview'][0]['positive_gbp']==10
    write_source(db,tmp_path,'2025-04',[('Type','B','99','Area','2')],filename='revision.csv',active=False)
    # Fixture-only source activation; never mutate the main database.
    with db.begin() as conn:
        conn.execute(text('UPDATE procureiq.source_file SET active=FALSE WHERE active'))
        conn.execute(text("UPDATE procureiq.source_file SET active=TRUE WHERE filename='revision.csv'"))
    new=svc.version();assert new!=old
    with pytest.raises(SourceChanged):svc.analytics({},old,('overview',))
    assert svc.analytics({},new,('overview',))['overview'][0]['positive_gbp']==99
    assert cache_key('overview',{},new)!=cache_key('overview',{},old)


def test_app_missing_configuration(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    at=AppTest.from_file(APP).run()
    assert not at.exception
    assert 'configuration is missing' in at.error[0].value


def test_app_database_failure_sanitized(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://secret_user:secret_password@127.0.0.1:1/no_database?connect_timeout=1')
    at=AppTest.from_file(APP,default_timeout=15).run()
    assert not at.exception
    assert 'unavailable' in at.error[0].value
    assert 'secret_' not in at.error[0].value


def test_app_navigation_filter_reset_and_empty(db,fixture_source,monkeypatch):
    root,_,receipt=fixture_source;load_file(db,root,receipt,activate_initial=True)
    monkeypatch.setenv('DATABASE_URL',db.url.render_as_string(hide_password=False))
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception and not at.error
    assert at.metric[0].value=='£112.60'
    at.radio(key='navigation').set_value('Supplier Intelligence').run()
    assert not at.exception and not at.error
    at.radio(key='navigation').set_value('Opportunity Radar').run()
    assert not at.exception and not at.error
    sid=at.selectbox(key='filter_supplier').options[1]
    at.selectbox(key='filter_supplier').select(sid).run()
    assert any('suppressed' in info.value for info in at.info)
    next(b for b in at.button if b.label=='Reset Filters').click().run()
    assert at.selectbox(key='filter_supplier').value==ALL
    assert at.metric[0].value=='£112.60'
    at.slider(key='radar_minimum').set_value(100).run()
    assert at.selectbox(key='filter_supplier').value==ALL
    assert any('No eligible reviews' in i.value for i in at.info)
    write_source(db,root,'2025-05',[('Other type','Other supplier','50','Other area','extra')])
    at.run()
    assert any('versions changed' in i.value for i in at.info)
    at.selectbox(key='filter_expense_type').set_value('Type').run()
    at.selectbox(key='filter_expense_area').set_value('Other area').run()
    assert not at.exception and not at.error
    assert at.metric[0].value=='£0.00'
    assert any('No published lines' in i.value for i in at.info)


def test_actual_database_acceptance(db):
    load(db,ROOT)
    svc=DashboardService(db);version=svc.version()
    data=svc.analytics({},version,('overview','suppliers','concentration'))
    row=data['overview'][0]
    assert row['record_count']==12973
    assert (row['positive_gbp'],row['credit_gbp'],row['net_gbp'])==(D('2499145830.48'),D('30802967.80'),D('2468342862.68'))
    result=svc.opportunities({},version)
    assert sum(result['counts_by_type'].values())==34
    assert sum(result['qualified_before_cap'].values())==112
    top=result['opportunities'][0]
    assert top['primary_count']==6497
    assert top['positive_exposure_gbp']==D('721458382.18')
    assert 'PROJECT Mandays Supp' in top['title']
    assert len(svc.evidence({},version,top['opportunity_id'])['rows'])==50
    with db.connect() as conn:
        truth=detect(retrieve(conn))
    assert [i['scoring'] for i in result['opportunities']]==[i['scoring'] for i in truth['opportunities']]
