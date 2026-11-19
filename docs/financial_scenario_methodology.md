> The complete React product extends this historical documentation. See [product architecture](product_architecture.md), [user/development guide](product_user_guide.md), [API extensions](product_api.md) and [verification](product_verification.md). Existing calculations and source policies remain authoritative.

# Financial Scenario Lab — methodology

## Purpose and expenditure basis

Milestone 6 compares three hypothetical interventions for **one explicitly selected expenditure pool** over its selected reporting period. It is not a forecast, predicted procurement improvement, actual HMRC contract analysis or evidence of realized savings. Conservative, Base and Ambitious are independent user-named alternatives; their benefits must not be added. There is no portfolio aggregation of overlapping opportunities.

A database baseline is the existing analytical engine's **positive disclosed payments**, read together with credit magnitude, net payments, row count, reporting calendar, filters and source metadata inside one read-only repeatable-read snapshot. Credits are disclosed alongside the baseline and never silently subtracted from the positive modelling pool. Invalid/unparsed amounts remain excluded under the existing analytical rules and are flagged. Duplicate candidates and repeated identifiers are retained.

The user can select the current filtered population, a single named expense category within all current filters, or an explicitly user-supplied manual amount. A category choice never overrides a conflicting sidebar category. A manual baseline has no HMRC row count, credit/net figures or verified fingerprint. Its period follows the selected reporting-month range and its scope must be described by the user.

HMRC amounts are gross VAT-inclusive payments from a disclosure subset, not total organizational procurement expenditure. Addressability must account for VAT treatment, contractual restrictions, eligibility and noncomparable services. Costs must use a comparable VAT basis. No VAT recovery, unit-price reduction or contract terms are inferred. All benefit rates initially equal zero; selecting a large baseline does not make it addressable.

## Inputs and validation

| Input | Meaning / accepted values |
|---|---|
| Baseline GBP | Nonnegative positive-expenditure pool; exact decimal with at most two fractional digits |
| Addressable percentage | Assumed eligible share, 0–100 inclusive |
| Adoption percentage | Assumed share of addressable expenditure affected, 0–100 inclusive |
| Improvement percentage | Assumed benefit rate on affected expenditure, 0–100 inclusive |
| Implementation cost | Nonnegative one-time GBP cost within this model |
| Operating cost | Nonnegative GBP cost for the same selected period |

Percentages accept at most four decimal places in percentage units, e.g. `12.3456` means 12.3456%, not a fraction. Monetary inputs are capped at £999,999,999,999.99 each to bound the model and preserve practical spreadsheet precision. This is an input limit, not a financial assertion. Nonfinite values, booleans, negative values, excess decimal places and out-of-range percentages are rejected. The UI converts percentage-widget values via decimal text; no floating-point financial calculation is performed. Monetary text controls avoid implicit binary conversion and accept neither commas nor currency symbols.

## Formulas and rounding

Let `B` be the baseline, `A`, `D`, `I` be addressable/adoption/improvement percentages divided by 100, and `C₁`, `C₂` the two costs:

| Result | Calculation |
|---|---|
| Addressable expenditure | `B × A` |
| Affected expenditure | `B × A × D` |
| Gross hypothetical benefit | `B × A × D × I` |
| Total costs | `C₁ + C₂` |
| Net hypothetical benefit | `gross − total costs` |
| ROI (%) | `rounded net / total costs × 100`, when costs are positive |

The Python engine uses Decimal with precision 50. Intermediate addressable, affected and gross products remain unrounded when used in later steps. Each reported money result is rounded once to pennies using **ROUND_HALF_UP**. Inputs already have at most two monetary fractional digits. ROI deliberately uses the reported, penny-rounded net benefit, then rounds to four percentage decimals with HALF_UP; the UI displays two. With zero costs, ROI is `null` in JSON, “Unavailable” in the UI and `n.a.` in Excel. It is never infinite or manufactured as zero. Negative net benefit and negative ROI are valid outcomes.

