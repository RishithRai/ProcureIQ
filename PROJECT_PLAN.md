# ProcureIQ — Master Project Plan

**Project:** Procurement Spend Intelligence & Cost Optimization  
**Version:** 1.0 — architecture baseline, 15 October 2026  
**Target:** seven focused build days for a working MVP; follow-on improvements afterward  
**Primary data:** Official HMRC disclosed payments over £25,000, April 2025–March 2026  
**Status:** planning only; no implementation or measured project results are claimed.

## 1. Project mission

Transform 12 months of HMRC public payment-disclosure data into an auditable procurement analytics application that (1) reconciles source transactions, (2) explains spending and supplier concentration, (3) surfaces *candidate* areas for human investigation, (4) models explicitly hypothetical financial improvements, and (5) turns evidence into an executive briefing.

**Success is not an invented savings number.** Success is reproducible engineering, credible analytics, transparent assumptions, and recommendations that separate observable facts from decisions requiring additional private procurement information.

### Primary user journeys

1. **Procurement analyst:** choose a reporting period, category, area, or supplier; explore the disclosed gross payment mix and underlying entries.
2. **Category manager:** understand top-supplier exposure, fragmentation, and unusual payment patterns, with all denominators visible.
3. **Consultant:** review and rank explainable opportunity candidates and inspect supporting data.
4. **Finance partner:** explore one-year hypothetical improvement scenarios, implementation costs, sensitivity, and export assumptions.
5. **Executive:** read a succinct set of findings, caveats, and validation actions; export five presentation slides.

## 2. Authoritative data interpretation

- Dataset index: https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc
- Official collection and field definitions: https://www.gov.uk/government/collections/hmrc-spending-over-25000
- Official expenditure terminology: https://www.gov.uk/government/publications/hmrc-glossary-of-terms-used-in-departmental-spending-over-25000-pages
- Coverage: twelve **publication/reporting months**, April 2025 to March 2026 inclusive; do not mistake payment dates for reporting-month identity.
- HMRC states figures are **gross and VAT-inclusive**. Positive values generally indicate invoices, negative values credit notes/memos. Disclosed lines can be below £25,000 because a qualifying invoice can be split by expense type or area. Do not treat a below-threshold line as an error.
- Expense type is HMRC's ERP **material-group description**, not necessarily a homogeneous commodity or proof of price comparability.
- The public files are a **disclosure subset**, not total organizational procurement or full supplier contract/performance data.
- The July and August 2025 public previews each show optional `Supplier Type`, `Contract Number`, `Project Code` columns. Full-file schema variations must be measured in Milestone 1.
- Repeated transaction numbers and exactly repeated-looking source lines are *review candidates*, not safe deduplication criteria. Source row position + file version defines row identity.
- Source fields, counts, totals, missingness, data errors and realized results: **do not invent them**. Derive them from actual downloaded files.
- Recommended display term: **disclosed gross payments**, not 'total HMRC procurement spend'.

## 3. Technology and execution decisions

- Python 3.11+; Pandas, NumPy for cleaning/profiling and selected statistical calculations.
- PostgreSQL (local Docker Compose or existing PostgreSQL installation). SQL in checked-in `.sql` files.
- SQLAlchemy 2.x plus psycopg 3 as the minimal Python/PostgreSQL connection layer; no REST backend or microservices for MVP.
- Streamlit + Plotly for dashboard; Streamlit cache only for read queries and invalidation when a data refresh occurs.
- `decimal.Decimal` during currency parsing and PostgreSQL `NUMERIC(20,2)` for stored pounds/pence; no floating-point money storage. Explicit two-decimal validation, never silent rounding of a greater-precision source value.
- Python financial model and Excel export through openpyxl or XlsxWriter; verify calculated workbook outputs against Python.
- Pytest for unit and integration tests; Git + GitHub for version control.
- Optional python-pptx for programmatically generated five-slide executive deck, or a documented, manually assembled deck using exported figures.
- Dependencies pinned to compatible versions after implementation tests. Keep secrets in `.env` / Streamlit secrets, excluded from Git.

