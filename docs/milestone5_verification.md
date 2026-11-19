# Milestone 5 verification record

Executed on 15 October 2026 with Python 3.14.7, PostgreSQL 17.11, Streamlit 1.66.0 and Plotly 6.9.0. The application uses the actual local HMRC database. Integration tests reset only the guarded `procureiq_test` schema. No main-database records, supplier mappings, active-version selections, SQL migrations or opportunity policies were changed.

## Automated acceptance

- `python -m pytest tests/test_dashboard.py -q`: **8 passed in 12.40s**, including isolated PostgreSQL integration and Streamlit AppTest checks.
- `python -m pytest -q`: **86 passed in 70.05s**, without skips or failures, on the final implementation.
- `procureiq db verify`: passed the frozen-source hashes, row contents and monthly reconciliation gate.
- `procureiq analytics verify`: passed the existing independent Decimal/SQL analytics checks.
- `procureiq opportunities verify`: passed all 34 exported opportunity checks across 12,973 source rows.
- `python -m compileall -q src/procureiq`: passed.
- `python -m pip check`: no broken requirements.

Dashboard tests exercise exact KPI/CSV formatting; all backend filter dimensions; reset and post-reset interactions; empty/incompatible selections; supplier ranks, resolved-versus-full denominators and Pareto consistency; filtered HHI; read-only transactions; opportunity/backend ranking and score parity; supplier-filter suppression; unique evidence pagination and lineage; complete evidence export; source-version invalidation; sanitized database/configuration errors; cache reuse; and the deliberate absence of a summed opportunity-exposure metric. The actual-source test checks the full-period totals, 34/112 counts, top title/exposure and 6,497-row evidence population.

The final reset implementation assigns an explicit All option to each global filter. Browser testing found that deleting widget state alone could allow an old supplier selection to reappear on a later interaction. This was fixed and checked both with AppTest and the real browser. Development browser scripts also required locator corrections; these failures were not counted as successful verification.

## Actual financial and opportunity acceptance

| Metric | Database-backed application result |
|---|---:|
| Active published lines | 12,973 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Distinct resolved suppliers | 456 |
| Qualified review candidates | 112 |
| Exported reviews | 34 |
| Deferred by per-type caps | 78 |

Exported reviews comprise 10 concentration, 8 fragmentation, 10 payment-pattern and 6 data-quality reviews. The leading review is purchasing coordination for PROJECT Mandays Supp: £721,458,382.18 positive exposure, priority 97.95 after display rounding, and 6,497 primary source rows. These are observed context and investigation priority, not benefits or savings. The source and financial acceptance gates still match the approved frozen baseline.

## Actual application and browser walkthrough

Launched from the repository root with exported environment variables:

```sh
streamlit run src/procureiq/ui/app.py --server.port 8501
```

The application served at <http://127.0.0.1:8501>. The dedicated computer-use surface was unavailable, so verification used Playwright 1.64.0 from a temporary environment with a local headless Chromium executable. Browser tooling was not added as an application dependency. This was an actual browser run against the running Streamlit server, in addition to AppTest.

Verified interactions:

1. Opened Spend Overview; checked exact full-period KPI values and five Plotly charts. Inspected category/area/supplier/contribution chart layout.
2. Navigated to Supplier Intelligence; rendered the Pareto curve with its 80% reference, HHI/category metrics, supplier detail charts and tables.
3. Selected the real normalized supplier `capgemini` through the sidebar. Positive payments changed to £410,066,806.54; Radar explicitly suppressed concentration detection.
4. Reset filters; verified the All suppliers control and full 12,973-row population persisted through subsequent interactions.
5. Opened Radar; verified 34 exported, 112 qualified and 78 deferred, and opened the leading review's detail/evidence workspace.
6. Selected evidence page 2 of 130; fetched/displayed at most 50 rows. Prepared and downloaded complete JSON and parsed it to confirm all 6,497 primary references and corresponding detailed records were present.
7. Increased the minimum-priority control beyond the highest review score; verified the no-eligible-reviews state, then reset successfully.
8. Opened a fresh 390 × 844 mobile browser viewport. KPI cards stacked, the sidebar collapsed and the document width remained 390 pixels. Inspected the screenshot for legibility.
9. No browser JavaScript page errors were recorded in the successful walkthroughs.

Screenshots were captured and visually inspected; they are viewport captures, not claims that every off-screen pixel was examined:

- [Spend Overview](screenshots/milestone5_overview.png)
- [Overview breakdown charts](screenshots/milestone5_overview_charts.png)
- [Supplier Intelligence / Pareto](screenshots/milestone5_suppliers.png)
- [Opportunity Radar](screenshots/milestone5_radar.png)
- [Paginated evidence workspace](screenshots/milestone5_evidence.png)
- [Mobile layout](screenshots/milestone5_mobile.png)

## Performance observations and limits

A measured local service run took **1.058 seconds cold** and **0.004 seconds cached** to retrieve the full-period compact Radar result. This is one observation on this workstation, not a load-test guarantee. A separate changed-config request with a one-per-type cap produced four reviews, confirming the configuration participates in cache selection. The normal application retains the original ten-per-type policy.

Complete evidence stays in a three-entry server LRU; it is not sent as thousands of widget rows or stored in session state. Evidence details are queried for only the requested 50-row page. Complete JSON preparation is explicitly on demand and can consume several MB of server/download memory. Cache misses or evictions rerun the existing engine. Metadata fingerprint checks still query PostgreSQL on interactions, including cache hits. The service lock serializes access during a cold detector evaluation; high-concurrency hosting has not been load tested.

The 12-entry aggregate cache and three-entry opportunity cache are bounded. Source versions are checked on interaction/refresh, not continuously. Future manual supplier-mapping edits need a mapping revision key before relying on caches. The broad category labels, limited history, review thresholds, overlapping exposure and disclosure-subset caveats from Milestone 4 still apply. Wide source-line tables use horizontal scrolling on narrow screens. No known blocking functional defects remain after the reset correction.

See [dashboard guide](dashboard_guide.md) for architecture, launch, controls, downloads and configuration. No financial scenarios, executive presentation generation or AI functionality were implemented.
