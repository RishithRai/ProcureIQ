# Product workflow refinement — verification

Executed locally on 16 October 2026 against the actual React/FastAPI application and PostgreSQL database. This record supplements earlier acceptance records. The approved design system, analytical engines, financial model, solver and document generators were retained. See [workflow guide](product_workflow_refinement.md), [Data Operations guide](data_operations_guide.md) and [reporting guide](reporting_guide.md).

## Executed checks

- Full Python suite: **150 passed, 1 pre-existing warning in 78.61 seconds**. The original 143 tests remain, with seven new refinement tests.
- Final frontend suite: **46 passed across three files in 3.22 seconds**, including ten added refinement tests. ESLint and strict TypeScript/production build passed.
- `procureiq db verify`, `procureiq analytics verify` and `procureiq opportunities verify`: passed.
- Python compileall and pip check: passed.
- Application migrations 004/005 applied to the main application schema and checksum-verified on rerun. Destructive tests used only the guarded separate test database.

The existing Starlette/FastAPI TestClient httpx-adapter deprecation warning remains visible. It is not a failed test or runtime API error.

New backend coverage establishes namespace coexistence, independent deduplication, concurrent demo inserts, legacy classification and preserved relationships, historical evidence filtering/ordering/summaries, structured findings and citations, namespace/report guards, quality pagination, historical evidence after activation, actual PPTX preview extraction and stale-report content protection. Existing coverage retains normal concurrency, rollback, activation, financial arithmetic, MILP and artifact contracts. Frontend tests exercise adaptive home states, mode headers, filtered evidence navigation, citation editing, guided optimization, quality filters, supplier/category/month scope handoff and five-slide preview. Real-browser checks supplement component tests for sticky positioning, keyboard focus and responsive layouts.

## Persistence and source preservation

Migration `004_investigation_namespaces.sql` adds immutable NORMAL/DEMO namespaces and PostgreSQL uniqueness on review basis plus namespace. It checks conflicts and classifies only explicitly prefixed legacy local demos inside a transaction. Migration `005_finding_sections.sql` adds optional typed finding sections; historical reasoning text is unchanged.

Before/after hashes of original cases 1, 3 and 4, frozen evidence, entries, bookmarks, citations and audit events match exactly. Their statuses/versions remain INVESTIGATING/2, OPEN/1 and INVESTIGATING/5. They are now explicitly DEMO. No original IDs, references or content were rewritten.

Source, raw-row, supplier-mapping and complete opportunity-output snapshots match exactly before and after acceptance. Source fingerprint: `5886525e03a6b21493a7bd70ba3c8ec510ea8f8e01a753cc66850a0406192061`.

| Acceptance metric | Result |
|---|---:|
| Official monthly files / published lines | 12 / 12,973 |
| Resolved supplier keys / positive-payment suppliers | 456 / 455 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Qualified / exported / deferred reviews | 112 / 34 / 78 |

One intentional NORMAL acceptance case, **PIQ-000037**, was created through the UI for the same review/source basis as DEMO PIQ-000001. It retains 6,497 primary references, one bookmark, one explicitly preliminary verification finding and four audit events. Its current status/version is INVESTIGATING/2. Repeated creation returned the existing case independently in each namespace (37 and 1), without modifications. This is labelled local acceptance work, not a commercial conclusion. One illustrative sourcing result was also saved through the existing workflow. No main source version was activated during these checks.

## Actual browser acceptance

Playwright controlled real Chromium against React at `127.0.0.1:5173` and FastAPI at `127.0.0.1:8000`; no production mocks were used. Successful walkthroughs recorded no JavaScript page errors.

1. Viewed the empty NORMAL workspace, switched to existing DEMO cases, checked opposite-mode direct URL handling, and created the independent NORMAL case above.
2. Filtered its thousands of frozen references by supplier/month, inspected single records with previous/next navigation, bookmarked evidence, opened the finding editor with that citation, saved the finding and changed lifecycle status. Reloads showed persisted work and updated counts.
3. Followed supplier → reporting month → matching transactions and supplier/category → scoped scenario. Supplier breakdown percentages are supplied by backend Decimal calculations. The Pareto plot uses all 455 positive-payment suppliers, independently of table pagination.
4. Bound PROJECT Mandays Supp expenditure of £721,458,382.18 and explicitly loaded illustrative assumptions. Debounced backend calculation reproduced **£1,292,916.76 Base net hypothetical benefit**. Scenario JSON and Excel were downloaded and included in a compatible report.
5. Completed the four-step sourcing builder. A 100-unit illustrative requirement cost **£1,400 at a 60% dependency cap** and **£1,500 at 50%**. Compared configurations and saved/reloaded a strategy. These are modelled costs, not verified savings.
6. Inspected source versions, existing pipeline results, stage durations and recorded processing counts. Queried **all 1,761 retained quality issues across 18 bounded API pages**, with no missing or duplicate IDs; exercised UI pagination, filters and source details. Inspection found the existing endpoint defaulted to 50/max 100 per request, not a 200-record service cap. The earlier reported 200-item display is not evidence of the total population; its exact historical cause was not established. Current totals and complete pagination were directly verified.
7. Selected report content, viewed all five dynamically generated slide previews and downloaded the actual PPTX/evidence JSON. A separate compatible case report retained attributed finding text in speaker notes. Preview/download content hashes reject changed report state.
8. Checked eight routes at **1440 × 1000, 1280 × 900 and 390 × 844**: 24 checks, with document width equal to viewport width throughout. Tested mobile menu, drawer focus containment across 12 Tab presses, Escape, reduced motion, dark theme, desktop sticky review scrolling and enlarged mobile slide preview.
9. Opened the preserved Streamlit app and verified its actual full-period positive-payment total in the browser. The full Python regression also retains its application coverage; this refinement does not claim a repeat of every historical Streamlit browser journey.

