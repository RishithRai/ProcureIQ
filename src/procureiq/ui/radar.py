from decimal import Decimal
import streamlit as st
from procureiq.ui import charts
from procureiq.ui.components import chart,table,evidence_table
from procureiq.ui.formatting import money

LABELS={'supplier_concentration':'Supplier concentration','purchasing_fragmentation':'Purchasing fragmentation',
        'payment_pattern':'Payment pattern','data_quality':'Data quality'}


def render(service,filters,version,config):
    with st.spinner('Evaluating review opportunities from the selected population…'):
        result=service.opportunities(filters,version,config)
    st.warning('Investigation candidates only. Positive expenditure exposure is not estimated savings. Reviews overlap: never sum their exposures into a portfolio savings figure.')
    if filters['supplier_id'] is not None:
        st.info('Concentration detection is suppressed for a supplier-filtered population: selecting one supplier makes concentration trivial.')
    qualified=sum(result['qualified_before_cap'].values())
    exported=sum(result['counts_by_type'].values())
    a,b,c=st.columns(3)
    a.metric('Exported review opportunities',exported)
    b.metric('Qualified before output caps',qualified)
    c.metric('Deferred by output caps',qualified-exported)
    st.caption(f'Counts above apply to the sidebar population before the display controls below. Up to {config.max_per_type} reviews per detector; policy and scores are configurable analyst review rules.')
    st.dataframe([{'Detector':LABELS[k],'Qualified':result['qualified_before_cap'][k],'Exported':v} for k,v in result['counts_by_type'].items()],hide_index=True,width='stretch')
    a,b=st.columns([2,3])
    requested=st.session_state.pop('_executive_review',None)
    if requested and any(o['opportunity_id']==requested for o in result['opportunities']):
        st.session_state['radar_type']=None
        st.session_state['radar_minimum']=0
        st.session_state['radar_selected']=requested
    kind=a.selectbox('Review type',[None]+list(LABELS),format_func=lambda v:LABELS.get(v,'All review types'),key='radar_type')
    minimum=b.slider('Minimum priority',0,100,0,key='radar_minimum')
    items=[r for r in result['opportunities'] if (kind is None or r['opportunity_type']==kind) and r['scoring']['priority_score']>=Decimal(minimum)]
    if not items:
        st.info('No eligible reviews for these filters and display controls. Short periods can fail history requirements; broaden the selection or lower the display minimum.')
        with st.expander('Exclusion reasons'):st.json(result['rejection_counts'])
        return
    st.caption(f'{len(items)} reviews shown · scores and backend ordering are unchanged by these display controls.')
    chart(charts.scores(items),'radar_scores')
    table([dict(rank=i+1,title=o['title'],review_type=LABELS[o['opportunity_type']],
        priority=o['scoring']['priority_score'],positive_exposure_gbp=o['positive_exposure_gbp']) for i,o in enumerate(items)],'radar_ranking','Ranked reviews')
    lookup={o['opportunity_id']:o for o in items}
    chosen=st.selectbox('Inspect opportunity',list(lookup),format_func=lambda i:lookup[i]['title'],key='radar_selected')
    item=lookup[chosen]
    with st.expander('Opportunity detail workspace',expanded=True):
        st.subheader(item['title'])
        from procureiq.ui.scenarios import start_from_review
        st.button('Start a scenario from this review',on_click=start_from_review,args=(item,filters,version))
        st.caption(LABELS[item['opportunity_type']]+' · '+item['opportunity_id'])
        a,b=st.columns(2)
        a.metric('Positive expenditure exposure',money(item['positive_exposure_gbp']))
        b.metric('Investigation priority /100',f"{item['scoring']['priority_score']:.2f}")
        st.caption(item['exposure_definition'])
        st.markdown('**Observed evidence**');st.write(item['evidence_summary'])
        a,b=st.columns([1,1])
        with a:
            st.markdown('**Score contributions**');chart(charts.contributions(item),'radar_components')
        with b:
            for name,value in item['scoring']['components'].items():
                st.write(f'{name.capitalize()}: {value:.4f} / 1 · {item["scoring"]["weighted_points"][name]:.2f} weighted points')
            st.caption('Evidence completeness measures traceability and rule-specific coverage, not probability of inefficiency or confidence that savings exist.')
            st.write(item['scoring']['signal_formula']);st.write(item['scoring']['evidence_formula'])
        st.markdown('**Procurement hypothesis**');st.write(item['business_interpretation'])
        st.markdown('**Recommended investigation**');st.write(item['next_investigation_step'])
        category=item['scope'].get('expense_type')
        if category is not None:
            context_filters=dict(filters,expense_type=category)
            context=service.analytics(context_filters,version,('monthly',))
            st.markdown('**Category payment context**')
            st.caption('Positive payments for this category within the sidebar population. This context may extend beyond a flagged payment window or quality-affected rows; it is not an additional exposure.')
            chart(charts.trend(context['monthly']),'radar_context')
        st.markdown('**Affected suppliers and purchasing areas**')
        st.write(', '.join(s['normalized_key'] for s in item['affected_suppliers']) or 'Unresolved supplier identities')
        st.write(', '.join(item['affected_areas']) or 'No named purchasing areas')
        with st.expander('Supporting numerical metrics'):st.json(item['metrics'],expanded=False)
        evidence_table(service,filters,version,item,config)
        st.markdown('**Limitations**')
        for caveat in item['caveats']:st.write('• '+caveat)
    with st.expander('Data basis, policy and exclusion audit'):
        st.json({'basis':result['basis'],'configuration':result['configuration'],'rejections':result['rejection_counts']},expanded=False)
