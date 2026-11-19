CREATE VIEW active_spend_line AS
SELECT s.*, r.file_id, r.source_record_number, f.reporting_month
FROM spend_line s JOIN raw_spend_row r USING(raw_row_id)
JOIN source_file f USING(file_id) WHERE f.active AND f.import_status='loaded';
CREATE VIEW monthly_reconciliation AS
SELECT reporting_month, count(*) AS record_count,
 coalesce(sum(amount_gbp) FILTER(WHERE amount_gbp>0),0)::NUMERIC(30,2) AS positive_payments_gbp,
 coalesce(-sum(amount_gbp) FILTER(WHERE amount_gbp<0),0)::NUMERIC(30,2) AS credit_magnitude_gbp,
 coalesce(sum(amount_gbp),0)::NUMERIC(30,2) AS net_disclosed_gbp,
 count(*) FILTER(WHERE amount_gbp IS NULL) AS unparsed_amounts,
 count(*) FILTER(WHERE parse_status='invalid') AS invalid_rows,
 count(*) FILTER(WHERE amount_gbp<0) AS negative_amounts,
 count(*) FILTER(WHERE amount_gbp=0) AS zero_amounts,
 count(*) FILTER(WHERE amount_gbp>0 AND amount_gbp<25000) AS positive_below_25000
FROM active_spend_line GROUP BY reporting_month;
CREATE VIEW supplier_mapping_coverage AS
SELECT count(*) AS total_rows, count(supplier_id) AS resolved_rows,
 count(*) FILTER(WHERE supplier_id IS NULL) AS unresolved_rows,
 count(DISTINCT supplier_raw) AS original_names,
 count(DISTINCT supplier_id) AS normalized_suppliers
FROM active_spend_line;
CREATE VIEW unresolved_quality_issues AS
SELECT q.*, coalesce(q.file_id,r.file_id) AS source_file_id
FROM data_quality_issue q LEFT JOIN raw_spend_row r USING(raw_row_id)
JOIN source_file f ON f.file_id=coalesce(q.file_id,r.file_id)
WHERE f.active AND q.resolved_at IS NULL;
