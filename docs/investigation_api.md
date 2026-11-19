> The complete React product extends this historical documentation. See [product architecture](product_architecture.md), [user/development guide](product_user_guide.md), [API extensions](product_api.md) and [verification](product_verification.md). Existing calculations and source policies remain authoritative.

# Investigation API — local V1

The backend is unauthenticated and intended for one local analyst. **Do not expose it publicly.** The separate Stage 2 [React frontend](investigation_frontend.md) consumes these contracts. The Streamlit application continues to run separately on port 8501.

## Setup and launch

From the repository root, with PostgreSQL already running:

```sh
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e '.[dev]'
set -a
source .env
set +a
procureiq app-db init
uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Documentation: <http://127.0.0.1:8000/docs>. OpenAPI: <http://127.0.0.1:8000/openapi.json>. `.env` is not implicitly loaded. `PROCUREIQ_OPPORTUNITY_CONFIG` optionally selects the same server-side policy format as Radar; restart the API after changing configuration. No migrations run automatically on API startup. `app-db init` only changes `procureiq_app` and its own migration ledger.

CORS allows `http://127.0.0.1:5173` and `http://localhost:5173`, with GET/POST/PATCH and Content-Type. It is not authentication or protection for a publicly exposed server. POST/PATCH bodies are limited to 16 KiB of actual streamed bytes. Unknown creation/status fields are rejected. Database failures and invalid input responses never echo connection URLs, request contents or tracebacks.

## Routes

| Method and path | Behavior |
|---|---|
| GET `/api/v1/health` | Database/application migration availability |
| GET `/api/v1/investigations/reviews` | Current exported review summaries, context token, counts and existing-case indicators |
| GET `/api/v1/investigations/reviews/{review_id}` | One review with explanation and measurements, without evidence arrays |
| POST `/api/v1/investigations/cases` | Create from a current exported review or return its exact existing case |
| GET `/api/v1/investigations/cases` | Saved case summaries; optional `status` |
| GET `/api/v1/investigations/cases/{case_id}` | Frozen case snapshot, lifecycle fields and current-source match flag |
| GET `/api/v1/investigations/cases/{case_id}/evidence` | One primary/contextual historical evidence page |
| GET `/api/v1/investigations/cases/{case_id}/activity` | Append-only activity in ascending event order |
| PATCH `/api/v1/investigations/cases/{case_id}/status` | Validated transition with optimistic version check |

All list/page endpoints return `items`, `total`, `offset` and `limit`. Default limit is 50, maximum 100; offset is bounded to 0–1,000,000. Review lists use unchanged engine score/ID order, case/activity lists ascending IDs, and evidence ascending saved ordinals. Evidence classification defaults to `primary`; `contextual` is separate. API monetary values and scores serialize as exact decimal strings, not binary floating-point JSON numbers.

## Review context

Review list/detail accept exact filters `start_month` and `end_month` (`YYYY-MM`, or canonical `YYYY-MM-01` dates echoed from a response), `expense_type`, `expense_area`, `entity`, `supplier_id`. Text filters are single-value exact matches with a 300-character bound. Dates must be valid and ordered. The list also accepts `detector_type` (one of the four engine types) and `minimum_priority` (0–100), which narrow the exported display only. They do not alter eligibility, scores or qualified/exported/deferred totals for the reporting population.

```sh
curl 'http://127.0.0.1:8000/api/v1/investigations/reviews?limit=5'
curl 'http://127.0.0.1:8000/api/v1/investigations/reviews?expense_type=PROJECT%20Mandays%20Supp'
```

The response supplies `basis_token`, a `basis` object with source fingerprint, rule/configuration identity and canonical filters, plus `qualified_count`, `exported_count`, `deferred_count` and per-type counts. Each item includes its source counts and optional `existing_case` indicator. Detail uses the same envelope with one item. Neither endpoint returns thousands of evidence references. Full per-row quality flags remain frozen in persistence rather than expanding the detail response.

## Create or open an existing case

Use an actual review ID and token from the preceding response, and the same reporting filters. The following is a schema illustration; placeholders must be replaced with live values:

```json
{
  "review_id": "opp_<24 hexadecimal characters from the response>",
  "basis_token": "<64 hexadecimal characters from the response>",
  "filters": {},
  "title": "Review purchasing coordination for the selected category",
  "objective": "Compare service specifications and purchasing arrangements against source evidence."
}
```

