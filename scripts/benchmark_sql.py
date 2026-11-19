"""Read-only plan comparison; no analytical schema/index mutations."""
import json
from pathlib import Path
from sqlalchemy import text
from procureiq.db import engine_from_env
QUERIES={
 'filtered_spend':"SELECT * FROM procureiq.analytics_groups('overall',NULL,NULL,'PROJECT Mandays Supp',NULL,NULL,NULL)",
 'supplier_ranking':"SELECT * FROM procureiq.analytics_suppliers(FALSE,NULL,NULL,NULL,NULL,NULL,NULL)",
 'transaction_page':"SELECT a.raw_row_id,a.amount_gbp FROM procureiq.analytics_lines(NULL,NULL,NULL,NULL,NULL,31) a ORDER BY a.reporting_month,a.file_id,a.source_record_number LIMIT 50",
}
def main():
 result={}
 engine=engine_from_env()
 for name,sql in QUERIES.items():
  result[name]={}
  for mode in ('default','index_preference'):
   plans=[]
   for _ in range(3):
    with engine.connect() as c,c.begin():
     c.exec_driver_sql('SET TRANSACTION READ ONLY')
     c.exec_driver_sql("SET LOCAL statement_timeout='30s'")
     if mode=='index_preference':c.exec_driver_sql('SET LOCAL enable_seqscan=off')
     plans.append(c.execute(text('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+sql)).scalar_one()[0])
   result[name][mode]=plans
 Path('reports/sql_performance_plans.json').write_text(json.dumps(result,indent=2))
 for name,modes in result.items():print(name,{mode:[p['Execution Time'] for p in plans] for mode,plans in modes.items()})
if __name__=='__main__':main()