## 4. Architectural flow

```
Official HMRC CSVs (12) + provenance manifest
            |
            v
Acquire -> immutable downloaded files -> schema/data-quality report
            |
            v
PostgreSQL: ingestion manifest + raw source rows (lossless JSONB)
            |
            v
Validated typed expenditure lines + curated supplier aliases
            |
            v
Versioned SQL analytical views + row-level evidence links
            |
       +----+----------------+
       |                     |
       v                     v
Supplier and spend       Opportunity detector
analytics                  (rules + explanations)
       |                     |
       +-----------+---------+
                   v
          Scenario calculator
                   |
                   v
       Streamlit/Plotly app
                   |
        CSV + Excel + 5 slides
```

**Architectural rule:** raw source rows are immutable; derived tables are reproducible. Every analytical output is calculated from known filters, source files and code versions. No silent dropping of rows or undocumented manual transformations.

## 5. Repository structure (target, not yet created)

```
ProcureIQ/
  README.md
  PROJECT_PLAN.md
  pyproject.toml
  .env.example
  .gitignore
  docker-compose.yml                 # PostgreSQL only, if used
  data/
    raw/                           # original files, gitignored
    fixtures/                      # tiny synthetic test CSVs
  manifests/
    hmrc_sources.json               # official source links and reporting month
  src/procureiq/
    acquisition.py
    profiling.py
    parsing.py
    supplier_identity.py
    db.py
    ingestion.py
    queries.py
    opportunities.py
    scenarios.py
    reporting.py
  sql/
    001_schema.sql
    002_views.sql
    003_analyses.sql
  app/
    Home.py
    pages/
      1_Spend_Overview.py
      2_Supplier_Intelligence.py
      3_Opportunity_Radar.py
      4_Scenario_Lab.py
      5_Executive_Brief.py
  tests/
    test_acquisition.py
    test_parsing.py
    test_ingestion.py
    test_sql_analytics.py
    test_opportunities.py
    test_scenarios.py
  reports/
    milestone1_findings.md
    file_inventory.csv
    schema_comparison.csv
    data_quality_summary.csv
  deliverables/
    procurement_scenario_model.xlsx
    ProcureIQ_Executive_Brief.pptx
    screenshots/
```

A smaller actual layout is acceptable if justified. Avoid boilerplate folders, generic repository abstractions, distributed components, and unused services.

## 6. Database logical model

**Confirm exact source columns and parsing first in Milestone 1.** Proposed minimal relational model:

1. `source_file`: `file_id` PK, reporting month, source URL, source filename, content SHA-256, byte size, downloaded timestamp, ingestion status, expected/observed line count. Store every different source version separately; select one active version per reporting month when aggregating.
2. `raw_spend_row`: `raw_row_id` PK, `file_id` FK, `source_row_number`, `source_values JSONB`, `row_hash`, ingestion timestamp, unique `(file_id, source_row_number)`. Never enforce uniqueness on a public transaction number.
3. `supplier`: `supplier_id` PK, `canonical_name`, optional provenance/review metadata. Every supplier shown is traceable to an original name.
4. `supplier_alias`: raw supplier name, normalized search key, `supplier_id`, mapping method, reviewed flag/review date. Apply only safe automatic whitespace/case canonicalization; uncertain legal-entity merges require explicit analyst approval. Preserve original names.
5. `spend_line`: `spend_line_id` PK, `raw_row_id` UNIQUE FK, `payment_date`, `reporting_month` (or infer from `source_file`), `entity`, `department_family`, `expense_type`, `expense_area`, `supplier_raw`, `supplier_id`, `transaction_number TEXT`, `amount_gbp NUMERIC(20,2)`, `description`, `supplier_postcode`, optional source fields, `parse_status`. Invalid typed values may remain NULL, never converted to zero. Unparsed raw rows must still be preserved and their exclusion from analysis flagged.
6. `data_quality_issue`: issue_id, raw row/file FK, issue code, severity, original offending value, details, observed timestamp.

