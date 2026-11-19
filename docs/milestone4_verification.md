# Milestone 4 verification record

Executed on 15 October 2026 using Python 3.14.7, PostgreSQL 17.11 and the existing environment. Integration tests used only the guarded, separate `procureiq_test` database.

## Executed checks

- `python -m pytest tests/test_opportunities.py -q`: 19 passed during development.
- `python -m pytest -q`: **78 passed in 49.97s**, no skips or failures.
- `procureiq db verify`: passed the frozen-source reconciliation gate.
- `procureiq analytics verify`: passed independent analytical reconciliation.
- `procureiq opportunities detect`: generated the actual ranked population.
- `procureiq opportunities verify`: passed all 34 selected opportunity checks across 12,973 source rows.
- `procureiq opportunities export`: wrote the findings report, CSV and JSON with complete evidence and scoring configuration.
- `procureiq opportunities verify --supplier-id 31`: passed on 2,598 selected rows; concentration opportunities correctly suppressed (zero), four payment-pattern and one quality review emitted.
- `python -m compileall -q src/procureiq`: passed.
- CSV/JSON comparison: all 34 ordered IDs, exact exposures and full primary source references agree. Python's CSV reader required an increased field-size limit because evidence arrays are deliberately complete.

## Actual-data acceptance

The selected population remains 12,973 rows: positive payments £2,499,145,830.48, credit magnitude £30,802,967.80 and net £2,468,342,862.68. Original source hashes and frozen monthly reconciliation passed. Opportunity commands use read-only repeatable-read snapshots; no source rows, mappings, active versions or migrations were changed.

| Detector | Qualified before cap | Exported |
|---|---:|---:|
| Supplier concentration | 38 | 10 |
| Purchasing fragmentation | 8 | 8 |
| Payment pattern | 60 | 10 |
| Data quality | 6 | 6 |

The default cap defers 78 candidates after scoring. Exclusion records retain their scopes, IDs and scores. Financial exposures can overlap and are never added as savings.

## Coverage and review limitations

Tests cover all four detectors, negative cases, materiality/recurrence/history gates, missing coverage, zero baselines, credit activity, March evidence adjustment, raw MAD, score bounds and weights, unique-row quality exposure, harmless repeated identifiers, contextual identifiers, supplier aliases, unresolved names, filters, injection-shaped literals, supplier-filter concentration suppression, inactive revisions, stable IDs and ranking, tampered evidence/exposure rejection, exports and preservation of existing analytics.

Thresholds and materiality scaling are initial review policy, not empirically calibrated predictions. Six prior covered months constrain available history. March receives an explicit 0.75 evidence factor; this is not a learned seasonal adjustment. Broad categories do not establish substitutable services. Duplicate candidates and aliases require investigation, not automatic deletion or merging. Large CSV evidence cells may exceed spreadsheet limits; JSON retains complete records.

See [findings](../reports/milestone4_findings.md) for top-ranked exposures and score breakdowns, and [methodology](opportunity_methodology.md) for formulas and exclusions. No execution blockers remain.
