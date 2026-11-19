# Milestone 1 — HMRC dataset investigation

## Executive dataset summary

Investigated **12 actual monthly source files**, April 2025–March 2026 inclusive, containing **12,973 source records**. No rows were removed, no supplier identities were merged, and transaction identifiers remain strings. Counts describe published lines, not unique invoices.

Positive disclosed payments: **£2,499,145,830.48**; credit magnitude: **£30,802,967.80**; net disclosed payments: **£2,468,342,862.68**.

[Official dataset catalogue](https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc). Exact monthly URLs, byte sizes, SHA-256 hashes and acquisition timestamps are in `file_inventory.csv` and `../manifests/download_manifest.json`. Findings refer to those frozen versions.
Acquisition provenance: 12 files verified against official downloads; 0 manual files with unverified origin.

## Coverage and financial reconciliation

| Reporting month | Rows | Columns | Positive GBP | Credit magnitude GBP | Net GBP |
|---|---:|---:|---:|---:|---:|
| 2025-04 | 1,116 | 10 | 217220774.13 | 2263741.14 | 214957032.99 |
| 2025-05 | 946 | 10 | 187871937.71 | 2734879.94 | 185137057.77 |
| 2025-06 | 962 | 10 | 243706737.72 | 1087793.90 | 242618943.82 |
| 2025-07 | 1,013 | 13 | 188451137.50 | 2239344.99 | 186211792.51 |
| 2025-08 | 907 | 13 | 157385698.65 | 577649.46 | 156808049.19 |
| 2025-09 | 1,057 | 10 | 198514838.22 | 1552338.10 | 196962500.12 |
| 2025-10 | 1,038 | 10 | 202023018.71 | 2241452.11 | 199781566.60 |
| 2025-11 | 1,015 | 10 | 172072109.00 | 2237833.53 | 169834275.47 |
| 2025-12 | 1,197 | 10 | 241421719.34 | 2168448.44 | 239253270.90 |
| 2026-01 | 1,022 | 10 | 201247311.09 | 1075997.85 | 200171313.24 |
| 2026-02 | 1,117 | 10 | 179685339.33 | 5907443.31 | 173777896.02 |
| 2026-03 | 1,583 | 10 | 309545209.08 | 6716045.03 | 302829164.05 |

Every monthly total satisfies positive − credit magnitude = net, using Decimal throughout. Unparsed/missing monetary values: 0; totals include only successfully parsed amounts. Reporting month comes from the catalogue, not the payment date.

## Schema and file formats

- 2025-04: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-05: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-06: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-07: 13 columns; added versus April: `["Supplier Type", "Contract Number", "Project Code"]`; absent: `[]`.
- 2025-08: 13 columns; added versus April: `["Supplier Type", "Contract Number", "Project Code"]`; absent: `[]`.
- 2025-09: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-10: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-11: 10 columns; added versus April: `[]`; absent: `[]`.
- 2025-12: 10 columns; added versus April: `[]`; absent: `[]`.
- 2026-01: 10 columns; added versus April: `[]`; absent: `[]`.
- 2026-02: 10 columns; added versus April: `[]`; absent: `[]`.
- 2026-03: 10 columns; added versus April: `[]`; absent: `[]`.

Exact baseline headers: `Department family`, `Entity`, `Date`, `Expense type`, `Expense area`, `Supplier`, `Transaction number`, `Amount`, `Description`, `Supplier Postcode`.
Exact ordered headers for every month are also recorded in `schema_comparison.csv`.

Selected decoding(s): cp1252. Decoding tries strict UTF-8 (including BOM), then Windows-1252. Successful decoding is evidence of compatibility, not proof of the publisher’s encoding declaration; ASCII-only files are explicitly flagged.
Observed delimiters: [',']. Observed date formats: {'%d/%m/%Y': 12973} (counts across all files; monthly details in the CSV).
Source monetary fractional digits: {'0': 1564, '1': 750, '2': 10659}; pound-symbol values: 3715; comma-grouped values: 3645.
Monetary format observations (fractional digit counts, currency symbols and grouping separators) are in `data_quality_summary.csv`. Values with more than two decimal places are rejected rather than rounded. Missing means empty or whitespace-only; literal text such as NA is preserved.

## Data quality

| Metric | Count |
|---|---:|
| ragged_rows | 0 |
| missing_amounts | 0 |
| invalid_amounts | 0 |
| missing_dates | 0 |
| invalid_dates | 0 |
| negative_amounts | 322 |
| zero_amounts | 1 |
| positive_below_25000 | 1,648 |
| signed_below_25000 | 1,971 |
| absolute_below_25000 | 1,677 |
| repeated_identifier_groups | 662 |
| repeated_identifier_rows | 1,688 |
| repeated_identifier_excess | 1,026 |
| exact_duplicate_rows | 73 |
| exact_duplicate_excess | 41 |
| outside_reporting_month | 0 |

