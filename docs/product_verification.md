# Complete product verification — 16 October 2026

The six local React/FastAPI workspaces are implemented: Command Center, Spend Explorer, Investigations, Strategy Studio, Data Operations and Reports. Existing Streamlit, SQL analytics, opportunity policy, Decimal scenario calculations, XlsxWriter and python-pptx engines remain in use. This record supplements the historical milestone and Stage 1/2 records; it does not rewrite their acceptance history.

## Automated and source acceptance

The final full Python suite passed **143 tests in 67.91 seconds**, including the original 130 and 13 product tests. New tests cover independent MILP expected allocations/costs, supplier bounds/eligibility, infeasibility and nonoptimal termination, saved runs, API precision/pagination/validation, financial/report compatibility, transactional notes/findings and event rollback, bookmark lineage, closed-case guards, incremental idempotency, new inactive revisions, stale/explicit activation, failed schema contracts, receipt tampering/retry, worker restart recovery and queue bounds. Destructive simulations run only in the guarded separate test database.

After the final report total/truncation metadata addition, the 13 focused product tests passed again.

Frontend acceptance: 30 Vitest/Testing Library tests passed across existing investigation coverage and the added product workspaces. ESLint, strict TypeScript production build, Python compileall and pip check passed. Production npm audit reported zero advisories. Charts are split into a separate approximately 374 kB minified chunk; the main bundle is approximately 374 kB. No high-concurrency or remote-hosting performance claim is made.

`procureiq db verify`, `procureiq analytics verify` and `procureiq opportunities verify` passed. Before/after read-only snapshots match exactly for the source fingerprint, raw-row content hash, supplier/alias hash, full opportunity-output hash and analytical totals:

| Acceptance metric | Preserved result |
|---|---:|
| Official monthly files | 12 |
| Source lines | 12,973 |
| Resolved supplier keys | 456 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Qualified / exported / deferred reviews | 112 / 34 / 78 |

Source fingerprint: `5886525e03a6b21493a7bd70ba3c8ec510ea8f8e01a753cc66850a0406192061`. No analytical migrations, opportunity thresholds, supplier mappings, original bytes or active selections were changed. Additive application migrations 002/003 were applied and checksum-verified through the existing application migrator.

## Actual local browser workflows

Playwright controlled real headless Chromium against React on 127.0.0.1:5173 and FastAPI on 127.0.0.1:8000. No production mocks were used. Successful walkthroughs recorded no JavaScript page errors.

- Command Center showed exact actual totals and actual case/pipeline activity; links opened reviews and saved cases.
- Spend Explorer selected real normalized supplier capgemini and showed £410,066,806.54 positive payments. Transaction detail exposed original lineage. Empty search and filter reset worked. Supplier detail, original-case page 2 evidence, and cross-workspace links were exercised.
- The earlier PIQ-000001 and PIQ-000003 cases retain their original statuses/versions (INVESTIGATING/2 and OPEN/1). A separate labelled PIQ-000004 was created through the UI, with 499 frozen primary references. It has one bookmarked source, a finding citing it, and a note. OPEN → INVESTIGATING → REVIEWED → CLOSED → INVESTIGATING was explicitly confirmed with written explanations. Reload confirmed persisted analyst work and activity. Current version is 5. These are intentional application-demo records, not commercial findings.
- The real PROJECT Mandays Supp baseline was £721,458,382.18. Explicit illustrative assumptions reproduced £1,292,916.76 Base net hypothetical benefit. Editing Base improvement to 4% produced £2,735,833.53. A deliberately old fingerprint in an imported configuration blocked exports; explicit source refresh restored calculation. This test did not alter database source selection.
- A labelled illustrative sourcing model solved 100 units with a 60% dependency cap at £1,400. Changing the cap to 50% yielded £1,500 and equal allocations. One result was saved, reloaded and checked. Configuration/result comparison and chart output used actual solver results.
- Pipeline run 1 performed real read-only frozen-source verification. Run 2 registered the existing controlled acquisition manifest and revalidated/reconciled all loaded versions through incremental ingestion. Both succeeded, with recorded stage timestamps/durations/output. No revised main-data source was activated. Failure, restart, retry and new-version activation were exercised in isolated database fixtures.
- Reports downloaded actual scenario-compatible five-slide PPTX and complete evidence JSON. A separate case-context export included the demo's attributed finding, citation lineage and speaker notes, without turning the finding into financial savings.
- Six mobile workspaces were captured at 390 × 844. Document width remained 390 px; mobile Menu navigation worked. Wide data tables scroll within their containers. Screenshots are viewport evidence, not exhaustive off-screen inspection.

