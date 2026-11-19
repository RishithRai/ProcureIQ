# Final project verification — Milestone 7

Executed locally on 15 October 2026. This record distinguishes implemented behavior, executed checks and limits. Earlier milestone records remain historical evidence; this document covers final integration. Python 3.14.7, PostgreSQL 17.11, Streamlit 1.66.0, Plotly 6.9.0, XlsxWriter 3.2.9 and python-pptx 1.0.2 were used.

## Implemented

The application now has five functional pages: Spend Overview, Supplier Intelligence, Opportunity Radar, Financial Scenario Lab and Executive Brief. The new deterministic recommendation layer covers all four existing review types. It retains original scores, selects diverse themes with materiality/overlap controls and separates observed evidence from actions and validation requirements. Each recommendation retains complete source references and opens its matching Radar review.

Executive Brief respects global filters and reads one consistent snapshot. Scenario inclusion is explicit, validates the current source/period/filter basis and blocks stale or incompatible scenarios. No valid selected scenario means a framework-only financial slide. The reusable Python presentation generator produces exactly five editable widescreen slides; CLI and browser use the same implementation. No procurement formulas, detector policy, source mappings, active-version flags or database migrations were changed.

The README, dashboard guide, [technical architecture](technical_architecture.md), [executive methodology](executive_methodology.md) and [resume description](resume_project_description.md) document the completed local project. No AI or UI redesign was implemented.

## Automated execution

- `python -m pytest -q`: **116 passed in 84.04s**, no skips or failures.
- `python -m pytest tests/test_executive.py -q`: **6 passed in 10.32s** after the final slide layout and Executive Brief financial-table formatting adjustments. The six tests contain independent selection, data, scope, artifact and UI assertions.
- `procureiq db verify`: passed frozen-source hashes, row contents and exact monthly reconciliation.
- `procureiq analytics verify`: passed independent Decimal/SQL analytical checks.
- `procureiq opportunities verify`: passed all 34 selected review checks across 12,973 rows.
- `procureiq executive export`: generated the actual default deck and evidence JSON from live read-only data.
- `procureiq executive export --scenario deliverables/procureiq_scenarios.json --output .local/m7-saved-scenario.pptx`: successfully exercised optional validated JSON input.
- `python -m compileall -q src/procureiq` and `python -m pip check`: passed.

Integration tests ran only in the guarded, separate `procureiq_test` database. Coverage includes deterministic ordering/ties, theme diversity, overlap avoidance and disclosure, source references, exact filtered totals, empty populations, stale versions, source changes, scenario scope/period validation, tampered saved results, manual-pool exclusion, explicit inclusion and preserved Lab state. The full suite retains all 110 earlier tests, including financial engine/workbook and dashboard regressions.

Development checks found an inexact widescreen dimension, renderer rejection of signed chart axis IDs and crowded management-slide text. These were corrected. Initial browser scripts also needed locator corrections for evidence headings, a styled checkbox, virtualized option lists and mobile sidebar controls. Failed development attempts were not counted as successful acceptance.

## Financial and review reconciliation

| Metric | Actual verified result |
|---|---:|
| Source files | 12 |
| Published lines | 12,973 |
| Normalized supplier keys | 456 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Qualified reviews | 112 |
| Exported reviews | 34 |
| Deferred by caps | 78 |

The live analytical query retrieved Capgemini as the leading supplier with £410,066,806.54 positive payments. The default shortlist covers purchasing coordination for PROJECT Mandays Supp, dependency for Physical Hosting and Infrastructure, payment timing for Rent (Irrec VAT), and source/master-data review for Business Rates. The four selected primary evidence sets have no pairwise overlap in this run; synthetic tests exercise overlap disclosure and avoidance. This does not make opportunities additive savings.

## Financial illustration and Excel preservation

The default deck recomputed the Milestone 6 example using the actual PROJECT Mandays Supp positive baseline **£721,458,382.18**. All three alternatives assume **20% addressability, £100,000 implementation and £50,000 same-period operating costs**. Conservative uses 25% adoption/1% improvement, Base 50%/2%, and Ambitious 75%/3%. Recomputed net hypothetical benefits are **£210,729.19**, **£1,292,916.76** and **£3,096,562.72**, respectively.

These are explicitly illustrative assumptions and arithmetic outputs, not predictions, realized savings or contract terms. They are alternatives and are never summed. The model retains same-period labels without annualizing partial coverage.

