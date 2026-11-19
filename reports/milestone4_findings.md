# Milestone 4 — Procurement Opportunity Radar

## Scope and observed evidence

Evaluated **12,973 active source rows**, with **£2,499,145,830.48 positive disclosed payments**, **£30,802,967.80 credit magnitude** and **£2,468,342,862.68 net payments**. Reporting months, source hashes, filters, scoring configuration and full source references are embedded in `opportunities.json` and `opportunities.csv`.

Rule version: `opportunity_rules_v1`. Filters: `{"end_month":null,"entity":null,"expense_area":null,"expense_type":null,"start_month":null,"supplier_id":null}`.

These are deterministic **review opportunities**, not confirmed inefficiency, recoverable overpayments or savings. Exposure is disclosed positive-payment context; overlapping opportunities must not be added together.

## Counts and selection

| Detector | Qualified before cap | Exported |
|---|---:|---:|
| supplier_concentration | 38 | 10 |
| purchasing_fragmentation | 8 | 8 |
| payment_pattern | 60 | 10 |
| data_quality | 6 | 6 |

Each detector is capped at 10 candidates after scoring; all exclusions and cap decisions remain in the JSON audit trail.

## Top-ranked review opportunities

| Rank | Review opportunity | Exposure GBP | Materiality | Signal | Evidence | Priority /100 |
|---|---|---:|---:|---:|---:|---:|
| 1 | Purchasing coordination review: PROJECT Mandays Supp | 721,458,382.18 | 1.0000 | 0.9415 | 1.0000 | 97.95 |
| 2 | Supplier dependency review: Physical Hosting and Infrastructure | 73,702,602.00 | 0.7370 | 1.0000 | 1.0000 | 88.17 |
| 3 | Purchasing coordination review: PROJECT Mandays HMRC | 75,800,808.58 | 0.7580 | 0.9530 | 1.0000 | 87.47 |
| 4 | Supplier dependency review: Project Development | 112,776,111.66 | 1.0000 | 0.6097 | 1.0000 | 86.34 |
| 5 | Supplier dependency review: Virtual Hosting and Infrastructure | 86,691,368.26 | 0.8669 | 0.7689 | 1.0000 | 85.92 |
| 6 | Supplier dependency review: Rent (Irrec VAT) | 83,248,930.45 | 0.8325 | 0.7717 | 1.0000 | 84.47 |
| 7 | Supplier dependency review: National postal EVAT | 64,639,933.55 | 0.6464 | 1.0000 | 1.0000 | 84.09 |
| 8 | Payment timing review: Rent (Irrec VAT) (2026-03) | 67,278,526.11 | 0.6728 | 1.0000 | 0.7500 | 80.28 |
| 9 | Payment timing review: Rent (Irrec VAT) (2025-12) | 54,745,164.77 | 0.5475 | 1.0000 | 1.0000 | 79.64 |
| 10 | Payment timing review: IT Software Licenses and Support (2026-01) | 49,887,885.94 | 0.4989 | 1.0000 | 1.0000 | 77.45 |

## Evidence and interpretation for the top five

### 1. Purchasing coordination review: PROJECT Mandays Supp

ID: `opp_4fcc1847763f23e1eb055ee2`

**Observed:** Observed £721,458,382.18 positive payments across 12 months; HHI 1754.94, 59 positive suppliers and 40 positive purchasing areas.

**Exposure definition:** All positive payments in the selected category; credits and all supporting source rows are retained.

**Reason for priority:** materiality 45.00, signal 32.95, evidence 20.00 weighted points. The complete metric values and formulas are in both exports.

**Hypothesis to investigate:** Investigate coordination across purchasing areas; the category label does not establish interchangeable services.

**Next step:** Compare specifications, frameworks, contract owners and buying requirements across the named areas before considering coordination.

**Caveats:** Broad expense types can contain non-substitutable goods and services; consolidation could increase dependency. These are disclosed gross payments, not addressable spend or savings. Opportunities can overlap; do not add their exposures or interpret exposure as savings.

