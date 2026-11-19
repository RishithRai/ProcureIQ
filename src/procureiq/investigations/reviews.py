"""Framework-independent adapter to the single existing opportunity engine."""
from dataclasses import asdict
from hashlib import sha256
from procureiq.opportunities import detect,canonical
from procureiq.opportunity_data import retrieve
from procureiq.opportunity_model import OpportunityConfig,RULE_VERSION
from procureiq.queries import validate_filters
from procureiq.source_basis import fingerprint
from .domain import InvestigationError


def digest(value):return sha256(canonical(value).encode()).hexdigest()


def context(conn,filters,config):
    filters=validate_filters(filters)
    version=fingerprint(conn)
    configuration_identity=digest(asdict(config))
    basis=dict(source_fingerprint=version,rule_version=RULE_VERSION,configuration_identity=configuration_identity,filters=filters)
    return basis,digest(basis)


def resolve(conn,filters,config):
    basis,token=context(conn,filters,config)
    result=detect(retrieve(conn,basis['filters']),config)
    return result,basis,token


def find_review(result,review_id):
    item=next((o for o in result['opportunities'] if o['opportunity_id']==review_id),None)
    if item:return item
    if any(r.get('opportunity_id')==review_id and r['reason']=='output_cap_after_scoring' for r in result['rejections']):
        raise InvestigationError('review_not_eligible','This review is deferred by the output cap and cannot create a case.')
    raise InvestigationError('review_not_found','No current exported review has that reference in this population.',404)


def review_key(item,basis):return digest(dict(opportunity_id=item['opportunity_id'],**basis))


def summary(item):
    return {key:item[key] for key in ('opportunity_id','opportunity_type','title','scope','positive_exposure_gbp','evidence_summary')} | dict(
        priority_score=item['scoring']['priority_score'],primary_count=len(item['source_references']),contextual_count=len(item['context_source_references']))
