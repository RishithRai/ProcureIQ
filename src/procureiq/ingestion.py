"""Per-file atomic ingestion, strict rerun comparison and explicit version activation."""
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from sqlalchemy import select, text
from .acquisition import digest
from .db import LOCK, tables
from .parsing import money, payment_date
from .profiling import profile
from .supplier_identity import identity, punctuation_candidates

TEXT_FIELDS = {'Department family': 'department_family', 'Entity': 'entity', 'Expense type': 'expense_type',
               'Expense area': 'expense_area', 'Supplier': 'supplier_raw', 'Transaction number': 'transaction_number',
               'Description': 'description', 'Supplier Postcode': 'supplier_postcode',
               'Supplier Type': 'supplier_type', 'Contract Number': 'contract_number', 'Project Code': 'project_code'}
BASE_COLUMNS = list(TEXT_FIELDS)[:8] + ['Date', 'Amount']
MONEY_KEYS = ['positive_payments_gbp', 'credit_magnitude_gbp', 'net_disclosed_gbp']


def row_hash(values):
    return digest(json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def typed_row(values):
    result = {target: values.get(source) or None for source, target in TEXT_FIELDS.items()}
    errors = []
    for field, target, parser in [('Amount', 'amount_gbp', money), ('Date', 'payment_date', lambda s: payment_date(s)[0])]:
        try:
            value = parser(values.get(field, ''))
            if target == 'amount_gbp' and value is not None and abs(value) >= Decimal('1000000000000000000'):
                raise ValueError('Exceeds NUMERIC(20,2)')
            result[target] = value
            if value is None:
                errors.append(dict(code='missing_' + field.lower(), field=field, value=values.get(field)))
        except (ValueError, InvalidOperation):
            result[target] = None
            errors.append(dict(code='invalid_' + field.lower(), field=field, value=values.get(field)))
    result['parse_status'] = 'invalid' if errors else 'valid'
    return result, errors


def prepare(root, receipt):
    if receipt.get('status') not in ('downloaded', 'verified'):
        raise ValueError('Only verified official-source receipts may be loaded')
    filename = receipt['filename']
    if filename != Path(filename).name:
        raise ValueError('Source filename must be a basename inside data/raw')
    path = root / 'data/raw' / filename
    content = path.read_bytes()
    if digest(content) != receipt['sha256'] or len(content) != receipt['size_bytes']:
        raise ValueError(f'Source hash/size mismatch: {filename}')
    frame, columns, refs, issues, summary = profile(path, receipt['reporting_month'])
    # Catch a source changed while profiling; load only bytes represented by the receipt.
    if path.read_bytes() != content:
        raise ValueError('Source changed while profiling')
    raw_values = frame.to_dict(orient='records')
    # Ragged records retain exact positional values and column names alongside mapped fields.
    for issue in issues:
        if issue['code'] == 'ragged_row':
            raw_values[issue['source_record_number'] - 1]['__original_fields'] = issue['raw_values']
            raw_values[issue['source_record_number'] - 1]['__original_headers'] = columns
    missing = sorted(set(BASE_COLUMNS) - set(columns))
    extra = sorted(set(columns) - set(TEXT_FIELDS) - {'Date', 'Amount'})
    if missing or extra:
        issues.append(dict(code='schema_drift', missing=missing, unexpected=extra))
    rows = []
    for i, values in enumerate(raw_values):
        typed, errors = typed_row(values)
        if missing or any(q.get('source_record_number') == i + 1 and q['code'] == 'ragged_row' for q in issues):
            typed['parse_status'] = 'invalid'
        for error in errors:
            if not any(q.get('source_record_number') == i + 1 and q['code'] == error['code'] for q in issues):
                issues.append(dict(error, source_record_number=i + 1))
        if identity(values.get('Supplier', ''))['review_status'] == 'unresolved':
            issues.append(dict(code='unresolved_supplier', field='Supplier', value=values.get('Supplier'), source_record_number=i + 1))
        rows.append(dict(values=values, typed=typed, ref=refs[i], hash=row_hash(values)))
    valid_amounts = [r['typed']['amount_gbp'] for r in rows if r['typed']['amount_gbp'] is not None]
    summary = dict(summary)
    summary['positive_payments_gbp'] = str(sum((v for v in valid_amounts if v > 0), Decimal('0.00')))
    summary['credit_magnitude_gbp'] = str(sum((-v for v in valid_amounts if v < 0), Decimal('0.00')))
    summary['net_disclosed_gbp'] = str(sum(valid_amounts, Decimal('0.00')))
    return rows, issues, summary


def resolve_alias(conn, t, name):
    alias = identity(name)
    existing = conn.execute(select(t['supplier_alias']).where(t['supplier_alias'].c.original_name == name)).mappings().first()
    supplier_id = None
    if alias['review_status'] == 'auto_resolved':
        supplier_id = conn.execute(select(t['supplier'].c.supplier_id).where(t['supplier'].c.normalized_key == alias['normalized_key'])).scalar()
        if supplier_id is None:
            supplier_id = conn.execute(t['supplier'].insert().values(
                canonical_name=alias['normalized_key'], normalized_key=alias['normalized_key']).returning(t['supplier'].c.supplier_id)).scalar_one()
    alias['supplier_id'] = supplier_id
    if existing:
        if any(existing[k] != v for k, v in alias.items()):
            raise ValueError(f'Alias mapping conflict: {name!r}')
    else:
        conn.execute(t['supplier_alias'].insert().values(**alias))
    return supplier_id


def file_totals(conn, file_id):
    return dict(conn.execute(text('''SELECT count(*) AS record_count,
        coalesce(sum(s.amount_gbp) FILTER(WHERE s.amount_gbp>0),0) AS positive_payments_gbp,
        coalesce(-sum(s.amount_gbp) FILTER(WHERE s.amount_gbp<0),0) AS credit_magnitude_gbp,
        coalesce(sum(s.amount_gbp),0) AS net_disclosed_gbp
        FROM procureiq.raw_spend_row r JOIN procureiq.spend_line s USING(raw_row_id) WHERE r.file_id=:id'''), {'id': file_id}).mappings().one())


def compare_totals(actual, expected):
    if actual['record_count'] != int(expected['record_count']):
        raise ValueError('Source/database record count mismatch')
    for key in MONEY_KEYS:
        if actual[key] != Decimal(expected[key]):
            raise ValueError('Exact financial reconciliation failed: ' + key)


def check_rows(conn, t, file_id, rows):
    raw = conn.execute(select(t['raw_spend_row']).where(t['raw_spend_row'].c.file_id == file_id)
                       .order_by(t['raw_spend_row'].c.source_record_number)).mappings().all()
    typed = {r['raw_row_id']: r for r in conn.execute(select(t['spend_line']).join(t['raw_spend_row'])
             .where(t['raw_spend_row'].c.file_id == file_id)).mappings()}
    aliases = {r['original_name']: r['supplier_id'] for r in conn.execute(select(t['supplier_alias'])).mappings()}
    if len(raw) != len(rows) or len(typed) != len(rows):
        raise ValueError('Missing or extra raw/typed rows')
    for observed, expected in zip(raw, rows):
        ref = expected['ref']
        comparisons = dict(source_record_number=ref['source_record_number'], physical_line_start=ref['source_line_start'],
                           physical_line_end=ref['source_line_end'], source_values=expected['values'], row_hash=expected['hash'])
        if any(observed[k] != v for k, v in comparisons.items()):
            raise ValueError('Conflicting raw row contents')
        derived = typed[observed['raw_row_id']]
        if any(derived[k] != v for k, v in expected['typed'].items()):
            raise ValueError('Conflicting typed row contents')
        name = expected['values'].get('Supplier', '')
        if name not in aliases or derived['supplier_id'] != aliases[name]:
            raise ValueError('Supplier lineage mismatch')


def quality_records(file_id, ids, issues):
    quality = []
    for issue in issues:
        number = issue.get('source_record_number')
        code = issue['code']
        field = issue.get('field') or issue.get('column')
        if code.endswith('_amount'):
            field = 'Amount'
        if code.endswith('_date'):
            field = 'Date'
        if code == 'repeated_identifier':
            field = 'Transaction number'
        quality.append(dict(file_id=None if number else file_id, raw_row_id=ids[number] if number else None,
                            issue_code=code, field=field, details=issue,
                            severity='error' if code.startswith(('missing_', 'invalid_')) or code == 'ragged_row' else 'warning'))
    return quality


def check_quality(conn, t, file_id, issues):
    ids = dict(conn.execute(select(t['raw_spend_row'].c.source_record_number, t['raw_spend_row'].c.raw_row_id)
                           .where(t['raw_spend_row'].c.file_id == file_id)).all())
    expected = quality_records(file_id, ids, issues)
    observed = conn.execute(text('''SELECT q.file_id,q.raw_row_id,q.issue_code,q.field,q.details,q.severity
        FROM procureiq.data_quality_issue q LEFT JOIN procureiq.raw_spend_row r USING(raw_row_id)
        WHERE coalesce(q.file_id,r.file_id)=:id'''), {'id': file_id}).mappings().all()
    serialize = lambda values: sorted(json.dumps(dict(v), sort_keys=True) for v in values)
    if serialize(expected) != serialize(observed):
        raise ValueError('Missing or conflicting quality evidence')


def load_file(engine, root, receipt, activate_initial=False, expected=None):
    rows, issues, summary = prepare(root, receipt)
    if expected:
        compare_totals({k: Decimal(summary[k]) if k in MONEY_KEYS else summary[k] for k in ['record_count'] + MONEY_KEYS}, expected)
    t = tables(engine)
    month = date.fromisoformat(receipt['reporting_month'] + '-01')
    metadata = dict(reporting_month=month, source_url=receipt['url'], filename=receipt['filename'],
                    sha256=receipt['sha256'], size_bytes=receipt['size_bytes'], original_row_count=len(rows),
                    acquired_at=datetime.fromisoformat(receipt['downloaded_at']) if receipt.get('downloaded_at') else None)
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': LOCK})
        source = t['source_file']
        old = conn.execute(select(source).where(source.c.reporting_month == month, source.c.sha256 == receipt['sha256'])).mappings().first()
        if old:
            if any(old[k] != v for k, v in metadata.items()) or old['import_status'] != 'loaded':
                raise ValueError('Existing source metadata conflicts with receipt')
            for name in sorted({r['values'].get('Supplier', '') for r in rows}):
                resolve_alias(conn, t, name)
            check_rows(conn, t, old['file_id'], rows)
            check_quality(conn, t, old['file_id'], issues)
            compare_totals(file_totals(conn, old['file_id']), summary)
            return dict(file_id=old['file_id'], status='verified_existing', active=old['active'])
        occupied = conn.execute(select(source.c.file_id).where(source.c.filename == receipt['filename'])).first()
        if occupied:
            raise ValueError('New source versions require separate filenames; retain original bytes')
        file_id = conn.execute(source.insert().values(**metadata, active=False, import_status='loading').returning(source.c.file_id)).scalar_one()
        mapping = {name: resolve_alias(conn, t, name) for name in sorted({r['values'].get('Supplier', '') for r in rows})}
        records = [dict(file_id=file_id, source_record_number=r['ref']['source_record_number'],
                        physical_line_start=r['ref']['source_line_start'], physical_line_end=r['ref']['source_line_end'],
                        source_values=r['values'], row_hash=r['hash']) for r in rows]
        if records:
            conn.execute(t['raw_spend_row'].insert(), records)
        ids = dict(conn.execute(select(t['raw_spend_row'].c.source_record_number, t['raw_spend_row'].c.raw_row_id)
                               .where(t['raw_spend_row'].c.file_id == file_id)).all())
        if rows:
            conn.execute(t['spend_line'].insert(), [dict(r['typed'], raw_row_id=ids[r['ref']['source_record_number']],
                         supplier_id=mapping[r['values'].get('Supplier', '')]) for r in rows])
        quality = quality_records(file_id, ids, issues)
        if quality:
            conn.execute(t['data_quality_issue'].insert(), quality)
        check_rows(conn, t, file_id, rows)
        check_quality(conn, t, file_id, issues)
        compare_totals(file_totals(conn, file_id), summary)
        active_exists = conn.execute(select(source.c.file_id).where(source.c.reporting_month == month, source.c.active)).first()
        active = activate_initial and active_exists is None
        conn.execute(source.update().where(source.c.file_id == file_id).values(import_status='loaded', active=active))
    return dict(file_id=file_id, status='loaded', active=active)


def load(engine, root, manifest=None):
    baseline = json.loads((root / 'manifests/milestone1_baseline.json').read_text())
    frozen = {(r['reporting_month'], r['sha256']): r for r in baseline}
    receipts = json.loads((manifest or root / 'manifests/download_manifest.json').read_text())
    keys = [(r['reporting_month'], r['sha256']) for r in receipts]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate source versions in manifest')
    if manifest is None and set(keys) != set(frozen):
        raise ValueError('Default receipt manifest differs from frozen baseline; register revisions with --manifest')
    # Preflight all files before any writes, so a hash mismatch is found immediately.
    for receipt in receipts:
        prepare(root, receipt)
    results = []
    for receipt in receipts:
        original = frozen.get((receipt['reporting_month'], receipt['sha256']))
        results.append(load_file(engine, root, receipt, activate_initial=original is not None,
                                 expected=original['expected'] if original else None))
    return results


def activate(engine, root, month, checksum, expected_fingerprint=None):
    t = tables(engine)
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': LOCK})
        if expected_fingerprint is not None:
            from procureiq.source_basis import fingerprint
            if fingerprint(conn) != expected_fingerprint:
                raise ValueError("Reviewed source basis changed before activation")
        source = t['source_file']
        target = conn.execute(select(source).where(source.c.reporting_month == date.fromisoformat(month + '-01'),
                                                   source.c.sha256 == checksum)).mappings().one()
        receipt = dict(reporting_month=month, filename=target['filename'], url=target['source_url'], sha256=checksum,
                       size_bytes=target['size_bytes'], status='verified')
        rows, issues, summary = prepare(root, receipt)
        if target['import_status'] != 'loaded':
            raise ValueError('Cannot activate an incomplete import')
        check_rows(conn, t, target['file_id'], rows)
        check_quality(conn, t, target['file_id'], issues)
        compare_totals(file_totals(conn, target['file_id']), summary)
        conn.execute(source.update().where(source.c.reporting_month == target['reporting_month']).values(active=False))
        conn.execute(source.update().where(source.c.file_id == target['file_id']).values(active=True))
