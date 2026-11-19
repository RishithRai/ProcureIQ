"""Evidence-based Markdown assembled exclusively from measured profiles."""
import json
from collections import Counter
from decimal import Decimal


def findings(summaries, schemas, combined, candidates, punctuation, inventory):
    def total(key):
        return sum(s[key] for s in summaries)
    def money_total(key):
        return sum((Decimal(s[key]) for s in summaries), Decimal('0.00'))
    date_formats = Counter()
    fractions = Counter()
    for summary in summaries:
        date_formats.update(json.loads(summary['date_formats']))
        fractions.update(json.loads(summary['amount_decimal_places']))
    unverified = sum(i['download_status'] == 'manual_unverified' for i in inventory)
    lines = ['# Milestone 1 — HMRC dataset investigation', '',
             '## Executive dataset summary', '',
             f'Investigated **{len(inventory)} actual monthly source files**, April 2025–March 2026 inclusive, '
             f'containing **{len(combined):,} source records**. No rows were removed, no supplier identities were merged, '
             'and transaction identifiers remain strings. Counts describe published lines, not unique invoices.', '',
             f"Positive disclosed payments: **£{money_total('positive_payments_gbp'):,.2f}**; "
             f"credit magnitude: **£{money_total('credit_magnitude_gbp'):,.2f}**; "
             f"net disclosed payments: **£{money_total('net_disclosed_gbp'):,.2f}**.", '',
             '[Official dataset catalogue](https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc). '
             'Exact monthly URLs, byte sizes, SHA-256 hashes and acquisition timestamps are in `file_inventory.csv` '
             'and `../manifests/download_manifest.json`. Findings refer to those frozen versions.',
             f'Acquisition provenance: {len(inventory) - unverified} files verified against official downloads; {unverified} manual files with unverified origin.', '',
             '## Coverage and financial reconciliation', '',
             '| Reporting month | Rows | Columns | Positive GBP | Credit magnitude GBP | Net GBP |',
             '|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        lines.append(f"| {s['reporting_month']} | {s['record_count']:,} | {s['column_count']} | "
                     f"{s['positive_payments_gbp']} | {s['credit_magnitude_gbp']} | {s['net_disclosed_gbp']} |")
    lines += ['', 'Every monthly total satisfies positive − credit magnitude = net, using Decimal throughout. '
              f"Unparsed/missing monetary values: {total('invalid_amounts') + total('missing_amounts')}; "
              'totals include only successfully parsed amounts. Reporting month comes from the catalogue, not the payment date.', '',
              '## Schema and file formats', '']
    for schema in schemas:
        lines.append(f"- {schema['reporting_month']}: {schema['column_count']} columns; added versus April: "
                     f"`{schema['added_vs_april']}`; absent: `{schema['absent_vs_april']}`.")
    lines += ['', 'Exact baseline headers: ' + ', '.join('`' + c + '`' for c in json.loads(schemas[0]['columns'])) + '.',
              'Exact ordered headers for every month are also recorded in `schema_comparison.csv`.', '',
              f"Selected decoding(s): {', '.join(sorted({s['encoding'] for s in summaries}))}. "
              'Decoding tries strict UTF-8 (including BOM), then Windows-1252. Successful decoding is evidence of compatibility, '
              'not proof of the publisher’s encoding declaration; ASCII-only files are explicitly flagged.',
              f"Observed delimiters: {sorted({s['delimiter'] for s in summaries})!r}. "
              f"Observed date formats: {dict(date_formats)} (counts across all files; monthly details in the CSV).",
              f"Source monetary fractional digits: {dict(sorted(fractions.items()))}; pound-symbol values: {total('amount_currency_symbols')}; comma-grouped values: {total('amount_thousands_separators')}.",
              'Monetary format observations (fractional digit counts, currency symbols and grouping separators) are in '
              '`data_quality_summary.csv`. Values with more than two decimal places are rejected rather than rounded. '
              'Missing means empty or whitespace-only; literal text such as NA is preserved.', '',
              '## Data quality', '',
              '| Metric | Count |', '|---|---:|']
    keys = ['ragged_rows', 'missing_amounts', 'invalid_amounts', 'missing_dates', 'invalid_dates',
            'negative_amounts', 'zero_amounts', 'positive_below_25000', 'signed_below_25000',
            'absolute_below_25000', 'repeated_identifier_groups', 'repeated_identifier_rows',
            'repeated_identifier_excess', 'exact_duplicate_rows', 'exact_duplicate_excess', 'outside_reporting_month']
    for key in keys:
        lines.append(f'| {key} | {total(key):,} |')
    ids = combined['Transaction number']
    counts = ids[ids.str.strip().ne('')].value_counts()
    lines += ['', f'Across the whole period, {(counts > 1).sum():,} distinct nonblank identifier strings occur more than once, '
              f'covering {counts[counts > 1].sum():,} rows. Monthly group counts above may count the same identifier in different months.',
              f'Across the union schema, {combined.duplicated(keep=False).sum():,} rows belong to exact duplicate candidates '
              f'({combined.duplicated().sum():,} occurrences after the first). Absent optional fields are compared as blank for this cross-file check.',
              'Repeated identifier rows count every member of a repeated group; excess counts all occurrences after the first. '
              'Exact duplicates compare every source field within a file, before any normalization. Neither indicates proven duplicate payment.',
              'Signed below-threshold counts include negative and zero amounts; positive and absolute-value counts are supplied separately.', '',
              '### Blank values in columns present in each file', '']
    for s in summaries:
        missing = {k.removeprefix('missing:'): v for k, v in s.items() if k.startswith('missing:') and v}
        lines.append(f"- {s['reporting_month']}: {missing if missing else 'none'}.")
    lines += ['', 'Absent optional columns are schema differences, not blank cells. `quality_issues.jsonl` supplies source-file/hash '
              'and record/physical-line references for parsing, date and duplicate candidates. '
              '`source_rows.jsonl` (generated locally, gitignored) preserves every decoded field plus provenance; original bytes remain in `data/raw/`.', '',
              '## Supplier-name normalization considerations', '']
    for field in ('Supplier', 'Expense type', 'Expense area'):
        values = combined[field]
        lines.append(f"- Distinct exact nonblank {field} values: {values[values.str.strip().ne('')].nunique():,}.")
    lines += [f'- Case/whitespace variant groups: {len(candidates)}.',
              f'- Review-only punctuation-insensitive groups: {len(punctuation)}.', '',
              'Complete frequency lists are in `supplier_names.csv`, `expense_types.csv` and `expense_areas.csv`. '
              'Candidate names appear in the supplier candidate CSVs. Only case and whitespace keys are proposed for initial matching; '
              'punctuation removal is review-only, and no legal suffix stripping or fuzzy entity merges are applied. '
              'Name changes, redactions and shared postcodes require external evidence. A zero candidate count would not prove consistent identities.', '',
              '## Interpretation and limitations', '',
              'HMRC describes these as gross VAT-inclusive payments; negatives represent credit notes/memos, and dates are payment dates. '
              'Invoices split across expense types/areas can yield lines below £25,000. Expense type is an ERP material-group description. '
              '[HMRC field definitions](https://www.gov.uk/government/collections/hmrc-spending-over-25000#amounts).', '',
              'This disclosure subset is not all HMRC procurement expenditure. It does not establish unit prices, contract scope, supplier performance '
              'or realized savings. Credits, repeated identifiers and below-threshold lines are retained. No actual procurement savings are inferred. '
              'Checksums prove local byte identity relative to the receipt, not publisher authenticity signatures or completeness of undisclosed expenditure.', '',
              '## Proposed PostgreSQL model for review (not implemented)', '',
              '| Table | Key fields and types |', '|---|---|',
              '| source_file | BIGINT identity PK; reporting_month DATE (first day); URL/filename TEXT; SHA-256 CHAR(64); size BIGINT; downloaded_at TIMESTAMPTZ; status TEXT; row_count BIGINT. Version by hash; select one active version/month. |',
              '| raw_spend_row | BIGINT identity PK; file_id FK; source_record_number INTEGER; physical_line_start/end INTEGER; source_values JSONB; row_hash CHAR(64); UNIQUE(file_id, source_record_number). |',
              '| spend_line | BIGINT PK; raw_row_id UNIQUE FK; payment_date DATE; department/entity, expense type/area, supplier_raw, transaction_number, description, postcode TEXT; amount_gbp NUMERIC(20,2); optional supplier type/contract/project TEXT NULL; parse_status TEXT. |',
              '| supplier / supplier_alias | BIGINT supplier PK; canonical_name TEXT; raw_name TEXT; normalized_key TEXT; supplier_id FK; method TEXT; reviewed BOOLEAN; reviewed_at TIMESTAMPTZ. |',
              '| data_quality_issue | BIGINT PK; file_id/raw_row_id FK; issue_code/severity TEXT; original_value/details JSONB; observed_at TIMESTAMPTZ. |', '',
              'Keep raw JSONB lossless and source files immutable. Do not put a uniqueness constraint on transaction_number. '
              'Invalid typed values remain NULL with an issue record; blank optional fields remain distinguishable from absent raw keys. '
              'Index file/row relationships, payment date, supplier and reporting-month access paths in Milestone 2. '
              'Retain all duplicate candidates pending reviewed decisions.', '',
              '## Decisions before Milestone 2', '',
              '- Approve the proposed tables and version-selection policy; no database or ingestion is implemented.',
              '- Approve case/whitespace alias rules and review any punctuation variants; retain raw names in every case.',
              '- Decide how to represent publisher redactions and literal placeholders, without interpreting them as true supplier identities.',
              '- Review duplicate candidates using source references; retain them unless external evidence supports a correction. No out-of-month dates were observed in this run.' if total('outside_reporting_month') == 0 else '- Review out-of-month dates and duplicate candidates without deleting them.',
              '- Freeze these source hashes for the initial load; revised official files require a new version, never replacement of the original.', '',
              '## Reproduction and scope', '',
              'Run `procureiq download`, then `procureiq investigate`, then `python -m pytest -q` from the repository root '
              'after installing the environment described in README.md. Generated profiles are deterministic for identical bytes and dependency versions. '
              'Acquisition timestamps intentionally describe retrieval events. Synthetic fixtures are used only in tests. Milestone 1 ends here.', '']
    return '\n'.join(lines)
