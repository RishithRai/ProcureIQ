# Product API extension

The existing [investigation API](investigation_api.md) remains supported. Interactive typed request/response documentation is served at `/docs` and `/openapi.json`. All routes below use `/api/v1`. Error bodies retain the existing `{error:{code,message}}` envelope; unknown internal database errors are sanitized. Monetary values are decimal strings, not floating-point JSON totals.

| Route | Purpose |
|---|---|
| GET `/command` | Actual spend, case status counts, recent activity and source basis |
| GET `/spend/options`, `/spend/summary` | Existing analytical filter choices, overview and monthly totals |
| GET `/spend/groups/{kind}` | Paginated expense_types, expense_areas, suppliers or category_concentration |
| GET `/spend/transactions`, `/spend/transactions/{raw_id}` | Server search/order, bounded source rows and complete lineage |
| GET `/spend/suppliers/{id}` | Normalized identity, aliases and filtered supplier intelligence |
| GET/POST `/investigations/cases/{id}/entries` | Read/create analyst note or finding |
| PATCH `/investigations/cases/{id}/entries/{entry_id}` | Expected-revision edit or soft deletion |
| GET/POST `/investigations/cases/{id}/bookmarks` | Paginated frozen evidence references; explicit active flag |
| POST `/strategy/baseline`, `/calculate`, `/import`, `/refresh`, `/excel` | Existing validated financial engine and interchange |
| POST `/strategy/optimization/solve` | Actual bounded MILP execution |
| GET/POST `/strategy/optimization/runs`, GET `/{run_id}` | Immutable saved assumptions/results; POST re-solves server-side |
| GET `/operations/manifests`, POST `/operations/registrations` | Controlled receipt discovery/registration |
| GET/POST `/operations/runs`, GET `/{run_id}`, POST `/{run_id}/retry` | Durable worker operations and recorded stage outcomes |
| GET `/operations/sources`, `/operations/quality` | Paginated active/inactive sources and issue lineage |
| POST `/reports/preview`, `/reports/download/{pptx|json}` | One-basis executive output with optional compatible scenario/cases |

Lists default to 50 with maximum 100 and stable ordering. Filter choice metadata is the existing dataset's distinct labels; aggregate supplier detail is bounded by the selected dataset dimensions. Exact text filters preserve whitespace and use parameterized SQL. Transaction order is an allowlist, not submitted SQL. Expected basis mismatches return a structured conflict. Entry revisions are independent of lifecycle row versions; both protect their respective mutable fields.

Entry inputs: kind (`note`/`finding`), meaningful title/content, expected_version for updates, deleted for soft removal, and up to 100 distinct `{classification,ordinal}` citations belonging to this case's active bookmarks. All edits and event evidence commit atomically. Closed cases reject analyst writes.

Pipeline POST uses operation `verify`, `ingest` plus registration_id, or `activate` plus source_file_id, expected_fingerprint and confirm_activation=true. Registration returns 201; queued jobs return 202; inspect the run for actual success/failure. No browser-supplied command or path is executed.

Financial calculations require exactly the three named alternatives and an explicit baseline. Existing scenario JSON validation recomputes results and rejects forged current-source claims. Reports require compatible financial scope; investigation inclusion requires the same source and exact reporting filters. Saved optimizer results never trust a client-supplied objective or allocation.


## Workflow refinement endpoints

`GET /spend/groups/{kind}` adds full-population aggregate `search` before pagination. `GET /spend/pareto` returns all positive-supplier aggregates, original cumulative percentages and supplier ranks. Supplier breakdowns include Decimal `supplier_positive_share_pct`. Quality adds `issue_code`, `severity`, `reporting_month`, `search`, `all_total` and grouped counts. Report requests add `include_insights`, `include_recommendations`, `include_findings` (default true) and optional `expected_content_hash`. Preview returns dynamic `presentation` slide data and `brief.content_hash`; a mismatched pinned hash returns 409 `stale_report`. Report case selection is namespace-aware.
