# Investigation Backend Foundation — Stage 1 verification

Executed locally on **16 October 2026** (Asia/Kolkata), using Python 3.14.7, PostgreSQL 17.11, FastAPI 0.143.2, Pydantic 2.14.1 and Uvicorn 0.54.0. This stage adds persistent investigation workflows and FastAPI alongside the existing Streamlit application. No React frontend, investigation UI, notes/bookmarks workflow, authentication, AI, deployment or publication was implemented.

## Implemented and inspected

The backend reuses the existing `retrieve`/`detect` opportunity path, exact analytical filters and immutable source-reference structure. A minimal shared `source_basis.py` extraction preserves existing dashboard imports and fingerprint behavior. API imports were checked in a fresh Python process and did not import Streamlit.

The separate `procureiq_app` schema contains cases, frozen evidence references, append-only events and its own checksum migration ledger. Database uniqueness implements one case per exact review basis. Creation resolves all scores/metrics/evidence server-side, rejects stale context tokens and commits case/evidence/event atomically. Source-table locks prevent activation interleaving. Lifecycle changes use expected row versions and transactional events. Original case snapshots and evidence are immutable through ordinary application operations.

Modules and consistency rules are documented in [investigation architecture](investigation_architecture.md); routes, examples, validation and launch commands are in [API documentation](investigation_api.md).

## Automated acceptance

- Full Pytest suite: **130 passed in 62.63s**, with no skips or failures.
- Focused backend suite: **14 passed in 10.78s** after adding an explicit barrier to exercise simultaneous conflicting inserts; all 14 also passed in the final full run.
- `procureiq db verify`: passed frozen-source hashes, row contents and exact monthly financial reconciliation.
- `procureiq analytics verify`: passed independent Decimal/SQL analytical checks.
- `procureiq opportunities verify`: passed all 34 selected review checks across 12,973 rows.
- `procureiq app-db init`: applied the single application migration; an immediate rerun verified its checksum without changing analytical migrations.
- `python -m compileall -q src/procureiq`: passed.
- `python -m pip check`: no broken requirements.

The suite retains the previous 116 tests and adds 14 investigation tests. Integration tests verify the separate `_test` database name before resetting either test schema; they never reset the main database. New coverage includes:

- Fresh application installation, reruns/checksum rejection, database uniqueness and immutability protections.
- Server-resolved review creation, unknown/deferred/stale/forged requests, changed policy/scope and duplicate retrieval without modification.
- Simultaneous inserts synchronized at the database write, producing exactly one case; concurrent status updates with one version conflict.
- Evidence insertion and event failures rolling back the corresponding whole transaction.
- Primary/contextual reference pagination, source lineage, source activation lock exclusion and historical evidence after activation.
- Explicit missing-history errors under deliberately simulated corruption in the guarded test schema; no transaction-reference substitution.
- All 6,497 references of the leading actual review retrieved across bounded pages without missing/duplicate IDs; default HTTP evidence response limited to 50 rows.
- Valid/invalid lifecycle transitions, required closure/reopening explanations, immutable audit history and retrieval of CLOSED cases without reopening.
- FastAPI schemas, exact text filters, decimal serialization, pagination limits, CORS preflight behavior, request-size limits and sanitized database failures.

One dependency warning remains: Starlette deprecates the `httpx` adapter used by FastAPI TestClient in favor of its newer adapter. The executed tests succeed; this is not a runtime API failure. No warning was hidden. Development failures exposed FastAPI query-model composition behavior and a fixture without contextual evidence; both were corrected before acceptance. Exact filter whitespace preservation and creation by echoing canonical first-of-month filters were explicitly tested in the final run.

## Deliberate main-database demonstration

Exactly one clearly labeled application-generated demo case was created through the running HTTP API:

| Field | Actual result |
|---|---|
| Reference / internal ID | **PIQ-000001 / 1** |
| Title | `[LOCAL DEMO] Stage 1 acceptance — PROJECT Mandays Supp` |
| Origin review | Purchasing coordination review: PROJECT Mandays Supp |
| Opportunity ID | `opp_4fcc1847763f23e1eb055ee2` |
| Original priority | `97.9525744600650518067000` |
| Primary / contextual references | **6,497 / 0** |
| Initial creation | **201**, created true |
| Duplicate request | **200**, created false, same case ID/reference |
| Current status / version | **INVESTIGATING / 2** |
| Persisted activity | **2 events**, both actor `local_application` |

