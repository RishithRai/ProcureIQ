from .product_models import ResultPage,SpendSummary,SupplierDetail
"""Product HTTP adapters; Decimal values are serialized as exact strings."""
import json
from typing import Literal
from fastapi import APIRouter,Request,Query,Depends,Response
from fastapi.responses import JSONResponse
from pydantic import Field
from .models import Input,Filters
from procureiq.opportunities import canonical
from procureiq.product.analytics import SpendService
from procureiq.investigations.domain import InvestigationError
router=APIRouter(prefix='/api/v1',tags=['Product'])

def output(value,status=200):return JSONResponse(json.loads(canonical(value)),status_code=status)
def existing(request):
    svc=getattr(request.app.state,'service',None)
    if svc is None:raise InvestigationError('service_unavailable','Local database service unavailable.',503)
    return svc

def filters(start_month:str|None=None,end_month:str|None=None,expense_type:str|None=Query(None,max_length=300),expense_area:str|None=Query(None,max_length=300),entity:str|None=Query(None,max_length=300),supplier_id:int|None=Query(None,gt=0)):
    return Filters(start_month=start_month,end_month=end_month,expense_type=expense_type,expense_area=expense_area,entity=entity,supplier_id=supplier_id).model_dump()

@router.get('/spend/summary',response_model=SpendSummary)
def summary(request:Request,f:dict=Depends(filters),basis:str|None=None):return output(SpendService(existing(request).engine).summary(f,basis))
@router.get('/spend/groups/{kind}',response_model=ResultPage[dict])
def groups(request:Request,kind:Literal['expense_types','expense_areas','suppliers','category_concentration'],f:dict=Depends(filters),offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=100),basis:str|None=None,search:str=Query('',max_length=300)):
    return output(SpendService(existing(request).engine).groups(kind,f,offset,limit,basis,search))
@router.get('/spend/pareto')
def pareto(request:Request,f:dict=Depends(filters),basis:str|None=None):
    from procureiq.queries import query
    service=SpendService(existing(request).engine)
    with service.dashboard.snapshot(basis) as (c,version):
        rows=[r for r in query(c,'suppliers',f) if r['positive_gbp']>0]
        return output(dict(items=[{k:r.get(k) for k in ('supplier_id','canonical_name','supplier_rank','cumulative_resolved_pct','positive_gbp')} for r in rows if r.get('cumulative_resolved_pct') is not None],total=len(rows),source_fingerprint=version))
@router.get('/spend/transactions',response_model=ResultPage[dict])
def transactions(request:Request,f:dict=Depends(filters),search:str=Query('',max_length=300),offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=100),order:Literal['source','amount_desc','amount_asc']='source',basis:str|None=None):
    return output(SpendService(existing(request).engine).transactions(f,search,offset,limit,order,basis))
@router.get('/spend/transactions/{raw_id}')
def transaction(request:Request,raw_id:int):return output(SpendService(existing(request).engine).transaction(raw_id))
@router.get('/spend/suppliers/{id}',response_model=SupplierDetail)
def supplier(request:Request,id:int,f:dict=Depends(filters),basis:str|None=None):return output(SpendService(existing(request).engine).supplier(id,f,basis))
@router.get('/spend/options')
def options(request:Request):
    service=SpendService(existing(request).engine).dashboard
    version=service.version()
    return output(dict(source_fingerprint=version,options=service.options(version)))
@router.get('/command')
def command(request:Request):
    svc=existing(request)
    from sqlalchemy import text
    with svc.read() as c:
        from procureiq.queries import query
        from procureiq.source_basis import fingerprint
        from procureiq.investigations.namespace import current_namespace
        params=dict(namespace=current_namespace.get())
        statuses={r[0]:r[1] for r in c.execute(text('SELECT status,count(*) FROM procureiq_app.investigation_case WHERE namespace=:namespace GROUP BY status'),params)}
        activity=[dict(r) for r in c.execute(text('SELECT e.*,c.case_reference,c.title FROM procureiq_app.case_event e JOIN procureiq_app.investigation_case c USING(case_id) WHERE c.namespace=:namespace ORDER BY event_id DESC LIMIT 8'),params).mappings()]
        data=dict(source_fingerprint=fingerprint(c),overview=query(c,'overview'),months=query(c,'monthly'),case_counts=statuses,activity=activity)
    return output(data)