The existing delivered Excel model was re-imported and actually recalculated by the independent spreadsheet engine. All three cases and 121 sensitivity cells matched the independent expected values. Improvement/cost edits propagated, zero-cost ROI remained unavailable, blank/excess-precision inputs were rejected, and the small rounding fixture passed. The recalculated error scan found no formula errors. The original XLSX was preserved. Microsoft Excel itself was not automated; spreadsheet binary precision limits remain documented.

## Presentation generation, rendering and inspection

The generated [PowerPoint](../deliverables/procureiq_executive_review.pptx) contains exactly five slides in the requested order. Automated checks verified the slide count/order, exact widescreen ratio, monetary values, opportunity counts, scenario assumptions/results, reporting period, source attribution and hypothetical-benefit disclaimer. Editable chart data and native text/tables remain in the PPTX. Separate checks verified shape bounds and inclusion/exclusion of results in browser-downloaded scenario, framework-only and empty-population decks.

A presentation renderer rendered the actual final PowerPoint to five PNG previews. Every slide was visually inspected; management-slide overlap and Radar caption spacing were corrected. Rendering did not replace the original python-pptx file. This is local renderer verification, not a claim of inspection in Microsoft PowerPoint.

- [Slide 1 — Executive Overview](../deliverables/screenshots/slide-1.png)
- [Slide 2 — Expenditure & Supplier Intelligence](../deliverables/screenshots/slide-2.png)
- [Slide 3 — Opportunity Radar](../deliverables/screenshots/slide-3.png)
- [Slide 4 — Financial Scenario Illustration](../deliverables/screenshots/slide-4.png)
- [Slide 5 — Recommendations & Management Actions](../deliverables/screenshots/slide-5.png)

The [evidence JSON](../deliverables/procureiq_executive_review.evidence.json) freezes full source hashes, filter basis, analytical outputs, recommendations, primary/context references and scenario conventions/results. It supports detailed audit beyond abbreviated slide footers.

## Actual browser walkthrough

The local application ran at <http://127.0.0.1:8501>. A temporary Playwright 1.64.0 environment controlled local headless Chromium; browser tooling was not added as an application dependency.

1. Navigated through all five pages; checked the original Overview KPI and Supplier Intelligence/Radar content.
2. Opened Executive Brief, checked full-population KPIs and rendered recommendations, and downloaded a framework-only deck with no automatically inserted scenario results.
3. Followed a recommendation to its exact Radar review and the 6,497-row source-evidence workspace. Started a Lab scenario from that review, explicitly bound the category and loaded labeled illustrative assumptions.
4. Returned to Executive Brief, explicitly included the reviewed scenario and downloaded a five-slide deck containing the expected Base hypothetical result.
5. Filtered to Capgemini and checked **£410,066,806.54** positive payments; the unrelated scenario was blocked. Reset Filters restored the full population.
6. Combined Capgemini with Physical Hosting and Infrastructure to obtain an empty selection. The brief displayed no analytical findings/recommendations and generated a five-slide framework-only empty-population deck. Reset restored the original totals.
7. Checked the Executive Brief at a 390 × 844 viewport, including sidebar navigation, stacked KPIs and document width. Screenshots below record the final inspected layouts.

- [Executive Brief](screenshots/milestone7_executive.png)
- [Explicit scenario inclusion](screenshots/milestone7_scenario.png)
- [Mobile Executive Brief](screenshots/milestone7_mobile.png)

The completed walkthrough recorded no browser JavaScript page errors. Screenshots are viewport captures, not claims of inspecting every off-screen pixel. AppTest additionally exercised actual test-database source-version changes and stale-scenario blocking. Browser checks used current data without mutating main source versions.

## Local hygiene and limitations

A read-only repository inventory found no tracked files and no tracked environment files. A path-only credential-pattern scan of source, tests, docs, configuration and manifests found only the `.env.example` placeholder URLs and a synthetic invalid-credential test. The real ignored `.env` remains mode 0600. Reusable documentation contains no personal absolute paths. Temporary browser/validation files stay in ignored `.local/`; frozen sources and prior deliverables were preserved. Dependencies and local documentation links were checked.

No commits, pushes, remote changes, repository visibility changes, deployments or public sharing were performed. The application and all artifacts remain local.

No known blocking functional defects remain. Unverified assumptions include actual addressability, achievable improvement, contract comparability, VAT recovery and commercial feasibility. The shortlist is deterministic review policy, not an optimal procurement strategy. Disclosures are incomplete expenditure coverage; supplier keys are not independently verified legal identities. Native Microsoft PowerPoint/Excel, fresh-machine rebuild and high-concurrency hosting were not tested. Arbitrary future long category labels may require slide layout review. Existing cache limits for future manual supplier-mapping changes remain.

Milestone 7 completes the core analytical application.
