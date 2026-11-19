"""Scenario lab rendering; assumptions persist outside Streamlit widget lifecycle."""
from dataclasses import asdict
from decimal import Decimal
import streamlit as st
import plotly.graph_objects as go
from procureiq.financial_model import NAMES,Assumptions,comparison,sensitivity,break_even,illustrative
from procureiq.scenario_basis import database_baseline,manual_baseline,is_stale,refresh_baseline
from procureiq.scenario_io import document,export_json,load_json,validate_database_claim,canonical
from procureiq.scenario_excel import workbook_bytes
from procureiq.ui.formatting import money,display_rows,csv_bytes
from procureiq.ui.components import chart
from procureiq.ui.charts import style

D=Decimal
FIELDS=('addressable_pct','adoption_pct','improvement_pct','implementation_cost','operating_cost')
LABELS=('Addressable expenditure (%)','Adoption (%)','Improvement (%)','Implementation cost (£)','Operating cost for period (£)')


def start_from_review(item,filters,version):
    from procureiq.scenario_basis import opportunity_request
    st.session_state['_scenario_request']=opportunity_request(item,filters,version)
    st.session_state['navigation']='Financial Scenario Lab'


def set_cases(cases):
    st.session_state['_scenario_drafts']={n:{k:str(v) for k,v in asdict(cases[n]).items()} for n in NAMES}
    st.session_state['_scenario_epoch']=st.session_state.get('_scenario_epoch',0)+1


def save_input(name,field,key):
    st.session_state['_scenario_drafts'][name][field]=str(st.session_state[key])


def bind_baseline(baseline):
    st.session_state['_scenario_baseline']=baseline


