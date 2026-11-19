# PostgreSQL query performance experiment

Executed locally on PostgreSQL 17.11 against the 12,973-line accepted population. `scripts/benchmark_sql.py` runs three repetitions of each query using `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` in read-only transactions. Exact queries, complete plans, settings and timings are in [plan evidence](../reports/sql_performance_plans.json).

The comparison uses the normal planner against `SET LOCAL enable_seqscan=off`, a diagnostic evaluation of existing index access paths. It is not a deployment recommendation. No index or analytical schema change was made.

| Query | Normal planner execution ms | Index-preference execution ms |
|---|---|---|
| Filtered spend | 33.074, 14.419, 12.152 | 12.264, 12.357, 12.248 |
| Supplier ranking | 40.098, 36.381, 36.001 | 36.976, 36.117, 36.429 |
| Transaction page | 4.681, 4.435, 4.398 | 4.767, 4.674, 4.616 |

Warm-cache normal and index-preference results are comparable. The slow first filtered-spend sample is not evidence of an indexing benefit: cache warmup and run ordering confound it. Transaction pagination was slightly slower with index preference. This experiment does not justify a persistent index or planner-setting change. Existing selective/date/supplier/source relationships are retained. No large-scale latency, throughput or scalability improvement is claimed from this small local dataset.

Reproduce with exported `DATABASE_URL`: `.venv/bin/python scripts/benchmark_sql.py`. Run only against a database where these read-only analytical queries are acceptable. Timings vary with cache state and concurrent activity; compare full plans/buffers, not a single fastest sample.
