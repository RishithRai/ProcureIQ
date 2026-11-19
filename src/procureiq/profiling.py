"""Deterministic source investigation; no deduplication or supplier merges."""
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
import pandas as pd
from .acquisition import digest
from .parsing import money, payment_date, read_csv

ZERO = Decimal('0.00')


def profile(path, month):
    frame, columns, refs, issues, metadata = read_csv(path)
    required = {'Amount', 'Date', 'Supplier', 'Transaction number', 'Expense type', 'Expense area'}
    missing_columns = sorted(required - set(columns))
    for column in missing_columns:
        issues.append({'code': 'missing_required_column', 'column': column})
    amounts, dates, formats = [], [], Counter()
    for i, row in frame.iterrows():
        for column, parser, target in [('Amount', money, amounts), ('Date', payment_date, dates)]:
            raw = row.get(column, '')
            try:
                parsed = parser(raw)
                if column == 'Date':
                    parsed, fmt = parsed
                    if fmt:
                        formats[fmt] += 1
                if parsed is None:
                    issues.append({'source_record_number': i + 1, 'code': 'missing_' + column.lower(), 'value': raw})
            except ValueError:
                parsed = None
                issues.append({'source_record_number': i + 1, 'code': 'invalid_' + column.lower(), 'value': raw})
            target.append(parsed)
    valid = [v for v in amounts if v is not None]
    positive = sum((v for v in valid if v > 0), ZERO)
    credits = -sum((v for v in valid if v < 0), ZERO)
    net = sum(valid, ZERO)
    assert positive - credits == net
    identifiers = frame.get('Transaction number', pd.Series([], dtype=str))
    id_counts = identifiers[identifiers.str.strip().ne('')].value_counts()
    repeated = set(id_counts[id_counts > 1].index)
    duplicate_mask = frame.duplicated(keep=False)
    for i, row in frame.iterrows():
        for code, condition in [
            ('repeated_identifier', row.get('Transaction number') in repeated),
            ('exact_duplicate_candidate', bool(duplicate_mask.iloc[i])),
            ('outside_reporting_month', dates[i] is not None and dates[i].strftime('%Y-%m') != month),
        ]:
            if condition:
                issues.append({'source_record_number': i + 1, 'code': code})
    summary = dict(reporting_month=month, record_count=len(frame), column_count=len(columns), **metadata,
                   missing_required_columns=json.dumps(missing_columns),
                   ragged_rows=sum(x['code'] == 'ragged_row' for x in issues),
                   invalid_amounts=sum(x['code'] == 'invalid_amount' for x in issues),
                   missing_amounts=sum(v is None for v in amounts) - sum(x['code'] == 'invalid_amount' for x in issues),
                   invalid_dates=sum(x['code'] == 'invalid_date' for x in issues),
                   missing_dates=sum(v is None for v in dates) - sum(x['code'] == 'invalid_date' for x in issues),
                   negative_amounts=sum(v < 0 for v in valid), zero_amounts=sum(v == 0 for v in valid),
                   signed_below_25000=sum(v < 25000 for v in valid),
                   positive_below_25000=sum(0 < v < 25000 for v in valid),
                   absolute_below_25000=sum(abs(v) < 25000 for v in valid),
                   repeated_identifier_groups=len(repeated),
                   repeated_identifier_rows=int(id_counts[id_counts > 1].sum()),
                   repeated_identifier_excess=int((id_counts[id_counts > 1] - 1).sum()),
                   exact_duplicate_rows=int(duplicate_mask.sum()),
                   exact_duplicate_excess=int(frame.duplicated().sum()),
                   outside_reporting_month=sum(d is not None and d.strftime('%Y-%m') != month for d in dates),
                   positive_payments_gbp=str(positive), credit_magnitude_gbp=str(credits),
                   net_disclosed_gbp=str(net), financial_totals_complete=len(valid) == len(frame),
                   date_formats=json.dumps(dict(sorted(formats.items()))),
                   amount_decimal_places=json.dumps(dict(sorted(Counter(
                       len(v.strip().split('.')[-1]) if '.' in v else 0 for v in frame.get('Amount', [])).items()))),
                   amount_currency_symbols=sum('£' in v for v in frame.get('Amount', [])),
                   amount_thousands_separators=sum(',' in v for v in frame.get('Amount', [])))
    for column in columns:
        summary['missing:' + column] = int(frame[column].str.strip().eq('').sum())
    for column in ('Supplier', 'Expense type', 'Expense area'):
        values = frame.get(column, pd.Series([], dtype=str))
        summary['distinct:' + column] = int(values[values.str.strip().ne('')].nunique())
    return frame, columns, refs, issues, summary


