# ProcureIQ dashboard — Milestones 5–7

## Launch

Run from the repository root with the existing PostgreSQL cluster running:

```sh
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e '.[dev]'
set -a
source .env
set +a
streamlit run src/procureiq/ui/app.py
```

Open <http://127.0.0.1:8501>. The project configuration binds the application to loopback and disables usage telemetry. `.env` is not read implicitly. Keep credentials uncommitted; see [database setup](data_pipeline.md) for starting PostgreSQL. The installed `procureiq` package supplies all imports; no working-directory `sys.path` changes are used. Stop the application with Ctrl+C. No database initialization or ingestion runs from the UI.

The lock records the actual verified environment, including Streamlit 1.66.0 and Plotly 6.9.0. Python 3.14.7 was used for acceptance. Milestone 6 adds the Financial Scenario Lab and XlsxWriter 3.2.9 exports. Milestone 7 adds Executive Brief and editable PowerPoint generation. AI remains unimplemented.

## Shared population controls

Use the sidebar to choose a reporting-month range and exact, single-value expense type, expense area, entity and normalized supplier. All means no restriction in that dimension; the full available month range uses the backend's unfiltered date semantics. Options come from active database records. Incompatible combinations show an empty-state message and zero totals rather than substitute data. NULL classifications and unresolved suppliers remain included under All; unresolved-only filtering is not part of the existing backend contract.

Reset Filters restores the full population and resets table, drill-down and Radar controls. The active page remains selected. Filter changes recalculate SQL aggregates and opportunity scores from selected underlying lines; they do not average existing HHIs. The current period, source-basis fingerprint and active line count appear on every page. Unparsed monetary values and unresolved identities are flagged when present. On smaller screens, use the sidebar toggle to open filters and navigation.

The application checks active versions on each rerun. A changed version resets filters and drill-downs, announces the change and selects a new cache key. If the source changes between queries, the interface stops with a refresh message instead of combining snapshots. Refresh source basis explicitly triggers this check without changing data. Changes in another process become visible on the next interaction; the application does not continuously poll.

## Spend Overview

Five KPI cards show exact positive disclosed payments, credit magnitude, net payments, published line count and distinct resolved suppliers. Values come from SQL NUMERIC/Decimal. The positive/net chart control changes the monthly trend, top ten categories, areas and supplier charts. Category contribution always uses selected positive payments and is explicitly labeled. Missing source months create chart gaps; covered months with no matching lines show zero.

The expenditure explorer switches between category, area and monthly tables. Search and the Sort by/Descending controls operate across the whole aggregate table before pagination; at most 50 rows enter the rendered table. Native column-header sorting applies to the visible page. CSV downloads include every row matching the table search, not just the visible page. Financial CSV values retain exact decimal text. Treat published labels as data when importing CSV into spreadsheet software.

## Supplier Intelligence

Rankings retain positive payments, credits, net, shares, activity months and purchasing-area counts. Overall and category Pareto curves reuse the SQL cumulative percentages, including the crossing supplier at 80%. The cumulative curve uses the resolved-supplier denominator; supplier shares of all selected positives remain separate. Credit-only/zero suppliers remain in the ranking but do not enter the positive-payment Pareto curve. Empty positive denominators show unavailable metrics.

Category concentration includes HHI, top-one and top-three shares, positive supplier counts, area coverage and mapping coverage. A supplier-filtered selection may have HHI 10,000; it describes the selected population, not inefficiency. The supplier drill-down applies the chosen supplier within the sidebar filters and displays summary, categories, trend, purchasing areas, exact published aliases and paginated transaction lines. It does not replace the broader rankings above it. Alias names shown are those occurring in the selected population, not inferred legal identities.

## Opportunity Radar

The existing engine supplies candidates, scores and evidence without changing detection policy. The page separately shows qualified candidates, exported reviews and cap-deferred candidates. Default acceptance yields 112 qualified, 34 exported and 78 deferred; these are calculated results, not UI constants. Type and minimum-priority controls only narrow the exported review display. They do not recalculate scores, promote cap-deferred reviews or change sidebar population counts. Supplier filtering disables concentration detection explicitly.

