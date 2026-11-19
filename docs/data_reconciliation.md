# Database reconciliation — Milestone 2

Executed on 15 October 2026 against the dedicated local PostgreSQL 17.11 (Homebrew) instance, using Python 3.14.7. This is an executed result, not a projected target. Machine-readable evidence: `reports/database_verification.json` and `reports/database_reconciliation.csv`.

## Acceptance results

| Table (all registered versions) | Actual records |
|---|---:|
| `source_file` | 12 |
| `raw_spend_row` | 12,973 |
| `spend_line` | 12,973 |
| `supplier` | 456 |
| `supplier_alias` | 460 |
| `data_quality_issue` | 1,761 |

Exactly 12 original versions are active. Every one of the 12,973 raw rows has exactly one typed row, verified field by field against the source. No monetary/date parsing failures occurred. Source hashes, row ordinals, physical lines, alias references and quality evidence were checked.

| Measure | Exact GBP |
|---|---:|
| positive_payments_gbp | 2499145830.48 |
| credit_magnitude_gbp | 30802967.80 |
| net_disclosed_gbp | 2468342862.68 |

Positive payments − credit magnitude = net payments, without floating-point tolerances. Every monthly value also agrees with the Milestone 1 CSV report and the frozen baseline manifest.

| Reporting month | Rows | Positive GBP | Credit GBP | Net GBP | Result |
|---|---:|---:|---:|---:|---|
| 2025-04 | 1116 | 217220774.13 | 2263741.14 | 214957032.99 | PASS |
| 2025-05 | 946 | 187871937.71 | 2734879.94 | 185137057.77 | PASS |
| 2025-06 | 962 | 243706737.72 | 1087793.90 | 242618943.82 | PASS |
| 2025-07 | 1013 | 188451137.50 | 2239344.99 | 186211792.51 | PASS |
| 2025-08 | 907 | 157385698.65 | 577649.46 | 156808049.19 | PASS |
| 2025-09 | 1057 | 198514838.22 | 1552338.10 | 196962500.12 | PASS |
| 2025-10 | 1038 | 202023018.71 | 2241452.11 | 199781566.60 | PASS |
| 2025-11 | 1015 | 172072109.00 | 2237833.53 | 169834275.47 | PASS |
| 2025-12 | 1197 | 241421719.34 | 2168448.44 | 239253270.90 | PASS |
| 2026-01 | 1022 | 201247311.09 | 1075997.85 | 200171313.24 | PASS |
| 2026-02 | 1117 | 179685339.33 | 5907443.31 | 173777896.02 | PASS |
| 2026-03 | 1583 | 309545209.08 | 6716045.03 | 302829164.05 | PASS |

Retained sign/threshold counts: **322 negative**, **1 zero**, **1,648 positive below £25,000**. All **73 exact duplicate-candidate rows** remain; no transaction-ID deduplication occurred.

## Supplier and quality results

- Original exact nonblank supplier names: **460**.
- Normalized supplier keys: **456**, using only whitespace/casefold rules.
- Automatically resolved aliases: **460**; unresolved placeholder aliases: **0**.
- Active row mapping coverage: **12,973 resolved**, **0 unresolved**.
- **2 punctuation review groups** remain separate supplier identities. See `reports/supplier_mapping_review.csv`. These are not included in the unresolved-placeholder count.
- **1,761 quality records** retained: **1,688 repeated-identifier flags** and **73 exact-duplicate candidate flags**. Flags overlap and must not be added to infer a count of distinct affected rows.
- Review flags remain unresolved until evidence supports a human decision. Automated supplier matching does not establish verified legal identities.

## Execution and test evidence

Commands executed against the project database: `procureiq db init`, `procureiq db load`, `procureiq db verify`, then a second `db load` and `db verify`. The second load returned `verified_existing` for all twelve files and preserved row/payment totals.

Final automated suite: **46 passed in 18.07s; no failures or skips**. PostgreSQL tests used the separate `procureiq_test` database, not the project database. Coverage includes migration creation, FK/unique/active constraints, immutable raw rows, actual full ingestion and monthly reconciliation, safe reruns, conflicting typed/quality content, hash mismatch, transaction rollback, source activation, optional/unknown columns, normalization, placeholders, and numeric overflow. Milestone 1 tests also passed.

## Verification SQL

```sql
-- Connect to the configured database; all default reporting queries select active versions.
SELECT count(*) AS active_records FROM procureiq.active_spend_line;
SELECT * FROM procureiq.monthly_reconciliation ORDER BY reporting_month;
SELECT * FROM procureiq.supplier_mapping_coverage;
SELECT issue_code, count(*) FROM procureiq.unresolved_quality_issues GROUP BY issue_code;

-- Completeness across ALL registered versions (must return zero).
SELECT count(*) AS raw_without_typed
FROM procureiq.raw_spend_row r LEFT JOIN procureiq.spend_line s USING(raw_row_id)
WHERE s.raw_row_id IS NULL;

-- Active source versions and original counts.
SELECT reporting_month, sha256, original_row_count, active, import_status
FROM procureiq.source_file ORDER BY reporting_month, file_id;
```

## Remaining decisions and scope

No execution defects or blockers remain from the completed checks. Punctuation candidates require human review before any broader mapping policy; no such merges were performed. New source revisions load inactive and require explicit activation. The default acceptance verifier remains tied to the original approved baseline; approving a revised baseline is a later decision.

Native PostgreSQL was executed and tested; the supplied Docker Compose alternative was not executed. The server is local development infrastructure, not a production security deployment. These disclosed payments are not total HMRC procurement expenditure and do not demonstrate savings. Milestone 2 ends here; no dashboard, opportunity engine, scenarios, AI or Milestone 3 analytical views were implemented.
