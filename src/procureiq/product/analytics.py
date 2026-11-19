"""Read-only product queries. Financial calculations remain in existing SQL."""
from sqlalchemy import text
from procureiq.queries import query,validate_filters,ARGS
from procureiq.ui.service import DashboardService
from procureiq.investigations.domain import InvestigationError

class SpendService:
    def __init__(self,engine):self.dashboard=DashboardService(engine)
    def summary(self,filters,expected=None):
        with self.dashboard.snapshot(expected) as (c,version):
            return dict(source_fingerprint=version,filters=validate_filters(filters),
                overview=query(c,'overview',filters),monthly=query(c,'monthly',filters),concentration=query(c,'concentration',filters))
    def groups(self,kind,filters,offset,limit,expected=None,search=""):
        if kind not in ('expense_types','expense_areas','suppliers','category_concentration'):raise ValueError('Unknown dimension')
        with self.dashboard.snapshot(expected) as (c,version):
            values=query(c,kind,filters)
            if search:values=[v for v in values if search.casefold() in str(v.get("canonical_name") or v.get("group_value") or "").casefold()]
            return dict(items=values[offset:offset+limit],total=len(values),offset=offset,limit=limit,source_fingerprint=version)
    def transactions(self,filters,search,offset,limit,order,expected=None):
        orders={'source':'a.reporting_month,a.file_id,a.source_record_number','amount_desc':'a.amount_gbp DESC NULLS LAST,a.raw_row_id','amount_asc':'a.amount_gbp ASC NULLS LAST,a.raw_row_id'}
        params=dict(validate_filters(filters),search=search,offset=offset,limit=limit)
        where=" WHERE (:search='' OR strpos(lower(coalesce(a.supplier_raw,'') || ' ' || coalesce(a.transaction_number,'') || ' ' || coalesce(a.description,'')),lower(:search))>0)"
        base=f' FROM procureiq.analytics_lines({ARGS}) a JOIN procureiq.source_file f ON f.file_id=a.file_id'
        with self.dashboard.snapshot(expected) as (c,version):
            total=c.execute(text('SELECT count(*)'+base+where),params).scalar_one()
            items=[dict(r) for r in c.execute(text('SELECT a.raw_row_id,a.reporting_month,a.supplier_raw,a.expense_type,a.expense_area,a.amount_gbp,a.transaction_number,a.source_record_number,f.filename,f.sha256'+base+where+' ORDER BY '+orders[order]+' LIMIT :limit OFFSET :offset'),params).mappings()]
            return dict(items=items,total=total,offset=offset,limit=limit,source_fingerprint=version)
    def transaction(self,raw_id):
        with self.dashboard.snapshot() as (c,version):
            r=c.execute(text('''SELECT r.*,f.filename,f.sha256,f.reporting_month,f.active AS source_currently_active FROM procureiq.raw_spend_row r
                JOIN procureiq.source_file f USING(file_id) WHERE raw_row_id=:id'''),dict(id=raw_id)).mappings().first()
            if not r:raise InvestigationError('record_not_found','Source record not found.',404)
            return dict(record=dict(r),source_fingerprint=version)
    def supplier(self,supplier_id,filters,expected=None):
        filters=validate_filters(filters)
        if filters['supplier_id'] not in (None,supplier_id):raise ValueError('Supplier conflict')
        with self.dashboard.snapshot(expected) as (c,version):
            supplier=c.execute(text('SELECT * FROM procureiq.supplier WHERE supplier_id=:id'),dict(id=supplier_id)).mappings().first()
            if not supplier:raise InvestigationError('supplier_not_found','Supplier not found.',404)
            context=query(c,'concentration',filters)
            rank=next((r for r in query(c,'suppliers',filters) if r['supplier_id']==supplier_id),None)
            filters['supplier_id']=supplier_id
            aliases=[dict(r) for r in c.execute(text('SELECT * FROM procureiq.supplier_alias WHERE supplier_id=:id ORDER BY alias_id'),dict(id=supplier_id)).mappings()]
            analytics={n:query(c,n,filters) for n in ('overview','monthly','expense_types','expense_areas')}
            total=analytics['overview'][0]['positive_gbp']
            from decimal import Decimal
            for kind in ('expense_types','expense_areas'):
                for row in analytics[kind]:row['supplier_positive_share_pct']=row['positive_gbp']/total*Decimal(100) if total else None
            return dict(supplier=dict(supplier),aliases=aliases,share_context=rank,concentration_context=context,
                analytics=analytics,source_fingerprint=version,filters=filters)
