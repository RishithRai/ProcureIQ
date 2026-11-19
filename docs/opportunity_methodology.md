# Opportunity methodology — Milestone 4

## Purpose and architecture

The Opportunity Radar generates **questions for procurement review**, not verified waste, fraud, inefficiency, financial benefits or savings. All observations refer to the selected public HMRC payment-disclosure records. Exposure is positive gross VAT-inclusive disclosed payments associated with the question, not addressable spend or the value of an accounting error.

The engine reuses the approved PostgreSQL analytical functions, supplier keys and filter semantics. No new migration, infrastructure, database table or dependency is added.

| Component | Responsibility |
|---|---|
| `opportunity_data.py` | Read filtered lines, category concentration, calendar coverage, source references and separate quality issues in one snapshot. |
| `opportunity_detectors.py` | Four deterministic detectors; return candidates and explicit rejection reasons. |
| `opportunity_model.py` | Typed candidate, validated configuration and Decimal priority arithmetic. |
| `opportunities.py` | Assemble evidence, IDs and scores; rank/cap candidates; verify references and arithmetic; read-only CLI orchestration. |
| `opportunity_reporting.py` | JSON, CSV and generated findings with evidence/hypothesis separation. |

CLI execution uses a read-only repeatable-read transaction. Monetary lines are never joined directly to multiple quality flags. All original records, supplier mappings, source versions and analytical totals remain unchanged. The `source_lines` and `query` accessors apply month/type/area/entity/supplier filters before detectors evaluate a category.

## Configuration and scoring

Default rules are `opportunity_rules_v1`. Every opportunity and export contains the complete configuration. `--config config/opportunities.example.json` accepts JSON overrides; unspecified settings retain their defaults. Money and fractional values are parsed as Decimal, including decimal-valued JSON numbers. Unknown keys, nonfinite values, invalid bounds, non-integer counts and weights not summing to exactly one are rejected.

For exposed positive payments `E`:

```
materiality = min(E / £100,000,000, 1)
priority = 100 × (0.45 × materiality + 0.35 × signal + 0.20 × evidence)
```

Each component is bounded to [0,1]. Exports retain unrounded Decimal values and the three weighted-point contributions; display tables round only for readability. Deterministic ranking uses descending unrounded score, then opportunity ID.

The £100m reference provides a fixed, auditable scale for this roughly £2.5bn disclosed positive-payment population. It is an analyst priority convention, not an economic model. It stays fixed under filtering, so a small selection does not make a small amount appear financially large. It can be changed explicitly in configuration. Exposures at or above the reference saturate materiality, leaving signal and evidence to distinguish them.

- **Exposure:** financial context measured from distinct referenced source rows.
- **Signal:** strength of the selected descriptive rule, not evidence of causation.
- **Evidence:** completeness, coverage and relevant history; its definition depends on the detector.
- **Priority:** relative review attention under this explicit configuration.

The label `stronger_evidence` means an evidence component at least 0.8; otherwise it is `limited_evidence`. Neither label means a probability of inefficiency or verified legal identity. These labels and weights are not calibrated with procurement outcomes.

After scoring, keep at most **10 opportunities per detector** (maximum 40 by default). Qualified candidates beyond the cap retain scope, ID and score in the rejection/deferment audit trail. The JSON distinguishes qualified counts before the cap from exported counts. Cap changes and threshold changes are configuration changes and therefore produce new opportunity IDs.

## Shared category safeguards

Concentration and fragmentation both require:

- A nonblank expense category.
- At least **£5m** selected positive payments.
- Positive payments in at least **6 distinct reporting months**.
- At least **90%** of calendar months in the selected range covered by active source files.
- All selected category rows have valid typed status and parsed monetary values.
- At least **95%** of category positive value mapped to resolved supplier keys.

The £5m cutoff is roughly 0.2% of this period's positive disclosure total, chosen to avoid large lists of trivial categories. It is a configurable review convention. A category with one supplier and £20m in a single month is rejected for sparse activity, even though HHI is 10,000. Six small monthly payments are also insufficient when the materiality gate fails.

