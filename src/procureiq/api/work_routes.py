from .product_models import ResultPage,AnalystEntry
"""Thin routes for persistent analyst notes, findings and bookmarks."""
from typing import Literal
from pydantic import Field,StrictInt,field_validator
from fastapi import APIRouter,Request,Query
from .models import Input
from procureiq.investigations.domain import InvestigationError
from procureiq.investigations.work import CaseWork
router=APIRouter(prefix='/api/v1/investigations/cases',tags=['Analyst work'])

class Citation(Input):
    classification:Literal['primary','contextual']
    ordinal:StrictInt=Field(gt=0)
class Bookmark(Citation):
    active:bool=True
class FindingSections(Input):
    assessment:str=Field(default="",max_length=4000)
    next_step:str=Field(default="",max_length=4000)

class Entry(Input):
    sections:FindingSections|None=None
    kind:Literal['note','finding']
    title:str=Field(min_length=3,max_length=240)
    content:str=Field(min_length=10,max_length=8000)
    expected_version:StrictInt|None=Field(None,gt=0)
    deleted:bool=False
    citations:list[Citation]=Field(default_factory=list,max_length=100)
    @field_validator('title','content')
    @classmethod
    def meaningful(cls,v,info):
        if len(v.strip())<(10 if info.field_name=='content' else 3) or sum(c.isalnum() for c in v)<3:raise ValueError('Meaningful text required')
        return v
    @field_validator('citations')
    @classmethod
    def distinct(cls,v):
        if len({(x.classification,x.ordinal) for x in v})!=len(v):raise ValueError('Duplicate citations')
        return v

def service(request):
    svc=getattr(request.app.state,'service',None)
    if svc is None:raise InvestigationError('service_unavailable','Local database is unavailable.',503)
    return CaseWork(svc.engine)

@router.get('/{case_id}/entries',response_model=ResultPage[AnalystEntry])
def entries(request:Request,case_id:int,offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=100)):
    return service(request).list(case_id,offset,limit)
@router.post('/{case_id}/entries',status_code=201,response_model=AnalystEntry)
def create(request:Request,case_id:int,body:Entry):return service(request).save(case_id,body)
@router.patch('/{case_id}/entries/{entry_id}',response_model=AnalystEntry)
def update(request:Request,case_id:int,entry_id:int,body:Entry):return service(request).save(case_id,body,entry_id)
@router.get('/{case_id}/bookmarks',response_model=ResultPage[dict])
def bookmarks(request:Request,case_id:int,offset:int=Query(0,ge=0,le=1000000),limit:int=Query(50,ge=1,le=100)):
    return service(request).bookmarks(case_id,offset,limit)
@router.post('/{case_id}/bookmarks')
def bookmark(request:Request,case_id:int,body:Bookmark):return service(request).bookmark(case_id,body.classification,body.ordinal,body.active)
