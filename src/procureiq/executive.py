"""Deterministic management interpretation of existing verified outputs."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from procureiq.opportunities import canonical
from procureiq.queries import validate_filters
from procureiq.scenario_io import load_json, export_json, validate_database_claim

POLICY_VERSION = 'theme_diversity_v1'
ATTRIBUTION = 'HMRC published spending-over-£25,000 disclosures (gross, VAT-inclusive)'
DATASET_URL = 'https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc'
THEMES = {
 'supplier_concentration': ('Supplier dependency', 'Review contract resilience and continuity arrangements with the category owner; assess feasible sourcing alternatives.', 'Contract scope and expiry dates, continuity plans, framework terms and evidence of qualified alternatives.', 'Observed payment concentration is not market concentration or proof of inefficient procurement.'),
 'purchasing_fragmentation': ('Purchasing coordination', 'Ask purchasing-area owners to compare specifications and buying arrangements before considering coordinated sourcing.', 'Comparable service specifications, contract rates, purchasing authority and existing framework agreements.', 'Multiple suppliers do not establish interchangeable services or guaranteed consolidation benefits.'),
 'payment_pattern': ('Payment timing', 'Reconcile the highlighted payment period to invoicing cycles, contractual milestones and credit adjustments.', 'Invoices, milestone schedules, accrual explanations and the corresponding credit notes.', 'Payment variation does not establish fraud, financial misstatement or overpayment.'),
 'data_quality': ('Source and supplier records', 'Review flagged source records and supplier identifiers against supporting documents before proposing corrections.', 'Original invoices, source ledger records and independently verified supplier identity documentation.', 'Retain duplicate candidates and supplier identities pending evidence; do not automatically delete or merge.')
}


def reference_key(ref):
    return ref['sha256'], ref['source_record_number']


def recommend(opportunities):
    """One candidate per available theme. Preserve priority; disclose all intersections."""
    ranked=sorted(opportunities,key=lambda o:(-Decimal(o['scoring']['priority_score']),-Decimal(o['positive_exposure_gbp']),o['opportunity_id']))
    selected=[]
    themes=list(dict.fromkeys(o['opportunity_type'] for o in ranked))
    for theme in themes:
        if theme not in THEMES:raise ValueError('Unsupported review theme')
        candidates=[o for o in ranked if o['opportunity_type']==theme]
        def duplicates_previous(item):
            keys={reference_key(r) for r in item['source_references']}
            for previous in selected:
                other={reference_key(r) for r in previous['source_references']}
                denominator=min(len(keys),len(other))
                if denominator and 5*len(keys & other)>=4*denominator:return True
            return False
        # 80% containment is a transparent selection guard, not a new priority score.
        selected.append(next((o for o in candidates if not duplicates_previous(o)),candidates[0]))
    selected.sort(key=lambda o:(-Decimal(o['scoring']['priority_score']),-Decimal(o['positive_exposure_gbp']),o['opportunity_id']))
    result=[]
    for item in selected:
        title,action,required,caution=THEMES[item['opportunity_type']]
        refs=item['source_references']
        keys={reference_key(r) for r in refs}
        overlaps=[]
        for other in selected:
            if other is item:continue
            count=len(keys & {reference_key(r) for r in other['source_references']})
            if count:overlaps.append(dict(opportunity_id=other['opportunity_id'],shared_primary_rows=count))
        result.append(dict(reference='REC-'+sha256((POLICY_VERSION+item['opportunity_id']).encode()).hexdigest()[:16],
            title=f"{title}: {item['scope'].get('expense_type') or 'selected population'}",
            opportunity_type=item['opportunity_type'],observed_evidence=item['evidence_summary'],
            positive_exposure_gbp=item['positive_exposure_gbp'],exposure_definition=item['exposure_definition'],
            measurements=deepcopy(item['metrics']),priority_score=item['scoring']['priority_score'],
            business_interpretation=item['business_interpretation'],recommended_action=action,evidence_required=required,
            opportunity_ids=[item['opportunity_id']],source_references=deepcopy(refs),
            context_source_references=deepcopy(item['context_source_references']),overlaps=overlaps,
            caveats=list(dict.fromkeys([caution]+item['caveats']))))
    return result


def findings(data):
    result=[]
    ranking=data['suppliers']; categories=data['expense_types']; c=data['concentration'][0] if data['concentration'] else {}
    if ranking and ranking[0]['positive_gbp']>0:
        s=ranking[0]
        result.append(f"{s['canonical_name']} leads observed supplier payments at £{s['positive_gbp']:,.2f}, {s['share_all_positive_pct']:.2f}% of selected positive payments.")
    if categories:
        r=categories[0]
        result.append(f"{r['group_value'] or 'Unclassified expense'} is the largest expense category at £{r['positive_gbp']:,.2f} positive payments.")
    if c.get('suppliers_to_80') is not None:
        result.append(f"{c['suppliers_to_80']} of {c['positive_supplier_count']} positive-payment suppliers account for at least 80% of resolved positive payments.")
    if c.get('hhi') is not None:
        result.append(f"Observed supplier HHI is {c['hhi']:,.2f}; the top three suppliers represent {c['top_three_pct']:.2f}% of resolved positive payments. This does not establish procurement inefficiency.")
    return result


def compatible_scenario(service, brief, doc):
    """Validate both arithmetic and current database evidence, then enforce scope inclusion."""
    doc,_=load_json(export_json(doc))
    b=doc['baseline']
    if b['kind']!='hmrc':raise ValueError('Executive illustrations require an HMRC-linked pool with verifiable scope.')
    if b['source_fingerprint']!=brief['source_fingerprint']:raise ValueError('Scenario source is stale. Review it in Financial Scenario Lab.')
    validate_database_claim(service,b,brief['source_fingerprint'])
    if (b['start_month'],b['end_month'])!=(brief['start_month'],brief['end_month']):raise ValueError('Scenario reporting period does not match this brief.')
    f=validate_filters(brief['filters']); sf=validate_filters(b['filters'])
    for key in ('expense_area','entity','supplier_id'):
        if f[key]!=sf[key]:raise ValueError('Scenario filters do not match this brief.')
    if f['expense_type'] is not None and f['expense_type']!=sf['expense_type']:
        raise ValueError('Scenario category does not match this brief.')
    # An explicitly selected category subset is allowed in a broader population.
    return doc


def build_brief(data,radar,basis,filters,version):
    months=data['monthly']
    if not months:raise ValueError('No active reporting calendar')
    qualified=sum(radar['qualified_before_cap'].values()); exported=sum(radar['counts_by_type'].values())
    return dict(policy_version=POLICY_VERSION,source_fingerprint=version,filters=validate_filters(filters),basis=basis,
        start_month=str(months[0]['reporting_month']),end_month=str(months[-1]['reporting_month']),
        period=f"{months[0]['reporting_month']:%b %Y} – {months[-1]['reporting_month']:%b %Y}",
        covered_months=sum(r['source_available'] for r in months),analytics=data,
        overview=data['overview'][0] if data['overview'] else dict(positive_gbp=Decimal('0.00'),credit_gbp=Decimal('0.00'),net_gbp=Decimal('0.00'),record_count=0,supplier_count=0),
        counts=dict(qualified=qualified,exported=exported,deferred=qualified-exported),
        counts_by_type=radar['counts_by_type'],qualified_by_type=radar['qualified_before_cap'],
        findings=findings(data),recommendations=recommend(radar['opportunities']),
        attribution=ATTRIBUTION,dataset_url=DATASET_URL,
        caveat='Published payments are a disclosure subset, not complete procurement expenditure. Investigation exposures overlap and must not be summed as savings.')


def export_default(service,root,scenario_path=None,output=None):
    from pathlib import Path
    from procureiq.financial_model import illustrative
    from procureiq.scenario_basis import database_baseline
    from procureiq.scenario_io import document
    from procureiq.executive_presentation import presentation_bytes
    version=service.version()
    brief=service.executive({},version)
    if scenario_path:
        doc,_=load_json(Path(scenario_path).read_bytes())
    else:
        b=database_baseline(service,{},version,category='PROJECT Mandays Supp')
        doc=document(b,illustrative())
    doc=compatible_scenario(service,brief,doc)
    payload=presentation_bytes(brief,doc)
    destination=Path(output) if output else Path(root)/'deliverables/procureiq_executive_review.pptx'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(payload)
    evidence=destination.with_suffix('.evidence.json')
    evidence.write_text(canonical(dict(brief=brief,scenario=doc)),encoding='utf-8')
    return dict(presentation=str(destination),evidence=str(evidence),slides=5,source_fingerprint=version,counts=brief['counts'])