Use sensible unique constraints and indexes for `payment_date`, `reporting_month`, supplier ID, expense type/area and source relationships. Avoid prematurely building a large star schema. More elaborate dimensional models only if verified queries need them.

**Reconciliation invariants:** one manifest entry per selected month, 12 selected months, raw row counts match parsed-file row counts, every raw row has an ingestion classification, every valid typed row maps to exactly one raw row, source parsed currency totals equal typed row totals to the penny, and no unreviewed alias merge changes money totals.

**Typed-record exclusions:** explicitly report invalid dates/amounts, record counts, and affected monetary totals when computable; never silently substitute `0` or drop lines. Never delete duplicates automatically.

## 7. Analytical definitions

**Population:** exactly the selected official source versions for April 2025–March 2026. Every chart identifies whether its grouping is by `reporting_month` or `payment_date`.

**Money conventions:**
- `net_disclosed_gbp = SUM(all correctly parsed signed amounts)` (gross VAT-inclusive payments, net of published credits).
- `positive_disclosed_gbp = SUM(amount WHERE amount > 0)`.
- `credit_magnitude_gbp = -SUM(amount WHERE amount < 0)`.
- Validate `net = positive - credit_magnitude` and reconcile both by source month.
- Use **positive payment amounts** for supplier share/Pareto/HHI and opportunity exposure, to avoid negative or zero denominators. Show net/credits alongside. Label this basis everywhere and never imply it is contractual spend or addressable savings.
- Missing or invalid monetary records make financial metrics incomplete and are displayed in a data-quality banner.

**Views / advanced SQL examples:**
- `vw_monthly_disclosed_spend`: gross-positive, credits, net, row count by reporting month, with source coverage.
- `vw_category_supplier_spend`: positive disclosed amount by expense type, supplier, area.
- `vw_supplier_ranking`: ranking, share, `SUM(...) OVER`, cumulative Pareto %, top 5/top 10 contribution, category-specific rankings.
- `vw_category_concentration`: category supplier share and HHI = 10,000 * SUM(share^2), plus largest supplier share and supplier count. HHI describes *observed spend concentration*, not antitrust market shares.
- `vw_supplier_monthly_trends`: month, lagged amount, period-on-period changes, movement coverage.
- `vw_data_quality_summary`: reporting-month anomaly/parse counts and exact-duplicate candidates.
- Additional SQL: CTEs, window functions (`RANK`, `LAG`, running cumulative totals), `FILTER`, conditional aggregation, and careful joins. Use `PERCENTILE_CONT` when analytically useful rather than just to demonstrate syntax.

**Metric definitions:**
- Unique suppliers = count of reviewed canonical supplier identities; supply a raw-name count for comparison.
- Supplier dependency = fraction of positive reported category spend allocated to a supplier in that reporting slice.
- Category fragmentation = high distinct supplier count and low top-supplier share, but not proof that spend is commercially substitutable.
- Payment volatility = observed variability in month-level positive paid amounts, not price inflation or invoice overcharging.
- Avoid classifying absent monthly spending as an operational stop without evidence; distinguish missing source month from true zero in present data.

## 8. Opportunity Radar design

Generate **review candidates**, never verified waste or guaranteed savings. All detectors return a common object: `opportunity_id`, `type`, `scope` (supplier/category/area/timeframe), `evidence_metrics`, `source_row_refs`, `positive_gross_exposure_gbp`, `severity_score`, `evidence_quality`, `priority_score`, `rationale`, `limitations`, `recommended_validation_action`, `generated_at`, `rule_version`.

**MVP detectors:**

A. **Concentration / dependency review** — categories with a meaningful disclosed positive spend base and elevated top supplier share and/or category HHI. Action: review contract resilience, switching constraints, single-vendor reliance; never conclude overpayment.

B. **Fragmentation / sourcing-coordination review** — material categories with numerous suppliers and diffuse shares, or the same category across multiple expense areas. Action: investigate whether purchases are genuinely substitutable, contracts overlap, or aggregation is appropriate. Do not presume consolidation is always optimal: it may worsen concentration.