Definitions used below:

- `source_coverage = covered_source_months / selected_calendar_months`.
- `valid_row_fraction = valid typed rows with parsed amounts / category rows`.
- `recurrence = positive_activity_months / selected_calendar_months`.
- `mapping = resolved_positive_gbp / category_positive_gbp`.

Category evidence = `source_coverage × valid_row_fraction × recurrence × mapping`.

Coverage is based on publication files. A covered file with no category lines is not evidence that all actual purchasing for that category was zero. The selected calendar has the same explicit/default bounds as Milestone 3, so broad date filters containing missing periods reduce evidence.

## A. Supplier concentration

After shared safeguards, require **HHI ≥ 2,500** and either **top-one share ≥ 50%** or **top-three share ≥ 80%** of resolved positive payments. These are descriptive review thresholds, not regulatory classifications or proof of market concentration.

```
signal = (HHI/10,000 + top_one_fraction + top_three_fraction) / 3
```

Exposure includes all positive payments on the selected category rows; credits remain in numerical metrics and supporting references. Metrics disclose HHI, supplier counts/shares, top-three named supplier keys, mapping coverage, positive activity months and area counts.

**Supplier-filtered populations disable this detector entirely**, since selecting one supplier makes HHI trivially concentrated. Other filters are applied before the category SQL calculations and can materially change the result.

Interpretation: review dependency, continuity, contract alternatives and sourcing arrangements. A single supplier may be entirely appropriate. External contract scope, duration, tender/framework terms and feasible alternatives are required before considering any procurement action.

## B. Purchasing fragmentation

After shared safeguards, require:

- At least **10 resolved positive-payment suppliers**.
- At least **3 distinct areas with positive payments**.
- **HHI ≤ 2,500**.
- **Top-three share ≤ 80%** of resolved positives.

```
signal = (min(positive_supplier_count / (2 × minimum_suppliers), 1)
        + min(positive_area_count / (2 × minimum_areas), 1)
        + (1 - HHI/10,000)) / 3
```

Exposure and evidence use the same category definitions as concentration. Area/supplier counts are recalculated from selected lines, not from overall results. The broader SQL `expense_area_count` includes all activity; the detector explicitly uses `positive_expense_areas`.

Interpretation: investigate purchasing coordination across areas. A broad expense label is not evidence of interchangeable specifications, overlapping contracts or substitutable suppliers. Coordination might help, be irrelevant, or increase dependency; this engine does not select a remedy or estimate consolidation savings.

## C. Payment-pattern review

Scope is **expense category and reporting month**. The detector examines the immediately preceding **6 calendar months** in the selected window. All six prior months and the current month must have source coverage, all supporting typed rows must be valid, and at least **4 prior months** must contain positive payments or credits. No hidden history outside the requested filter is fetched.

From the six prior positive-payment totals, compute an exact Decimal median `m` and median absolute deviation `MAD = median(abs(x-m))`. The current positive amount is `p`, preceding month's positive amount is `previous`, current credits are `c`, and selected-category positive total is `T`.

A candidate needs at least one trigger:

| Trigger | Default conditions | Signal contribution, bounded to 1 |
|---|---|---|
| Historical positive spike | `m > 0`; `p ≥ £1m`; `p-m ≥ £1m`; `p/m ≥ 2`; and either MAD=0 or `(p-m)/MAD ≥ 6` | `(p/m - 1)/2` |
| Material monthly change | `m > 0`; `abs(p-m) ≥ £1m`; `previous > 0`; `abs(p-previous) ≥ £1m`; `abs((p-previous)/previous) ≥ 0.50` | `abs((p-previous)/previous)` |
| Concentrated payment month | `m > 0`; `p/T ≥ 0.35`; `p/m ≥ 2`; `p-m ≥ £1m` | `(p/T)/(2 × month_share_threshold)` |
| Material credit activity | `c ≥ £1m`; `c/(p+c) ≥ 0.20` | `(c/(p+c))/(2 × credit_ratio_threshold)` |

