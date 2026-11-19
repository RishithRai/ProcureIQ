# Product workflow refinement

Implemented locally on 16 October 2026, on the approved neutral/indigo React design system. The application still uses the existing FastAPI, PostgreSQL, opportunity detectors, Decimal financial engine, MILP solver and editable document generators.

## Start with the right workspace

The shell's **Demo Mode** switch selects a persisted investigation namespace: `NORMAL` or `DEMO`. Normal is the default for new sessions and clients without the namespace header. The selected mode survives a page reload in the same browser session. Analytical HMRC payments are real in both modes. This is logical local separation, not authentication or an authorization boundary.

Normal counts, recent activity, reviews, case lists and report selection exclude demo investigations. A normal and demo case can coexist for the same opportunity and exact source/policy/filter basis. Each namespace independently deduplicates in PostgreSQL. Opening a case URL in the opposite mode shows an explicit message requiring a switch; it does not silently change mode. Switching clears queries and scenario/report selection state; pending API writes disable the switch.

Migration `004_investigation_namespaces.sql` takes an exclusive case-table lock, checks legacy basis conflicts, adds the constrained namespace, classifies only the exact leading `[LOCAL DEMO]` prefix and replaces the unique basis constraint with `(review_basis_key, namespace)`. It runs in the existing checksum-tracked application migration transaction. Existing IDs, references, titles, objectives, frozen snapshots, source references, findings, notes, bookmarks and event history are retained. Ordinary snapshot protection also makes the new namespace immutable. The existing three explicitly prefixed cases were classified DEMO. No ambiguous title was inferred to be a demo.

Migration `005_finding_sections.sql` adds nullable structured finding sections. Existing free text stays unchanged. New optional assessment and next-step fields are included in the existing transactional before/after audit events. Neither migration changes analytical migrations or source fingerprints.

## Explore → investigate

Command Center uses backend counts for the selected namespace. With no cases it presents a three-step introduction and priority reviews without oversized empty activity panels. With work in progress it prioritizes current cases and events; reviewed cases still count as work requiring a disposition. An all-closed workspace gets a completed-work message. Compact expenditure values retain exact values in their tooltips.

Review Queue retains its two-panel layout. Review type and minimum priority are available beside the bounded-page search. Reporting filters remain exact. The desktop detail is sticky and independently scrollable. Its action reflects the selected namespace: Create Investigation, Open Investigation or View Closed Investigation. Closed cases never reopen implicitly. Deferred candidates remain ineligible.

A case opens with an Investigation Brief, original priority/exposure, evidence counts and **Continue Investigation**. This opens Evidence for open/investigating cases and Findings for reviewed/closed cases. Lifecycle controls and actual bookmark/finding/note counts are in the context panel; less frequent scope, scenario, sourcing and report links are under More actions. All original objective/hypothesis wording remains accessible.

## Historical Evidence Explorer

Evidence searches only the saved case references and their retained original source versions. It never substitutes the current active transaction population. Filters support exact original supplier, bounded reporting month range, minimum/maximum parsed amount, transaction-reference substring, original-field text search and primary/contextual classification. Text search is a case-insensitive literal substring of original field JSON, including field names; it is not fuzzy entity matching. Transaction references are not assumed unique.

Filters run on the server before deterministic ordinal pagination. The response contains filtered and unfiltered totals plus leading suppliers, month counts and positive/credit composition for the filtered historical population. Summary buttons apply filters. The browser displays at most 50 rows per page; an open drawer retrieves one record at its position within the same filtered ordering. Previous/Next cross page boundaries without loading the population. Technical hashes and raw fields remain expandable. A large payment is not labelled suspicious.

The drawer can bookmark a record or **Add to finding**. The latter first persists a case-validated bookmark and opens a preliminary finding editor with that citation selected. Existing finding citations remain frozen even if their bookmark is subsequently removed. The existing revision and closed-case rules remain enforced.

Findings and notes form a notebook, with a focused New Finding/New Note drawer, original observation text, optional assessment and next step, selectable bookmarked evidence, and citation links. Bookmark selection is paginated. Historical unstructured reasoning remains the original observation field; it is not heuristically split or rewritten. Edit/removal uses optimistic versions and append-only before/after events. Activity filters lifecycle, finding, note and evidence events on the server while retaining event-ID chronology.

## Spend discovery → financial decisions

Spend Overview combines monthly payments, five leading categories/suppliers and concentration context. Category search applies to the complete selected aggregate population before pagination. Click a category bar to choose matching transactions, related suppliers/reviews or an exact-scope scenario. Supplier cards and the full ranking table are separate views. Pareto receives every positive-payment supplier aggregate in scope, uses full-population cumulative resolved shares and has an 80% reference; it is independent of the 50-row ranking page.

