# Milestone 3 verification record

Executed on 15 October 2026 with Python 3.14.7 and PostgreSQL 17.11 (Homebrew), using the existing pinned environment and separate `procureiq_test` integration database.

## Commands actually executed

- `procureiq db init`: applied only new migration `003_analytical_views.sql`; prior migrations retained their checksums.
- `python -m pytest tests/test_analytics.py -q`: 13 analytical test cases passed in 8.23s during development.
- `python -m pytest -q`: **59 passed in 31.88s**, with no skips or failures, after the supplier-month verification checks were added.
- `procureiq db verify`: the existing frozen-source gate passed for all twelve monthly versions and all 12,973 source/typed rows.
- `procureiq analytics verify`: independent Decimal verification passed for money, category/area/entity grouping, ranking, shares, Pareto, concentration and calendar/supplier-month trends.
- `procureiq analytics summary`: generated the verified actual dataset summary.
- `procureiq analytics export`: generated ten full-period CSVs, source/migration metadata, verification evidence and the findings report.
- `procureiq analytics export --start-month 2025-07 --end-month 2025-08 --expense-area 'CDIO - Core'`: generated a separate filtered export and passed recalculated verification.
- `python -m compileall -q src/procureiq`: passed.

The main database received the additive analytical migration only. Tests reset schemas exclusively in the guarded test database; analytics commands use read-only snapshots. No expenditure records, mappings, active-version flags or source files were rewritten by analytics.

## Financial acceptance

| Population | Lines | Positive GBP | Credit magnitude GBP | Net GBP |
|---|---:|---:|---:|---:|
| Complete active baseline | 12,973 | 2,499,145,830.48 | 30,802,967.80 | 2,468,342,862.68 |
| July–August 2025, CDIO - Core | 711 | 146,434,867.50 | 1,623,391.22 | 144,811,476.28 |

Money reconciles exactly; there are no floating-point tolerances. Each category and expense-area group is independently recomputed from selected lines and each dimension's totals equal the full selected population. Supplier-month totals are independently checked. The source gate also verifies actual CSV data and all monthly baseline totals, separately from database analytics consistency.

## Analytical results

- Largest supplier: Capgemini, £410,066,806.54 positive payments; 16.4082784421283757% of the full positive-payment total.
- Largest expense type: PROJECT Mandays Supp, £721,458,382.18 positive payments.
- Largest expense area: CDIO - Core, £1,090,999,186.45 positive payments.
- 456 resolved supplier keys; 455 have positive payments. Mapping coverage by positive value is 100%; unresolved positive payments are £0.
- 32 suppliers (7.0329670329670330% of positive-payment suppliers) reach at least 80% of resolved positive payments.
- Overall HHI: 541.1250159803472288; top-three share: 34.4613652679317816%.
- 139 expense types have one resolved positive-payment supplier.

## Test coverage and interpretation

Synthetic tests independently establish single-supplier HHI 10,000, equal-share HHI 5,000, a four-supplier HHI of 3,000, top-one/top-three shares and exact 80% crossing rules. Tests exercise case/whitespace aliases, unknown suppliers, credit-only and zero groups, NULL expense classifications, duplicate rows, deterministic ties, all five filter dimensions, SQL-looking text literals, empty selections, inactive revisions, explicit activation, missing calendar months and zero prior-month denominators. An actual-data integration test verifies full analytics and unfiltered SQL view parity. The full suite also retains the earlier acquisition, ingestion, rollback and source-preservation tests.

No execution blockers remain. Text filters are exact, single-value selections; multi-select and explicit unresolved-only selection are documented future extensions. High observed concentration is not proof of inefficient procurement. No scoring, dashboard, scenarios or AI were implemented. Stop for Milestone 3 review.
