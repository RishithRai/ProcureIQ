# Milestone 1 methodology

## Acquisition and provenance

The catalogue was inspected on 15 October 2026. The twelve links whose labels match April 2025 through March 2026 are frozen in `manifests/hmrc_sources.json`; the month is not inferred from file contents. Dates in retrieval receipts are actual UTC clock values. The catalogue and publication pages can show different update/publication dates; these are not used as payment dates.

The downloader uses standard-library urllib (no extra HTTP dependency), bounded retries, SHA-256 and byte counts, exclusive source publication, and atomic receipt replacement. It downloads complete bytes before publishing a local file, preserves pre-existing bytes, and records failures separately without destroying the last successful receipt. HTTP error pages are rejected. A real parse is still required to establish CSV validity. The source manifest is trusted checked-in configuration, not arbitrary user-supplied paths. All successful versions are retained by policy; automatic source-version discovery is outside this milestone.

## Parsing and counting

CSV parsing uses Python's CSV reader for exact strings and physical line positions, then constructs a Pandas DataFrame. This avoids numeric identifier coercion, automatic NA conversion, duplicate-header mangling, and implicit row dropping. Each record gets a 1-based data-record ordinal (header excluded) plus inclusive physical start/end lines (header is line 1); multiline quoted records can span lines. Duplicate headers fail explicitly. Ragged rows retain extra fields and generate issues; short rows are padded for analysis while the original length/values remain in the issue evidence and source bytes. Unrecoverable quoting/encoding errors fail explicitly.

Delimiter detection is restricted to comma, semicolon, tab and pipe. Decoding is strict UTF-8/BOM, then Windows-1252; no replacement characters are introduced. This is a deterministic compatibility decision rather than an authoritative encoding declaration. Date patterns are explicitly ordered, day-first for slash dates. Original source strings are never rewritten.

Blank counts mean empty or whitespace-only, separately for each present column. Structurally absent columns remain absent in individual raw records. Literal placeholder values such as `NA`, `N/A` or redactions are not automatically null. Whole-period distinct counts use exact nonblank strings; monthly distinct counts should not be summed.

## Financial and duplicate definitions

Money is parsed using Decimal, validating no more than two fractional digits, optional leading minus/pound symbol, and valid thousands grouping. Unsupported syntax is an issue; no rounding, floating-point money, zero substitution, or exclusion of negative transactions occurs. Missing/invalid amounts make financial totals incomplete. Positive − credit magnitude equals net for every reporting month. An independent actual-data test calculates integer-pence totals directly from the original files.

Repeated identifier groups count exact nonblank identifier strings with frequency greater than one. Member counts include the first occurrence; excess counts exclude it. Monthly and whole-period scopes are explicit. Exact duplicate candidates compare all raw decoded field values; no candidate is removed. Whole-period comparison aligns the union schema with absent optional cells as empty solely for candidate comparison. Transaction identifiers have no assumed uniqueness.

The three threshold metrics are signed amount < 25000, positive 0 < amount < 25000, and absolute magnitude < 25000. They deliberately answer different questions. Date exceptions compare the parsed payment month with the catalogue reporting month. Every row remains in the source-row export regardless of validity.

Supplier case/whitespace and punctuation keys only produce review lists. No mapping or merge is applied. Legal suffix removal and fuzzy matching are deferred until there is evidence and an approved policy.

## Output and verification

CSV outputs are UTF-8, deterministic, and preserve exact money strings. They are analytical artifacts; import transaction identifiers as text when opening in spreadsheet software. `quality_issues.jsonl` has row/file/hash references; `source_rows.jsonl` provides the corresponding original values. Large source-row exports and original raw data are gitignored; compact derived reports and manifests can be versioned.

The actual-data integration test verifies all twelve monthly row counts and positive/credit/net totals independently, checks that source hashes remain unchanged, and compares generated report bytes over a rerun. Unit tests cover quoted multiline CSV, BOM and Windows-1252 decoding, delimiters, ragged records, precision rejection, blanks, credits, repeated identifiers, schema differences, network failure, offline imports, source conflicts and publisher revision detection.

Stop at this milestone: PostgreSQL recommendations in the findings are proposals only. No SQL schema or database ingestion has been implemented.