Send to `POST /api/v1/investigations/cases`. The response contains `created` and `case`, including ID/reference, status/version, linked review, source fingerprint, basis key, original metrics/configuration and evidence counts. A new case returns **201**; an identical review basis returns **200** with `created:false`. A duplicate request does not rename, modify or reopen an existing case, even if it is CLOSED. Sequence gaps are normal.

Clients cannot submit exposure, score, type, fingerprint claims, evidence arrays or metrics. The server resolves those values under a locked consistent snapshot and validates the client-observed token. A stale token returns 409; refresh the review list rather than silently retrying with new assumptions. Only exported reviews are eligible; output-cap-deferred reviews cannot create cases.

## Workflow and activity

```json
{
  "status": "INVESTIGATING",
  "expected_version": 1
}
```

PATCH this to the case status endpoint. Use the latest returned `row_version` for subsequent requests. Continue to REVIEWED, then close with:

```json
{
  "status": "CLOSED",
  "expected_version": 3,
  "disposition": "INSUFFICIENT_EVIDENCE",
  "reason": "Contract-level specifications are unavailable, so the procurement hypothesis cannot yet be validated."
}
```

To reopen, request INVESTIGATING with the current version and a meaningful written reason, without a disposition. Reasons/objectives must contain meaningful alphanumeric text; closing/reopening reasons are 10–4000 characters. Unsupported transitions and stale versions fail without recording an event. Successful changes record `local_application` as actor. History preserves earlier closure explanations after reopening.

## Historical evidence

```sh
curl 'http://127.0.0.1:8000/api/v1/investigations/cases/1/evidence?classification=primary&offset=0&limit=50'
curl 'http://127.0.0.1:8000/api/v1/investigations/cases/1/activity?limit=50'
```

IDs above are illustrative, not an instruction to create/reset case 1. Evidence includes original decoded fields, raw/file identities, SHA-256, source-record and physical-line positions, saved ordinal and whether that original file is currently active. The endpoint does not join current active transaction views. Its `basis_matches_current_source` may be false while historical evidence remains fully readable. Missing or corrupted lineage produces an explicit integrity error; transaction numbers are never used as substitute identity.

## Typed errors

Errors use `{"error":{"code":"...","message":"..."}}`:

| HTTP | Codes |
|---|---|
| 404 | `review_not_found`, `case_not_found` |
| 409 | `review_not_eligible`, `stale_review_basis`, `invalid_transition`, `case_version_conflict`, `concurrent_change`, `evidence_integrity` |
| 422 | `invalid_input`, `invalid_pagination`, `invalid_closure`, `reopen_reason_required` |
| 413 | `request_too_large` |
| 503 | `service_unavailable` |
| 500 | `internal_error` (sanitized unexpected failure) |

A transient database lock timeout is surfaced as service unavailable; retry only after refreshing the relevant basis/version. No successful response is sent before the corresponding transaction commits.

## Testing

Set both DATABASE_URL and the guarded separate TEST_DATABASE_URL, then run:

```sh
python -m pytest tests/test_investigations.py -q
python -m pytest -q
procureiq db verify
procureiq analytics verify
procureiq opportunities verify
```

The existing test guard verifies the database name before resetting either schema. The main database is never reset by tests. See [architecture](investigation_architecture.md) for source locks and immutable-history requirements, and [Stage 1 verification](investigation_stage1_verification.md) for actual execution and the deliberately labeled local demonstration case.


## Current namespace and exploration contract

All investigation endpoints default to NORMAL. Set `X-Investigation-Namespace: DEMO` for the demo workspace; the header is allowed by local CORS. Opposite-mode case access returns 409 `namespace_mismatch`. Case responses include `namespace` and detail `work_counts`. Evidence adds `supplier`, `start_month`, `end_month` (YYYY-MM), `minimum_amount`, `maximum_amount`, `transaction` and `search`; responses add `unfiltered_total`, `summary`, parsed `amount_gbp` and `bookmarked`. Ordinal ordering is preserved after filters. Activity accepts `kind=lifecycle|findings|notes|evidence`. Entry bodies optionally accept `sections: {assessment, next_step}`; existing content/revision/citation semantics are unchanged. See [workflow details](product_workflow_refinement.md).
