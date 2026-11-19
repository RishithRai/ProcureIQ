# Data Operations, pipeline architecture and contracts

The React workspace controls only three operations: frozen-source verification, ingestion of a registered local receipt manifest, and separately confirmed activation of an already-loaded version. It accepts no arbitrary URL, shell command or filesystem path. Main-data verification is read-only.

## Receipt and source contract

A controlled `manifests/<name>.json` contains 1–120 acquisition receipts (maximum 2 MB). Names use letters, digits, underscore or hyphen. Each receipt retains filename, reporting month, official source URL, SHA-256, byte size, acquisition timestamp and verified/downloaded status. Resolved source paths must remain inside `data/raw`. A status string alone is not proof of provenance: acquisition must use the established official-download process. The UI registers existing local receipts; it does not fabricate receipts or download arbitrary addresses.

Registration freezes the manifest hash and receipt JSON. Repeated registration deduplicates by name/hash. Execution rejects changed receipt bytes. Existing parser/preflight checks source hashes, sizes, mandatory schema, strict decoding, physical-line references and all values. Missing required columns and ragged records fail the pipeline contract before writes. Existing typed parsing preserves invalid values as raw evidence with issues and NULL typed values; it never repairs financial amounts by guessing. Dates, missing values, below-threshold lines, duplicate candidates and supplier placeholders retain the prior investigation/ingestion policy.

## Recorded stages

Ingestion records source_validation, parsing_and_contracts, incremental_ingestion, reconciliation_and_quality, activation_readiness and downstream_analytics. Stage records contain real start/end times, measured durations, output summaries and succeeded/failed/interrupted state. Errors identify the failed stage; known receipt, identity and schema failures have safe diagnostic summaries. Database internals and credentials are not returned.

Existing `prepare` and `load_file` do the work. Every source file is transactional; previously committed files survive a later failure. Reruns validate complete existing raw/typed rows, aliases, issues and totals instead of duplicating them. New month/hash pairs create inactive versions. Existing active selections are preserved, and automatic activation is never performed.

Activation is a distinct confirmed operation. The UI submits a selected file ID and reviewed active fingerprint. The backend compares that fingerprint inside the existing ingestion advisory-lock transaction, then validates source bytes/evidence/totals before switching selection. Historical versions remain retained. A normal ingestion never reverses explicit selection. The frozen `db verify` gate intentionally fails if a different version becomes active; downstream analytics can still validate that active population.

## Queue, recovery and limits

The PostgreSQL application schema stores registrations, runs and stages. A bounded local worker holds a session advisory lock; only one worker executes jobs. Queue admission is serialized and capped at eight pending/running operations. A replacement worker that obtains the exclusive lock marks orphaned running work interrupted. Retry creates a new run linked by retry_of, revalidates receipts and verifies prior committed files. Activation retries require a new explicit review instead of reusing an old confirmation.

Inspect run details before retrying. Restore a registered receipt if it was accidentally changed; otherwise register its new verified version. Correct a schema contract or source identity failure through the controlled acquisition process. No failed operation is displayed as successful. Failed stages are not patched in place.

Source lists and quality results are paginated. Quality records retain filenames, hashes and source positions; the original raw fields remain available through transaction/case evidence. Source selection changes refresh API snapshots and invalidate dependent requests through fingerprints. Existing historical cases remain on their original basis. Jobs are local and synchronous within the bounded worker; remote scheduling, distributed execution, production roles and high-concurrency performance are not claimed.

[Measured PostgreSQL study](sql_performance.md) evaluates existing indexes without speculative schema changes.