Supplier profiles show period, positive/credit/net totals, source-line count and share context. Monthly points and equivalent keyboard-accessible month links open exact supplier/month transactions. Category/area bars show the five leading groups, backend-calculated Decimal shares of the supplier's positive payments, and an expandable complete breakdown. Selecting a group opens cross-workspace actions without merging similar published labels. Charts use display precision; exact amounts remain in text/tooltips.

Financial Scenario Lab deliberately binds one expenditure scope. Selecting the completely unfiltered population requires an explicit acknowledgement; it never implies full addressability. JSON import is under Load saved scenario. The three independent assumption cards provide plain-language help, exact inputs/sliders, labelled examples and Copy from Base. A 700 ms debounced preview calls the verified backend; JavaScript does not calculate financial outputs. Invalid input does not generate a replacement result. Source incompatibility still blocks outputs/exports until reviewed.

Comparison shows gross benefit versus costs alongside exact gross/net/cost/ROI cards. Sensitivity cells expose their assumptions, highlight matching current assumptions, and support click/Enter to apply a pair and recalculate through the backend. Break-even is the improvement needed to cover same-period costs, not a forecast. Excel/JSON downloads and report navigation retain the bound baseline's scope.

## Optimization → comparison

Optimization is a four-step builder: requirement, suppliers, constraints, optimize/compare. Inputs remain explicit analyst assumptions, never inferred from HMRC payments. Requirement validation and constraint bounds give actionable guidance. The final step has one Run optimization action, actual status/cost, one allocation-share chart, allocation/cost table and binding constraints. Infeasible results do not show a feasible allocation.

Saved Strategies is separate. Loading copies a saved configuration into the builder and makes it available for comparison. Comparison shows only runs sharing units, demand and supplier names, alongside cost, allocation, dependency, supplier-count constraints and expandable complete assumptions. That structural check does not prove commercial equivalence; analysts must compare all assumptions. No solver-cost difference is labelled verified savings. Saved runs remain immutable.

## Supporting data operations

Overview, Pipeline Runs, Sources and Data Quality are separate tabs. The run view reports actual stage durations/output and labels a successful run's final stage correctly. Success can mean already-ingested sources were revalidated; it does not imply new records.

Sources is a compact version table. Add source uses the existing controlled receipt registration/ingestion flow. Revised versions stay inactive until explicit reviewed activation. No browser filesystem path or arbitrary remote URL is accepted.

Quality has exact all-version/filtered totals, code/severity/month/search filters, grouped counts, server pagination and an issue/source-record drawer. Stored issue codes and warning severities are unchanged. Examination of the existing React API found a default page of 50 and maximum 100, not a 200-item service cap; the earlier observed 200 was not the total population. Actual acceptance traversed all **1,761** recorded issues through 18 pages of at most 100 without missing/duplicate IDs. The UI uses 50 per page. This count concerns recorded quality issues, not proven duplicate payments.

## Evidence → executive report

Reports has scope, inclusion and preview/export stages. Select key spending insights, recommended reviews, compatible saved cases, their analyst findings and a compatible calculated scenario. Saved-case search is explicitly limited to the loaded first 100 records; exact IDs remain a secondary fallback. The server enforces namespace, exact case scope/source and scenario compatibility.

Key Spending Insights are disclosed-payment observations, distinct from attributed analyst findings and hypothetical scenarios. The five-slide visual preview is dynamically extracted from the **actual generated PPTX**: slide positions, text, tables and chart data. It is explicitly labelled a browser approximation, not pixel-exact Microsoft Office rendering. No static slides are substituted. Case findings remain attributed in the report context and editable speaker notes, as in the existing generator.

The preview returns a content hash. Downloads submit that hash and source fingerprint; changed case content or source requires a fresh preview. Download Presentation is primary; evidence JSON and compatible Excel are secondary. Existing editable PPTX/XLSX engines are preserved.

## Operating boundaries

Run the application migrations before starting the updated API. Existing clients default to NORMAL. Send `X-Investigation-Namespace: DEMO` explicitly for demo workflows. Keep the unauthenticated API on loopback.

The local acceptance case **PIQ-000037** is intentionally NORMAL to prove coexistence with DEMO **PIQ-000001**. Its title/objective/finding explicitly identify workflow verification and assert no commercial conclusion. Original demo cases remain unchanged. See [verification](product_workflow_verification.md) for executed checks and limitations.
