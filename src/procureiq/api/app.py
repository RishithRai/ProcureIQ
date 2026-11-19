"""Run locally: uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000."""
import os
from pathlib import Path
from decimal import Decimal
from typing import Annotated,Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,Response,Query,Depends,Path as PathParam
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from procureiq.db import engine_from_env
from procureiq.opportunity_model import load_config
from procureiq.investigations.service import InvestigationService
from procureiq.investigations.domain import InvestigationError,Status
from .models import Filters,CreateCase,StatusChange,Creation,Case,CasePage,Reviews,EvidencePage,EventPage

Limit=Annotated[int,Query(ge=1,le=100)]
Offset=Annotated[int,Query(ge=0,le=1000000)]
CaseId=Annotated[int,PathParam(gt=0)]


def create_app(engine=None,config=None,root=None,workers=None):
    owned=engine is None
    @asynccontextmanager
    async def lifespan(app):
        nonlocal engine
        try:
            if engine is None:engine=engine_from_env()
            path=os.environ.get('PROCUREIQ_OPPORTUNITY_CONFIG')
            policy=config or load_config(Path(path) if path else None)
            app.state.service=InvestigationService(engine,policy)
        except (ValueError,OSError):app.state.service=None
        from procureiq.product.pipeline import Pipeline
        app.state.pipeline=Pipeline(engine,root or Path.cwd()) if engine is not None else None
        if app.state.pipeline and (owned if workers is None else workers):app.state.pipeline.start()
        yield
        if app.state.pipeline:app.state.pipeline.close()
        if owned and engine is not None:engine.dispose()

    app=FastAPI(title='ProcureIQ Investigation API',version='1.0.0',lifespan=lifespan,
        description='Local single-analyst API. No authentication: bind to loopback and never expose publicly.')
    app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],
        allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type','X-Investigation-Namespace'],allow_credentials=False)

    @app.middleware('http')
    async def workspace(request,call_next):
        from procureiq.investigations.namespace import current_namespace
        mode=request.headers.get('X-Investigation-Namespace','NORMAL')
        if mode not in ('NORMAL','DEMO'):
            return JSONResponse(status_code=422,content={'error':{'code':'invalid_namespace','message':'Choose NORMAL or DEMO.'}})
        token=current_namespace.set(mode)
        try:return await call_next(request)
        finally:current_namespace.reset(token)

    @app.middleware('http')
    async def bounded_body(request,call_next):
        # Bound actual streamed bytes, including requests with no Content-Length.
        if request.method in ('POST','PATCH'):
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>16384:return JSONResponse(status_code=413,content={'error':{'code':'request_too_large','message':'Request body exceeds 16 KiB.'}})
                chunks.append(chunk)
            request._body=b''.join(chunks)
        return await call_next(request)

    @app.exception_handler(InvestigationError)
    async def domain_error(request,exc):return JSONResponse(status_code=exc.status,content={'error':{'code':exc.code,'message':exc.message}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        return JSONResponse(status_code=422,content={'error':{'code':'invalid_input','message':'Request does not match the API schema. Check field names, types and bounds.'}})

    @app.exception_handler(ValueError)
    async def value_error(request,exc):
        return JSONResponse(status_code=422,content={'error':{'code':'invalid_input','message':'Invalid reporting filters or input values.'}})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request,exc):
        return JSONResponse(status_code=503,content={'error':{'code':'service_unavailable','message':'Database service is unavailable or not initialized. Check local configuration and migrations.'}})

    @app.exception_handler(Exception)
    async def internal_error(request,exc):
        return JSONResponse(status_code=500,content={'error':{'code':'internal_error','message':'The operation could not complete. No internal details are exposed.'}})

    def service(request):
        svc=getattr(request.app.state,'service',None)
        if svc is None:raise InvestigationError('service_unavailable','Local database or policy configuration is unavailable.',503)
        return svc

    def reporting_filters(request:Request,
            start_month:Annotated[str|None,Query(pattern=r'^\d{4}-\d{2}(?:-01)?$')]=None,
            end_month:Annotated[str|None,Query(pattern=r'^\d{4}-\d{2}(?:-01)?$')]=None,
            expense_type:Annotated[str|None,Query(max_length=300)]=None,
            expense_area:Annotated[str|None,Query(max_length=300)]=None,
            entity:Annotated[str|None,Query(max_length=300)]=None,
            supplier_id:Annotated[int|None,Query(gt=0)]=None):
        allowed={'start_month','end_month','expense_type','expense_area','entity','supplier_id','detector_type','minimum_priority','offset','limit'}
        if set(request.query_params)-allowed:raise InvestigationError('invalid_input','Unsupported reporting query parameter.',422)
        return Filters(start_month=start_month,end_month=end_month,expense_type=expense_type,expense_area=expense_area,entity=entity,supplier_id=supplier_id)

    prefix='/api/v1'
    @app.get(prefix+'/health')
    def health(request:Request):return service(request).health()

    @app.get(prefix+'/investigations/reviews',response_model=Reviews,response_model_exclude_none=True)
    def reviews(request:Request,filters:Annotated[Filters,Depends(reporting_filters)],
                detector_type:Literal['supplier_concentration','purchasing_fragmentation','payment_pattern','data_quality']|None=None,
                minimum_priority:Annotated[Decimal,Query(ge=0,le=100)]=Decimal('0'),offset:Offset=0,limit:Limit=50):
        return service(request).reviews(filters.model_dump(),detector_type,minimum_priority,offset,limit)

    @app.get(prefix+'/investigations/reviews/{review_id}',response_model=Reviews,response_model_exclude_none=True)
    def review(request:Request,review_id:str,filters:Annotated[Filters,Depends(reporting_filters)]):
        return service(request).reviews(filters.model_dump(),review_id=review_id)

    @app.post(prefix+'/investigations/cases',response_model=Creation)
    def create(request:Request,body:CreateCase,response:Response):
        result=service(request).create(body.review_id,body.filters.model_dump(),body.basis_token,body.title,body.objective)
        response.status_code=201 if result['created'] else 200
        return result

    @app.get(prefix+'/investigations/cases',response_model=CasePage,response_model_exclude_none=True)
    def cases(request:Request,status:Status|None=None,offset:Offset=0,limit:Limit=50):
        return service(request).cases(status.value if status else None,offset,limit)

    @app.get(prefix+'/investigations/cases/{case_id}',response_model=Case)
    def case(request:Request,case_id:CaseId):return service(request).get(case_id)

    @app.get(prefix+'/investigations/cases/{case_id}/evidence',response_model=EvidencePage)
    def evidence(request:Request,case_id:CaseId,classification:Literal['primary','contextual']='primary',offset:Offset=0,limit:Limit=50,
        supplier:str|None=Query(None,max_length=300),start_month:str|None=Query(None,pattern=r'^\d{4}-\d{2}$'),end_month:str|None=Query(None,pattern=r'^\d{4}-\d{2}$'),
        minimum_amount:Decimal|None=None,maximum_amount:Decimal|None=None,transaction:str|None=Query(None,max_length=300),search:str|None=Query(None,max_length=300)):
        from datetime import date
        start=date.fromisoformat(start_month+'-01') if start_month else None
        end=date.fromisoformat(end_month+'-01') if end_month else None
        if start and end and start>end:raise ValueError('Month range')
        if minimum_amount is not None and maximum_amount is not None and minimum_amount>maximum_amount:raise ValueError('Amount range')
        for amount in (minimum_amount,maximum_amount):
            if amount is not None and not amount.is_finite():raise ValueError('Finite amount required')
        return service(request).evidence(case_id,classification,offset,limit,dict(supplier=supplier,start_month=start,end_month=end,minimum_amount=minimum_amount,maximum_amount=maximum_amount,transaction=transaction,search=search))

    @app.get(prefix+'/investigations/cases/{case_id}/activity',response_model=EventPage)
    def activity(request:Request,case_id:CaseId,offset:Offset=0,limit:Limit=50,kind:Literal['lifecycle','findings','notes','evidence']|None=None):
        return service(request).activity(case_id,offset,limit,kind)

    @app.patch(prefix+'/investigations/cases/{case_id}/status',response_model=Case)
    def status(request:Request,case_id:CaseId,body:StatusChange):
        return service(request).status(case_id,body.status.value,body.expected_version,body.reason,body.disposition.value if body.disposition else None)
    from .work_routes import router as work_router
    app.include_router(work_router)
    from .product_routes import router as product_router
    app.include_router(product_router)
    from procureiq.source_basis import SourceChanged
    @app.exception_handler(SourceChanged)
    async def changed(request,exc):
        return JSONResponse(status_code=409,content={"error":{"code":"stale_source","message":"Source basis changed. Refresh and explicitly review the current population."}})
    from .strategy_routes import router as strategy_router
    from .operations_routes import router as operations_router
    from .report_routes import router as report_router
    app.include_router(strategy_router)
    app.include_router(operations_router)
    app.include_router(report_router)
    return app
