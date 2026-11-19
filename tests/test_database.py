"""Destructive schema tests ONLY in an explicitly designated separate test database."""
import csv
import json
import os
from pathlib import Path
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, DBAPIError
from procureiq.acquisition import digest
from procureiq.db import initialize
from procureiq.ingestion import load_file, load, activate
from procureiq.reconciliation import verify

ROOT = Path(__file__).resolve().parents[1]


def safe_test_url():
    value = os.environ.get('TEST_DATABASE_URL')
    if not value:
        pytest.skip('Set TEST_DATABASE_URL to run PostgreSQL integration tests')
    url = make_url(value)
    main = make_url(os.environ['DATABASE_URL']) if os.environ.get('DATABASE_URL') else None
    if not url.database or not url.database.endswith('_test') or (main and url.database == main.database):
        raise ValueError('Integration tests require a separate database with a name ending _test')
    return url


@pytest.fixture
def db():
    engine = create_engine(safe_test_url(), hide_parameters=True)
    with engine.begin() as conn:
        # Verify the server-selected name as well as the connection URL.
        actual = conn.execute(text('SELECT current_database()')).scalar_one()
        if actual != engine.url.database or not actual.endswith('_test'):
            raise ValueError('Unsafe integration database')
        conn.exec_driver_sql('DROP SCHEMA IF EXISTS procureiq_app CASCADE')
        conn.exec_driver_sql('DROP SCHEMA IF EXISTS procureiq CASCADE')
    initialize(engine, ROOT)
    yield engine
    engine.dispose()


@pytest.fixture
def fixture_source(tmp_path):
    raw = tmp_path / 'data/raw'
    raw.mkdir(parents=True)
    path = raw / 'fixture.csv'
    with path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Department family', 'Entity', 'Date', 'Expense type', 'Expense area', 'Supplier',
                    'Transaction number', 'Amount', 'Description', 'Supplier Postcode', 'Supplier Type'])
        for name, amount, txn, dt in [(' Acme  LTD ', '100.10', '001', '01/04/2025'),
                                      ('ACME LTD', '-0.20', '001', '01/04/2025'),
                                      ('ACME LTD', '0', '002', '01/04/2025'),
                                      ('Acme Ltd.', '10.00', '003', '01/04/2025'),
                                      ('[REDACTED]', '2.50', '004', '01/04/2025'),
                                      ('Unknown', 'bad', '005', 'bad'),
                                      ('ACME LTD', '0', '002', '01/04/2025')]:
            w.writerow(['HMRC', 'HMRC', dt, 'Type', 'Area', name, txn, amount, 'Description', 'SW1', ''])
    receipt = dict(reporting_month='2025-04', filename=path.name, url='https://example.invalid/fixture.csv',
                   sha256=digest(path.read_bytes()), size_bytes=path.stat().st_size,
                   downloaded_at='2026-10-15T00:00:00+00:00', status='verified')
    return tmp_path, path, receipt


def scalar(db, sql):
    with db.connect() as c:
        return c.execute(text(sql)).scalar_one()


def test_schema_and_key_constraints(db, fixture_source):
    initialize(db, ROOT)
    assert scalar(db, 'SELECT count(*) FROM procureiq.schema_migration') == len(list((ROOT / 'sql').glob('[0-9]*.sql')))
    root, path, receipt = fixture_source
    load_file(db, root, receipt, activate_initial=True)
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text('INSERT INTO procureiq.spend_line(raw_row_id,parse_status) SELECT raw_row_id,\'invalid\' FROM procureiq.spend_line LIMIT 1'))
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text("INSERT INTO procureiq.spend_line(raw_row_id,parse_status) VALUES(99999,'invalid')"))
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text('''INSERT INTO procureiq.raw_spend_row(file_id,source_record_number,physical_line_start,physical_line_end,source_values,row_hash)
         SELECT file_id,source_record_number,physical_line_start,physical_line_end,source_values,row_hash FROM procureiq.raw_spend_row LIMIT 1'''))
    with pytest.raises(DBAPIError), db.begin() as c:
        c.execute(text("UPDATE procureiq.raw_spend_row SET source_values='{}'"))
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text('''INSERT INTO procureiq.source_file(reporting_month,source_url,filename,sha256,size_bytes,original_row_count,import_status)
        SELECT reporting_month,source_url,filename,sha256,size_bytes,original_row_count,import_status FROM procureiq.source_file'''))


