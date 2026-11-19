"""One read-only snapshot, reusing the filtered analytical SQL access layer."""
from collections import defaultdict
from sqlalchemy import text
from .queries import query, source_lines, validate_filters, ARGS
from .analytics import snapshot_metadata
from .supplier_identity import punctuation_candidates


def retrieve(conn, filters=None):
    filters = validate_filters(filters)
    lines = source_lines(conn, filters)
    refs = {r['raw_row_id']: dict(r) for r in conn.execute(text(f'''
        SELECT a.raw_row_id,a.file_id,a.source_record_number,r.physical_line_start,r.physical_line_end,
               f.filename,f.sha256,a.reporting_month,a.transaction_number
        FROM procureiq.analytics_lines({ARGS}) a
        JOIN procureiq.raw_spend_row r USING(raw_row_id)
        JOIN procureiq.source_file f ON f.file_id=a.file_id
        ORDER BY f.reporting_month,f.sha256,a.source_record_number'''), filters).mappings()}
    # Retrieve issues separately: never multiply monetary source rows through an issue join.
    issues = [dict(r) for r in conn.execute(text(f'''
        SELECT q.issue_id,q.raw_row_id,q.file_id,q.issue_code,q.field,q.details
        FROM procureiq.data_quality_issue q
        WHERE q.resolved_at IS NULL AND (
          q.raw_row_id IN (SELECT raw_row_id FROM procureiq.analytics_lines({ARGS})) OR
          q.file_id IN (SELECT DISTINCT file_id FROM procureiq.analytics_lines({ARGS})))
        ORDER BY q.issue_id'''), filters).mappings()]
    by_category = defaultdict(list)
    for row in lines:
        by_category[row['expense_type']].append(row)
    return dict(filters=filters, lines=lines, by_category=dict(by_category), references=refs,
                categories=query(conn,'category_concentration',filters),
                category_suppliers=query(conn,'category_suppliers',filters),
                calendar=query(conn,'monthly',filters), issues=issues,
                alias_candidates=punctuation_candidates([r['supplier_raw'] for r in lines if r['supplier_raw'] is not None]),
                basis=snapshot_metadata(conn, filters))
