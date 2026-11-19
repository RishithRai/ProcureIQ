"""V1 HTTP request/response contracts."""
from typing import Any,Literal
from datetime import datetime,date
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,StrictInt,field_validator
from procureiq.investigations.domain import Status,Disposition,meaningful


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Filters(Input):
    start_month:str|None=Field(None,pattern=r'^\d{4}-\d{2}(?:-01)?$')
    end_month:str|None=Field(None,pattern=r'^\d{4}-\d{2}(?:-01)?$')
    expense_type:str|None=Field(None,max_length=300)
    expense_area:str|None=Field(None,max_length=300)
    entity:str|None=Field(None,max_length=300)
    supplier_id:StrictInt|None=Field(None,gt=0)

    @field_validator('start_month','end_month')
    @classmethod
    def canonical_month(cls,value):
        # A client can echo first-of-month dates from the returned canonical basis.
        return value[:7] if value is not None else None



class CreateCase(Input):
    review_id:str=Field(pattern=r'^opp_[0-9a-f]{24}$')
    filters:Filters=Field(default_factory=Filters)
    basis_token:str=Field(pattern=r'^[0-9a-f]{64}$')
    title:str=Field(min_length=3,max_length=240)
    objective:str=Field(min_length=10,max_length=4000)

    @field_validator('objective')
    @classmethod
    def valid_objective(cls,value):
        if not meaningful(value):raise ValueError('Meaningful investigation objective required')
        return value


class StatusChange(Input):
    status:Status
    expected_version:StrictInt=Field(gt=0)
    reason:str|None=Field(None,min_length=10,max_length=4000)
    disposition:Disposition|None=None


class Case(BaseModel):
    work_counts:dict[str,int]=Field(default_factory=dict)
    namespace:Literal['NORMAL','DEMO']
    case_id:int
    case_reference:str
    title:str
    objective:str
    opportunity_id:str
    opportunity_type:str
    original_score:Decimal
    rule_version:str
    configuration_identity:str
    reporting_filters:dict[str,Any]
    source_fingerprint:str
    review_basis_key:str
    status:Status
    row_version:int
    primary_count:int
    contextual_count:int
    created_at:datetime
    updated_at:datetime
    reviewed_at:datetime|None
    closed_at:datetime|None
    disposition:Disposition|None
    closure_explanation:str|None
    basis_matches_current_source:bool
    review_snapshot:dict[str,Any]|None=None
    configuration:dict[str,Any]|None=None


class Creation(BaseModel):
    created:bool
    case:Case


class CasePage(BaseModel):
    items:list[Case]
    total:int
    offset:int
    limit:int


class Review(BaseModel):
    opportunity_id:str
    opportunity_type:str
    title:str
    scope:dict[str,Any]
    positive_exposure_gbp:Decimal
    priority_score:Decimal
    evidence_summary:str
    primary_count:int
    contextual_count:int
    review_basis_key:str
    existing_case:dict[str,Any]|None
    scoring:dict[str,Any]|None=None
    metrics:dict[str,Any]|None=None
    business_interpretation:str|None=None
    next_investigation_step:str|None=None
    caveats:list[str]|None=None
    exposure_definition:str|None=None


class Reviews(BaseModel):
    items:list[Review]
    total:int
    offset:int
    limit:int
    basis:dict[str,Any]
    basis_token:str
    qualified_count:int
    exported_count:int
    deferred_count:int
    counts_by_type:dict[str,int]
    qualified_by_type:dict[str,int]


class Evidence(BaseModel):
    amount_gbp:Decimal|None=None
    bookmarked:bool=False
    case_id:int
    classification:Literal['primary','contextual']
    ordinal:int
    raw_row_id:int
    file_id:int
    file_sha256:str
    source_record_number:int
    row_hash:str
    source_values:dict[str,Any]
    physical_line_start:int
    physical_line_end:int
    filename:str
    reporting_month:date
    source_currently_active:bool


class EvidencePage(BaseModel):
    unfiltered_total:int
    summary:dict[str,Any]
    items:list[Evidence]
    total:int
    offset:int
    limit:int
    classification:Literal['primary','contextual']
    basis_matches_current_source:bool


class Event(BaseModel):
    event_id:int
    case_id:int
    event_type:str
    occurred_at:datetime
    actor:Literal['local_application']
    previous_status:Status|None
    new_status:Status
    reason:str|None
    details:dict[str,Any]


class EventPage(BaseModel):
    items:list[Event]
    total:int
    offset:int
    limit:int
