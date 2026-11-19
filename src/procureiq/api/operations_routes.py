from typing import Literal
from fastapi import APIRouter,Request,Query
from pydantic import Field
from sqlalchemy import text
from .models import Input
from .product_routes import existing,output
from procureiq.investigations.domain import InvestigationError
router=APIRouter(prefix='/api/v1/operations',tags=['Data operations'])
class Registration(Input):
    manifest_name:str=Field(pattern=r'^[A-Za-z0-9_-]+\.json$')
class RunInput(Input):
    operation:Literal['verify','ingest','activate']
    registration_id:int|None=Field(None,gt=0)
    source_file_id:int|None=Field(None,gt=0)
    expected_fingerprint:str|None=Field(None,pattern='^[a-f0-9]{64}$')
    confirm_activation:bool=False

def pipeline(request):
    p=getattr(request.app.state,'pipeline',None)
    if p is None:raise InvestigationError('service_unavailable','Local pipeline service is unavailable.',503)
    return p
@router.get('/manifests')
def manifests(request:Request):return output(dict(items=pipeline(request).discover()))
@router.post('/registrations',status_code=201)
def register(request:Request,body:Registration):return output(pipeline(request).register(body.manifest_name),201)
@router.post('/runs',status_code=202)
def launch(request:Request,body:RunInput):
    if body.operation=='activate' and not body.confirm_activation:raise InvestigationError('confirmation_required','Explicit reviewed source activation confirmation is required.',422)
    return output(pipeline(request).enqueue(body.operation,body.registration_id,body.source_file_id,body.expected_fingerprint),202)
@router.post('/runs/{run_id}/retry',status_code=202)
def retry(request:Request,run_id:int):return output(pipeline(request).retry(run_id),202)
@router.get('/runs')
def runs(request:Request,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    with existing(request).read() as c:
        total=c.execute(text('SELECT count(*) FROM procureiq_app.pipeline_run')).scalar_one()
        items=[dict(r) for r in c.execute(text('SELECT * FROM procureiq_app.pipeline_run ORDER BY run_id DESC LIMIT :limit OFFSET :offset'),dict(limit=limit,offset=offset)).mappings()]
        return output(dict(items=items,total=total,offset=offset,limit=limit))
@router.get('/runs/{run_id}')
def run(request:Request,run_id:int):
    with existing(request).read() as c:
        r=c.execute(text('SELECT * FROM procureiq_app.pipeline_run WHERE run_id=:id'),dict(id=run_id)).mappings().first()
        if not r:raise InvestigationError('run_not_found','Pipeline run not found.',404)
        stages=[dict(s) for s in c.execute(text('SELECT * FROM procureiq_app.pipeline_stage WHERE run_id=:id ORDER BY stage_id'),dict(id=run_id)).mappings()]
        return output(dict(run=dict(r),stages=stages))
@router.get('/sources')
def sources(request:Request,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    from procureiq.source_basis import fingerprint
    with existing(request).read() as c:
        items=[dict(r) for r in c.execute(text('SELECT * FROM procureiq.source_file ORDER BY reporting_month DESC,file_id DESC LIMIT :limit OFFSET :offset'),dict(limit=limit,offset=offset)).mappings()]
        total=c.execute(text('SELECT count(*) FROM procureiq.source_file')).scalar_one()
        return output(dict(items=items,total=total,offset=offset,limit=limit,source_fingerprint=fingerprint(c)))
@router.get('/quality')
def quality(request:Request,file_id:int|None=Query(None,gt=0),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),
    issue_code:str|None=Query(None,max_length=100),severity:str|None=Query(None,max_length=50),reporting_month:str|None=Query(None,pattern=r'^\d{4}-\d{2}$'),search:str=Query('',max_length=300)):
    from datetime import date
    month=date.fromisoformat(reporting_month+'-01') if reporting_month else None
    with existing(request).read() as c:
        base=' FROM procureiq.data_quality_issue q LEFT JOIN procureiq.raw_spend_row r USING(raw_row_id) JOIN procureiq.source_file f ON f.file_id=coalesce(q.file_id,r.file_id)'
        clause=base+" WHERE (CAST(:file AS bigint) IS NULL OR f.file_id=CAST(:file AS bigint)) AND (CAST(:code AS text) IS NULL OR q.issue_code=:code) AND (CAST(:severity AS text) IS NULL OR q.severity=:severity) AND (CAST(:month AS date) IS NULL OR f.reporting_month=CAST(:month AS date)) AND (:search='' OR strpos(lower(q.details::text || ' ' || q.issue_code || ' ' || f.filename),lower(:search))>0)"
        params=dict(file=file_id,code=issue_code,severity=severity,month=month,search=search,offset=offset,limit=limit)
        total=c.execute(text('SELECT count(*)'+clause),params).scalar_one()
        all_total=c.execute(text('SELECT count(*)'+base)).scalar_one()
        groups=[dict(r) for r in c.execute(text('SELECT q.issue_code,q.severity,f.reporting_month,count(*) AS count'+base+' GROUP BY 1,2,3 ORDER BY 1,2,3')).mappings()]
        items=[dict(r) for r in c.execute(text('SELECT q.*,f.filename,f.sha256,f.active,f.reporting_month,r.source_record_number'+clause+' ORDER BY q.issue_id LIMIT :limit OFFSET :offset'),params).mappings()]
        return output(dict(items=items,total=total,all_total=all_total,groups=groups,offset=offset,limit=limit))
