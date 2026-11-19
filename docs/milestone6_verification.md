# Milestone 6 verification record

Executed on 15 October 2026 with Python 3.14.7, PostgreSQL 17.11, Streamlit 1.66.0, Plotly 6.9.0 and XlsxWriter 3.2.9. The application reads the actual local HMRC database. Integration tests reset only the guarded, separate `procureiq_test` schema. No main-database expenditure, supplier mappings, active-version selections, SQL migrations or opportunity policies were changed.

## Executed acceptance

- `python -m pytest tests/test_financial_scenarios.py -q`: **24 passed in 9.78s** during development.
- `python -m pytest -q`: **110 passed in 72.56s**, with no skips or failures, on the final implementation.
- `procureiq db verify`: passed the frozen-source and monthly financial gate.
- `procureiq analytics verify`: passed independent analytical reconciliation.
- `procureiq opportunities verify`: passed all 34 selected reviews across 12,973 rows.
- `python -m compileall -q src/procureiq`: passed.
- `python -m pip check`: no broken requirements.
- Generated and inspected JSON and XLSX deliverables; independently recalculated the workbook using a separate spreadsheet engine, including input edits, all three cases and all 121 sensitivity cells.
- Ran the actual Streamlit application in Chromium through Playwright, including final downloads after restarting the server with the final implementation. No browser JavaScript page errors were recorded.

The new tests use independent expected-value fixtures for Decimal arithmetic, unrounded intermediate products, penny rounding, positive/negative outcomes, zero costs, ROI, input boundaries, independent cases, sensitivity and break-even. They cover full/partial period labels, actual database baseline consistency, opportunity scope restrictions, one-pool safeguards, stale-source handling, forged-current-source rejection, JSON round trips, workbook formulas/references/caches and Streamlit inputs/navigation. The previous dashboard and ingestion tests remain in the full suite.

A £1,000,000 fixture with 40% addressability, 50% adoption, 10% improvement, £10,000 implementation and £5,000 operating costs independently yields £20,000 gross, £5,000 net and 33.3333% ROI. A £0.05 fixture checks that intermediate rounding does not inflate the gross benefit. AppTest changes source versions only in the isolated test database and confirms blocked stale outputs followed by explicit refresh.

## Preserved source acceptance

| Metric | Verified value |
|---|---:|
| Published source lines | 12,973 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |

These values were queried and verified, not substituted as application calculations. Baseline selection uses read-only repeatable-read snapshots and the existing analytical layer.

## Illustrative deliverables

The [JSON configuration](../deliverables/procureiq_scenarios.json) and [Excel financial model](../deliverables/procureiq_scenario_model.xlsx) use the actual PROJECT Mandays Supp category for April 2025–March 2026: **£721,458,382.18 positive payments**, 6,497 source lines, £5,012,458.96 credits and £716,445,923.22 net. This is a same-period scenario, not an annualized forecast.

All cases assume **20% addressability, £100,000 implementation cost and £50,000 same-period operating cost**. These are explicitly illustrative assumptions, not validated procurement rates or contract terms.

| Case | Adoption | Improvement | Gross hypothetical benefit | Net hypothetical benefit |
|---|---:|---:|---:|---:|
| Conservative | 25% | 1% | £360,729.19 | £210,729.19 |
| Base | 50% | 2% | £1,442,916.76 | £1,292,916.76 |
| Ambitious | 75% | 3% | £3,246,562.72 | £3,096,562.72 |

The Base case yields £144,291,676.44 addressable, £72,145,838.22 affected and 861.9445% ROI under these assumptions. These three alternatives must not be added. None represents expected or realized savings.

## Excel formula evaluation and visual checks

The workbook has exactly four sheets: Model Inputs, Scenario Comparison, Sensitivity Analysis, and Methodology & Limitations. openpyxl inspected formulas, input references, numeric types, formats, validation and cached results. XlsxWriter writes formulas and Python-derived initial caches; it does not evaluate them.