Evidence: 6497 distinct primary source rows plus 0 additional context rows; all references were verified against the filtered active snapshot.

### 2. Supplier dependency review: Physical Hosting and Infrastructure

ID: `opp_0286a5a0a1eb2d09e04fb7a0`

**Observed:** Observed £73,702,602.00 positive payments across 12 months; HHI 10000.00, 1 positive suppliers and 1 positive purchasing areas.

**Exposure definition:** All positive payments in the selected category; credits and all supporting source rows are retained.

**Reason for priority:** materiality 33.17, signal 35.00, evidence 20.00 weighted points. The complete metric values and formulas are in both exports.

**Hypothesis to investigate:** Assess dependency and sourcing arrangements; concentration alone does not establish inefficient procurement.

**Next step:** Review contract scope, duration, renewal rights, continuity plans and feasible supplier alternatives with the category owner.

**Caveats:** A single disclosed supplier may be appropriate for a specialized requirement or existing contract. These are disclosed gross payments, not addressable spend or savings. Opportunities can overlap; do not add their exposures or interpret exposure as savings.

Evidence: 268 distinct primary source rows plus 0 additional context rows; all references were verified against the filtered active snapshot.

### 3. Purchasing coordination review: PROJECT Mandays HMRC

ID: `opp_3e24cc97d6e4ef04b37dbbf5`

**Observed:** Observed £75,800,808.58 positive payments across 12 months; HHI 1408.88, 27 positive suppliers and 17 positive purchasing areas.

**Exposure definition:** All positive payments in the selected category; credits and all supporting source rows are retained.

**Reason for priority:** materiality 34.11, signal 33.36, evidence 20.00 weighted points. The complete metric values and formulas are in both exports.

**Hypothesis to investigate:** Investigate coordination across purchasing areas; the category label does not establish interchangeable services.

**Next step:** Compare specifications, frameworks, contract owners and buying requirements across the named areas before considering coordination.

**Caveats:** Broad expense types can contain non-substitutable goods and services; consolidation could increase dependency. These are disclosed gross payments, not addressable spend or savings. Opportunities can overlap; do not add their exposures or interpret exposure as savings.

Evidence: 499 distinct primary source rows plus 0 additional context rows; all references were verified against the filtered active snapshot.

### 4. Supplier dependency review: Project Development

ID: `opp_51280d5e3a515cabbc5c5e73`

**Observed:** Observed £112,776,111.66 positive payments across 12 months; HHI 3951.02, 7 positive suppliers and 4 positive purchasing areas.

**Exposure definition:** All positive payments in the selected category; credits and all supporting source rows are retained.

**Reason for priority:** materiality 45.00, signal 21.34, evidence 20.00 weighted points. The complete metric values and formulas are in both exports.

**Hypothesis to investigate:** Assess dependency and sourcing arrangements; concentration alone does not establish inefficient procurement.

**Next step:** Review contract scope, duration, renewal rights, continuity plans and feasible supplier alternatives with the category owner.

**Caveats:** A single disclosed supplier may be appropriate for a specialized requirement or existing contract. These are disclosed gross payments, not addressable spend or savings. Opportunities can overlap; do not add their exposures or interpret exposure as savings.

Evidence: 336 distinct primary source rows plus 0 additional context rows; all references were verified against the filtered active snapshot.

### 5. Supplier dependency review: Virtual Hosting and Infrastructure

ID: `opp_e5c634670612d2c1a3a16d88`

**Observed:** Observed £86,691,368.26 positive payments across 12 months; HHI 5768.14, 3 positive suppliers and 1 positive purchasing areas.

**Exposure definition:** All positive payments in the selected category; credits and all supporting source rows are retained.

**Reason for priority:** materiality 39.01, signal 26.91, evidence 20.00 weighted points. The complete metric values and formulas are in both exports.

**Hypothesis to investigate:** Assess dependency and sourcing arrangements; concentration alone does not establish inefficient procurement.