C. **Payment-pattern review** — major month-on-month shifts, exceptional credit activity, or unusual spikes in established supplier/category payment histories; use minimum-history and spend filters, with simple baselines and robust statistics where defensible. Action: determine whether shifts come from billing cadence, one-off projects, annual renewals or anomalies. Never label fraudulent activity.

D. **Data-quality / master-data review** — probable supplier aliases, parse failures, duplicate-looking rows, missing supplier metadata or unusual classification patterns. Action: fix accounting/master-data lineage; don't treat repeated invoice IDs as proven duplicate payments.

**Explainable priority score:** define a documented, normalized 0–100 ranking over three 0–100 factors: e.g. 45% materiality (positive exposure relative to observed opportunities), 35% signal strength (rule-specific severity), 20% evidence completeness. Weights are explicit, configurable, and illustrative analyst priorities, not learned truth. Provide separate evidence confidence labels; a high priority is not a guaranteed saving. In thin categories or insufficient history, suppress or downgrade signal. Cap candidate count sensibly and show false-positive caveats.

**Evidence interactions:** select a flagged candidate -> show relevant supplier, category, months, computation details and the original source rows/file names, with CSV export. Include 'Next validation step' and 'What data would be needed to confirm?'. Keep recommendations reproducible and deterministic.

## 9. Financial Scenario Lab

The lab is a deterministic **one-year hypothetical model**, not a forecast of actual HMRC savings. Model one clearly selected opportunity/expenditure pool at a time by default; separately compare conservative/base/ambitious assumptions. Do not add the results of overlapping opportunity pools.

**Inputs**:
- `eligible_disclosed_positive_gross_gbp`: a filtered, traceable subset of the positive payments; user editable with explanation.
- `addressable_share` (0–100%): assumed portion of that pool actually comparable/contractually in-scope.
- `adoption_rate` (0–100%): assumed proportion taking up a change.
- `improvement_rate` (0–100%): hypothetical economic improvement for adopted/eligible amounts.
- `one_time_implementation_cost_gbp` and `annual_operating_cost_gbp`.
- `scenario_name`, source filters, date range, assumption notes, calculation timestamp.

**Equations (one-year equivalent, same currency/basis):**

```
addressable_base = eligible_disclosed_positive_gross_gbp * addressable_share
effective_base   = addressable_base * adoption_rate
hypothetical_gross_benefit = effective_base * improvement_rate
one_year_total_cost = one_time_implementation_cost_gbp + annual_operating_cost_gbp
hypothetical_net_benefit = hypothetical_gross_benefit - one_year_total_cost
scenario_ROI = hypothetical_net_benefit / one_year_total_cost  # only when total cost > 0
```

Use Decimal internally for amounts, validated bounded decimal rates, an explicitly rounded display and auditable calculation order. Show both percentage and £ values. If expenses include VAT but implementation costs do not, warn that the bases are not directly comparable. Do not infer VAT recovery, procurement unit economics, or realizable net savings. If projecting the reference period forward one year, explicitly state that **the disclosed 12-month baseline is assumed to recur**, not that it will.

**UI**: scenario sliders or number inputs; 3 scenario cards; waterfall or comparative bar chart; improvement-versus-adoption sensitivity heatmap; assumptions disclosure; CSV/Excel export. Excel should include editable inputs, readable formulas, unit labels, caveats and a Python-vs-Excel parity check where feasible. Negative results allowed.

## 10. Streamlit application: five screens

**1. Spend Overview:** KPI strip with net, positive, credit amounts, raw rows, suppliers and months; monthly trend, spending by type/area, top suppliers and a drillable source table. Filters: report month, payment-date window (where applicable), entity, type, area, supplier. Always state the amount basis. Data-health warning displayed when relevant.

**2. Supplier Intelligence:** top suppliers and Pareto; supplier share and category HHI; concentration/fragmentation scatter or ranked table; supplier-by-month trends; a profile view with categories and raw supporting rows. Warning about disclosed payments versus market concentration.

**3. Opportunity Radar:** ranked candidates, filters by type/severity/evidence quality, explicit rule explanation, key supporting metrics, false-positive notes, next validation action and source drill-down. Don't label items as confirmed cost savings.