Select a review to inspect exposure, observed evidence, procurement hypothesis, recommendation, score contributions, affected suppliers/areas, numerical metrics and limitations. The category trend is labeled as context for the sidebar population: it can cover more lines than a quality flag or payment window. Evidence completeness is never a probability of inefficiency or of savings. Scores and thresholds are analyst review policy; exposures overlap and must never be added as a portfolio savings figure.

Evidence defaults to the first 50 primary rows. Choose Primary or Contextual and a page number to fetch only that page's source details, including month, original supplier, amount, transaction reference, filename, source hash and record/physical-line references. Contextual rows support interpretation and are excluded from exposure. The largest default review has 6,497 primary rows, so the page control spans 130 pages.

Prepare complete evidence JSON constructs a download on demand containing the opportunity, full configuration/source/filter basis, all primary/contextual references and all corresponding detailed records. Nothing is truncated. The payload exists in server download memory; no full evidence table is stored in widget/session state. Preparing a download incurs a separate complete-record query. Large complete exports are best consumed as JSON rather than spreadsheet cells.

Optional policy overrides reuse the Milestone 4 config loader:

```sh
export PROCUREIQ_OPPORTUNITY_CONFIG=config/opportunities.example.json
streamlit run src/procureiq/ui/app.py
```

Unset the variable to use defaults. Policy settings are visible in the Radar audit expander. The UI does not silently tune thresholds. See [opportunity methodology](opportunity_methodology.md) for every formula and exclusion.

## Financial Scenario Lab

1. Choose the current filtered positive expenditure, a single expense category within those filters, or a user-supplied manual baseline. Click **Use selected baseline** to bind that one pool. Review the displayed period, positive/credit/net amounts, population and source fingerprint. Manual amounts carry no HMRC verification claim.
2. Enter independent assumptions for Conservative, Base and Ambitious. Addressability, adoption and improvement start at zero. The optional illustrative-example loader is explicitly unvalidated. Enter costs as plain decimal GBP text without currency symbols or commas.
3. Compare gross benefit, costs, net benefit and ROI. Zero costs yield unavailable ROI. Select a case and improvement range for the adoption/improvement heatmap; its break-even line and exact CSV show how outcomes depend on assumptions.
4. Download JSON for reproducibility or prepare the formula-driven Excel workbook on demand. Use the saved-configuration uploader to load validated JSON. Excel has editable highlighted assumption cells; use a recalculating spreadsheet application after edits. Workbook changes do not synchronize into the dashboard.

The Radar's **Start a scenario from this review** offers category expenditure for concentration/fragmentation reviews. Payment-pattern and data-quality reviews supply context only; their exposures are not copied into a benefit pool. Scores never determine improvement rates.

Changing sidebar filters does not overwrite a bound baseline or scenario inputs; a scope-difference message explains this. Ordinary page navigation preserves assumptions. **Reset scenario assumptions** restores all three cases to zero while retaining the pool. State lasts for the Streamlit session; save JSON before a session or server restart.

A changed active source fingerprint suspends calculations and exports for an old HMRC baseline. Review the old/current basis and explicitly adopt the new version, or select a new baseline. JSON imports undergo the same check; current-version imports must match fresh database evidence. The model performs no database mutations.

Results describe the selected period and are not annualized. VAT-inclusive disclosure amounts do not establish addressability or contract terms. The three cases are alternatives and must not be summed. See [financial methodology](financial_scenario_methodology.md) for formulas, rounding, input limits, JSON validation and Excel precision limitations.

## Architecture, caching and precision

| File | Responsibility |
|---|---|
| `src/procureiq/ui/app.py` | Entry point, sidebar, shared population, sanitized error handling |
| `service.py` | Read-only snapshots, source fingerprint, bounded caches, backend orchestration, paged source access |
| `formatting.py` | Exact Decimal display/CSV, filter construction and reset |
| `charts.py` | Reusable Plotly charts; numeric conversion only for visualization |
| `components.py` | Shared KPIs, searchable/sortable paged tables and evidence controls |
| `overview.py`, `suppliers.py`, `radar.py` | Page rendering without procurement formulas or embedded SQL |
| `scenarios.py` | Scenario page, persistent session assumptions, explicit baseline binding and exports |
| `financial_model.py`, `scenario_basis.py`, `scenario_io.py`, `scenario_excel.py` | Decimal engine, read-only baseline evidence, validated JSON and formula workbook |
| `.streamlit/config.toml` | Light theme, loopback binding, telemetry/error-display settings |