Across the whole period, 790 distinct nonblank identifier strings occur more than once, covering 1,946 rows. Monthly group counts above may count the same identifier in different months.
Across the union schema, 73 rows belong to exact duplicate candidates (41 occurrences after the first). Absent optional fields are compared as blank for this cross-file check.
Repeated identifier rows count every member of a repeated group; excess counts all occurrences after the first. Exact duplicates compare every source field within a file, before any normalization. Neither indicates proven duplicate payment.
Signed below-threshold counts include negative and zero amounts; positive and absolute-value counts are supplied separately.

### Blank values in columns present in each file

- 2025-04: none.
- 2025-05: none.
- 2025-06: none.
- 2025-07: {'Supplier Type': 1013, 'Contract Number': 1013, 'Project Code': 1013}.
- 2025-08: {'Supplier Type': 907, 'Contract Number': 907, 'Project Code': 907}.
- 2025-09: none.
- 2025-10: none.
- 2025-11: none.
- 2025-12: none.
- 2026-01: none.
- 2026-02: none.
- 2026-03: none.

Absent optional columns are schema differences, not blank cells. `quality_issues.jsonl` supplies source-file/hash and record/physical-line references for parsing, date and duplicate candidates. `source_rows.jsonl` (generated locally, gitignored) preserves every decoded field plus provenance; original bytes remain in `data/raw/`.

## Supplier-name normalization considerations

- Distinct exact nonblank Supplier values: 460.
- Distinct exact nonblank Expense type values: 256.
- Distinct exact nonblank Expense area values: 69.
- Case/whitespace variant groups: 4.
- Review-only punctuation-insensitive groups: 6.

Complete frequency lists are in `supplier_names.csv`, `expense_types.csv` and `expense_areas.csv`. Candidate names appear in the supplier candidate CSVs. Only case and whitespace keys are proposed for initial matching; punctuation removal is review-only, and no legal suffix stripping or fuzzy entity merges are applied. Name changes, redactions and shared postcodes require external evidence. A zero candidate count would not prove consistent identities.

## Interpretation and limitations

HMRC describes these as gross VAT-inclusive payments; negatives represent credit notes/memos, and dates are payment dates. Invoices split across expense types/areas can yield lines below £25,000. Expense type is an ERP material-group description. [HMRC field definitions](https://www.gov.uk/government/collections/hmrc-spending-over-25000#amounts).

This disclosure subset is not all HMRC procurement expenditure. It does not establish unit prices, contract scope, supplier performance or realized savings. Credits, repeated identifiers and below-threshold lines are retained. No actual procurement savings are inferred. Checksums prove local byte identity relative to the receipt, not publisher authenticity signatures or completeness of undisclosed expenditure.

## Proposed PostgreSQL model for review (not implemented)

| Table | Key fields and types |
|---|---|
| source_file | BIGINT identity PK; reporting_month DATE (first day); URL/filename TEXT; SHA-256 CHAR(64); size BIGINT; downloaded_at TIMESTAMPTZ; status TEXT; row_count BIGINT. Version by hash; select one active version/month. |
| raw_spend_row | BIGINT identity PK; file_id FK; source_record_number INTEGER; physical_line_start/end INTEGER; source_values JSONB; row_hash CHAR(64); UNIQUE(file_id, source_record_number). |
| spend_line | BIGINT PK; raw_row_id UNIQUE FK; payment_date DATE; department/entity, expense type/area, supplier_raw, transaction_number, description, postcode TEXT; amount_gbp NUMERIC(20,2); optional supplier type/contract/project TEXT NULL; parse_status TEXT. |
| supplier / supplier_alias | BIGINT supplier PK; canonical_name TEXT; raw_name TEXT; normalized_key TEXT; supplier_id FK; method TEXT; reviewed BOOLEAN; reviewed_at TIMESTAMPTZ. |
| data_quality_issue | BIGINT PK; file_id/raw_row_id FK; issue_code/severity TEXT; original_value/details JSONB; observed_at TIMESTAMPTZ. |

Keep raw JSONB lossless and source files immutable. Do not put a uniqueness constraint on transaction_number. Invalid typed values remain NULL with an issue record; blank optional fields remain distinguishable from absent raw keys. Index file/row relationships, payment date, supplier and reporting-month access paths in Milestone 2. Retain all duplicate candidates pending reviewed decisions.

## Decisions before Milestone 2

- Approve the proposed tables and version-selection policy; no database or ingestion is implemented.
- Approve case/whitespace alias rules and review any punctuation variants; retain raw names in every case.
- Decide how to represent publisher redactions and literal placeholders, without interpreting them as true supplier identities.
- Review duplicate candidates using source references; retain them unless external evidence supports a correction. No out-of-month dates were observed in this run.
- Freeze these source hashes for the initial load; revised official files require a new version, never replacement of the original.

## Reproduction and scope

Run `procureiq download`, then `procureiq investigate`, then `python -m pytest -q` from the repository root after installing the environment described in README.md. Generated profiles are deterministic for identical bytes and dependency versions. Acquisition timestamps intentionally describe retrieval events. Synthetic fixtures are used only in tests. Milestone 1 ends here.