The preserved Streamlit application also passed its five-page browser regression: analytical totals, supplier filtering/reset, empty population, review-to-scenario navigation, scenario compatibility, PowerPoint downloads and mobile width. It was restarted after PostgreSQL recovery to discard stale cached connections.

## Artifact verification

The actual React downloads are retained as [scenario JSON](../deliverables/product_scenario.json), [formula-driven Excel](../deliverables/product_scenario.xlsx), [editable PowerPoint](../deliverables/product_executive.pptx), and [report evidence JSON](../deliverables/product_executive.evidence.json). Hashes are in [artifact receipt](../reports/product_artifact_receipt.json).

The Excel workbook has four sheets. openpyxl inspected formulas and cached values; independently, a spreadsheet engine imported and recalculated all three cases and 121 sensitivity cells against independent expected values. Input edits, zero costs, blank/invalid precision and the half-penny rounding fixture passed. Recalculated formula-error scan found zero errors. All four worksheet renders were visually inspected. Original XlsxWriter bytes were retained.

The PowerPoint contains five slides, two native charts and native editable tables/text. Package integrity checks found no structural issues. A presentation renderer rendered all five actual slides; each was visually inspected. Scenario numbers agree exactly with JSON. The case-context deck's speaker notes contain explicitly attributed findings and frozen citation hashes. Original python-pptx files were retained. Native Microsoft Excel/PowerPoint applications were not automated; renderer/recalculation checks do not establish their complete behavior.

## Screenshots and evidence

[Command](screenshots/product_command.png), [Spend](screenshots/product_spend.png), [supplier](screenshots/product_supplier_detail.png), [transaction](screenshots/product_transaction.png), [historical evidence page](screenshots/product_historical_page.png), [findings](screenshots/product_findings_persisted.png), [activity](screenshots/product_activity.png), [financial scenario](screenshots/product_scenario.png), [stale scenario](screenshots/product_stale_scenario.png), [optimization](screenshots/product_optimization_saved.png), [pipeline stages](screenshots/product_pipeline_stages.png), [executive report](screenshots/product_report.png), [mobile](screenshots/product_mobile_spend.png).

[Actual demo and pipeline receipt](../reports/product_demo.json) retains the persisted records. [SQL benchmark](sql_performance.md) records actual EXPLAIN plans/timings; evidence did not justify a permanent index change.

## Development failures and limits

Development testing found route/query parameter collision, JSONResponse status-code overrides, an untyped PostgreSQL NULL filter, and premature blob-URL revocation; each was corrected and retested. Browser scripts also needed locator corrections. An edit now retains an existing frozen finding citation after its bookmark is removed; new citations still require active case bookmarks.

A workstation disk-full event interrupted one full run (1 failure, 102 passes, 40 storage-related errors) and a screenshot write; these are not accepted results. PostgreSQL stopped because recovery could not extend a test-database file. npm's built-in cache verification reclaimed unused cache entries; the user then explicitly authorized clearing remaining pip/npm download caches. The existing cluster recovered normally, source snapshots matched, and a fresh full regression passed. No database files or source bytes were manually removed.

One pre-existing Starlette/FastAPI TestClient httpx deprecation warning remains visible. Exact financial results use Decimal; MILP uses disclosed numerical tolerances and hypothetical commercial inputs. Filter metadata derives from the current dataset; larger-scale search/hosting needs separate assessment. Report case context requires exact scope/source compatibility and includes at most 50 active findings per case with explicit total/truncation metadata. Client request cancellation does not imply cancellation of an already-running synchronous server operation. The combined `scripts/dev.sh` launcher was executed successfully; it starts the two loopback servers and preserves the separately running Streamlit process. The API is unauthenticated and loopback-only. No authentication, AI, enterprise identities, remote deployment, commits, pushes or publication were introduced.
