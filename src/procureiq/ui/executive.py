"""Executive Brief presentation layer; all calculations stay in reusable engines."""
from hashlib import sha256
import streamlit as st
from procureiq.executive import compatible_scenario
from procureiq.executive_presentation import presentation_bytes
from procureiq.financial_model import Assumptions,NAMES
from procureiq.scenario_io import document,canonical
from procureiq.ui.formatting import money,display_rows


def navigate(page):st.session_state['navigation']=page


def inspect_review(opportunity_id):
    st.session_state['_executive_review']=opportunity_id
    st.session_state['navigation']='Opportunity Radar'


def render(service,filters,version,config):
    brief=service.executive(filters,version,config)
    st.subheader('Executive summary')
    st.write(f"The {brief['period']} selection contains {brief['overview']['record_count']:,} published lines and {money(brief['overview']['positive_gbp'])} positive disclosed payments. All findings below use the current sidebar filters.")
    a,b,c=st.columns(3)
    for col,label,key in [(a,'Qualified review candidates','qualified'),(b,'Exported reviews','exported'),(c,'Deferred by caps','deferred')]:col.metric(label,brief['counts'][key])
    if brief['analytics']['concentration']:
        row=brief['analytics']['concentration'][0]
        st.caption(f"Observed HHI: {row['hhi']:,.2f} · Top-three share of resolved positives: {row['top_three_pct']:.2f}%" if row['hhi'] is not None else 'No positive resolved-supplier denominator for concentration.')
    st.subheader('Key analytical findings')
    for finding in brief['findings']:st.write('• '+finding)
    if not brief['findings']:st.info('No analytical findings for this population. Reset Filters or broaden the selection.')
    st.subheader('Management recommendations')
    st.caption('One review per eligible theme, using existing scores and materiality. Overlap controls avoid near-duplicate evidence where alternatives exist; all remaining overlap is disclosed. These are investigation priorities, not validated savings.')
    if not brief['recommendations']:st.info('No eligible recommendations. Short history or materiality rules can exclude review candidates.')
    for i,r in enumerate(brief['recommendations'],1):
        with st.expander(f"{i}. {r['title']}",expanded=i==1):
            st.caption(f"{r['reference']} · priority {r['priority_score']:.2f}/100 · positive exposure {money(r['positive_exposure_gbp'])}")
            for heading,key in [('Observed evidence','observed_evidence'),('Business interpretation','business_interpretation'),('Recommended action','recommended_action'),('Evidence required','evidence_required')]:
                st.markdown('**'+heading+'**');st.write(r[key])
            st.caption(r['exposure_definition'])
            if r['overlaps']:
                st.warning('Shared primary source rows: '+ '; '.join(f"{x['shared_primary_rows']:,} with {x['opportunity_id']}" for x in r['overlaps'])+'. Do not add these exposures.')
            for caveat in r['caveats']:st.caption(caveat)
            st.button('Inspect this review in Opportunity Radar',key='executive_review_'+r['reference'],on_click=inspect_review,args=(r['opportunity_ids'][0],))
            with st.expander('Supporting measurements and source sample'):
                st.json(r['measurements'],expanded=False)
                st.dataframe(display_rows(r['source_references'][:5]),hide_index=True,width='stretch')
                st.caption(f"{len(r['source_references']):,} complete primary references available through Radar evidence download.")
    st.subheader('Financial illustration')
    candidate=None; chosen=None
    baseline=st.session_state.get('_scenario_baseline')
    drafts=st.session_state.get('_scenario_drafts')
    if baseline and drafts:
        try:
            candidate=compatible_scenario(service,brief,document(baseline,{n:Assumptions(**drafts[n]) for n in NAMES}))
        except ValueError as exc:st.warning(str(exc))
    if candidate:
        key=sha256(canonical([candidate,filters,version]).encode()).hexdigest()[:20]
        if st.checkbox('Include this reviewed scenario in the brief and presentation',key='executive_scenario_'+key):
            chosen=candidate
            st.warning('Hypothetical financial illustration, not predicted or realized savings. Cases are alternatives and must not be added.')
            st.write(candidate['baseline']['scope']+' · '+candidate['baseline']['period_label'])
            st.write('Baseline positive expenditure: '+money(candidate['baseline']['amount_gbp']))
            rows=[]
            for label,field in [('Addressability','addressable_pct'),('Adoption','adoption_pct'),('Improvement','improvement_pct')]:
                rows.append(dict(Measure=label,**{n:f"{candidate['scenarios'][n][field]}%" for n in NAMES}))
            for label,field in [('Implementation cost','implementation_cost_gbp'),('Same-period operating cost','operating_cost_gbp'),('Gross hypothetical benefit','gross_benefit_gbp'),('Net hypothetical benefit','net_benefit_gbp')]:
                rows.append(dict(Measure=label,**{n:money(candidate['outputs'][n][field]) for n in NAMES}))
            rows.append(dict(Measure='ROI',**{n:('Unavailable — zero costs' if candidate['outputs'][n]['roi_pct'] is None else f"{candidate['outputs'][n]['roi_pct']:.2f}%") for n in NAMES}))
            st.dataframe(rows,hide_index=True,width='stretch')
    else:st.info('No valid matching scenario is available. Define a pool and assumptions in Financial Scenario Lab; stale sources require explicit review there.')
    st.button('Open Financial Scenario Lab',on_click=navigate,args=('Financial Scenario Lab',))
    st.subheader('Evidence and limitations')
    st.write(brief['caveat'])
    st.markdown(f"[{brief['attribution']}]({brief['dataset_url']})")
    st.caption('Period: '+brief['period']+' · active source fingerprint: '+version)
    st.caption('Analytical methods: positive-payment denominators, resolved-supplier HHI and Pareto. Opportunity priorities use the unchanged materiality, signal and evidence policy. Scenario benefits use explicit Decimal assumptions with HALF_UP penny rounding and no annualization.')
    with st.expander('Methods and complete reporting basis'):
        st.write('Repository documentation: docs/analytical_methodology.md; docs/opportunity_methodology.md; docs/financial_scenario_methodology.md; docs/executive_methodology.md.')
        st.json(dict(filters=brief['filters'],basis=brief['basis']),expanded=False)
    if st.button('Prepare executive PowerPoint'):
        payload=presentation_bytes(brief,chosen)
        # Recheck before exposing a download created from the snapshot.
        if service.version()!=version:
            from procureiq.ui.service import SourceChanged
            raise SourceChanged('Source changed')
        st.download_button('Download executive PowerPoint',payload,'procureiq_executive_review.pptx','application/vnd.openxmlformats-officedocument.presentationml.presentation',on_click='ignore')