**4. Scenario Lab:** select a candidate or category, eligible spend derived from its evidence, explicitly enter assumptions, compare scenarios, inspect sensitivities and export model.

**5. Executive Brief:** three-to-five evidence-backed findings, recommended verification steps, limitation banner and exportable briefing inputs/deck.

**Design:** coherent restrained neutral UI, clear chart captions and definitions, useful whitespace; cached read-only SQL queries; persistent filters only where useful. A row-level Data Lineage drawer / expandable table is more valuable than flashy visual effects.

## 11. Five-slide executive deck

1. **Executive decision page:** scope, verified headline figures and top takeaway; highlight limitation that disclosed payments are a subset.
2. **Where money goes:** expense-type/area mix, monthly pattern, Pareto of suppliers (actual figures from pipeline).
3. **Supplier concentration and review candidates:** 2–3 quantified candidate findings with evidence and uncertainty.
4. **One-year hypothetical scenario:** assumptions, eligible exposure, gross/net benefit and sensitivity ranges; clear 'scenario, not realized savings'.
5. **Recommended validation actions:** actions, evidence required, proposed owners and a staged 30/60/90-day *illustrative* validation plan.

Keep presentation claims and charts programmatically tied to a frozen reporting export where practical; prohibit manually entered fake numbers.

## 12. Seven-day milestone schedule and acceptance gates

### Day 1 — M1: Acquire and investigate
**Build:** official manifest and immutable file downloader, CSV profiling, per-file hashes/rows/schema/missingness/amount parsing, initial quality report, acquisition tests.  
**Gate:** 12 actual files verified; all reporting months accounted for; real schema comparison, record counts, totals and limitations documented. If downloads are blocked, implement manual-file fallback; do **not** claim gate passed until actual files are inspected.

### Day 2 — M2: PostgreSQL and reconciliation
**Build:** schema SQL, raw and typed ingestion, supplier alias strategy, row-level provenance, quality issues, repeatable loading, indexes, integration tests.  
**Gate:** same inputs load deterministically without duplicating rows; source-to-DB row and amount reconciliation passes; invalid typed fields remain visible.

### Day 3 — M3: SQL analytics and supplier intelligence
**Build:** 5–6 documented SQL views; Python query access; Pareto, category HHI, supplier monthly trends; SQL tests comparing simple independent Pandas/fixture answers.  
**Gate:** correct formula denominator (positive gross), correct joins, visible filter semantics, reproducible top-supplier/category results.

### Day 4 — M4: Opportunity Radar
**Build:** 4 deterministic rule-based candidate generators, configurable thresholds, score decomposition, text rationale/limitations/source rows; tests for edge cases, low history, same names and zero denominator.  
**Gate:** opportunities are traceable, reproducible, and never overstate evidence; no unsupported 'duplicate payment' or 'guaranteed saving' claims.

### Day 5 — M5: Interactive Streamlit MVP
**Build:** five navigable pages with functional overview, supplier analysis and radar; filtered SQL queries, tables, charts and evidence drilldown; initially a minimal placeholder message is acceptable for unfinished scenario/export functions, but no dummy KPI values.  
**Gate:** runs locally against real DB; filters affect tables, charts, summaries consistently; no mock values passed off as actual data; pages handle empty selections.

### Day 6 — M6: Financial scenario modelling
**Build:** validated one-year model, assumptions and comparison UI, sensitivity table, scenario export to Excel, financial calculation tests. Finish scenario and executive pages.  
**Gate:** calculations match hand-checked synthetic cases, extreme inputs are handled, overlapping candidates aren't silently double-counted, outputs labelled hypothetical.

### Day 7 — M7: Quality, documentation and executive briefing
**Build:** full end-to-end reload test, integration fixtures, reconciliation smoke tests, screenshots, README with one-command or few-command setup, known limitations, five-slide deck, polished demo and factual resume text.  
**Gate:** fresh clone works with documented dependencies and official source access; all tests pass or failures disclosed; no manufactured impact figures; completed demo walk-through.