The first event is CASE_CREATED (new status OPEN). The second is STATUS_CHANGED from OPEN to INVESTIGATING with the written reason “Local demonstration: verifying the persisted investigation workflow.” The objective explicitly identifies the case as application-generated verification state, with no asserted commercial finding. The demo was not closed or automatically reopened. It remains visible as intentional local application data.

Two successive evidence pages each returned 50 source records with no overlapping raw-row IDs. The review list subsequently exposed the existing-case indicator. Review detail, filtered review list, case retrieval, activity, evidence, health, duplicate POST and status PATCH were exercised against the actual loopback server. [Demonstration receipt](../reports/investigation_stage1_demo.json) records the actual responses and audit events without credentials.

## Preserved analytical and source state

Before application migration/creation, a read-only repeatable-read snapshot recorded the source fingerprint, analytical totals, canonical hashes of all raw source rows, supplier mappings and complete opportunity output. A second snapshot after the demo matched **exactly** on every field. Application migrations, case creation and status changes did not change the analytical fingerprint:

`5886525e03a6b21493a7bd70ba3c8ec510ea8f8e01a753cc66850a0406192061`

| Regression target | Actual verified value |
|---|---:|
| Official monthly source files | 12 |
| Published lines | 12,973 |
| Normalized supplier keys | 456 |
| Positive disclosed payments | £2,499,145,830.48 |
| Credit magnitude | £30,802,967.80 |
| Net disclosed payments | £2,468,342,862.68 |
| Qualified / exported / deferred reviews | 112 / 34 / 78 |

Existing source verification ran after demonstration changes. No original expenditure rows, supplier mappings, active versions, analytical migration checksums or opportunity scores were modified. Main-database writes were confined to the separately authorized application schema.

## Historical integrity verification

A guarded integration test created a case, activated a different original source version, and verified that saved score and source fields stayed unchanged while `basis_matches_current_source` became false. Historical pages resolved stored raw-row/file IDs, SHA-256 and record positions without using active views. A new current review could create a separate case under a different basis. A stale creation token failed.

Another test deliberately removed the test evidence foreign key/disabled the test evidence trigger and pointed a reference at a nonexistent raw row, simulating external destructive administration. Retrieval raised `evidence_integrity` rather than substituting a record. This deliberate corruption occurred only inside the guarded test schema, which later fixtures reset. Main historical data was not altered. Normal foreign keys and immutable triggers prevent such changes through ordinary application operations.

## Actual running application and browser checks

The API served at <http://127.0.0.1:8000>. `/docs` and `/openapi.json` returned successfully. An actual Chromium browser loaded interactive Swagger UI and executed **Try it out → health**, receiving `status: ok`, with no JavaScript page errors. [OpenAPI screenshot](screenshots/investigation_stage1_openapi.png).

The existing Streamlit app on port 8501 also passed an actual desktop/mobile walkthrough after application-schema creation: all five pages, supplier filtering, filter reset, Radar evidence navigation, Financial Scenario Lab inputs, Executive Brief explicit scenario inclusion and PowerPoint download, and an empty population. The familiar Base example still showed £1,292,916.76 net hypothetical benefit under its explicit illustrative assumptions; no new financial calculation was introduced. Mobile document width remained 390 pixels, with no JavaScript page errors.

Browser automation used the existing temporary Playwright/Chromium environment. It was not added as an application dependency. Screenshots are viewport evidence, not a claim to inspect every off-screen pixel. Tests and artifacts remain local.

## Exact local launch

With the native PostgreSQL cluster already running, from the repository root:

```sh
source .venv/bin/activate
set -a
source .env
set +a
procureiq app-db init
uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Interactive documentation: <http://127.0.0.1:8000/docs>. The existing dashboard command remains `streamlit run src/procureiq/ui/app.py --server.port 8501`.

## Limits and local status

No known blocking functional defect remains. The API is unauthenticated and must stay on loopback; CORS is restricted to the planned local development origins and is not authentication. Historical correctness depends on retaining immutable original source versions. Integrity checking is page-scoped and database-owner tampering cannot be fully prevented. Unsupported future manual supplier/typed-data changes need their own revision discipline. Review recomputation is synchronous; no high-concurrency or remote-hosting performance claim is made. Fresh-machine deployment and production roles were not tested or implemented.

Temporary acceptance scripts/logs stay in ignored `.local/`; the one labeled demo case is retained intentionally.