Candidate signal is the maximum contribution among fired triggers, not their sum. Trigger names and individual strengths are exported. `p+c` is the unsigned current payment volume; this prevents division by a near-zero or negative net denominator. Credit-only current months can therefore be reviewed with sufficient preceding activity.

MAD=0 does not cause division by zero: the spike rule explicitly falls back to the absolute increase and ratio conditions. A zero historical median suppresses positive spike/change/month-concentration triggers; it is not converted to a tiny denominator. Credit review remains possible if its independent conditions are met. This is an explainable median/MAD heuristic, **not a significance test, forecast or trained anomaly model**.

Payment evidence = `active_prior_months / history_months`, multiplied by **0.75 for March**. The March adjustment is an explicit implementation constant of rule v1, reflecting a plausible financial year-end timing explanation. It is not a seasonally estimated coefficient; a single year's disclosure cannot establish seasonality. Source/typed completeness is enforced before emission rather than merely scored down. The rule currently detects within each category, not every supplier/category combination, to keep the result manageable.

**Exposure includes positive payments from the current month plus the six-month historical context window.** This supports review of payment schedules and comparability; it is not the size of a suspected error. `current_positive_gbp`, `current_credit_gbp`, median, MAD, prior values/months, differences, ratios and year-end context are separately exported. References include all actual records in the window. A zero-current month can have only historical source references; it does not fabricate a current transaction.

False-positive explanations include milestones, annual renewals, settlement timing, invoice splitting, delayed disclosure and credit adjustments. A payment pattern never implies fraud, overpayment or accounting error.

## D. Data-quality review

Start from persisted unresolved quality issues for the selected rows/files. Retrieve these separately from financial lines. Re-evaluate supplier punctuation candidates using the **same `punctuation_candidates` rule** used to generate the Milestone 2 supplier mapping review output; do not apply a stale full-population CSV to a filtered selection.

The engine considers:

- Exact duplicate-row candidates and other existing non-repetition quality flags.
- Repeated nonblank identifiers **within a selected source file**, only when their selected rows span more than one resolved supplier or more than one payment date. This is a context-review question, not an error conclusion. Plain repeated identifiers alone are rejected as a reason to emit a candidate; legitimate invoice splits are retained.
- Punctuation-based alias candidates with at least two distinct case/whitespace keys present in the selected population. No identities are merged.
- NULL/unresolved suppliers, NULL amounts, invalid typed status, or missing department/entity/type/area/transaction/date information. Expected empty optional fields such as Project Code do not cause a quality opportunity.

Candidates are grouped by expense category, including an unclassified bucket when needed. The primary affected rows are a **set union** across all applicable flags. Exposure sums positive amounts from this set exactly once. Flag-specific counts can overlap and are never summed as an affected-row count.

Require at least **£25,000** measurable affected positive payments, or at least **3 missing/unresolved rows** when money may not be measurable. This threshold is a review-materiality convention, not an assertion that below-threshold published lines are wrong. Unknown amounts remain unknown; a zero measurable exposure does not claim the missing value was zero. A pure-credit issue below the positive-exposure gate is not promoted without the missing-row safeguard; credit activity has its own payment detector.

```
flag_strength = maximum applicable strength:
    1.0  invalid/missing/unresolved/schema/ragged evidence
    0.8  exact duplicate candidate
    0.5  identifier context review
    0.4  alias/other review observations
signal = (flag_strength + min(affected_row_fraction / 0.10, 1)) / 2
evidence = source_coverage × 0.8
```

The flag weights and 10% saturation point are transparent review conventions. The evidence ceiling reflects known row provenance but unreviewed interpretation; it is not a probability that an issue is real. For alias or identifier context spanning categories, extra source references are exported separately as `context_source_references`. **These extra rows are not added to that candidate's financial exposure.**

## IDs, evidence and overlapping exposure