Separately, a spreadsheet engine imported and **actually recalculated** the workbook. Comparison results and every cell of the 11 × 11 sensitivity grid matched independent Python expected values. Changing Base improvement from 2% to 4% recalculated gross/net benefits; increasing operating cost by £1,000 reduced sensitivity results by £1,000. Zero costs produced unavailable ROI. Blank costs and excessive-precision inputs produced invalid-input states. A small half-penny fixture confirmed the intended intermediate-rounding behavior. The final recalculated error scan found no formula error cells.

Development evaluation exposed a blank-input guard issue; the final formulas test numeric counts before evaluating precision checks. The final full test suite and independent recalculation ran after that correction. The original XlsxWriter delivery file was preserved; artifact rendering did not replace it.

All four sheet renders were visually inspected for readable formatting and differentiated inputs:

- [Model Inputs](screenshots/milestone6_excel_inputs.png)
- [Scenario Comparison](screenshots/milestone6_excel_comparison.png)
- [Sensitivity Analysis](screenshots/milestone6_excel_sensitivity.png)
- [Methodology & Limitations](screenshots/milestone6_excel_methodology.png)

Microsoft Excel itself was not automated. The workbook requests automatic/full recalculation on opening; use a recalculating spreadsheet application after edits. Binary spreadsheet arithmetic can differ from Decimal near precision boundaries. Exact JSON/Python results remain authoritative.

## Actual application walkthrough

Started the existing application with exported environment variables:

```sh
streamlit run src/procureiq/ui/app.py --server.port 8501
```

The app served at <http://127.0.0.1:8501>. A temporary Playwright 1.64.0 environment controlled local headless Chromium; browser tooling was not added as an application dependency.

1. Confirmed the existing Spend Overview positive total, opened Radar and started a scenario from the leading fragmentation review.
2. Confirmed the offered category, explicitly bound its baseline and checked all three cases initially had zero benefit assumptions and unavailable ROI.
3. Loaded clearly labeled illustrative assumptions; checked the Base £1,292,916.76 net output and rendered comparison/sensitivity charts.
4. Navigated to Spend Overview and back; confirmed baseline and assumptions persisted.
5. Downloaded JSON and the formula-driven workbook. Parsed the JSON and checked its exact Base output. The final browser-downloaded workbook contains the corrected input-validity formula.
6. Uploaded a saved configuration with an old source fingerprint. Calculations/exports were suspended pending review; explicitly accepting the current source restored outputs. This browser test did not change database versions.
7. Reset assumptions and confirmed zero-cost ROI returned to unavailable. No JavaScript page errors were observed.

Screenshots were captured and visually inspected:

- [Baseline and scope](screenshots/milestone6_baseline.png)
- [Independent assumptions and output cards](screenshots/milestone6_assumptions.png)
- [Sensitivity and break-even](screenshots/milestone6_sensitivity.png)

These are viewport captures, not an assertion that every off-screen pixel was inspected. Automated AppTest additionally exercises manual input changes and actual test-database version changes.

## Limitations and review boundary

The model is deterministic hypothetical decision support, not prediction. VAT treatment, addressability, service comparability, contractual restrictions and intervention feasibility require external review. Broad disclosed categories and overlapping opportunities do not establish a portfolio savings estimate. No annualization, probabilities, discounting or tax adjustment is inferred.

Scenario state survives ordinary page navigation within a Streamlit session; JSON provides persistence across sessions/restarts. Excel edits do not synchronize to the app. Source versions are checked on interaction, not continuously. The existing cache limitation for future manual supplier-mapping edits still applies. Native Microsoft Excel behavior and high-concurrency hosting were not tested.

No known blocking functional defects remain. See [financial methodology](financial_scenario_methodology.md) for formulas and conventions and [dashboard guide](dashboard_guide.md) for operation.