For example, £0.05 × 50% × 50% × 100% yields unrounded gross £0.0125 and reported gross £0.01. Rounding addressable expenditure to £0.03 and feeding that rounded amount onward would be incorrect under this policy.

Every result is a **same-period scenario**. A July–August selection is labeled a two-month same-period scenario, not annual savings. A twelve-month selection is labeled a twelve-month same-period scenario; it is not assumed to recur. Missing source months remain a coverage limitation, not confirmed zero spending. No extrapolation, discounting, financing, inflation, tax adjustment or probabilistic forecast is included.

## Opportunity integration and user state

Radar's “Start a scenario from this review” carries one review's identity, filters, type, source fingerprint and category context. Concentration and fragmentation reviews can offer their single category's positive expenditure, recalculated through analytics, for explicit adoption as the baseline. Payment-pattern and data-quality review exposures may contain historical context or disputed records: they are never automatically copied into a savings pool. They carry context only, and the user must separately choose a baseline and assumptions. Priority scores and HHI never set improvement rates.

Use selected baseline explicitly binds a pool. Sidebar changes do not overwrite it or the user's assumptions. A visible message identifies differences between sidebar and bound scenario scope. Assumptions are stored independently of Streamlit widget state, so ordinary page navigation preserves them. Reset scenario assumptions restores all three cases to zero without replacing the pool. Reset Filters affects the dashboard filters, not the scenario assumptions. This state lasts for the current Streamlit session; JSON is the persistence/export mechanism. No database tables or writes were added.

If the active database fingerprint changes, a previously bound HMRC baseline becomes stale. Calculations and exports are suspended. The user sees saved/current values and fingerprints and must explicitly review and adopt the current source version, or choose a new baseline. Old origin metadata remains an historical reference, not a newly generated procurement review.

## Comparison and sensitivity

All three cases use the same bound baseline and independently editable five-field assumption sets. Comparison displays assumptions, addressable/affected expenditure, gross benefit, both costs, total costs, net benefit and ROI. Cases have no enforced monotonic relationship: “Ambitious” can produce a lower net benefit if the user assigns higher costs.

Sensitivity varies adoption and improvement, holding addressability, baseline and both costs fixed to the selected case. It calls the **same `calculate` function** for every cell. Standard adoption points span 0–100% in ten-point increments; improvement spans 0–10% by default, with optional 25%, 50% or 100% upper ranges. The selected case's exact adoption/improvement values are included. Imported JSON can retain validated custom axes (1–51 unique values each). The grid and CSV contain exact rounded GBP; Plotly receives numeric coordinates solely for drawing.

The heatmap distinguishes negative, zero and positive net benefit around zero. The dashed theoretical break-even line solves `required improvement % = total costs / affected expenditure × 100` at each adoption value. At zero costs, 0% improvement breaks even. Positive costs with no affected expenditure cannot break even; a required improvement above 100% is infeasible. The visible line only includes points inside the plotted range. The theoretical line uses unrounded gross equality, whereas rounded zero-net outcomes occupy a half-penny band. At fixed rates, each additional £1 of either cost reduces net benefit by £1. There are no probability distributions or Monte Carlo simulations.

## Excel export

`scenario_excel.py` uses XlsxWriter, a lightweight Python writer suitable for on-demand exports from the existing application. The workbook contains four requested sheets:

1. **Model Inputs:** source type, scope, period, fingerprint, positive baseline, source credits/net/count, editable assumptions and a sensitivity-case selector. Yellow cells with blue text are editable. Database baselines are locked to their exported evidence; manual baselines are editable. Worksheet protection prevents accidental editing, not malicious changes.
2. **Scenario Comparison:** direct input references, visible unrounded calculation rows, rounded financial outputs and guarded ROI. Each case has its own live formulas and input-validity guard. Blank, nonnumeric, out-of-range or excessive-precision inputs invalidate affected results rather than silently becoming zero. Cases do not depend on each other's results.
3. **Sensitivity Analysis:** formula-linked net-benefit grid, selected-case inputs and negative/zero/positive conditional formatting. Changing the case number or its addressability/costs recalculates dependent grid cells. Adoption/improvement grid points are fixed at export.
4. **Methodology & Limitations:** formulas, rounding, VAT/period conventions, interpretation, filters, origin metadata and active source filenames/hashes.

Money and rates are numeric spreadsheet values with GBP/percentage formats. Initial formula caches contain Python results so a noncalculating viewer can display the export. **Caches are not evidence of Excel formula evaluation.** Automatic calculation and full recalculation on opening are requested. Use a recalculating spreadsheet application after input edits. XlsxWriter itself does not evaluate formulas; see its [formula documentation](https://xlsxwriter.readthedocs.io/working_with_formulas.html).

The saved XLSX was structurally inspected with openpyxl, and an independent spreadsheet engine actually recalculated comparison and sensitivity formulas, including edited inputs and boundary cases. Microsoft Excel itself was not automated or claimed as verified. Binary spreadsheet arithmetic can differ from Decimal at extreme precision/half-penny boundaries; the exact JSON/Python model is authoritative. Workbook edits do not update PostgreSQL or synchronize back into the dashboard. Re-enter desired edits or load a validated JSON configuration to use them in the UI.

## JSON reproducibility

JSON includes model version `same_period_decimal_v1`, GBP currency, complete baseline and source/filter basis, exact decimal assumptions/results, period labels, calculation conventions and sensitivity axes/selected case. Import is limited to 2 MB and validates schema, model version, names, duplicate keys, numeric limits, period labels and saved output consistency. Outputs are recomputed and compared rather than trusted. A manual pool cannot claim HMRC provenance.

For a current-fingerprint HMRC import, its baseline, population and metadata must also match a fresh database query; a claimed fingerprint alone proves nothing. Older-version imports are retained as stale and require explicit review before new calculations. There is no automatic baseline rebasing. These controls support reproducibility, not cryptographic document authenticity or proof of real contract terms.

## Illustrative demonstration

The delivered demonstration files use the actual **PROJECT Mandays Supp** category, April 2025–March 2026, positive baseline **£721,458,382.18** across **6,497 source lines**. Credits are **£5,012,458.96** and net payments **£716,445,923.22**. This category may include non-substitutable services.

The assumptions below were deliberately loaded as examples. They are **not empirically validated rates** or an assessment that the expenditure can actually be improved.

| Case | Addressable | Adoption | Improvement | Implementation | Period operating | Gross hypothetical benefit | Net hypothetical benefit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Conservative | 20% | 25% | 1% | £100,000 | £50,000 | £360,729.19 | £210,729.19 |
| Base | 20% | 50% | 2% | £100,000 | £50,000 | £1,442,916.76 | £1,292,916.76 |
| Ambitious | 20% | 75% | 3% | £100,000 | £50,000 | £3,246,562.72 | £3,096,562.72 |

The Base case's reported addressable amount is £144,291,676.44, affected amount £72,145,838.22 and ROI 861.9445%. These are arithmetic consequences of the stated assumptions, not expected outcomes. Do not add the three alternatives.

See [Milestone 6 verification](milestone6_verification.md) for executed checks and screenshots. Executive Brief, presentation generation and AI remain deferred.


## Guided React interaction

The React model now offers explicit full-population acknowledgement, assumption tooltips, Copy from Base, a 700 ms debounced backend preview, gross-benefit/cost comparison and interactive sensitivity cells. All authoritative outputs still come from the existing Decimal engine. Current assumptions are highlighted only when they exactly match a sensitivity grid point. Imports and source refresh retain existing safeguards. See [workflow guide](product_workflow_refinement.md).
