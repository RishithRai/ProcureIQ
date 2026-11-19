from .product_models import CalculationResult,SolverResult,ResultPage
"""Verified financial model and actual solver adapters."""
import json
from typing import Literal,Any
from fastapi import APIRouter,Request,Query,Response
from pydantic import Field, field_validator
from sqlalchemy import text
from .models import Input,Filters
from .product_routes import existing,output
from procureiq.ui.service import DashboardService
from procureiq.scenario_basis import database_baseline,manual_baseline,is_stale,refresh_baseline
from procureiq.scenario_io import document,load_json,export_json,validate_database_claim
from procureiq.financial_model import Assumptions,sensitivity,break_even
from procureiq.product.optimization import OptimizationInput,solve,MODEL_VERSION
from procureiq.opportunities import canonical
from procureiq.investigations.domain import InvestigationError
router=APIRouter(prefix='/api/v1/strategy',tags=['Strategy'])
class BaselineInput(Input):
    kind:Literal['hmrc','manual']='hmrc'
    filters:Filters=Field(default_factory=Filters)
    amount:str='0'
    start_month:str|None=None
    end_month:str|None=None
    scope:str=Field(default='Selected expenditure population',max_length=500)
class AssumptionInput(Input):
    addressable_pct:str='0'
    adoption_pct:str='0'
    improvement_pct:str='0'
    implementation_cost:str='0'
    operating_cost:str='0'
class Calculation(Input):
    baseline:dict[str,Any]
    scenarios:dict[str,AssumptionInput]
    selected:Literal['Conservative','Base','Ambitious']='Base'
    @field_validator('baseline')
    @classmethod
    def baseline_keys(cls,v):
        if not {'kind','amount_gbp','source_fingerprint'} <= set(v):raise ValueError('Baseline schema required')
        return v
    @field_validator('scenarios')
    @classmethod
    def case_names(cls,v):
        if set(v)!={'Conservative','Base','Ambitious'}:raise ValueError('Exactly three named alternatives required')
        return v
class SavedScenario(Input):
    document:dict[str,Any]
class SavedOptimization(Input):
    assumptions:OptimizationInput

def dashboard(request):return DashboardService(existing(request).engine)
def validate_scenario(request,doc):
    service=dashboard(request);version=service.version()
    parsed,cases=load_json(export_json(doc))
    if is_stale(parsed['baseline'],version):raise InvestigationError('stale_source','Scenario source changed; explicitly select or refresh the baseline.')
    validate_database_claim(service,parsed['baseline'],version)
    return parsed,cases
@router.post('/baseline')
def baseline(request:Request,body:BaselineInput):
    service=dashboard(request)
    if body.kind=='manual':b=manual_baseline(body.amount,body.start_month,body.end_month,body.scope)
    else:b=database_baseline(service,body.filters.model_dump(),service.version())
    return output(b)
@router.post('/calculate',response_model=CalculationResult)
def calculate(request:Request,body:Calculation):
    service=dashboard(request);version=service.version()
    if is_stale(body.baseline,version):raise InvestigationError('stale_source','Scenario source changed; choose a new baseline.')
    cases={k:Assumptions(**v.model_dump()) for k,v in body.scenarios.items()}
    doc=document(body.baseline,cases,body.selected)
    doc,cases=validate_scenario(request,doc)
    return output(dict(document=doc,sensitivity=sensitivity(doc['baseline']['amount_gbp'],cases[body.selected]),break_even=break_even(doc['baseline']['amount_gbp'],cases[body.selected])))
@router.post('/import')
def import_scenario(request:Request,body:SavedScenario):
    doc,cases=load_json(export_json(body.document));service=dashboard(request);version=service.version()
    stale=is_stale(doc['baseline'],version)
    if not stale:validate_database_claim(service,doc['baseline'],version)
    return output(dict(document=doc,stale=stale))
@router.post('/refresh')
def refresh(request:Request,body:SavedScenario):
    doc,cases=load_json(export_json(body.document));service=dashboard(request)
    b=refresh_baseline(service,doc['baseline'],service.version())
    return output(document(b,cases,doc['sensitivity']['selected']))
@router.post('/excel')
def excel(request:Request,body:SavedScenario):
    from procureiq.scenario_excel import workbook_bytes
    doc,_=validate_scenario(request,body.document)
    return Response(workbook_bytes(doc),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="procureiq_scenario.xlsx"'})
@router.post('/optimization/solve',response_model=SolverResult)
def optimize(request:Request,body:OptimizationInput):return output(solve(body))
@router.post('/optimization/runs',status_code=201)
def save_optimization(request:Request,body:SavedOptimization):
    # Re-solve server-side; never trust client result fields.
    result=solve(body.assumptions)
    with existing(request).engine.begin() as c:
        row=c.execute(text('INSERT INTO procureiq_app.optimization_run(model_version,assumptions,result) VALUES(:version,CAST(:inputs AS jsonb),CAST(:result AS jsonb)) RETURNING *'),dict(version=MODEL_VERSION,inputs=canonical(body.assumptions.model_dump()),result=canonical(result))).mappings().one()
        return output(dict(row),201)
@router.get('/optimization/runs',response_model=ResultPage[dict])
def optimization_runs(request:Request,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    with existing(request).read() as c:
        items=[dict(r) for r in c.execute(text("SELECT run_id,model_version,created_at,assumptions->>'title' AS title,result->>'status' AS status,result->>'objective_gbp' AS objective_gbp FROM procureiq_app.optimization_run ORDER BY run_id DESC LIMIT :limit OFFSET :offset"),dict(limit=limit,offset=offset)).mappings()]
        total=c.execute(text('SELECT count(*) FROM procureiq_app.optimization_run')).scalar_one()
        return output(dict(items=items,total=total,offset=offset,limit=limit))
@router.get('/optimization/runs/{run_id}')
def optimization_run(request:Request,run_id:int):
    with existing(request).read() as c:
        row=c.execute(text('SELECT * FROM procureiq_app.optimization_run WHERE run_id=:id'),dict(id=run_id)).mappings().first()
        if not row:raise InvestigationError('run_not_found','Saved optimization not found.',404)
        return output(dict(row))
