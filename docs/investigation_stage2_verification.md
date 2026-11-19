# React Investigation Workspace — Stage 2 verification

Executed locally on **16 October 2026**. The separate frontend uses Node 24.11.0, npm 11.6.1, React 19.3.1, TypeScript 5.9.3, Vite 8.3.4, React Router 7.18.4 and TanStack Query 5.104.3. The existing FastAPI/PostgreSQL backend and Streamlit application were retained unchanged. No analytical calculation, API route, database migration, supplier mapping or opportunity policy was modified.

## Implemented

`apps/web` contains the focused Investigations shell, Review Queue with exact reporting/display filters and bounded search, contextual review preview, validated creation dialog, Saved Cases and direct case routes. Cases expose Overview, paginated frozen Evidence with source-record detail, and chronological Activity. Status is read-only, including closed cases. No findings, notes, bookmarks or future-workspace placeholders were added.

The client was implemented after reading the running `/openapi.json`, API modules and actual review/case/evidence/activity responses. Data is backend-derived. React components, shared UI, typed API models/client, data-fetching hooks, URL-state validation and formatting are separate modules. Native dialogs provide keyboard focus containment; controls have visible focus and accessible names. Money remains an exact string and is never converted to a float for financial arithmetic or writes.

See [frontend guide](investigation_frontend.md) and [architecture](investigation_architecture.md) for source layout, local configuration, routes, state and consistency behavior.

## Executed automated checks

| Check | Result |
|---|---|
| `npm run typecheck` | Passed strict TypeScript checking |
| `npm run lint` | Passed, no lint errors or warnings |
| `npm test` | **21 passed**, final run 1.64 seconds |
| `npm run build` | Passed; local production assets generated, not deployed |
| `npm audit --json` | Zero reported vulnerabilities in the final installed dependency graph |
| `python -m pytest -q` | **130 passed in 65.51 seconds**, no skips or failures |
| `procureiq db verify` | Passed frozen source/row/monthly reconciliation |
| `procureiq analytics verify` | Passed independent analytical checks |
| `procureiq opportunities verify` | Passed all 34 selected review checks |
| `python -m pip check` | No broken requirements |

Frontend tests cover routing, list/detail rendering, exact filters and reset, explicitly page-scoped search, validation, server-basis creation payloads, successful and concurrent-existing responses, stale-basis refresh without automatic resubmission, existing/closed-case read-only retrieval, case navigation/status filtering, evidence classification/pagination/source detail, activity ordering, historical/integrity errors, empty populations, offline retry, keyboard activation, invalid URL filters, navigation-state retention, request cancellation/older-response isolation and exact money beyond JavaScript's safe-integer range. Small response fixtures were captured from the actual Stage 1 API; error/closed/historical variations are synthetic test cases, not claimed main-database states.

Python integration tests used only the existing guarded test database. The existing Starlette warning about its deprecated `httpx` TestClient adapter remains visible; all tests pass. The first frontend install reported test-runner dependency advisories; the test runner and compatible Vite tooling were upgraded before final acceptance. ESLint 9 emitted an upstream deprecation notice during installation; it passes locally and has no reported advisory in this audit. Dependency audits are point-in-time checks, not a security guarantee.

## Actual browser acceptance

FastAPI served at <http://127.0.0.1:8000> and Vite at <http://127.0.0.1:5173>. Existing temporary Playwright/Chromium tooling drove a real browser; it was not added as an application dependency. Successful desktop checks used a 1440 × 1040 viewport; mobile used 390 × 844.

The walkthrough:

1. Loaded the actual default 34 exported / 112 qualified / 78 deferred population.
2. Selected the purchasing-coordination review for PROJECT Mandays Supp, inspected its exposure and evidence, and followed its existing-case indicator to `PIQ-000001`.
3. Confirmed its persisted INVESTIGATING status, original objective and source context.
4. Retrieved exactly 50 primary records on page one and 50 on page two, and checked that their raw-row IDs were disjoint. The frontend did not fetch all 6,497 records.
5. Opened a record dialog and matched its complete SHA-256 to the API response. Switched to contextual evidence and saw the actual empty classification.
6. Read the CASE_CREATED and STATUS_CHANGED events in API order, including the existing explanation. Refreshed the direct case route and retained the Activity section.
7. Returned to the queue, exercised search, the real normalized-supplier-ID filter and reset, then created the one labeled Stage 2 case described below.
8. Browsed saved cases and verified the original case remained visible. Deliberately aborted review requests to exercise offline errors, then removed interception and recovered with Retry. No fabricated response data was substituted.
9. Used mobile list/detail navigation, case evidence and the collapsible menu. Document width remained 390 pixels for the queue, case evidence and saved-case views; wide evidence content scrolled inside its container.
10. Recorded **no JavaScript page errors** in successful walkthroughs. A final rerun after extracting the dedicated query hooks reused the new demo case rather than creating another.

