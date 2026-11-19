"""Orchestrate pure detectors, validate evidence and keep all database access read-only."""
import json
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from sqlalchemy import text
from .opportunity_model import OpportunityConfig, RULE_VERSION, score
from .opportunity_data import retrieve
from .opportunity_detectors import category_detectors, payment_detector, quality_detector
from .queries import validate_filters
from .analytics import amounts, require

TYPES = ('supplier_concentration','purchasing_fragmentation','payment_pattern','data_quality')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str, ensure_ascii=False)


def opportunity_id(kind, scope, basis, cfg):
    stable_sources = [(str(s['reporting_month']),s['sha256']) for s in basis['sources']]
    payload = dict(rule_version=RULE_VERSION, opportunity_type=kind, scope=scope,
                   filters=basis['filters'], source_versions=stable_sources, configuration=asdict(cfg))
    return 'opp_' + sha256(canonical(payload).encode()).hexdigest()[:24]


def assemble(candidate, data, cfg):
    selected = set(candidate.row_ids)
    rows = [r for r in data['lines'] if r['raw_row_id'] in selected]
    if len(selected) != len(rows):
        raise ValueError('Candidate includes nonexistent or out-of-filter evidence')
    exposure = amounts(rows)['positive_gbp']
    scoring = score(exposure,candidate.signal,candidate.evidence,cfg)
    refs = [data['references'][r['raw_row_id']] for r in rows]
    refs.sort(key=lambda r:(r['reporting_month'],r['sha256'],r['source_record_number']))
    suppliers = {r['supplier_id']:r['normalized_key'] for r in rows if r['supplier_id'] is not None}
    context = set()
    if candidate.opportunity_type == 'data_quality':
        alias_names = {name for group in candidate.metrics['alias_candidates'] for name in group['original_names']}
        contextual_keys = {(r['file_id'],r['transaction_number']) for r in rows
                           if 'identifier_context_review' in candidate.metrics['source_flags'][str(r['raw_row_id'])]}
        context = {r['raw_row_id'] for r in data['lines'] if r['supplier_raw'] in alias_names or (r['file_id'],r['transaction_number']) in contextual_keys} - selected
    return dict(opportunity_id=opportunity_id(candidate.opportunity_type,candidate.scope,data['basis'],cfg),
        opportunity_type=candidate.opportunity_type,title=candidate.title,scope=candidate.scope,
        affected_suppliers=[dict(supplier_id=sid,normalized_key=key) for sid,key in sorted(suppliers.items(),key=lambda item:(item[1],item[0]))],
        affected_areas=sorted({r['expense_area'] for r in rows if r['expense_area']}),
        positive_exposure_gbp=exposure,exposure_definition=candidate.exposure_definition,
        metrics=candidate.metrics,scoring=dict(scoring, signal_formula=candidate.signal_formula,evidence_formula=candidate.evidence_formula),
        evidence_confidence='stronger_evidence' if scoring['components']['evidence']>=Decimal('0.8') else 'limited_evidence',
        confidence_meaning='Rule-based completeness/traceability label, not probability of inefficiency or benefit.',
        evidence_summary=candidate.evidence_summary,business_interpretation=candidate.business_interpretation,
        caveats=candidate.caveats+['Opportunities can overlap; do not add their exposures or interpret exposure as savings.'],
        next_investigation_step=candidate.next_step,
        source_references=refs,context_source_references=[data['references'][rid] for rid in sorted(context)],
        rule_version=RULE_VERSION,basis=data['basis'],configuration=asdict(cfg))


def detect(data, cfg=None):
    cfg = cfg or OpportunityConfig()
    raw, rejected = [],[]
    for detector in (category_detectors,payment_detector,quality_detector):
        candidates, exclusions = detector(data,cfg)
        raw.extend(candidates); rejected.extend(exclusions)
    candidates = [assemble(c,data,cfg) for c in raw]
    candidates.sort(key=lambda c:(-c['scoring']['priority_score'],c['opportunity_id']))
    kept,counts = [],Counter()
    for c in candidates:
        kind = c['opportunity_type']
        if counts[kind] < cfg.max_per_type:
            kept.append(c);counts[kind]+=1
        else:
            rejected.append(dict(opportunity_type=kind,scope=c['scope'],reason='output_cap_after_scoring',
                                 opportunity_id=c['opportunity_id'],priority_score=c['scoring']['priority_score']))
    return dict(rule_version=RULE_VERSION,configuration=asdict(cfg),basis=data['basis'],
                population=dict(record_count=len(data['lines']),**amounts(data['lines'])),
                counts_by_type={kind:counts[kind] for kind in TYPES},
                qualified_before_cap={kind:sum(c['opportunity_type']==kind for c in candidates) for kind in TYPES},
                opportunities=kept,rejections=rejected,
                rejection_counts=dict(sorted(Counter(r['reason'] for r in rejected).items())),
                exposure_warning='Exposures overlap across categories, detector types and payment windows; never sum them as independent savings.')


