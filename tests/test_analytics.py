"""Independent expectations; all integration mutations use the guarded test database."""
import csv
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import text
from test_database import db, ROOT, scalar
from procureiq.acquisition import digest
from procureiq.ingestion import load_file, load, activate
from procureiq.queries import query, validate_filters
from procureiq.analytics import verify_analytics, ratio_equal


def source(root, db, month, rows, filename=None, active=True):
    raw = root / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / (filename or month + '.csv')
    with path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Department family', 'Entity', 'Date', 'Expense type', 'Expense area', 'Supplier',
                    'Transaction number', 'Amount', 'Description', 'Supplier Postcode'])
        for name, amount, category, area, entity in rows:
            w.writerow(['HMRC', entity, date.fromisoformat(month+'-01').strftime('%d/%m/%Y'), category,
                        area, name, '0001', amount, 'fixture', 'SW1'])
    receipt = dict(reporting_month=month, filename=path.name, url='https://example.invalid/'+path.name,
                   sha256=digest(path.read_bytes()), size_bytes=path.stat().st_size,
                   downloaded_at='2026-10-15T00:00:00+00:00', status='verified')
    load_file(db, root, receipt, activate_initial=active)
    return receipt


@pytest.fixture
def population(db, tmp_path):
    april = [
        (' A LTD ', '100', 'Equal', 'North', 'HMRC'), ('B', '100', 'Equal', 'South', 'HMRC'),
        ('a ltd', '-20', 'Equal', 'North', 'HMRC'), ('C', '0', 'Equal', 'North', 'HMRC'),
        ('D', '-5', 'Equal', 'North', 'HMRC'), ('Unknown', '100', 'Equal', 'North', 'HMRC'),
        ('A LTD', '50', 'Single', 'North', 'HMRC'),
        ('A LTD', '10', 'Four', 'North', 'HMRC'), ('B', '20', 'Four', 'South', 'HMRC'),
        ('C', '30', 'Four', 'North', 'HMRC'), ('D', '40', 'Four', 'South', 'HMRC'),
        ('A LTD', '5', 'Duplicate', 'North', 'HMRC'), ('A LTD', '5', 'Duplicate', 'North', 'HMRC'),
        ('Unknown', '70', 'Unknown only', 'North', 'HMRC'), ('C', '0', 'Zero', 'North', 'HMRC'),
        ('C', '-3', 'Credits only', 'North', 'HMRC'), ('B', '7', '', '', 'HMRC'),
    ]
    original = source(tmp_path, db, '2025-04', april)
    source(tmp_path, db, '2025-05', [('A LTD','300','Equal','North','HMRC'), ('B','100','Equal','South','Other')])
    source(tmp_path, db, '2025-04', [('A LTD','9999','Equal','North','HMRC')], filename='revision.csv', active=False)
    return db, tmp_path, original


def result(db, name, filters=None):
    with db.connect() as conn:
        return query(conn, name, filters)


@pytest.mark.parametrize('bad', [{'unexpected': 1}, {'start_month': '2025-13'}, {'start_month': 'April'},
    {'start_month':'2025-05','end_month':'2025-04'}, {'supplier_id':True}, {'supplier_id':-1}, {'entity':['HMRC']}])
def test_filter_validation(bad):
    with pytest.raises(ValueError):
        validate_filters(bad)


def test_known_hhi_top_shares_pareto_and_zero_cases(population):
    db, _, _ = population
    rows = {r['group_value']:r for r in result(db, 'category_concentration', {'end_month':'2025-04'})}
    equal = rows['Equal']
    assert equal['hhi'] == 5000
    assert equal['top_one_pct'] == 50 and equal['top_three_pct'] == 100
    assert equal['resolved_positive_gbp'] == 200 and equal['unresolved_positive_gbp'] == 100
    assert equal['supplier_count'] == 4 and equal['positive_supplier_count'] == 2
    assert equal['suppliers_to_80'] == 2 and equal['suppliers_to_80_pct'] == 100
    assert rows['Single']['hhi'] == 10000
    four = rows['Four']
    assert four['hhi'] == 3000 and four['top_one_pct'] == 40 and four['top_three_pct'] == 90
    assert four['suppliers_to_80'] == 3 and four['suppliers_to_80_pct'] == 75
    for name in ('Zero','Credits only','Unknown only'):
        assert rows[name]['hhi'] is None and rows[name]['suppliers_to_80'] is None
    assert rows['Unknown only']['unresolved_positive_gbp'] == 70
    assert rows[None]['positive_gbp'] == 7


