# Milestone 1 verification record

Verified on 15 October 2026 using Python 3.14.7 and `requirements-lock.txt`.

- `procureiq download`: downloaded all 12 official monthly files.
- `procureiq download --offline`: verified all 12 against their receipts, retaining their original download timestamps and source bytes.
- `procureiq investigate`: processed 12,973 actual source records and generated all requested reports.
- `python -m pytest -q`: **23 passed in 7.33s**, including the actual-data integration test; no skips.
- `python -m pip check`: no broken requirements found.
- `git check-ignore`: confirmed all 12 raw CSVs, local source-row JSONL, and virtual environment are ignored.
- Git repository initialized on branch `main`; no commit, push or remote created.

The integration test independently reads original CSVs with `csv.DictReader`, converts source monetary strings to integer pence, and reconciles row counts plus positive, credit and net totals for each month against the Pandas/Decimal profiles. It verifies SHA-256 preservation and identical generated report bytes across two investigation executions.

An initial integration-test assumption that all amounts were unadorned decimals failed on actual pound-symbol/thousands-grouped values. The independent check was corrected to handle those observed formats; the production parser already supported them. The final full suite passed.

Financial reconciliation:

- Positive payments: £2,499,145,830.48.
- Credit magnitude: £30,802,967.80.
- Net disclosed payments: £2,468,342,862.68.

No acquisition or execution blockers remain. Approval of the proposed model, alias-review rules and explicit source-version selection remains a Milestone 2 review decision. Disclosed payments are not total HMRC procurement expenditure and these findings do not establish savings.
