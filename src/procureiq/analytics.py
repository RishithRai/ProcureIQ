"""Independent Decimal checks, snapshot exports and the analytics CLI workflow."""
import csv
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from hashlib import sha256
from sqlalchemy import text
from .queries import query, execute_query, source_lines, validate_filters, QUERIES

ZERO = Decimal('0.00')
MONEY = ('positive_gbp', 'credit_gbp', 'net_gbp')


def amounts(rows):
    values = [r['amount_gbp'] for r in rows if r['amount_gbp'] is not None]
    return dict(positive_gbp=sum((v for v in values if v > 0), ZERO),
                credit_gbp=sum((-v for v in values if v < 0), ZERO), net_gbp=sum(values, ZERO))


def require(condition, message):
    if not condition:
        raise ValueError('Analytical verification failed: ' + message)


def ratio_equal(actual, expected):
    # Monetary values never use tolerances. SQL NUMERIC division has finite scale.
    return actual is None if expected is None else actual is not None and abs(actual - expected) <= Decimal('1e-12')


def verify_analytics(conn, filters=None):
    filters = validate_filters(filters)
    lines = source_lines(conn, filters)
    expected = amounts(lines)
    outputs = {name: query(conn, name, filters) for name in QUERIES if name != 'supplier_monthly'}
    overview = outputs['overview']
    require(bool(overview) == bool(lines), 'empty population behavior')
    if overview:
        require(overview[0]['record_count'] == len(lines), 'overall row count')
        for key in MONEY:
            require(overview[0][key] == expected[key], 'overall ' + key)
        require(overview[0]['unparsed_amounts'] == sum(r['amount_gbp'] is None for r in lines), 'unparsed amounts')
    require(expected['positive_gbp'] - expected['credit_gbp'] == expected['net_gbp'], 'signed reconciliation')
    for output, field in [('expense_types', 'expense_type'), ('expense_areas', 'expense_area'), ('entities', 'entity')]:
        groups = defaultdict(list)
        for row in lines:
            groups[row[field]].append(row)
        require({r['group_value'] for r in outputs[output]} == set(groups), output + ' group coverage')
        require(sum(r['record_count'] for r in outputs[output]) == len(lines), output + ' rows')
        for row in outputs[output]:
            truth = amounts(groups[row['group_value']])
            for key in MONEY:
                require(row[key] == truth[key], output + ' ' + key)
        for key in MONEY:
            require(sum((r[key] for r in outputs[output]), ZERO) == expected[key], output + ' total ' + key)
    for by_category, ranking_name, concentration_name in [(False, 'suppliers', 'concentration'), (True, 'category_suppliers', 'category_concentration')]:
        groups = defaultdict(list)
        for row in lines:
            groups[row['expense_type'] if by_category else 'All'].append(row)
        ranked = defaultdict(list)
        for row in outputs[ranking_name]:
            ranked[row['group_value']].append(row)
        concentration = {r['group_value']: r for r in outputs[concentration_name]}
        require(set(concentration) == set(groups), 'concentration group coverage')
        for group, group_lines in groups.items():
            supplier_lines = defaultdict(list)
            for row in group_lines:
                if row['supplier_id'] is not None:
                    supplier_lines[row['supplier_id']].append(row)
            stats = {sid: amounts(rows) for sid, rows in supplier_lines.items()}
            ordering = sorted(stats, key=lambda sid: (-stats[sid]['positive_gbp'], supplier_lines[sid][0]['normalized_key'].encode('utf-8'), sid))
            require([r['supplier_id'] for r in ranked[group]] == ordering, 'supplier ranking and tie order')
            pool = sum((s['positive_gbp'] for s in stats.values()), ZERO)
            all_pos = amounts(group_lines)['positive_gbp']
            cumulative = ZERO
            threshold = None
            for position, row in enumerate(ranked[group], 1):
                truth = stats[row['supplier_id']]
                for key in MONEY:
                    require(row[key] == truth[key], 'supplier ' + key)
                cumulative += truth['positive_gbp']
                require(row['supplier_rank'] == position and row['cumulative_positive_gbp'] == cumulative, 'Pareto cumulative GBP')
                require(ratio_equal(row['cumulative_resolved_pct'], 100*cumulative/pool if pool else None), 'Pareto cumulative percentage')
                require(ratio_equal(row['share_all_positive_pct'], 100*truth['positive_gbp']/all_pos if all_pos else None), 'supplier share of all positives')
                if threshold is None and pool and cumulative*5 >= pool*4:
                    threshold = position
            c = concentration[group]
            require(c['suppliers_to_80'] == threshold, '80 percent crossing supplier included')
            require(c['positive_supplier_count'] == sum(s['positive_gbp'] > 0 for s in stats.values()), 'positive supplier population')
            require(c['resolved_positive_gbp'] == pool and c['unresolved_positive_gbp'] == all_pos-pool, 'mapping denominator')
            with localcontext() as ctx:
                ctx.prec = 50
                hhi = 10000*sum((s['positive_gbp']**2 for s in stats.values()), ZERO)/pool**2 if pool else None
                top_one = 100*max((s['positive_gbp'] for s in stats.values()), default=ZERO)/pool if pool else None
                top_three = 100*sum((stats[sid]['positive_gbp'] for sid in ordering[:3]), ZERO)/pool if pool else None
            require(ratio_equal(c['hhi'], hhi), 'HHI independent calculation')
            require(ratio_equal(c['top_one_pct'], top_one) and ratio_equal(c['top_three_pct'], top_three), 'top supplier concentration')
    monthly_lines = defaultdict(list)
    for row in lines:
        monthly_lines[row['reporting_month']].append(row)
    previous = None
    for row in outputs['monthly']:
        truth = amounts(monthly_lines[row['reporting_month']])
        for key in MONEY:
            require(row[key] == (truth[key] if row['source_available'] else None), 'monthly ' + key)
        require(row['record_count'] == len(monthly_lines[row['reporting_month']]), 'monthly row count')
        mom = 100*(row['positive_gbp']-previous)/previous if previous and row['positive_gbp'] is not None else None
        require(row['previous_positive_gbp'] == previous and ratio_equal(row['mom_positive_pct'], mom), 'calendar month-over-month')
        previous = row['positive_gbp']
    for key in MONEY:
        require(sum((r[key] for r in outputs['monthly'] if r[key] is not None), ZERO) == expected[key], 'monthly total ' + key)
    supplier_months = defaultdict(list)
    for row in lines:
        if row['supplier_id'] is not None:
            supplier_months[(row['supplier_id'], row['reporting_month'])].append(row)
    trends = query(conn, 'supplier_monthly', filters)
    seen = set()
    previous_by_supplier = {}
    for row in trends:
        key = (row['supplier_id'], row['reporting_month'])
        require(key not in seen, 'unique supplier/month trend')
        seen.add(key)
        truth = amounts(supplier_months[key])
        for metric in MONEY:
            require(row[metric] == (truth[metric] if row['source_available'] else None), 'supplier monthly ' + metric)
        require(row['record_count'] == len(supplier_months[key]), 'supplier monthly line count')
        prev = previous_by_supplier.get(row['supplier_id'])
        mom = 100*(row['positive_gbp']-prev)/prev if prev and row['positive_gbp'] is not None else None
        require(row['previous_positive_gbp'] == prev and ratio_equal(row['mom_positive_pct'], mom), 'supplier monthly change')
        previous_by_supplier[row['supplier_id']] = row['positive_gbp']
    require(all(key in seen for key, rows in supplier_months.items() if rows), 'supplier month coverage')
    return dict(passed=True, filters=filters, record_count=len(lines), **expected,
                checks=['independent Decimal line totals', 'category/area/entity reconciliation',
                        'supplier ranks and shares', 'Pareto crossing', 'HHI and top-one/top-three',
                        'unknown mapping denominators', 'calendar month trends', 'supplier monthly reconciliation'])