Development browser runs found a queue-selection loss after reloading a case page. The fix retains only the validated queue URL in session storage. Evidence and tokens are not stored there. Evidence pagination was moved above a bounded table after visual review. Browser selectors also needed correction for multiple PROJECT Mandays reviews and the objective textbox; failed development runs were not counted as acceptance.

## Deliberate local demonstration state

Exactly one additional case was created through the React form and actual API. The API returned HTTP 201 with `created:true`:

| Field | Result |
|---|---|
| Case reference / ID | **PIQ-000003 / 3** |
| Title | `[LOCAL DEMO] Stage 2 acceptance — Supplier dependency review: Physical Hosting and Infrastructure` |
| Review ID | `opp_0286a5a0a1eb2d09e04fb7a0` |
| Original priority | `88.1661709000` |
| Initial/current status | OPEN, version 1 |
| Frozen references | 268 primary, 0 contextual |

The objective identifies application-generated verification state and explicitly asserts no commercial finding. [Creation receipt](../reports/investigation_stage2_demo.json) records the real response. The script checks for this already-existing demo before attempting another creation. Identity gaps are normal under the existing backend sequence/deduplication design; no case was fabricated to fill a gap.

`PIQ-000001` remains INVESTIGATING, version 2, with its original two events. Stage 2 did not invoke any lifecycle PATCH. No demo was deleted, closed, reopened or relabeled.

## Preserved analytical acceptance and Streamlit regression

Before and after the Stage 2 demo, read-only repeatable-read snapshots matched exactly for the source fingerprint, overview values, canonical hashes of every raw row, supplier/alias mappings and the complete detector output. All three verification gates ran again after case creation.

Source fingerprint:

`5886525e03a6b21493a7bd70ba3c8ec510ea8f8e01a753cc66850a0406192061`

| Measure | Unchanged verified value |
|---|---:|
| Official monthly files | 12 |
| Published lines | 12,973 |
| Normalized supplier keys | 456 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Qualified / exported / deferred reviews | 112 / 34 / 78 |

The actual Streamlit browser regression navigated all five existing pages, opened Radar evidence, bound the original scenario baseline, loaded the illustrative assumptions and confirmed the Base **£1,292,916.76** net hypothetical benefit. Executive Brief required explicit scenario inclusion and successfully downloaded PowerPoint with and without it. Supplier filtering, reset, mismatched-scenario blocking, empty populations and mobile width checks passed with no JavaScript page errors. Streamlit source and historical delivery artifacts were not changed; new temporary regression captures/downloads remain in ignored `.local/`.

## Screenshots

Captured from the real local app and visually inspected for hierarchy, legibility, controls and overflow. These are viewport captures, not a claim to inspect every off-screen pixel.

- [Review Queue](screenshots/investigation_stage2_queue.png)
- [Selected opportunity](screenshots/investigation_stage2_review.png)
- [Create Investigation](screenshots/investigation_stage2_create.png)
- [Case Overview](screenshots/investigation_stage2_case.png)
- [Evidence workspace](screenshots/investigation_stage2_evidence.png)
- [Source record detail](screenshots/investigation_stage2_source.png)
- [Activity timeline](screenshots/investigation_stage2_activity.png)
- [Mobile layout](screenshots/investigation_stage2_mobile.png)
- [Offline read error](screenshots/investigation_stage2_error.png)

Exact repository directory: `/Users/rishithrai/Desktop/ProcureIQ/docs/screenshots/`.

## Launch and limits

From the repository root, with PostgreSQL already running:

```sh
source .venv/bin/activate
set -a
source .env
set +a
uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

In a separate terminal:

```sh
cd /Users/rishithrai/Desktop/ProcureIQ/apps/web
npm ci
npm run dev
```

The API remains unauthenticated and both servers must stay on loopback. Text search covers the loaded review page, explicitly labeled; supplier filtering takes the existing normalized supplier ID because Stage 1 has no supplier-name lookup endpoint. Saved-case summaries do not include exposure, so the exact original exposure is shown in the case detail snapshot rather than inferred in the list. Source checks occur on API interactions, not continuously. Wide evidence tables use controlled scrolling. Browser checks used Chromium; Safari/Firefox, screen-reader certification, high concurrency and deployment were not tested. Historical, closed and stale-conflict UI cases were covered with frontend fixtures and existing backend integration tests, without changing main-database source versions or lifecycle state.

Stage 2 scope excludes notes/findings/bookmarks, closure/reopening forms, authentication and other workspaces.