Source registration, ingestion, failure/retry and explicit activation safeguards are covered by the retained isolated integration tests. Browser acceptance inspected existing main-data pipeline records rather than introducing or activating a fabricated main source revision.

## Artifacts

Actual browser downloads are retained as [scenario JSON](../deliverables/workflow_scenario.json), [Excel model](../deliverables/workflow_scenario.xlsx), [executive PPTX](../deliverables/workflow_executive.pptx), [report evidence](../deliverables/workflow_evidence.json) and [case-context PPTX](../deliverables/workflow_case_report.pptx). The [artifact receipt](../reports/product_workflow_artifact_receipt.json) records SHA-256 and byte sizes. The [acceptance receipt](../reports/product_workflow_acceptance.json) records browser results and preservation comparisons.

Checks confirmed matching Base values in JSON/report evidence, four formula-bearing workbook sheets, five presentation slides, two native charts, valid ZIP packages and attributed case notes. Existing financial/workbook tests passed. This refinement did not repeat the earlier independent spreadsheet recalculation or automate native Microsoft Office.

No local Office-compatible renderer was available. The visual preview extracts text, positions, fonts, tables and chart values from the actual generated PPTX. It is explicitly labelled a dynamic content/layout preview, not pixel-exact Office rendering. Enlarging the preview supports reading on narrow screens.

## Visual evidence and corrections

Screenshots are actual viewport captures, not exhaustive inspection of every off-screen pixel. Representative workspace/detail screenshots were visually inspected. Layout sweeps additionally checked document widths across all listed viewports.

| Workflow | Screenshots |
|---|---|
| First-time and active home | [First-time NORMAL](screenshots/workflow_normal_first_time.png), [active NORMAL](screenshots/workflow_normal_active.png), [DEMO](screenshots/workflow_demo_command.png) |
| Review and case | [Sticky review](screenshots/workflow_sticky_review.png), [case brief](screenshots/workflow_desktop_case.png), [mobile case](screenshots/workflow_mobile_case.png) |
| Evidence and notebook | [Filtered evidence](screenshots/workflow_evidence_filtered.png), [mobile drawer](screenshots/workflow_mobile_evidence_drawer.png), [notebook](screenshots/workflow_notebook.png), [finding editor](screenshots/workflow_finding_editor.png) |
| Spend discovery | [Overview](screenshots/workflow_spend_overview.png), [supplier breakdowns](screenshots/workflow_supplier_breakdowns.png), [full Pareto](screenshots/workflow_pareto.png), [dark theme](screenshots/workflow_dark_suppliers.png) |
| Strategy | [Scenario comparison](screenshots/workflow_scenario_comparison.png), [sensitivity](screenshots/workflow_sensitivity.png), [optimization comparison](screenshots/workflow_optimization_compare.png), [mobile scenarios](screenshots/workflow_mobile_scenarios.png) |
| Operations | [Sources](screenshots/workflow_sources.png), [pipeline](screenshots/workflow_pipeline_run.png), [quality detail](screenshots/workflow_quality_issue.png), [mobile](screenshots/workflow_mobile_operations.png) |
| Reporting | [Slide 1](screenshots/workflow_report_slide_1.png), [slide 2](screenshots/workflow_report_slide_2.png), [slide 3](screenshots/workflow_report_slide_3.png), [slide 4](screenshots/workflow_report_slide_4.png), [full-scope slide 5](screenshots/workflow_report_slide_5_full_scope.png), [mobile enlarged preview](screenshots/workflow_mobile_report_zoom.png) |

Earlier product captures remain in [product verification](product_verification.md) for before/after comparison; they are historical states with different data context. Useful comparisons are the earlier source-card/quality presentation versus the compact source table and issue drawer, and the earlier finding form versus the notebook/editor. The first-time and active home captures above demonstrate the adaptive states directly.

Development checks exposed a mobile operations tab overflow, clipped preview text, a source-status property mismatch, stale work-count caching and a narrow drawer title/close overlap. Each was corrected before the final passing frontend/browser runs. Browser scripts also needed locator corrections; failed attempts were not counted as successful acceptance.

## Limits and local-only status

NORMAL/DEMO is logical local separation, not authentication. The API remains unauthenticated and loopback-only. Case/review search explicitly labels loaded-page or first-100 limits; exact-ID reporting fallback remains available. Historical evidence text search includes original JSON field names as well as values. Metadata and source checks occur on interaction. Large-scale search, high-concurrency hosting and native Office rendering remain unverified. Financial benefits remain hypothetical, source disclosure is incomplete procurement context, and optimization requires independently justified commercial inputs.

No known blocking functional defect remains in the executed acceptance. No commits, pushes, remote changes, deployments or public sharing were performed. Original source files, analytical migrations, mappings and active versions were preserved. The local acceptance records described above are intentional retained application data.