def snapshot_metadata(conn, filters):
    sources = [dict(r) for r in conn.execute(text('''SELECT file_id,reporting_month,filename,sha256,
        original_row_count FROM procureiq.source_file WHERE active AND import_status='loaded' ORDER BY reporting_month''')).mappings()]
    migrations = [dict(r) for r in conn.execute(text('SELECT name,sha256 FROM procureiq.schema_migration ORDER BY name')).mappings()]
    return dict(filters=filters, date_basis='reporting_month', money_basis='GBP gross VAT-inclusive disclosed payments',
                identity_basis='case_whitespace_v1 resolved supplier keys',
                source_scope='All active source versions; filters select lines within these files', sources=sources, migrations=migrations)


def run(engine, root, command, filters=None, output_dir=None):
    if command not in ('summary', 'verify', 'export'):
        raise ValueError('Unknown analytics command')
    filters = validate_filters(filters)
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
        with conn.begin():
            conn.exec_driver_sql('SET TRANSACTION READ ONLY')
            verification = verify_analytics(conn, filters)
            metadata = snapshot_metadata(conn, filters)
            if command == 'verify':
                result = dict(verification, basis=metadata)
                path = root / 'reports/analytics_verification.json'
                if not any(v is not None for v in filters.values()):
                    path.write_text(json.dumps(result, indent=2, default=str) + '\n')
                return result
            if command == 'summary':
                return dict(verification=verification, overview=query(conn, 'overview', filters),
                            concentration=query(conn, 'concentration', filters),
                            top_suppliers=query(conn, 'suppliers', filters)[:10],
                            top_expense_types=query(conn, 'expense_types', filters)[:10], basis=metadata)
            datasets = {}
            for name in QUERIES:
                result = execute_query(conn, name, filters)
                datasets[name] = (list(result.keys()), [dict(r) for r in result.mappings()])
    is_filtered = any(v is not None for v in filters.values())
    suffix = 'filtered_' + sha256(json.dumps(filters, sort_keys=True, default=str).encode()).hexdigest()[:12] if is_filtered else 'full'
    directory = output_dir or root / 'reports/analytics' / suffix
    directory.mkdir(parents=True, exist_ok=True)
    for name, (columns, rows) in datasets.items():
        with (directory / (name + '.csv')).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    (directory / 'basis.json').write_text(json.dumps(metadata, indent=2, default=str) + '\n')
    (directory / 'verification.json').write_text(json.dumps(verification, indent=2, default=str) + '\n')
    if not is_filtered:
        from .analytics_reporting import findings
        (root / 'reports/milestone3_findings.md').write_text(findings({k: v[1] for k, v in datasets.items()}, metadata), encoding='utf-8')
    return dict(directory=str(directory), exported=list(datasets), verification=verification)
