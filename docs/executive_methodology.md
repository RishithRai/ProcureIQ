> The complete React product extends this historical documentation. See [product architecture](product_architecture.md), [user/development guide](product_user_guide.md), [API extensions](product_api.md) and [verification](product_verification.md). Existing calculations and source policies remain authoritative.

# Executive intelligence methodology

## Evidence and interpretation

`executive.py` transforms existing analytical outputs and Opportunity Radar reviews into deterministic management recommendations. It adds no procurement detector, financial formula, learned model or LLM. Observations, business interpretation, recommended actions and evidence required remain separate fields. Full primary and contextual source references accompany each recommendation in the exported evidence JSON. Published exposure is never a benefit estimate.

`DashboardService.executive` reads overview, categories, suppliers, concentration, calendar, source metadata and opportunity results under one read-only repeatable-read snapshot. It reuses the existing bounded aggregate and detector caches. Every interaction checks the expected source fingerprint, including cache hits. A version mismatch raises `SourceChanged`; the interface requests a refresh. No database tables or mutations are added.

## Selection policy: theme_diversity_v1

The pool is the existing exported opportunities for the current global filters and opportunity configuration. Candidates deferred by the existing per-type output caps remain outside this pool. Those caps and original scores are unchanged.

1. Order candidates by descending **existing unrounded priority score**, then descending positive exposure as a materiality tie-break, then opportunity ID.
2. Visit the available themes in the order of their highest-ranked candidate. Select one candidate per theme, up to four recommendations. Fewer than three is valid when insufficient themes qualify; never manufacture recommendations.
3. Within each theme, prefer the first candidate whose primary source rows do not overlap at least 80% of the smaller row set of any already selected candidate. This is a documented redundancy guard, not a new priority score or calibrated economic threshold. If all candidates overlap, retain the highest-ranked one.
4. Present selected recommendations in original score/materiality/ID order. Disclose every nonempty pairwise primary-row intersection, even below the redundancy threshold. Shared-row counts measure overlap, not duplicate payment or overlapping monetary loss. Never sum exposures.

Source identity for overlap is `(SHA-256, source_record_number)`, not a database sequence ID. Recommendation references hash the policy version and underlying opportunity ID. Repeated runs on the same source/configuration/filter basis are deterministic. Selection is a management shortlist, not a re-ranking or modification of the original Radar.

Each theme has specific actions and required evidence: dependency/continuity and alternatives; specifications and purchasing coordination; invoices/milestones/credits; or source/supplier records. High HHI does not prove inefficiency. Multiple suppliers need not provide comparable services. Payment patterns do not imply fraud or overpayment. Quality candidates do not justify deletion or identity merging without external evidence.

## Findings and financial illustrations

Findings use actual leading supplier and category amounts, supplier shares, the SQL Pareto crossing count and HHI/top-three share. Shares explicitly identify full-positive versus resolved-positive denominators. Empty populations show no invented findings.

The Executive Brief never inserts illustrative assumptions automatically. The user must first define a scenario in Financial Scenario Lab, then explicitly select it for inclusion. All three cases and their assumptions/results are shown. Changing scenario inputs, source version or filters resets that selection because the control is keyed by the complete candidate/basis.

A scenario must pass the existing JSON/arithmetic validation and fresh database-baseline comparison. Its fingerprint and effective reporting period must match the brief. Expense area, entity and supplier filters must match exactly. A category-specific brief requires the same category; an all-category brief may explicitly illustrate one category subset, with its separate baseline displayed. Manual pools cannot establish this correspondence and are excluded from executive exports. Other saved scenarios remain usable in the Lab.

Stale or incompatible scenarios are blocked from the brief and export. The existing Lab workflow performs explicit source review; the Executive Brief does not silently refresh assumptions or amounts. Without a selected matching scenario, Slide 4 explains the model framework and contains no hypothetical results.

## Presentation generation and evidence

`executive_presentation.py` uses python-pptx, as requested for a lightweight reusable Python generator. Text, tables and charts are editable native PowerPoint objects. The five-slide order is fixed. Decimal values come from the existing engines; floats are used only as chart coordinates. Chart axis identifiers are normalized to the unsigned range required by OOXML for renderer compatibility.

```sh
procureiq executive export
procureiq executive export --scenario deliverables/procureiq_scenarios.json --output deliverables/custom_review.pptx
```

The default command reads the complete current active population and explicitly loads the Milestone 6 illustrative assumptions on the current PROJECT Mandays Supp category. It does not hardcode financial outputs. Run the frozen-source gate to establish that active versions still match the approved baseline. The optional JSON follows the same compatibility checks.

The CLI writes the PPTX plus a same-stem `.evidence.json` containing the reporting snapshot, filters, complete source metadata, recommendation measurements/references, conventions and recomputed scenario. The application generates a contextual five-slide download from current filters and selected scenario. A final version check precedes exposing the download. An already downloaded file remains a dated source snapshot, not a live document.

Full source fingerprint, filter basis and official attribution appear in slide notes; every slide shows the reporting period and abbreviated source fingerprint. The deck has no summed opportunity exposure or portfolio savings claim. Detailed evidence stays in the evidence JSON/Radar rather than thousands of rows on slides.

## Limits

Selection is deterministic analyst policy, not proof that the shortlist maximizes commercial value. Four themes may cover overlapping categories. Labels can be long, and arbitrary future source text may require presentation layout review. The recorded default deck and tested contextual cases were inspected; this is not exhaustive typography testing for every possible dataset. The local renderer is a separate render tool, not Microsoft PowerPoint. Native charts retain their embedded editable data. No AI, publication, deployment or collaborative UI redesign is included.


## Interactive briefing and preview integrity

The React builder selects content before preview/export. The browser preview extracts actual generated PPTX text, positions, tables and chart values; it is not pixel-exact Office rendering. Case context is restricted to the selected NORMAL/DEMO namespace. A deterministic preview content hash is rechecked for downloads, preventing silently changed findings from being exported under an old preview. Optional exclusion changes report inclusion, not analytical calculations. See [reporting guide](reporting_guide.md).