**Next step:** Review contract scope, duration, renewal rights, continuity plans and feasible supplier alternatives with the category owner.

**Caveats:** A single disclosed supplier may be appropriate for a specialized requirement or existing contract. These are disclosed gross payments, not addressable spend or savings. Opportunities can overlap; do not add their exposures or interpret exposure as savings.

Evidence: 148 distinct primary source rows plus 0 additional context rows; all references were verified against the filtered active snapshot.

## Rejected or deferred patterns

| Reason | Evaluated scopes |
|---|---:|
| below_materiality | 392 |
| concentration_threshold_not_met | 10 |
| fragmentation_threshold_not_met | 40 |
| insufficient_prior_history | 1536 |
| insufficient_recurring_activity | 24 |
| no_additional_quality_evidence | 250 |
| no_material_pattern_or_zero_baseline | 489 |
| output_cap_after_scoring | 78 |
| repeated_identifier_alone_not_an_error | 1 |
| sparse_prior_activity | 987 |

Rejection counts refer to detector/category or detector/category/month evaluations, not distinct transactions. The first failed safeguard is recorded. For repeated identifiers alone, the scope includes a separate row count; this is not a missing-data error. Cap exclusions are qualified candidates deferred for review, rather than failed evidence thresholds.

## Configuration and score definitions

Default materiality component is `min(exposure / £100,000,000, 1)`. Signal and evidence are independently bounded to [0,1]. Priority is `100 × (0.45 × materiality + 0.35 × signal + 0.20 × evidence)` under the default configuration. These are transparent analyst priorities, not calibrated probabilities or predicted financial benefits.

```json
{
  "category_min_gbp": "5000000",
  "min_active_months": 6,
  "min_mapping": "0.95",
  "min_source_coverage": "0.90",
  "concentration_hhi": "2500",
  "concentration_top_one": "0.50",
  "concentration_top_three": "0.80",
  "fragmentation_suppliers": 10,
  "fragmentation_areas": 3,
  "fragmentation_max_hhi": "2500",
  "fragmentation_max_top_three": "0.80",
  "history_months": 6,
  "history_active_months": 4,
  "payment_min_gbp": "1000000",
  "payment_change_ratio": "0.50",
  "spike_ratio": "2",
  "mad_multiple": "6",
  "month_share": "0.35",
  "credit_ratio": "0.20",
  "quality_min_gbp": "25000",
  "quality_min_missing_rows": 3,
  "materiality_reference_gbp": "100000000",
  "materiality_weight": "0.45",
  "signal_weight": "0.35",
  "evidence_weight": "0.20",
  "max_per_type": 10
}
```

See `docs/opportunity_methodology.md` for detector-specific formulas. Category patterns require recurring material expenditure and mapping coverage. Payment patterns need covered prior observations; March receives a lower evidence score because year-end timing is plausible. Quality flags count the union of affected rows, preserving all original records.

## Limitations and review decisions

- The public disclosure subset is not complete procurement expenditure, unit pricing or contract/performance data.
- High concentration can be appropriate. Fragmentation does not establish interchangeable goods/services.
- Short payment histories cannot establish seasonality. MAD=0 uses an explicit ratio-and-absolute-change fallback, not a claim of statistical significance.
- A payment-change candidate includes contextual historical payments in its exposure; this is not the amount of an error.
- Supplier aliases and duplicate-looking rows require external confirmation before any correction.
- Reference materiality and thresholds are configurable review assumptions. Large exposures can saturate the materiality component; scores are not comparable to estimated savings.
- Candidate exposures overlap across detector types and rolling windows. The exports intentionally contain no summed opportunity exposure or savings total.

## Reproduce

```sh
procureiq opportunities detect
procureiq opportunities verify
procureiq opportunities export
procureiq db verify
procureiq analytics verify
python -m pytest -q
```

The engine uses a read-only repeatable-read snapshot and preserves existing ingestion and financial results. No Streamlit dashboard, financial scenario model or AI functionality is implemented.
