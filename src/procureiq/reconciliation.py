"""Exact frozen-baseline verification with row-by-row source comparison."""
import csv
import json
from decimal import Decimal
from sqlalchemy import select, text, func
from .db import tables, LOCK
from .ingestion import prepare, check_rows, check_quality, compare_totals, MONEY_KEYS
from .supplier_identity import identity, punctuation_candidates


def verify(engine, root, write_reports=True):
    baseline = json.loads((root / 'manifests/milestone1_baseline.json').read_text())
    with (root / 'reports/data_quality_summary.csv').open() as f:
        m1 = {r['reporting_month']: r for r in csv.DictReader(f)}
    t = tables(engine)
    output = {}
    monthly = []
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': LOCK})
        active = conn.execute(select(t['source_file']).where(t['source_file'].c.active)).mappings().all()
        expected_versions = {(r['reporting_month'], r['sha256']) for r in baseline}
        if {(r['reporting_month'].strftime('%Y-%m'), r['sha256']) for r in active} != expected_versions:
            raise ValueError('Active versions do not exactly match the frozen Milestone 1 baseline')
        sql_monthly = {r['reporting_month'].strftime('%Y-%m'): dict(r) for r in conn.execute(
            text('SELECT * FROM procureiq.monthly_reconciliation ORDER BY reporting_month')).mappings()}
        for receipt in baseline:
            month = receipt['reporting_month']
            source = next(r for r in active if r['sha256'] == receipt['sha256'] and r['reporting_month'].strftime('%Y-%m') == month)
            rows, issues, summary = prepare(root, receipt)
            check_rows(conn, t, source['file_id'], rows)
            check_quality(conn, t, source['file_id'], issues)
            if source['original_row_count'] != len(rows):
                raise ValueError('Source metadata row count mismatch')
            actual = sql_monthly[month]
            for expected in (receipt['expected'], summary, m1[month]):
                compare_totals(actual, expected)
            if actual['unparsed_amounts'] != summary['invalid_amounts'] + summary['missing_amounts']:
                raise ValueError('Unparsed amount count mismatch')
            for key in ('negative_amounts', 'zero_amounts', 'positive_below_25000'):
                if actual[key] != int(receipt['expected'][key]):
                    raise ValueError('Retained amount classification mismatch: ' + key)
            monthly.append(dict(reporting_month=month, **{k: v for k, v in actual.items() if k != 'reporting_month'}, passed=True))
        aliases = conn.execute(select(t['supplier_alias'])).mappings().all()
        supplier_ids = {r['supplier_id']: r for r in conn.execute(select(t['supplier'])).mappings()}
        for alias in aliases:
            expected = identity(alias['original_name'])
            if any(alias[k] != v for k, v in expected.items()):
                raise ValueError('Supplier rule/mapping mismatch')
            if expected['review_status'] == 'auto_resolved':
                supplier = supplier_ids.get(alias['supplier_id'])
                if not supplier or supplier['normalized_key'] != expected['normalized_key'] or supplier['canonical_name'] != expected['normalized_key']:
                    raise ValueError('Supplier canonical identity mismatch')
            elif alias['supplier_id'] is not None:
                raise ValueError('Unresolved alias assigned to supplier')
        output['tables_all_versions'] = {name: conn.execute(select(func.count()).select_from(table)).scalar_one()
                                         for name, table in t.items()}
        output['mapping_active'] = dict(conn.execute(text('SELECT * FROM procureiq.supplier_mapping_coverage')).mappings().one())
        output['aliases_all_versions'] = dict(resolved=sum(r['supplier_id'] is not None for r in aliases),
                                              unresolved=sum(r['supplier_id'] is None for r in aliases))
        output['quality_active'] = {r['issue_code']: r['n'] for r in conn.execute(text(
            'SELECT issue_code,count(*) AS n FROM procureiq.unresolved_quality_issues GROUP BY issue_code ORDER BY issue_code')).mappings()}
        duplicate_rows = conn.execute(text('''SELECT count(*) FROM (
           SELECT count(*) OVER (PARTITION BY r.file_id,r.source_values) AS n
           FROM procureiq.raw_spend_row r JOIN procureiq.source_file f USING(file_id) WHERE f.active
           ) x WHERE n>1''')).scalar_one()
        if duplicate_rows != sum(int(r['expected']['exact_duplicate_rows']) for r in baseline):
            raise ValueError('Duplicate candidates not preserved')
        if output['quality_active'].get('exact_duplicate_candidate', 0) != duplicate_rows:
            raise ValueError('Duplicate issue evidence missing')
        output['duplicate_candidate_rows'] = duplicate_rows
        output['monthly'] = monthly
        output['totals_active'] = {key: sum((row[key] for row in monthly), Decimal('0.00') if key in MONEY_KEYS else 0)
                                   for key in ['record_count'] + MONEY_KEYS}
        expected_totals = dict(record_count=12973, positive_payments_gbp='2499145830.48',
                               credit_magnitude_gbp='30802967.80', net_disclosed_gbp='2468342862.68')
        compare_totals(output['totals_active'], expected_totals)
        review = punctuation_candidates([r['original_name'] for r in aliases])
        review += [dict(review_key=r['normalized_key'], original_names=[r['original_name']], reason='unresolved_placeholder')
                   for r in aliases if r['supplier_id'] is None]
        output['supplier_review_groups'] = len(review)
        output['passed'] = True
        output['postgresql_version'] = conn.execute(text('SHOW server_version')).scalar_one()
    if write_reports:
        reports = root / 'reports'
        (reports / 'database_verification.json').write_text(json.dumps(output, indent=2, default=str) + '\n')
        with (reports / 'database_reconciliation.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(monthly[0]))
            writer.writeheader(); writer.writerows(monthly)
        with (reports / 'supplier_mapping_review.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['review_key', 'original_names', 'reason'])
            writer.writeheader()
            writer.writerows(dict(r, original_names=json.dumps(r['original_names'])) for r in review)
    return output