Every day is a **gate**, not merely a calendar deadline: if a critical prerequisite fails, fix it before proceeding. Tests are written throughout, not postponed until Day 7. The timeline assumes concentrated work and local Python/PostgreSQL setup; external data problems may require reallocation.

## 13. Tests: non-negotiable cases

- CSV parsing: missing optional columns, BOMS/encoding, £ and comma separators, decimal precision, quoted commas, blank date/amount, signed credits, malformed strings, ragged rows, row-level error recording.
- Lineage: stable `file_id + source_row_number` uniqueness, hash match, source-file versioning and idempotent load; keep repeated transaction IDs and duplicate-looking lines.
- Financial reconciliation: `positive - credits = net` by month/whole dataset; selected source rows equal DB valid + invalid classifications; exact two-decimal aggregates.
- Identity mapping: case/whitespace variants merge only under approved deterministic rule; unrelated legal entities are not merged by aggressive fuzzy matching.
- Analytics: zero denominator, single supplier HHI = 10,000, equal split shares produce expected HHI, supplier Pareto cumulative reaches 100% for positive totals, financial totals unchanged across joins.
- Opportunity engine: deterministic rules; rule thresholds; low history yields 'insufficient evidence' not suspicious; evidence rows exist; no duplicate candidate references from duplicate joins.
- Scenario: 0% adoption/improvement -> no gross benefit; negative net allowed; no cost -> ROI N/A; 100% bound behavior; assumptions validation; Excel/Python consistency.
- UI: selected filters agree with SQL totals, empty filters do not crash, download output matches displayed scope, no secrets leaked in stack traces.

## 14. Evidence and provenance contract

Every dashboard/briefing claim should have:

```
claim_id | plain_language_finding | metric_definition
value | unit | observation_period | date_basis | money_basis
sql_view_or_query | filters | source_file_hashes
assumptions | limitations | created_at
```

The presentation uses a frozen `reports/executive_evidence.json` / CSV export based on query output, not hand-typed financial results. Actual figures may be shown only after verification. Recommendations are labeled `[Observed]`, `[Inference / review candidate]`, or `[Hypothetical scenario]` in documentation.

## 15. Scope priorities and boundaries

**Must ship (MVP):** 12-month acquisition + quality profiles; raw and typed PostgreSQL schema; row/amount reconciliation; supplier mapping; core SQL views; Pareto/HHI/monthly trends; 4 reviewed opportunity rules; real Streamlit UI with drilldowns; scenario calculations and Excel; five-slide deck; README + tests.

**Nice after MVP:** more rigorous alias curation, saved scenario comparisons, improved executive chart annotations, optional historic cross-year comparisons to separate annual seasonality from one-offs, reproducible containerized demo, CI, optional evidence-grounded LLM tool caller limited to audited read-only tools.

**Do not build:** prediction of procurement prices or vendor performance without relevant data; autonomous contract negotiation; real procurement savings claims; unverified duplicate-payment claims; generic LLM summaries hallucinating amounts; microservices, React front end, API layer, production-grade auth, orchestration infrastructure or expensive ML without decision value.

## 16. Suggested demo walkthrough (5–7 minutes)

1. Show 12 verified official source files and ingestion reconciliation.
2. Select an expense category in Spend Overview; show month, supplier and area breakdown.
3. Open Supplier Intelligence; interpret the observed top-supplier share and category HHI accurately.
4. Open Opportunity Radar; explain a review candidate and show original source-row evidence.
5. Open Scenario Lab; change one adoption assumption and see calculated gross/net hypothetical benefit and Excel export.
6. Close with concise executive recommendation and limitations.

## 17. Definition of done / resume standard

- Fresh setup and full-data rebuild run as documented.
- Source provenance, data scope and audit trail visibly function.
- SQL and calculations are independently tested and financially reconciled.
- Opportunity scoring is explainable and based on observed features.
- Scenario benefits are explicitly hypothetical with adjustable assumptions.
- Five-page app and five-slide executive deck use verified real data.
- Any resume metrics (rows, months, suppliers, tests, response times) are inserted **only after measured**.

