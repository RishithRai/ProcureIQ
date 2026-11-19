"""Read-only UI orchestration. No analytical or detector formulas live here."""
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from threading import RLock
from sqlalchemy import bindparam, text
from procureiq.analytics import snapshot_metadata
from procureiq.queries import query, validate_filters, ARGS
from procureiq.opportunity_data import retrieve
from procureiq.opportunities import detect, canonical
from procureiq.opportunity_model import OpportunityConfig, RULE_VERSION


from procureiq.source_basis import SourceChanged, fingerprint


def cache_key(kind, filters, version, config=None):
    return canonical([kind, validate_filters(filters), version, RULE_VERSION,
                      asdict(config) if config else None])


def compact(result):
    """Full evidence arrays never enter Streamlit state or serialized data caches."""
    output = {k: deepcopy(result[k]) for k in ('counts_by_type', 'qualified_before_cap', 'population', 'basis', 'configuration', 'rejection_counts')}
    output['opportunities'] = []
    for item in result['opportunities']:
        summary = {k: deepcopy(v) for k, v in item.items() if k not in
                   ('source_references', 'context_source_references', 'basis', 'configuration')}
        # Quality flags are one per source row and can also be large.
        summary['metrics'].pop('source_flags', None)
        summary['primary_count'] = len(item['source_references'])
        summary['context_count'] = len(item['context_source_references'])
        output['opportunities'].append(summary)
    return output


