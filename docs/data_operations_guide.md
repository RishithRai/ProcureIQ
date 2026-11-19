# Data Operations guide

Use **Overview** for actual execution/source/quality context, **Pipeline Runs** for recorded stage outcomes, **Sources** for immutable versions, and **Data Quality** for filtered issue exploration.

Run read-only verification from the main action. Add source opens the controlled local receipt selector; ingestion reuses original versions and leaves new revisions inactive. Review source identity/quality before explicit activation. Successful runs can consist entirely of already-ingested files. Stage outputs retain exact reconciliation details.

The quality list searches all retained versions, defaults to 50 rows per page, and displays both filtered and all-version totals. Filter by source, issue type, severity, reporting month or literal text. Open an issue to inspect original record fields and lineage. Warnings are investigation candidates, not confirmed accounting errors. The verified 1,761 issues are all reachable; there is no 200-item API cap.

See [workflow](product_workflow_refinement.md) and [verification](product_workflow_verification.md). Pipeline activation safeguards remain covered by guarded database tests; no revised main source was activated during this refinement.