def test_complete_fixture_idempotence_validation_and_suppliers(db, fixture_source):
    root, path, receipt = fixture_source
    before = path.read_bytes()
    load_file(db, root, receipt, activate_initial=True)
    assert load_file(db, root, receipt)['status'] == 'verified_existing'
    assert path.read_bytes() == before
    assert scalar(db, 'SELECT count(*) FROM procureiq.raw_spend_row') == 7
    assert scalar(db, 'SELECT count(*) FROM procureiq.spend_line') == 7
    assert scalar(db, 'SELECT net_disclosed_gbp FROM procureiq.monthly_reconciliation') == Decimal('112.40')
    assert scalar(db, "SELECT count(*) FROM procureiq.spend_line WHERE transaction_number='001'") == 2
    assert scalar(db, 'SELECT count(*) FROM procureiq.supplier') == 2
    assert scalar(db, 'SELECT count(*) FROM procureiq.supplier_alias WHERE supplier_id IS NULL') == 2
    assert scalar(db, "SELECT count(*) FROM procureiq.spend_line WHERE parse_status='invalid'") == 1
    assert scalar(db, 'SELECT count(*) FROM procureiq.spend_line WHERE supplier_type IS NULL AND project_code IS NULL') == 7
    assert scalar(db, "SELECT count(*) FROM procureiq.data_quality_issue WHERE issue_code='exact_duplicate_candidate'") == 2
    assert scalar(db, "SELECT count(*) FROM procureiq.raw_spend_row WHERE source_values ? 'Supplier Type' AND NOT source_values ? 'Project Code'") == 7


def test_conflicting_typed_content_detected(db, fixture_source):
    root, _, receipt = fixture_source
    load_file(db, root, receipt)
    with db.begin() as c:
        c.execute(text("UPDATE procureiq.spend_line SET description='tampered' WHERE spend_line_id=1"))
    with pytest.raises(ValueError, match='Conflicting typed'):
        load_file(db, root, receipt)


def test_hash_mismatch_no_writes(db, fixture_source):
    root, path, receipt = fixture_source
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='hash/size mismatch'):
        load_file(db, root, receipt)
    assert scalar(db, 'SELECT count(*) FROM procureiq.source_file') == 0


def test_file_transaction_rolls_back(db, fixture_source, monkeypatch):
    import procureiq.ingestion as ingestion
    root, _, receipt = fixture_source
    def fail(*args):
        raise ValueError('Injected reconciliation failure')
    monkeypatch.setattr(ingestion, 'compare_totals', fail)
    with pytest.raises(ValueError, match='Injected'):
        load_file(db, root, receipt)
    for name in ('source_file', 'raw_spend_row', 'spend_line', 'supplier', 'supplier_alias', 'data_quality_issue'):
        assert scalar(db, f'SELECT count(*) FROM procureiq.{name}') == 0


