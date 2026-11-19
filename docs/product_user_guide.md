# Product operation and development

Install the Python environment using the root README, then `npm --prefix apps/web ci`. Export root `.env`, start the existing PostgreSQL cluster, and run `procureiq app-db init`. With ports 8000 and 5173 free, `./scripts/dev.sh` starts both local servers and stops its own processes on exit. React is at <http://127.0.0.1:5173>; API documentation is at <http://127.0.0.1:8000/docs>. Start Streamlit separately with `streamlit run src/procureiq/ui/app.py --server.port 8501`.

The launcher does not create databases or delete existing volumes. Native PostgreSQL startup remains documented in [data pipeline](data_pipeline.md). Frontend `VITE_API_BASE_URL` contains only a local API origin; never put database credentials in Vite variables. Root `.env` is server-only and ignored.

## Connected workspaces

- Command Center shows actual spend, prioritized reviews, case activity and pipeline state. Open a review to inspect its explanation, then create or open its deduplicated case.
- Spend Explorer uses explicit reporting filters, positive/credit/net trends, supplier Pareto and category concentration. Search transactions on the server and inspect original source lineage. Category/supplier links carry reporting context into reviews and scenarios.
- Investigations preserve the original evidence basis. Bookmark evidence from its detail dialog. Record notes or findings, attach bookmarked evidence, edit with revision checks, or soft-delete with confirmation. Activity retains before/after text. Removal of a bookmark retains existing citation lineage. Close only after REVIEWED with a disposition and meaningful explanation; explicitly reopen before more analyst edits. A case outcome is not verified savings.
- Strategy Studio binds one selected positive-payment pool or an explicitly manual baseline. Enter independent Conservative/Base/Ambitious assumptions, calculate, inspect sensitivity/break-even and download JSON/XLSX. JSON persists across sessions; navigation within React preserves current state. Import never trusts stored outputs. Stale sources block calculations/exports until explicit refresh. See [financial methodology](financial_scenario_methodology.md).
- Optimization Studio requires comparable units and analyst-entered costs/capacities. Its example is clearly illustrative. Change constraints, solve, compare recent alternatives, save an immutable run, reopen/copy it or export complete assumptions/results. See [optimization methodology](optimization_methodology.md).
- Data Operations lists controlled manifests, source versions, quality evidence and durable runs. Read-only verification is the default. Register a receipt and ingest explicitly; new hashes remain inactive. Inspect stages before separately confirming activation. Failed/interrupted verification or ingestion can be retried; activation always needs a fresh review. See [operations guide](data_operations.md).
- Reports selects a scope and recomputes executive findings. Explicitly include a compatible calculated scenario and optional exact-scope case IDs. Case links prefill the case. Download editable five-slide PPTX, complete evidence JSON and scenario Excel. Analyst findings remain attributed; case context is included in the JSON and final-slide speaker notes. No overlapping exposures are added.

## Development checks

From the repository root, with guarded `TEST_DATABASE_URL` exported:

```sh
.venv/bin/python -m pytest -q
npm --prefix apps/web run lint
npm --prefix apps/web run build
npm --prefix apps/web test -- --run
procureiq db verify
procureiq analytics verify
procureiq opportunities verify
```

The build includes strict TypeScript checking. Tests use synthetic fixtures only in isolation; production pages read the local API. Vite dev binding is loopback. Restart Uvicorn after backend edits (the launcher deliberately does not enable reload); Vite handles frontend edits. The API's solver time limit is bounded at 30 seconds. Query cancellation aborts client fetches; it does not promise to cancel an already-running synchronous database/solver computation. Pipeline jobs survive browser navigation.

Wide evidence, sensitivity and supplier-input tables scroll horizontally on narrow screens. Mobile navigation uses the Menu button. Monetary totals are exact strings; charts use floating-point display coordinates. Native Office and multi-user/remote deployment are outside the verified scope.

## Redesigned interface controls

Use Cmd/Ctrl+K or **Quick jump** to search implemented workspace routes. The desktop sidebar collapses to icons; **Menu** opens the mobile drawer. Theme and sidebar preferences persist locally. The top bar shows the actual active reporting period and local API connection state.

Saved Cases and Command Center hide titles explicitly prefixed `[LOCAL DEMO]` by default. **Show demo cases** reveals the retained examples with Demo badges. The full original title is under **Original saved title** in case Overview; original objectives, findings and events remain unchanged. Search applies to the currently loaded case page, and counts explicitly distinguish loaded/demo-inclusive populations.

Spend Explorer has focused tabs and removable reporting-filter chips. Supplier cards open activity/category details. **Inspect** opens a source drawer; expand technical lineage for hashes and record positions. Case **Review evidence** opens the evidence tab. Findings' citation chips open the frozen referenced record directly, even when its original source version is no longer active. **Manage case lifecycle** opens the confirmation/reason form; Escape cancels without submission.

Scenario sliders supplement exact decimal inputs. Recalculate after changes; comparison cards and heatmap colors describe hypothetical outcomes, not expected savings. The dependency slider in Optimization also has an exact input. Allocation bars show actual solver results; infeasible outcomes show explanations instead of an allocation chart. Saved runs remain immutable.

Data Operations presents recorded stages and source versions; expand a stage for validation output. Reports offers a saved-case selector as well as exact IDs, checks scope/source compatibility on preview and exposes separate export cards. Demo report context remains explicitly attributed.

See the [design system](ui_design_system.md), [component provenance](ui_component_sources.md) and [browser/test verification](product_redesign_verification.md).


## Workflow refinement and Demo Mode

Use the shell Demo Mode switch to select a persisted investigation namespace. The former per-page “Show demo cases” pattern is superseded. Normal and demo cases now deduplicate independently. Follow the connected [workflow guide](product_workflow_refinement.md) for evidence filters, notebook findings, supplier drill-downs, guided models and report previews.