def write_csv(path, records, columns=None):
    pd.DataFrame(records, columns=columns).to_csv(path, index=False, lineterminator='\n')


def investigate(root):
    sources = json.loads((root / 'manifests/hmrc_sources.json').read_text())
    expected = [f'2025-{m:02}' for m in range(4, 13)] + [f'2026-{m:02}' for m in range(1, 4)]
    if [s['reporting_month'] for s in sources] != expected:
        raise ValueError('Source manifest must contain exactly the 12 ordered reporting months')
    receipts = {r['reporting_month']: r for r in json.loads((root / 'manifests/download_manifest.json').read_text())}
    reports = root / 'reports'
    reports.mkdir(exist_ok=True)
    inventory, summaries, schemas, evidence, raw_rows, all_frames = [], [], [], [], [], []
    baseline = None
    for source in sources:
        month = source['reporting_month']
        path = root / 'data/raw' / source['filename']
        receipt = receipts.get(month, {})
        if not path.exists() or digest(path.read_bytes()) != receipt.get('sha256'):
            raise ValueError(f'{month}: source missing or hash mismatch; run download first')
        frame, columns, refs, issues, summary = profile(path, month)
        baseline = columns if baseline is None else baseline
        summaries.append(summary)
        inventory.append(dict(source, sha256=receipt['sha256'], size_bytes=path.stat().st_size,
                              downloaded_at=receipt.get('downloaded_at'), download_status=receipt['status'],
                              record_count=len(frame)))
        schemas.append(dict(reporting_month=month, column_count=len(columns), columns=json.dumps(columns),
                            added_vs_april=json.dumps([c for c in columns if c not in baseline]),
                            absent_vs_april=json.dumps([c for c in baseline if c not in columns]),
                            same_order_as_april=columns == baseline))
        base = dict(source_file=path.name, reporting_month=month, sha256=receipt['sha256'])
        for i, row in frame.iterrows():
            raw_rows.append(dict(base, **refs[i], source_values=row.to_dict()))
        for issue in issues:
            ref = refs[issue['source_record_number'] - 1] if 'source_record_number' in issue else {}
            evidence.append(dict(base, **ref, **{k: v for k, v in issue.items() if k not in ref}))
        all_frames.append(frame)
    combined = pd.concat(all_frames, ignore_index=True, sort=False).fillna('')
    names = sorted(v for v in combined['Supplier'].unique() if v.strip())
    candidate_groups = defaultdict(list)
    for name in names:
        candidate_groups[' '.join(name.casefold().split())].append(name)
    candidates = [dict(normalized_key=k, raw_names=json.dumps(v), variant_count=len(v))
                  for k, v in sorted(candidate_groups.items()) if len(v) > 1]
    # A second, deliberately conservative review-only key highlights punctuation variants.
    punctuation = defaultdict(set)
    for name in names:
        punctuation[re.sub(r'[^\w]', '', name.casefold())].add(name)
    punctuation_candidates = [dict(review_key=k, raw_names=json.dumps(sorted(v)), variant_count=len(v))
                              for k, v in sorted(punctuation.items()) if len(v) > 1]
    write_csv(reports / 'file_inventory.csv', inventory)
    write_csv(reports / 'schema_comparison.csv', schemas)
    write_csv(reports / 'data_quality_summary.csv', summaries)
    write_csv(reports / 'supplier_name_candidates.csv', candidates, ['normalized_key', 'raw_names', 'variant_count'])
    write_csv(reports / 'supplier_punctuation_candidates.csv', punctuation_candidates, ['review_key', 'raw_names', 'variant_count'])
    for field, filename in [('Supplier', 'supplier_names'), ('Expense type', 'expense_types'), ('Expense area', 'expense_areas')]:
        counts = combined[field].value_counts().sort_index()
        write_csv(reports / (filename + '.csv'), [{'source_value': k, 'row_count': int(v)} for k, v in counts.items() if k.strip()])
    with (reports / 'source_rows.jsonl').open('w', encoding='utf-8') as output:
        for row in raw_rows:
            output.write(json.dumps(row, ensure_ascii=False) + '\n')
    with (reports / 'quality_issues.jsonl').open('w', encoding='utf-8') as output:
        for row in evidence:
            output.write(json.dumps(row, ensure_ascii=False) + '\n')
    from .reporting import findings
    (reports / 'milestone1_findings.md').write_text(
        findings(summaries, schemas, combined, candidates, punctuation_candidates, inventory), encoding='utf-8')
    print(f'Investigated {len(inventory)} actual files; {len(combined):,} source records. Reports: {reports}')