The engine is held by Streamlit's resource cache, not a serialized data cache. A thread-safe service maintains a 12-entry LRU for analytical outputs/options and a separate three-entry LRU for complete opportunity results. Cache keys include validated filters, active-source/migration fingerprint, rule version and configuration for opportunity results. Resource identity includes a hash of the configured connection URL. No credentials are rendered.

Full opportunity evidence stays in the bounded server cache; the UI receives compact summaries with counts, no reference arrays or per-row quality-flag map. Detection runs once on a cache miss, not on every table or evidence-page interaction. Cache eviction or process restart causes recalculation. Every read, including a cache hit, validates the expected fingerprint in a read-only repeatable-read snapshot. Small metadata checks intentionally remain uncached to detect activation. Queries have a 30-second statement timeout. Source detail retrieval uses parameterized IDs selected from the backend's actual opportunity references and rechecks active/filtered eligibility.

Caching assumes ingestion's immutable rows and current controlled supplier mapping policy. Future manual mapping-edit workflows need their own revision fingerprint before relying on these caches. Database health failures surface generic actionable messages, never dummy results or credential-bearing exceptions. Missing/invalid config paths and URLs are also handled. Streamlit hides unhandled error details in the browser.

Plotly receives floating-point coordinates only for drawing; exact totals, table money and evidence remain Decimal/string values. HHI, Pareto, shares and opportunities remain in the verified Milestone 3/4 layers. Scenario calculations use the separate Decimal financial engine.

Implementation references: [Streamlit caching](https://docs.streamlit.io/develop/concepts/architecture/caching), [download buttons](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button), and [Plotly multiple axes](https://plotly.com/python/multiple-axes/).

## Verification

Run the required checks with both database URLs exported; integration tests reset only the guarded test schema:

```sh
python -m pytest -q
procureiq db verify
procureiq analytics verify
procureiq opportunities verify
```

[Milestone 5 verification](milestone5_verification.md) records actual test results, the browser walkthrough, screenshots and limitations. Database ingestion, SQL migrations and opportunity policies remain unchanged.

[Milestone 6 verification](milestone6_verification.md) records the 110-test acceptance run, scenario browser walkthrough and independently recalculated workbook. Milestone 7 adds the Executive Brief described below; AI remains unimplemented.


## Executive Brief

The fifth page uses the same sidebar population and read-only service. Its summary includes exact current-filter money, line counts, concentration and qualified/exported/deferred review counts. Key findings come from the existing SQL outputs. Empty populations and populations with no eligible review themes show explicit messages rather than invented recommendations.

The management shortlist contains one recommendation per eligible theme, up to four. It retains existing scores, uses exposure as a materiality tie-break and avoids heavily overlapping source evidence when another candidate in the same theme is available. Every remaining shared primary-row intersection is disclosed. Expand a recommendation to distinguish observed evidence, interpretation, action and additional validation required. **Inspect this review in Opportunity Radar** opens the matching review and existing paginated evidence workspace.

Use **Open Financial Scenario Lab** to define or review a scenario. On return, explicitly check **Include this reviewed scenario in the brief and presentation**. Inclusion requires a current HMRC-linked baseline with matching period and filters; a category subset is allowed in an all-category brief. Manual, stale or incompatible pools are not included. The checkbox resets when inputs or reporting basis change. The Lab's assumptions remain intact during navigation.

**Prepare executive PowerPoint** creates a five-slide contextual deck from this population. The download appears after generation. If no matching scenario is selected, Slide 4 explains the framework without financial results. Source versions are rechecked before exposing the download. An already downloaded deck is a fixed snapshot, not a continuously updated report.

For the reproducible full-population demonstration, run `procureiq executive export`. This CLI intentionally uses the documented illustrative Milestone 6 assumptions. An optional `--scenario PATH` accepts validated, compatible JSON; `--output PATH` chooses a local PPTX filename. A same-stem evidence JSON accompanies the CLI deck. See [executive methodology](executive_methodology.md) and [final verification](final_project_verification.md).
