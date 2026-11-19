> The complete React product extends this historical documentation. See [product architecture](product_architecture.md), [user/development guide](product_user_guide.md), [API extensions](product_api.md) and [verification](product_verification.md). Existing calculations and source policies remain authoritative.

# React investigation workspace — local development

The React application is in `apps/web/`. It consumes the existing FastAPI investigation API and runs independently of the Streamlit dashboard. Procurement calculations, case deduplication and historical evidence resolution remain on the backend. Stage 2 offers Review Queue, Saved Cases and case Overview, Evidence and Activity. Status is read-only; there are no findings, notes, bookmarks or closure/reopening forms.

## Install and run

The verified workstation uses Node 24.11.0 and npm 11.6.1. Install the locked frontend dependencies:

```sh
cd apps/web
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Vite binds to loopback and refuses to silently choose another port. In a separate terminal, from the repository root, with the existing PostgreSQL cluster running:

```sh
source .venv/bin/activate
set -a
source .env
set +a
uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

On a new installation, run `procureiq app-db init` after following the existing database setup guide. No migrations are added by Stage 2. Interactive API documentation remains <http://127.0.0.1:8000/docs>.

The existing dashboard remains independently runnable:

```sh
streamlit run src/procureiq/ui/app.py --server.port 8501
```

The browser defaults to API origin `http://127.0.0.1:8000`. To change it, copy `apps/web/.env.example` to `apps/web/.env.local`, set `VITE_API_BASE_URL`, and restart Vite. Only public browser configuration belongs in Vite variables. Never copy the root database `.env` into the frontend. Both services must remain local; CORS and a basis token do not provide authentication.

## Structure

| Path under `apps/web/` | Responsibility |
|---|---|
| `src/App.tsx` | Focused shell, responsive navigation and React Router routes |
| `src/pages/ReviewQueue.tsx` | Exact filters, bounded search, list and contextual detail |
| `src/pages/Cases.tsx` | Paginated persisted-case list and status filter |
| `src/pages/CaseWorkspace.tsx` | Case header, frozen overview and context |
| `src/pages/CaseEvidence.tsx` | Primary/contextual pages and source-lineage dialog |
| `src/pages/CaseActivity.tsx` | Chronological backend event timeline |
| `src/components/` | Shared states, native modal, review details and creation form |
| `src/api/types.ts`, `client.ts` | Typed contracts, abortable requests and sanitized errors |
| `src/hooks/queries.ts` | Parameter-specific, abortable API query hooks |
| `src/hooks/queue.ts` | Validated URL state; reporting versus display-only filters |
| `src/format.ts` | Decimal-string money formatting and display-only score/date formatting |
| `src/test/` | Vitest/Testing Library tests and small actual API response fixtures |
| `src/styles.css` | Plain responsive CSS with visible focus and controlled table scrolling |

React, strict TypeScript, Vite, React Router and TanStack Query provide the application foundation. Lucide supplies a few navigation icons; there is no component framework. `package-lock.json` pins the installed dependency graph. Prettier is development-only.

## Routes and controls

- `/` redirects to `/investigations/reviews`.
- `/investigations/reviews` supports reporting month bounds, exact expense type/area/entity, normalized supplier **ID**, detector type and minimum priority. The API has no supplier-name lookup endpoint; a supplier ID is available in supporting measurements when present. Text inputs preserve exact whitespace. All filters are single value.
- `q` searches only the currently loaded page (at most 50 exported reviews). This limit is stated beside the search control. Pagination remains available when a policy exports more than 50 matches.
- `review` selects a contextual detail panel; `offset` selects the list page. Reporting and display filters are separate. Detail and creation use only canonical reporting filters, not search/detector/minimum-priority display controls.
- `/investigations/cases` supports `status` and `offset`, with 50 cases per request.
- `/investigations/cases/:caseId` supports `tab=overview|evidence|activity`, including direct loads and refreshes. Evidence classification starts at primary and resets to page one when changed. Activity preserves API order and has independent 50-event pagination.

Reset Filters clears all queue state. The last queue URL is retained in session storage so a case-page reload does not lose queue navigation context. Restored values are validated. Storage contains no evidence, case payloads, credentials or basis tokens. Without storage, ordinary in-app navigation still retains the URL in memory.

## Consistency and error behavior

All queries receive AbortSignals and use parameter-specific cache keys, so an older request cannot overwrite a newer selection. Query data is immediately stale and refreshed on remount; automatic focus refetch is disabled. Inactive query entries expire after 60 seconds. Health is fresh for 30 seconds. Evidence is loaded only for the selected 50-row page, not prefetched in bulk or written to browser storage. Source checks occur on backend requests, not continuously.

Creating a case sends only the selected review ID, current canonical filters, basis token, title and objective. The server supplies scores and frozen references. A `created:false` response is announced as an existing investigation and navigates without editing it. Stale-basis/concurrent-source conflicts dismiss the form, refresh the queue/detail, and require an explicit new review and submission. There is no automatic POST retry. Creation invalidates case and review queries.

Historical cases retain original measurements and source identities. A source mismatch is labeled **Historical Evidence Basis**. Missing/corrupt evidence produces an actionable integrity error, never a successful empty table or substituted current data. Read failures offer Retry. Browser errors use allowlisted explanations, never raw exception contents. There is no fallback mock data.

Money stays in its exact API string form. Formatting inserts separators without binary floating-point conversion; exact pence remain visible. Original source amounts and transaction references remain original strings. Nonmonetary scores and measurements are rounded only for display; original values are available in their title attribute. No financial value or score is recalculated or submitted from a formatted label. Dates use the browser's local time zone and consistent en-GB formatting.

## Checks

```sh
cd apps/web
npm run typecheck
npm run lint
npm test
npm run build
```

`npm run format` formats frontend source. `npm run build` produces ignored `apps/web/dist`; it does not publish or deploy anything. Tests derive their contracts from the real Stage 1 responses, with explicit synthetic variations for errors, closed/historical cases and empty results. They never write to the main database. Real-browser acceptance and the one intentionally persisted demo case are documented separately.

See [Stage 2 verification](investigation_stage2_verification.md) for exact results, screenshot links, actual browser checks and limitations. The existing Python test and source-reconciliation commands remain unchanged.