def render(service,filters,version,options):
    if '_scenario_drafts' not in st.session_state:set_cases({n:Assumptions() for n in NAMES})
    st.warning('Hypothetical same-period benefits only. One expenditure pool, three alternative cases. Results are not predicted or realized savings and must not be added across overlapping opportunities.')
    with st.expander('Load a saved scenario configuration'):
        uploaded=st.file_uploader('Scenario JSON',type='json',max_upload_size=2,key='scenario_upload')
        if st.button('Load scenario JSON',disabled=uploaded is None):
            try:
                doc,cases=load_json(uploaded.getvalue())
                validate_database_claim(service,doc['baseline'],version)
                bind_baseline(doc['baseline']);set_cases(cases)
                st.session_state['_scenario_sensitivity']=dict(doc['sensitivity'],custom_axes=True)
                st.session_state['scenario_sensitivity_case']=doc['sensitivity']['selected']
                st.success('Configuration loaded. Saved outputs were independently recomputed from its assumptions.')
            except ValueError as exc:st.error(str(exc))
    st.subheader('A. Define one expenditure pool')
    request=st.session_state.get('_scenario_request')
    modes=['Current filtered population','Expense category','User-supplied baseline']
    if request:
        st.info(request['title']+' — '+request['note'])
        if request['eligible'] and request['source_fingerprint']==version:modes.insert(0,'Selected review category')
        elif request['source_fingerprint']!=version:st.warning('The originating review uses an older source version. Choose a fresh pool explicitly.')
    mode=st.selectbox('Baseline source',modes,key='scenario_source')
    preview=None
    try:
        if mode=='User-supplied baseline':
            amount=st.text_input('User-supplied positive baseline (£)','0.00',key='scenario_manual_amount')
            scope=st.text_input('Describe this user-supplied pool',key='scenario_manual_scope')
            st.caption('Period follows the sidebar range. This amount is not HMRC-verified; credits, net and source-row counts are unavailable.')
            selected_period=st.session_state.get('filter_period',(options['months'][0],options['months'][-1]))
            preview=manual_baseline(amount,selected_period[0],selected_period[1],scope)
        elif mode=='Selected review category':
            preview=database_baseline(service,request['filters'],version,request['category'],origin=request)
        elif mode=='Expense category':
            groups=service.analytics(filters,version,('expense_types',))['expense_types']
            categories=[r['group_value'] for r in groups if r['group_value'] is not None]
            if categories:
                category=st.selectbox('Single expense category',categories,key='scenario_category')
                preview=database_baseline(service,filters,version,category)
            else:st.info('No named expense category is available in this selection.')
        else:preview=database_baseline(service,filters,version)
    except ValueError as exc:st.info(str(exc))
    if preview:
        st.write(f"Proposed pool: **{preview['scope']}** · **{money(preview['amount_gbp'])} positive expenditure**")
        st.caption(preview['period_label'])
        if st.button('Use selected baseline',type='primary'):bind_baseline(preview)
    baseline=st.session_state.get('_scenario_baseline')
    if baseline is None:
        st.info('Select and use one baseline to start. All benefit assumptions begin at zero.');return
    if is_stale(baseline,version):
        st.error('Saved HMRC baseline is stale. Calculations and exports are suspended until you explicitly review the current source version.')
        current=refresh_baseline(service,baseline,version)
        st.write(f"Saved positive baseline: {money(baseline['amount_gbp'])}; current same-scope baseline: {money(current['amount_gbp'])}.")
        st.caption(f"Saved fingerprint {baseline['source_fingerprint']} · Current fingerprint {version}")
        if st.button('Review complete — use current source version'):
            bind_baseline(current);st.rerun()
        return
    with st.container(border=True):
        st.markdown('**Bound scenario baseline**')
        st.write(baseline['scope']+' · '+baseline['period_label'])
        a,b,c,d=st.columns(4)
        a.metric('Baseline positive expenditure',money(baseline['amount_gbp']))
        population=baseline['population'] or {}
        b.metric('Published credit magnitude',money(population.get('credit_gbp')))
        c.metric('Published net payments',money(population.get('net_gbp')))
        d.metric('Source lines',f"{population['record_count']:,}" if population else 'User-supplied')
        st.caption(baseline['limitation'])
        st.caption('Source fingerprint: '+(baseline['source_fingerprint'] or 'None — user-supplied baseline'))
        if baseline['kind']=='hmrc':
            if canonical(filters)!=canonical(baseline['filters']):st.info('Scenario scope differs from the sidebar population. The bound pool and assumptions are retained; use a new baseline explicitly to replace it.')
            st.caption(f"Covered source months: {baseline['covered_months']}. Missing source months do not represent zero spending.")
            if population.get('unparsed_amounts'):st.warning('Unparsed amounts are excluded from this disclosed positive baseline.')
        st.caption('Addressability must account for VAT treatment, contractual constraints and ineligible expenditure. Costs and benefits must use a comparable VAT basis. No automatic VAT adjustment is made.')
    st.subheader('B. Enter independent assumptions')
    left,right=st.columns(2)
    left.button('Reset scenario assumptions to zero',on_click=set_cases,args=({n:Assumptions() for n in NAMES},))
    right.button('Load illustrative examples (not validated rates)',on_click=set_cases,args=(illustrative(),))
    epoch=st.session_state['_scenario_epoch']
    for column,name in zip(st.columns(3),NAMES):
        with column,st.container(border=True):
            st.markdown('#### '+name)
            for field,label in zip(FIELDS,LABELS):
                key=f'scenario_edit_{epoch}_{name}_{field}'
                draft=st.session_state['_scenario_drafts'][name][field]
                if field.endswith('_pct'):
                    st.number_input(label,min_value=0.0,max_value=100.0,value=float(draft),step=1.0,format='%.4f',key=key,
                        on_change=save_input,args=(name,field,key))
                else:
                    st.text_input(label,value=draft,key=key,on_change=save_input,args=(name,field,key),help='Nonnegative GBP, up to two decimal places. No currency symbol or commas.')
    st.button('Recalculate scenarios')
    try:cases={n:Assumptions(**st.session_state['_scenario_drafts'][n]) for n in NAMES}
    except ValueError as exc:st.error(str(exc));return
    results=comparison(baseline['amount_gbp'],cases)
    st.subheader('C. Same-period hypothetical outputs')
    for col,name in zip(st.columns(3),NAMES):
        with col,st.container(border=True):
            st.markdown('#### '+name)
            st.metric('Net hypothetical benefit',money(results[name]['net_benefit_gbp']))
            st.metric('Gross hypothetical benefit',money(results[name]['gross_benefit_gbp']))
            roi=results[name]['roi_pct'];st.metric('ROI','Unavailable — zero costs' if roi is None else f'{roi:,.2f}%')
    st.subheader('D. Scenario comparison')
    rows=[dict(scenario=n,**asdict(cases[n]),**results[n]) for n in NAMES]
    st.dataframe(display_rows(rows),hide_index=True,width='stretch')
    chart(style(go.Figure([go.Bar(name=label,x=list(NAMES),y=[float(results[n][key]) for n in NAMES])
        for label,key in [('Gross benefit','gross_benefit_gbp'),('Total costs','total_costs_gbp'),('Net benefit','net_benefit_gbp')]]).update_layout(barmode='group',yaxis_title='Hypothetical same-period GBP')),'scenario_comparison')
    st.subheader('E. Sensitivity and break-even')
    saved=st.session_state.get('_scenario_sensitivity',{})
    selected=st.selectbox('Sensitivity scenario',NAMES,index=NAMES.index(saved.get('selected','Base')),key='scenario_sensitivity_case')
    upper=st.selectbox('Improvement axis maximum (%)',[10,25,50,100],key='scenario_axis_max')
    # Preserve imported axes until the user explicitly resets/changes the grid.
    if saved and saved.get('custom_axes',False):
        ads=[D(str(v)) for v in saved['adoption_values']];imps=[D(str(v)) for v in saved['improvement_values']]
        st.caption('Using sensitivity axes from the loaded JSON configuration.')
        if st.button('Use standard sensitivity axes'):st.session_state['_scenario_sensitivity']={};st.rerun()
    else:
        ads=sorted(set([D(i) for i in range(0,101,10)]+[cases[selected].adoption_pct]))
        imps=sorted(set([D(upper)*D(i)/10 for i in range(11)]+[cases[selected].improvement_pct]))
    st.session_state['_scenario_sensitivity']=dict(selected=selected,adoption_values=ads,improvement_values=imps,custom_axes=saved.get('custom_axes',False))
    grid=sensitivity(baseline['amount_gbp'],cases[selected],ads,imps)
    values={(r['adoption_pct'],r['improvement_pct']):r['net_benefit_gbp'] for r in grid}
    z=[[float(values[a,i]) for i in imps] for a in ads];m=max(1,max(abs(v) for row in z for v in row))
    fig=go.Figure(go.Heatmap(x=[float(i) for i in imps],y=[float(a) for a in ads],z=z,zmin=-m,zmax=m,zmid=0,
        colorscale=[[0,'#BD4B46'],[.5,'#F6F8FB'],[1,'#237B60']],colorbar=dict(title='Net GBP'),
        hovertemplate='Adoption %{y}%<br>Improvement %{x}%<br>Net £%{z:,.2f}<extra></extra>'))
    boundary=[(float(break_even(baseline['amount_gbp'],cases[selected],a)['improvement_pct']),float(a)) for a in ads
              if break_even(baseline['amount_gbp'],cases[selected],a)['improvement_pct'] is not None
              and 0<=break_even(baseline['amount_gbp'],cases[selected],a)['improvement_pct']<=max(imps)]
    if boundary:fig.add_trace(go.Scatter(x=[x for x,y in boundary],y=[y for x,y in boundary],mode='lines+markers',name='Unrounded break-even',line=dict(color='#172E50',dash='dash')))
    chart(style(fig,430).update_layout(xaxis_title='Assumed improvement (%)',yaxis_title='Assumed adoption (%)'),'scenario_sensitivity')
    be=break_even(baseline['amount_gbp'],cases[selected])
    st.write('Break-even at selected adoption: '+(f"{be['improvement_pct']:.4f}% improvement" if be['improvement_pct'] is not None else 'Unavailable')+'. '+be['reason'])
    st.caption(f"{selected} fixed addressability: {cases[selected].addressable_pct}%. Implementation {money(cases[selected].implementation_cost)} + period operating {money(cases[selected].operating_cost)}. Edit either cost above to shift all cells; each additional £1 reduces net benefit by £1.")
    st.caption('Red is negative, neutral is zero and green is positive. The line is theoretical unrounded break-even; final two-decimal zero outcomes occupy a half-penny band.')
    with st.expander('Numerical sensitivity table'):st.dataframe(display_rows(grid),hide_index=True,width='stretch')
    st.download_button('Download sensitivity CSV',csv_bytes(grid),'scenario_sensitivity.csv','text/csv',on_click='ignore')
    st.subheader('F. Methodology, provenance and exports')
    doc=document(baseline,cases,selected,ads,imps)
    with st.expander('Assumptions and data basis'):st.json(doc,expanded=False)
    st.caption('Unrounded Decimal products feed final money rounded HALF_UP to pennies. ROI uses rounded net / total costs and is unavailable at zero cost. No rates are inferred from procurement scores. No annualization or recurrence assumption is applied.')
    st.download_button('Download scenario JSON',export_json(doc),'procureiq_scenarios.json','application/json',on_click='ignore')
    if st.button('Prepare Excel financial model'):
        with st.spinner('Building formula-linked workbook…'):payload=workbook_bytes(doc)
        st.download_button('Download Excel financial model',payload,'procureiq_scenario_model.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',on_click='ignore')
        st.caption('Excel formulas are live. Initial caches come from Python; recalculate in Excel after editing. The JSON preserves exact Decimal results.')