def test_filter_recalculation_and_supplier_selection(population):
    db, _, _ = population
    # April is 50:50; May is 75:25; combined resolved is 400:200 (not average HHI).
    all_period = result(db, 'concentration', {'expense_type':'Equal'})[0]
    expected = Decimal(10000)*(Decimal(400)**2+Decimal(200)**2)/Decimal(600)**2
    assert ratio_equal(all_period['hhi'], expected)
    assert all_period['hhi'] != (Decimal(5000)+Decimal(6250))/2
    assert result(db, 'concentration', {'expense_type':'Equal','expense_area':'North'})[0]['hhi'] == 10000
    assert result(db, 'concentration', {'expense_type':'Equal','entity':'Other'})[0]['hhi'] == 10000
    assert result(db, 'concentration', {'expense_type':'Equal','start_month':'2025-05'})[0]['hhi'] == 6250
    sid = result(db, 'suppliers', {'expense_type':'Equal'})[0]['supplier_id']
    filtered = result(db, 'concentration', {'expense_type':'Equal','supplier_id':sid})[0]
    assert filtered['hhi'] == 10000 and filtered['mapping_coverage_pct'] == 100
    with db.connect() as conn:
        assert verify_analytics(conn, {'expense_type':'Equal','expense_area':'North','entity':'HMRC','supplier_id':sid})['passed']


def test_deterministic_rank_aliases_and_no_join_multiplication(population):
    db, _, _ = population
    ranked = result(db, 'suppliers', {'expense_type':'Equal','end_month':'2025-04'})
    assert [r['canonical_name'] for r in ranked] == ['a ltd','b','c','d']
    assert [r['supplier_rank'] for r in ranked] == [1,2,3,4]
    assert ranked[0]['positive_gbp'] == 100 and ranked[0]['credit_gbp'] == 20
    assert ranked[0]['record_count'] == 2
    assert ranked[0]['cumulative_resolved_pct'] == 50
    assert ranked[1]['cumulative_resolved_pct'] == 100
    assert scalar(db, 'SELECT count(*) FROM procureiq.data_quality_issue') > 1
    duplicate = result(db, 'overview', {'expense_type':'Duplicate'})[0]
    assert duplicate['record_count'] == 2 and duplicate['positive_gbp'] == 10
    with db.connect() as conn:
        verified = verify_analytics(conn)
        assert verified['record_count'] == 19
        assert verified['positive_gbp'] == Decimal('937')
        assert verified['credit_gbp'] == Decimal('28')


def test_empty_injection_and_inactive_versions(population):
    db, root, original = population
    assert result(db, 'suppliers', {'expense_type':"'; DROP TABLE procureiq.supplier; --"}) == []
    assert result(db, 'concentration', {'expense_type':'absent'}) == []
    with db.connect() as conn:
        assert verify_analytics(conn, {'expense_type':'absent'})['record_count'] == 0
    assert result(db, 'overview')[0]['positive_gbp'] == 937
    revision_hash = scalar(db, "SELECT sha256 FROM procureiq.source_file WHERE filename='revision.csv'")
    activate(db, root, '2025-04', revision_hash)
    assert result(db, 'overview')[0]['positive_gbp'] == 10399
    activate(db, root, '2025-04', original['sha256'])
    assert result(db, 'overview')[0]['positive_gbp'] == 937


def test_calendar_gaps_zero_denominators_and_supplier_trends(db, tmp_path):
    source(tmp_path, db, '2025-04', [('A','100','Type','Area','HMRC')])
    source(tmp_path, db, '2025-05', [('B','0','Type','Area','HMRC')])
    source(tmp_path, db, '2025-07', [('A','200','Type','Area','HMRC')])
    monthly = result(db, 'monthly', {'end_month':'2025-08'})
    assert [r['source_available'] for r in monthly] == [True,True,False,True,False]
    assert [r['positive_gbp'] for r in monthly] == [100,0,None,200,None]
    assert [r['mom_positive_pct'] for r in monthly] == [None,-100,None,None,None]
    trends = result(db, 'supplier_monthly')
    a = [r for r in trends if r['canonical_name']=='a']
    assert [r['positive_gbp'] for r in a] == [100,0,None,200]
    with db.connect() as conn:
        assert verify_analytics(conn)['passed']
    assert result(db, 'monthly', {'start_month':'2025-07'})[0]['mom_positive_pct'] is None


def test_full_real_analytics_and_view_parity(db):
    load(db, ROOT)
    with db.connect() as conn:
        verified = verify_analytics(conn)
        assert verified['record_count'] == 12973
        assert verified['net_gbp'] == Decimal('2468342862.68')
        for view, name in [('vw_expenditure_overview','overview'), ('vw_supplier_ranking','suppliers'),
                           ('vw_category_concentration','category_concentration'), ('vw_monthly_disclosed_spend','monthly')]:
            view_rows = [dict(r) for r in conn.execute(text('SELECT * FROM procureiq.'+view)).mappings()]
            assert sorted(map(str, view_rows)) == sorted(map(str, query(conn, name)))
        assert verify_analytics(conn, {'start_month':'2025-07','end_month':'2025-08','expense_area':'CDIO - Core'})['passed']
