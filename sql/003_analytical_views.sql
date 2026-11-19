-- Milestone 3: shared SQL functions keep views and filtered queries on identical formulas.

CREATE FUNCTION analytics_lines(p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS SETOF active_spend_line
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
SELECT a.* FROM active_spend_line a
WHERE (p_start IS NULL OR a.reporting_month>=p_start)
 AND (p_end IS NULL OR a.reporting_month<=p_end)
 AND (p_type IS NULL OR a.expense_type=p_type)
 AND (p_area IS NULL OR a.expense_area=p_area)
 AND (p_entity IS NULL OR a.entity=p_entity)
 AND (p_supplier IS NULL OR a.supplier_id=p_supplier)
$$;

CREATE FUNCTION analytics_groups(p_group TEXT DEFAULT 'overall', p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS TABLE(
 group_value TEXT, record_count BIGINT, supplier_count BIGINT, positive_supplier_count BIGINT,
 expense_area_count BIGINT, positive_gbp NUMERIC, credit_gbp NUMERIC, net_gbp NUMERIC,
 resolved_positive_gbp NUMERIC, unresolved_positive_gbp NUMERIC, unresolved_credit_gbp NUMERIC,
 unresolved_net_gbp NUMERIC, mapping_coverage_pct NUMERIC, unresolved_rows BIGINT, unparsed_amounts BIGINT,
 invalid_rows BIGINT, materiality_pct NUMERIC)
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
WITH eligible AS (SELECT * FROM analytics_lines(p_start,p_end,p_type,p_area,p_entity,p_supplier)),
grouped AS (
 SELECT CASE p_group WHEN 'overall' THEN 'All' WHEN 'expense_type' THEN expense_type
   WHEN 'expense_area' THEN expense_area WHEN 'entity' THEN entity
   WHEN 'reporting_month' THEN reporting_month::text END AS label,
 count(*) AS n, count(DISTINCT supplier_id) AS suppliers,
 count(DISTINCT supplier_id) FILTER(WHERE amount_gbp>0) AS positive_suppliers,
 count(DISTINCT expense_area) AS areas,
 coalesce(sum(amount_gbp) FILTER(WHERE amount_gbp>0),0) AS pos,
 coalesce(-sum(amount_gbp) FILTER(WHERE amount_gbp<0),0) AS credit,
 coalesce(sum(amount_gbp),0) AS net,
 coalesce(sum(amount_gbp) FILTER(WHERE supplier_id IS NOT NULL AND amount_gbp>0),0) AS resolved,
 coalesce(sum(amount_gbp) FILTER(WHERE supplier_id IS NULL AND amount_gbp>0),0) AS unresolved_pos,
 coalesce(-sum(amount_gbp) FILTER(WHERE supplier_id IS NULL AND amount_gbp<0),0) AS unresolved_credit,
 coalesce(sum(amount_gbp) FILTER(WHERE supplier_id IS NULL),0) AS unresolved_net,
 count(*) FILTER(WHERE supplier_id IS NULL) AS unresolved_rows,
 count(*) FILTER(WHERE amount_gbp IS NULL) AS unparsed,
 count(*) FILTER(WHERE parse_status='invalid') AS invalid
 FROM eligible GROUP BY label
)
SELECT label,n,suppliers,positive_suppliers,areas,pos,credit,net,resolved,unresolved_pos,unresolved_credit,
 unresolved_net,100*resolved/NULLIF(pos,0),unresolved_rows,unparsed,invalid,
 100*pos/NULLIF(sum(pos) OVER (),0)
FROM grouped
$$;

CREATE FUNCTION analytics_suppliers(p_by_category BOOLEAN DEFAULT FALSE, p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS TABLE(
 group_value TEXT, supplier_id BIGINT, canonical_name TEXT, supplier_rank BIGINT,
 record_count BIGINT, positive_gbp NUMERIC, credit_gbp NUMERIC, net_gbp NUMERIC,
 active_months BIGINT, category_count BIGINT, expense_area_count BIGINT,
 share_all_positive_pct NUMERIC, share_resolved_positive_pct NUMERIC,
 cumulative_positive_gbp NUMERIC, cumulative_resolved_pct NUMERIC,
 resolved_positive_gbp NUMERIC, all_positive_gbp NUMERIC, positive_supplier_count BIGINT)
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
WITH eligible AS (SELECT * FROM analytics_lines(p_start,p_end,p_type,p_area,p_entity,p_supplier)),
pool AS (
 SELECT CASE WHEN p_by_category THEN expense_type ELSE 'All' END AS label,
 coalesce(sum(amount_gbp) FILTER(WHERE amount_gbp>0),0) AS all_pos FROM eligible GROUP BY label
), suppliers AS (
 SELECT CASE WHEN p_by_category THEN e.expense_type ELSE 'All' END AS label,e.supplier_id,
 s.canonical_name, s.normalized_key,count(*) AS n,
 coalesce(sum(e.amount_gbp) FILTER(WHERE e.amount_gbp>0),0) AS pos,
 coalesce(-sum(e.amount_gbp) FILTER(WHERE e.amount_gbp<0),0) AS credit,
 coalesce(sum(e.amount_gbp),0) AS net,
 count(DISTINCT e.reporting_month) AS months,count(DISTINCT e.expense_type) AS categories,
 count(DISTINCT e.expense_area) AS areas
 FROM eligible e JOIN supplier s ON s.supplier_id=e.supplier_id
 GROUP BY label,e.supplier_id,s.canonical_name,s.normalized_key
), ranked AS (
 SELECT s.*,row_number() OVER w AS position,
 sum(pos) OVER (PARTITION BY label) AS resolved,
 sum(pos) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative,
 count(*) FILTER(WHERE pos>0) OVER (PARTITION BY label) AS positive_suppliers
 FROM suppliers s
 WINDOW w AS (PARTITION BY label ORDER BY pos DESC,normalized_key COLLATE "C",supplier_id)
)
SELECT r.label,r.supplier_id,r.canonical_name,r.position,r.n,r.pos,r.credit,r.net,r.months,r.categories,r.areas,
 100*r.pos/NULLIF(p.all_pos,0),100*r.pos/NULLIF(r.resolved,0),r.cumulative,
 100*r.cumulative/NULLIF(r.resolved,0),r.resolved,p.all_pos,r.positive_suppliers
FROM ranked r JOIN pool p ON r.label IS NOT DISTINCT FROM p.label
$$;

CREATE FUNCTION analytics_concentration(p_by_category BOOLEAN DEFAULT FALSE, p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS TABLE(
 group_value TEXT, record_count BIGINT, supplier_count BIGINT, positive_supplier_count BIGINT,
 expense_area_count BIGINT, positive_gbp NUMERIC, credit_gbp NUMERIC, net_gbp NUMERIC,
 resolved_positive_gbp NUMERIC, unresolved_positive_gbp NUMERIC, mapping_coverage_pct NUMERIC,
 materiality_pct NUMERIC, hhi NUMERIC, top_one_pct NUMERIC, top_three_pct NUMERIC,
 suppliers_to_80 BIGINT, suppliers_to_80_pct NUMERIC, unparsed_amounts BIGINT)
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
WITH ranked AS (SELECT * FROM analytics_suppliers(p_by_category,p_start,p_end,p_type,p_area,p_entity,p_supplier)),
concentration AS (
 SELECT r.group_value,
 10000*sum(r.positive_gbp*r.positive_gbp)/NULLIF(max(r.resolved_positive_gbp)*max(r.resolved_positive_gbp),0) AS hhi,
 100*max(r.positive_gbp)/NULLIF(max(r.resolved_positive_gbp),0) AS top_one,
 100*sum(CASE WHEN r.supplier_rank<=3 THEN r.positive_gbp ELSE 0 END)/NULLIF(max(r.resolved_positive_gbp),0) AS top_three,
 min(r.supplier_rank) FILTER(WHERE r.positive_gbp>0 AND r.cumulative_positive_gbp*5>=r.resolved_positive_gbp*4) AS to_80
 FROM ranked r GROUP BY r.group_value
)
SELECT g.group_value,g.record_count,g.supplier_count,g.positive_supplier_count,g.expense_area_count,
 g.positive_gbp,g.credit_gbp,g.net_gbp,g.resolved_positive_gbp,g.unresolved_positive_gbp,g.mapping_coverage_pct,
 g.materiality_pct,c.hhi,c.top_one,c.top_three,c.to_80,
 100*c.to_80::numeric/NULLIF(g.positive_supplier_count,0),g.unparsed_amounts
FROM analytics_groups(CASE WHEN p_by_category THEN 'expense_type' ELSE 'overall' END,p_start,p_end,p_type,p_area,p_entity,p_supplier) g
LEFT JOIN concentration c ON c.group_value IS NOT DISTINCT FROM g.group_value
$$;

CREATE FUNCTION analytics_monthly(p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS TABLE(
 reporting_month DATE, source_available BOOLEAN, record_count BIGINT, supplier_count BIGINT,
 positive_gbp NUMERIC, credit_gbp NUMERIC, net_gbp NUMERIC, unparsed_amounts BIGINT,
 previous_positive_gbp NUMERIC, mom_positive_pct NUMERIC)
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
WITH bounds AS (
 SELECT coalesce(p_start,min(f.reporting_month)) AS first_month,coalesce(p_end,max(f.reporting_month)) AS last_month
 FROM source_file f WHERE f.active AND f.import_status='loaded'
), calendar AS (
 SELECT d::date AS month FROM bounds b,
 LATERAL generate_series(b.first_month::timestamp,b.last_month::timestamp,interval '1 month') d
), monthly AS (
 SELECT c.month,f.file_id IS NOT NULL AS available,coalesce(g.record_count,0) AS n,
 coalesce(g.supplier_count,0) AS suppliers,
 CASE WHEN f.file_id IS NOT NULL THEN coalesce(g.positive_gbp,0) END AS pos,
 CASE WHEN f.file_id IS NOT NULL THEN coalesce(g.credit_gbp,0) END AS credit,
 CASE WHEN f.file_id IS NOT NULL THEN coalesce(g.net_gbp,0) END AS net,
 coalesce(g.unparsed_amounts,0) AS unparsed
 FROM calendar c LEFT JOIN source_file f ON f.reporting_month=c.month AND f.active AND f.import_status='loaded'
 LEFT JOIN analytics_groups('reporting_month',p_start,p_end,p_type,p_area,p_entity,p_supplier) g ON g.group_value=c.month::text
), previous AS (
 SELECT m.*,lag(m.pos) OVER(ORDER BY m.month) AS prev FROM monthly m
)
SELECT month,available,n,suppliers,pos,credit,net,unparsed,prev,100*(pos-prev)/NULLIF(prev,0) FROM previous
$$;

CREATE FUNCTION analytics_supplier_monthly(p_start DATE DEFAULT NULL, p_end DATE DEFAULT NULL, p_type TEXT DEFAULT NULL, p_area TEXT DEFAULT NULL, p_entity TEXT DEFAULT NULL, p_supplier BIGINT DEFAULT NULL)
RETURNS TABLE(
 supplier_id BIGINT, canonical_name TEXT, reporting_month DATE, source_available BOOLEAN,
 record_count BIGINT, positive_gbp NUMERIC, credit_gbp NUMERIC, net_gbp NUMERIC,
 previous_positive_gbp NUMERIC, mom_positive_pct NUMERIC)
LANGUAGE SQL STABLE SET search_path TO procureiq, public AS $$
SELECT s.supplier_id,s.canonical_name,m.reporting_month,m.source_available,m.record_count,
 m.positive_gbp,m.credit_gbp,m.net_gbp,m.previous_positive_gbp,m.mom_positive_pct
FROM analytics_suppliers(FALSE,p_start,p_end,p_type,p_area,p_entity,p_supplier) s
CROSS JOIN LATERAL analytics_monthly(p_start,p_end,p_type,p_area,p_entity,s.supplier_id) m
$$;

CREATE VIEW vw_expenditure_overview AS SELECT * FROM analytics_groups('overall');

CREATE VIEW vw_expense_type_spend AS SELECT * FROM analytics_groups('expense_type');

CREATE VIEW vw_expense_area_spend AS SELECT * FROM analytics_groups('expense_area');

CREATE VIEW vw_entity_spend AS SELECT * FROM analytics_groups('entity');

CREATE VIEW vw_monthly_disclosed_spend AS SELECT * FROM analytics_monthly();

CREATE VIEW vw_supplier_ranking AS SELECT * FROM analytics_suppliers(FALSE);

CREATE VIEW vw_category_supplier_spend AS SELECT * FROM analytics_suppliers(TRUE);

CREATE VIEW vw_supplier_concentration AS SELECT * FROM analytics_concentration(FALSE);

CREATE VIEW vw_category_concentration AS SELECT * FROM analytics_concentration(TRUE);

CREATE VIEW vw_supplier_monthly_trends AS SELECT * FROM analytics_supplier_monthly();