def verify_result(data, result, cfg):
    rows = {r['raw_row_id']:r for r in data['lines']}
    ids = set()
    for item in result['opportunities']:
        require(item['opportunity_id'] not in ids,'unique opportunity IDs')
        ids.add(item['opportunity_id'])
        require(item['opportunity_id']==opportunity_id(item['opportunity_type'],item['scope'],data['basis'],cfg),'opportunity ID/basis')
        require(item['basis']==data['basis'] and item['configuration']==asdict(cfg),'active version/filter/config basis')
        refs = item['source_references']
        row_ids = {r['raw_row_id'] for r in refs}
        require(len(row_ids)==len(refs),'unique financial evidence rows')
        for ref in refs+item['context_source_references']:
            require(ref['raw_row_id'] in rows and data['references'][ref['raw_row_id']]==ref,'active source evidence resolves')
        exposure = sum((rows[rid]['amount_gbp'] for rid in row_ids if rows[rid]['amount_gbp'] is not None and rows[rid]['amount_gbp']>0),Decimal('0.00'))
        require(exposure==item['positive_exposure_gbp'],'exact independently summed positive exposure')
        s = item['scoring']
        for component in s['components'].values():
            require(0<=component<=1,'bounded score component')
        expected_materiality = min(exposure/cfg.materiality_reference_gbp,Decimal('1'))
        require(s['components']['materiality']==expected_materiality,'materiality formula')
        points = {k:Decimal('100')*v*getattr(cfg,k+'_weight') for k,v in s['components'].items()}
        require(points==s['weighted_points'] and sum(points.values())==s['priority_score'],'weighted priority math')
        require(0<=s['priority_score']<=100,'bounded priority')
        if item['opportunity_type']=='supplier_concentration':
            require(data['filters']['supplier_id'] is None,'supplier-filter safeguard')
        if item['opportunity_type']=='data_quality':
            require(item['metrics']['affected_rows']==len(row_ids),'deduplicated affected rows')
            require(sum(item['metrics']['flag_counts'].values())>=len(row_ids),'quality union, not additive flags')
    require(result['opportunities']==sorted(result['opportunities'],key=lambda c:(-c['scoring']['priority_score'],c['opportunity_id'])),'deterministic order')
    require(all(n<=cfg.max_per_type for n in result['counts_by_type'].values()),'per-type cap')
    rerun = detect(data,cfg)
    require(canonical(result)==canonical(rerun),'deterministic rerun')
    return dict(passed=True,opportunities_checked=len(ids),source_rows=len(rows),
                checks=['active selected source references','exact distinct-row exposures','component bounds and weighted scores',
                        'supplier-filter suppression','quality row union','deterministic IDs/order/rerun','output cap'])


def run(engine, root, command, filters=None, cfg=None, output_dir=None):
    if command not in ('detect','verify','export'):
        raise ValueError('Unknown opportunity command')
    cfg = cfg or OpportunityConfig()
    filters = validate_filters(filters)
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
        with conn.begin():
            conn.exec_driver_sql('SET TRANSACTION READ ONLY')
            data = retrieve(conn,filters)
            result = detect(data,cfg)
            verification = verify_result(data,result,cfg)
            result['verification'] = verification
    if command=='export':
        from .opportunity_reporting import export
        directory = export(root,result,output_dir)
        return dict(directory=str(directory),counts_by_type=result['counts_by_type'],verification=verification)
    if command=='verify':
        return dict(verification=verification,counts_by_type=result['counts_by_type'],population=result['population'],
                    configuration=result['configuration'],basis=result['basis'],rejection_counts=result['rejection_counts'])
    return dict(counts_by_type=result['counts_by_type'],population=result['population'],configuration=result['configuration'],
                rejection_counts=result['rejection_counts'],verification=verification,
                opportunities=[{k:c[k] for k in ('opportunity_id','opportunity_type','title','positive_exposure_gbp','scoring','evidence_summary')}
                               for c in result['opportunities']])