class DashboardService:
    """Engine pooled as a resource; bounded server caches protected across sessions.

    Every call checks the expected source fingerprint inside its read-only snapshot,
    including cache hits. A version switch cannot silently mix evidence and summaries.
    """
    def __init__(self, engine, max_entries=12, opportunity_entries=3):
        self.engine = engine
        self.max_entries = max_entries
        self.opportunity_entries = opportunity_entries
        self._cache = OrderedDict()
        self._radar = OrderedDict()
        self._lock = RLock()

    @contextmanager
    def snapshot(self, expected=None):
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            with conn.begin():
                conn.exec_driver_sql('SET TRANSACTION READ ONLY')
                conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
                version = fingerprint(conn)
                if expected is not None and expected != version:
                    raise SourceChanged('Active source versions changed. Refresh the data basis.')
                yield conn, version

    def version(self):
        with self.snapshot() as (_, version):
            return version

    def _cached(self, store, key, limit, build):
        if key not in store:
            store[key] = build()
            while len(store) > limit:
                store.popitem(last=False)
        store.move_to_end(key)
        return store[key]

    def options(self, version):
        with self._lock, self.snapshot(version) as (conn, _):
            def build():
                opts = {key: [r[0] for r in conn.execute(text(sql))] for key, sql in {
                    'months': "SELECT DISTINCT reporting_month FROM procureiq.source_file WHERE active AND import_status='loaded' ORDER BY 1",
                    'expense_type': 'SELECT DISTINCT expense_type FROM procureiq.active_spend_line WHERE expense_type IS NOT NULL ORDER BY 1',
                    'expense_area': 'SELECT DISTINCT expense_area FROM procureiq.active_spend_line WHERE expense_area IS NOT NULL ORDER BY 1',
                    'entity': 'SELECT DISTINCT entity FROM procureiq.active_spend_line WHERE entity IS NOT NULL ORDER BY 1',
                }.items()}
                opts['suppliers'] = [dict(r) for r in conn.execute(text('''SELECT DISTINCT s.supplier_id,s.canonical_name
                  FROM procureiq.active_spend_line a JOIN procureiq.supplier s USING(supplier_id)
                  ORDER BY s.canonical_name,s.supplier_id''')).mappings()]
                return opts
            return deepcopy(self._cached(self._cache, ('options',version), self.max_entries, build))

    def analytics(self, filters, version, names):
        filters = validate_filters(filters)
        with self._lock, self.snapshot(version) as (conn, _):
            return {name: deepcopy(self._cached(self._cache, cache_key(name,filters,version), self.max_entries,
                                               lambda name=name: query(conn,name,filters))) for name in names}

    def _opportunities(self, conn, filters, version, config):
        return self._cached(self._radar, cache_key('radar',filters,version,config), self.opportunity_entries,
                            lambda: detect(retrieve(conn, filters), config))

    def opportunities(self, filters, version, config=None):
        config = config or OpportunityConfig()
        with self._lock, self.snapshot(version) as (conn, _):
            return compact(self._opportunities(conn, filters, version, config))

    def _item(self, conn, filters, version, config, opportunity_id):
        result = self._opportunities(conn, filters, version, config)
        return next(item for item in result['opportunities'] if item['opportunity_id'] == opportunity_id)

    @staticmethod
    def _records(conn, filters, ids=None, offset=0, limit=50):
        clause = 'WHERE a.raw_row_id IN :ids' if ids is not None else ''
        statement = text(f'''SELECT a.raw_row_id,a.reporting_month,a.supplier_raw,a.amount_gbp,
            a.transaction_number,a.payment_date,a.expense_type,a.expense_area,f.filename,f.sha256,
            a.source_record_number,r.physical_line_start,r.physical_line_end
            FROM procureiq.analytics_lines({ARGS}) a
            JOIN procureiq.raw_spend_row r USING(raw_row_id)
            JOIN procureiq.source_file f ON f.file_id=a.file_id
            {clause} ORDER BY a.reporting_month,f.sha256,a.source_record_number
            LIMIT :limit OFFSET :offset''')
        params = dict(validate_filters(filters),limit=limit,offset=offset)
        if ids is not None:
            if not ids:
                return []
            statement = statement.bindparams(bindparam('ids', expanding=True))
            params['ids'] = ids
        return [dict(r) for r in conn.execute(statement,params).mappings()]

    def evidence(self, filters, version, opportunity_id, context=False, page=1, size=50, config=None):
        if type(page) is not int or page < 1 or size not in (25,50):
            raise ValueError('Invalid evidence page')
        with self._lock, self.snapshot(version) as (conn, _):
            item = self._item(conn,filters,version,config or OpportunityConfig(),opportunity_id)
            refs = item['context_source_references' if context else 'source_references']
            selected = refs[(page-1)*size:page*size]
            return dict(total=len(refs),rows=self._records(conn,filters,[r['raw_row_id'] for r in selected],limit=size))

    def evidence_download(self, filters, version, opportunity_id, config=None):
        """Explicit download only: complete primary AND contextual evidence, no truncation."""
        with self._lock, self.snapshot(version) as (conn, _):
            item = self._item(conn,filters,version,config or OpportunityConfig(),opportunity_id)
            payload = deepcopy(item)
            for kind in ('source_references','context_source_references'):
                ids = [r['raw_row_id'] for r in item[kind]]
                payload[kind+'_details'] = self._records(conn,filters,ids,limit=len(ids))
            return canonical(payload).encode('utf-8')

    def supplier_detail(self, filters, version, supplier_id):
        filters = validate_filters(filters)
        if filters['supplier_id'] not in (None,supplier_id):
            raise ValueError('Supplier is outside selected population')
        filters['supplier_id'] = supplier_id
        return self.analytics(filters,version,('overview','expense_types','expense_areas','monthly'))

    def supplier_records(self, filters, version, supplier_id, page=1):
        filters = validate_filters(filters)
        if filters['supplier_id'] not in (None,supplier_id) or type(page) is not int or page<1:
            raise ValueError('Invalid supplier selection or page')
        filters['supplier_id'] = supplier_id
        with self.snapshot(version) as (conn, _):
            return self._records(conn,filters,offset=(page-1)*50)

    def aliases(self, filters, version, supplier_id):
        filters = validate_filters(filters)
        if filters['supplier_id'] not in (None,supplier_id):
            raise ValueError('Supplier is outside selected population')
        filters['supplier_id'] = supplier_id
        with self.snapshot(version) as (conn, _):
            return [r[0] for r in conn.execute(text(f'SELECT DISTINCT supplier_raw FROM procureiq.analytics_lines({ARGS}) ORDER BY supplier_raw'),filters)]

    def executive(self, filters, version, config=None):
        """One snapshot for all brief data; reuse the existing bounded detector cache."""
        from procureiq.executive import build_brief
        filters=validate_filters(filters)
        config=config or OpportunityConfig()
        with self._lock, self.snapshot(version) as (conn,_):
            names=('overview','expense_types','suppliers','concentration','monthly')
            data={name:deepcopy(self._cached(self._cache,cache_key(name,filters,version),self.max_entries,
                lambda name=name:query(conn,name,filters))) for name in names}
            radar=self._opportunities(conn,filters,version,config)
            return build_brief(data,radar,snapshot_metadata(conn,filters),filters,version)