An opportunity ID is a SHA-256-derived identifier over rule version, detector type, analysis scope, filters, configuration and the ordered active month/hash basis. No wall-clock time or random value is included. The same snapshot/filter/configuration produces identical IDs and deterministic ordering. A source-version, filter or policy change yields new IDs; the full active-version list is intentionally part of the basis even if some files lie outside a date filter.

Each opportunity includes primary and additional context references with actual raw-row ID, file ID, filename, SHA-256, data-record ordinal, physical line boundaries, reporting month and original transaction identifier. File hash plus record ordinal is the portable identity; numeric database IDs are local conveniences. References must resolve to actual active records within the selected population. No records or identifiers are invented, and references are not sampled or truncated.

Exposures overlap between concentration and fragmentation, between category and quality reviews, and especially between rolling payment windows. The engine deliberately exports **no aggregate opportunity-exposure or savings total**. The separate population total is the selected dataset's reconciled total, not a sum of opportunities.

## CLI and output

```sh
procureiq opportunities detect
procureiq opportunities verify
procureiq opportunities export
procureiq opportunities detect --expense-area 'CDIO - Core'
procureiq opportunities export --start-month 2025-07 --end-month 2026-03 --config config/opportunities.example.json
```

All commands support Milestone 3's exact single-value text filters and normalized supplier-ID filter. `--config PATH` supplies thresholds/weights; `export --output PATH` chooses an output directory. `detect` prints ranked summaries rather than thousands of raw references. `verify` checks evidence, exposures, bounds, arithmetic, suppression, caps and deterministic reruns. `export` embeds the complete evidence and scoring breakdowns.

Unfiltered default exports are `reports/opportunities.csv`, `reports/opportunities.json` and `reports/milestone4_findings.md`. Filtered or nondefault-config runs use a separate deterministic `reports/opportunity_runs/<filter-and-config-hash>/` folder unless `--output` is supplied. This prevents an ordinary filtered run from replacing the full-period findings. Nested JSON cells in CSV preserve configuration, metrics, caveats and references; JSON Decimal amounts are serialized as strings so precision is retained. Empty results still produce a CSV header, JSON basis and a findings report.

The default maximum result is 40 candidates. Detailed rejection records distinguish insufficient history/materiality/mapping, missing source periods, nonqualifying signals, repeated IDs alone and output caps. A rejection records the first failed safeguard for a detector/scope; counts describe evaluations, not unique transactions.

## Verification and limitations

`verify_result` independently sums unique primary-row positive amounts, checks every primary/context reference against the filtered active snapshot, checks score bounds and weighted arithmetic, validates basis/IDs, confirms quality row union and supplier-filter suppression, and checks a deterministic re-run. Known synthetic fixtures independently establish expected detector decisions and signal/financial values, rather than relying solely on re-running the same rules.

PostgreSQL integration tests use only the existing guarded `procureiq_test` database. Tests include each detector's positive/negative cases, small and sparse single-supplier categories, unequal/missing history, zero baselines, March effects, credits, aliases, duplicate flags, contextual versus ordinary repeated IDs, all filter dimensions, inactive versions, actual reference resolution and export precision. Actual-data integration verifies that prior analytics remain unchanged. Acceptance also runs the full existing test suite and both database and analytics verification commands.

Human review is still needed to approve/refine policy thresholds, interpret contract comparability, confirm aliases/duplicate candidates and assess year-end explanations. No decision to consolidate suppliers, renegotiate contracts or claim savings follows automatically from a score. No Streamlit, financial scenario or AI functionality is implemented in this milestone.

### Export consumer limits

CSV evidence columns contain complete JSON arrays and can exceed spreadsheet cell limits and Python's default CSV field-size limit. Use the JSON export for full evidence browsing; Python CSV consumers should increase `csv.field_size_limit` before reading. No source references are truncated to fit a spreadsheet. Financial values and Decimal components are serialized as exact decimal strings; consumers should avoid binary float conversion when reconciling money.
