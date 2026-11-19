"""Shared typed response envelopes; flexible measurements come from existing SQL engines."""
from typing import Any,Generic,TypeVar
from pydantic import BaseModel,Field
T=TypeVar('T')
class ResultPage(BaseModel,Generic[T]):
    items:list[T]
    total:int
    offset:int
    limit:int
    source_fingerprint:str|None=None
class SpendSummary(BaseModel):
    source_fingerprint:str
    filters:dict[str,Any]
    overview:list[dict[str,Any]]
    monthly:list[dict[str,Any]]
    concentration:list[dict[str,Any]]
class SupplierDetail(BaseModel):
    supplier:dict[str,Any]
    aliases:list[dict[str,Any]]
    share_context:dict[str,Any]|None
    concentration_context:list[dict[str,Any]]
    analytics:dict[str,list[dict[str,Any]]]
    source_fingerprint:str
    filters:dict[str,Any]
class CalculationResult(BaseModel):
    document:dict[str,Any]
    sensitivity:list[dict[str,Any]]
    break_even:dict[str,Any]
class SolverResult(BaseModel):
    model_version:str
    status:str
    solver_status:int
    feasible:bool
    objective_gbp:str|None
    allocations:list[dict[str,Any]]
    binding_constraints:list[str]
    explanations:list[str]
    mip_gap:float|None
    validation:dict[str,Any]
    limitation:str
class AnalystEntry(BaseModel):
    sections:dict[str,str]|None=None
    entry_id:int
    case_id:int
    kind:str
    title:str
    content:str
    row_version:int
    deleted:bool
    created_at:Any
    updated_at:Any
    citations:list[dict[str,Any]]=Field(default_factory=list)
