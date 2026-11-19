"""One-basis executive exports through existing deterministic generators."""
from typing import Any,Literal
from fastapi import APIRouter,Request,Response
from pydantic import Field
from sqlalchemy import text
from .models import Input,Filters
from .product_routes import existing,output
from procureiq.ui.service import DashboardService
from procureiq.executive import compatible_scenario
from procureiq.executive_presentation import presentation_bytes
from procureiq.opportunities import canonical
from procureiq.investigations.domain import InvestigationError
router=APIRouter(prefix='/api/v1/reports',tags=['Executive reports'])
class ReportInput(Input):
    include_insights:bool=True
    include_recommendations:bool=True
    include_findings:bool=True
    expected_content_hash:str|None=Field(None,pattern="^[a-f0-9]{64}$")
    filters:Filters=Field(default_factory=Filters)
    expected_fingerprint:str|None=Field(None,pattern='^[a-f0-9]{64}$')
    scenario:dict[str,Any]|None=None
    case_ids:list[int]=Field(default_factory=list,max_length=10)

def build(request,body):
    svc=existing(request);dash=DashboardService(svc.engine);version=body.expected_fingerprint or dash.version()
    brief=dash.executive(body.filters.model_dump(),version,svc.config)
    scenario=compatible_scenario(dash,brief,body.scenario) if body.scenario else None
    context=[]
    with dash.snapshot(version) as (c,_):
        for cid in body.case_ids:
            from procureiq.investigations.repository import get_case
            case=get_case(c,cid)
            if case['source_fingerprint']!=version:raise InvestigationError('incompatible_case','Historical investigation source does not match this report.',422)
            # Require exact reporting context; no unsupported overlap inference.
            from procureiq.queries import validate_filters
            normalized={k:str(v) if v is not None else None for k,v in validate_filters(body.filters.model_dump()).items()}
            cf={k:str(v) if v is not None else None for k,v in case['reporting_filters'].items()}
            if normalized!=cf:raise InvestigationError('incompatible_case','Investigation reporting scope must match the report exactly.',422)
            entries=[dict(r) for r in c.execute(text("SELECT entry_id,title,content,sections,row_version FROM procureiq_app.case_entry WHERE case_id=:id AND kind='finding' AND NOT deleted ORDER BY entry_id LIMIT 50"),dict(id=cid)).mappings()]
            if not body.include_findings:entries=[]
            for entry in entries:
                entry['citations']=[dict(r) for r in c.execute(text('SELECT f.classification,f.ordinal,e.file_id,e.file_sha256,e.raw_row_id,e.source_record_number FROM procureiq_app.finding_evidence f JOIN procureiq_app.case_evidence e USING(case_id,classification,ordinal) WHERE f.entry_id=:id ORDER BY classification,ordinal'),dict(id=entry['entry_id'])).mappings()]
            finding_count=c.execute(text("SELECT count(*) FROM procureiq_app.case_entry WHERE case_id=:id AND kind='finding' AND NOT deleted"),dict(id=cid)).scalar_one()
            context.append(dict(findings_total=finding_count,findings_truncated=finding_count>len(entries),case_reference=case['case_reference'],status=case['status'],disposition=case['disposition'],closure_explanation=case['closure_explanation'],findings=entries,attribution='Analyst-recorded conclusions; not independently verified savings.'))
    brief['investigation_context']=context
    if not body.include_insights:brief['findings']=[]
    if not body.include_recommendations:brief['recommendations']=[]
    from hashlib import sha256
    digest=sha256(canonical(dict(brief=brief,scenario=scenario)).encode()).hexdigest()
    if body.expected_content_hash and digest!=body.expected_content_hash:raise InvestigationError('stale_report','Report content changed. Preview again before downloading.',409)
    brief['content_hash']=digest
    return brief,scenario
@router.post('/preview')
def preview(request:Request,body:ReportInput):
    brief,scenario=build(request,body)
    # Full reference arrays are available only through explicit evidence download.
    clean={k:v for k,v in brief.items() if k!='recommendations'}
    clean['recommendations']=[{k:v for k,v in r.items() if k not in ('source_references','context_source_references','measurements')} for r in brief['recommendations']]
    from procureiq.product.presentation_preview import slide_model
    return output(dict(brief=clean,scenario=scenario,presentation=slide_model(presentation_bytes(brief,scenario))))
@router.post('/download/{format}')
def download(request:Request,format:Literal['pptx','json'],body:ReportInput):
    brief,scenario=build(request,body)
    if format=='json':return Response(canonical(dict(brief=brief,scenario=scenario)),media_type='application/json',headers={'Content-Disposition':'attachment; filename="procureiq_evidence.json"'})
    payload=presentation_bytes(brief,scenario)
    # Attach attributed analyst context as editable speaker notes, retaining the five-slide engine.
    if brief['investigation_context']:
        from io import BytesIO
        from pptx import Presentation
        prs=Presentation(BytesIO(payload));prs.slides[4].notes_slide.notes_text_frame.text+='\nAnalyst-recorded investigation context (not verified savings):\n'+canonical(brief['investigation_context'])
        buf=BytesIO();prs.save(buf);payload=buf.getvalue()
    return Response(payload,media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',headers={'Content-Disposition':'attachment; filename="procureiq_executive.pptx"'})