def test_version_selection_and_active_constraint(db, fixture_source):
    root, path, receipt = fixture_source
    load_file(db, root, receipt, activate_initial=True)
    revision = path.with_name('revision.csv')
    revision.write_bytes(path.read_bytes().replace(b'100.10', b'200.10'))
    newer = dict(receipt, filename=revision.name, sha256=digest(revision.read_bytes()), size_bytes=revision.stat().st_size)
    result = load_file(db, root, newer)
    assert not result['active']
    assert scalar(db, 'SELECT count(*) FROM procureiq.raw_spend_row') == 14
    assert scalar(db, 'SELECT count(*) FROM procureiq.active_spend_line') == 7
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(text('UPDATE procureiq.source_file SET active=true'))
    activate(db, root, '2025-04', newer['sha256'])
    assert scalar(db, 'SELECT net_disclosed_gbp FROM procureiq.monthly_reconciliation') == Decimal('212.40')
    load_file(db, root, receipt, activate_initial=True)
    assert scalar(db, 'SELECT net_disclosed_gbp FROM procureiq.monthly_reconciliation') == Decimal('212.40')
    activate(db, root, '2025-04', receipt['sha256'])
    assert scalar(db, 'SELECT net_disclosed_gbp FROM procureiq.monthly_reconciliation') == Decimal('112.40')


def test_schema_drift_keeps_unknown_values(db, fixture_source):
    root, path, receipt = fixture_source
    data = path.read_text().replace('Expense area', 'Unexpected area')
    path.write_text(data)
    receipt.update(sha256=digest(path.read_bytes()), size_bytes=path.stat().st_size)
    load_file(db, root, receipt)
    assert scalar(db, "SELECT count(*) FROM procureiq.data_quality_issue WHERE issue_code='schema_drift'") == 1
    assert scalar(db, "SELECT count(*) FROM procureiq.raw_spend_row WHERE source_values ? 'Unexpected area'") == 7
    assert scalar(db, "SELECT count(*) FROM procureiq.spend_line WHERE parse_status='invalid'") == 7


def test_full_actual_ingestion_exact_monthly_and_safe_rerun(db):
    receipts = json.loads((ROOT / 'manifests/download_manifest.json').read_text())
    if not all((ROOT / 'data/raw' / r['filename']).exists() for r in receipts):
        pytest.skip('Official source files required for full integration test')
    load(db, ROOT)
    first = verify(db, ROOT, write_reports=False)
    load(db, ROOT)
    second = verify(db, ROOT, write_reports=False)
    assert first == second
    assert second['totals_active']['record_count'] == 12973
    assert second['totals_active']['net_disclosed_gbp'] == Decimal('2468342862.68')
    assert second['duplicate_candidate_rows'] == 73
    assert second['tables_all_versions']['raw_spend_row'] == second['tables_all_versions']['spend_line'] == 12973
    assert len(second['monthly']) == 12


def test_missing_quality_evidence_is_detected(db, fixture_source):
    root, _, receipt = fixture_source
    load_file(db, root, receipt)
    with db.begin() as c:
        c.execute(text('DELETE FROM procureiq.data_quality_issue WHERE issue_id=(SELECT min(issue_id) FROM procureiq.data_quality_issue)'))
    with pytest.raises(ValueError, match='quality evidence'):
        load_file(db, root, receipt)


def test_numeric_overflow_is_preserved_as_invalid(db, fixture_source):
    root, path, receipt = fixture_source
    path.write_bytes(path.read_bytes().replace(b'100.10', b'1000000000000000000.00'))
    receipt.update(sha256=digest(path.read_bytes()), size_bytes=path.stat().st_size)
    load_file(db, root, receipt)
    assert scalar(db, 'SELECT count(*) FROM procureiq.raw_spend_row') == 7
    assert scalar(db, 'SELECT count(*) FROM procureiq.spend_line WHERE amount_gbp IS NULL') == 2
    assert scalar(db, "SELECT count(*) FROM procureiq.data_quality_issue WHERE issue_code='invalid_amount'") == 2


def test_test_database_guard(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://localhost/procureiq')
    monkeypatch.setenv('TEST_DATABASE_URL', 'postgresql+psycopg://localhost/procureiq')
    with pytest.raises(ValueError, match='separate database'):
        safe_test_url()
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://localhost/procureiq_test')
    monkeypatch.setenv('TEST_DATABASE_URL', 'postgresql+psycopg://localhost/procureiq_test')
    with pytest.raises(ValueError, match='separate database'):
        safe_test_url()
