"""Launch from repository root: streamlit run src/procureiq/ui/app.py."""
import os
from pathlib import Path
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from procureiq.db import engine_from_env
from procureiq.opportunity_model import load_config
from procureiq.ui.service import DashboardService, SourceChanged
from procureiq.ui.formatting import ALL, reset_filters, selected_filters
from procureiq.ui.components import kpis
from procureiq.ui import overview,suppliers,radar,scenarios,executive

st.set_page_config(page_title='ProcureIQ | Procurement intelligence',page_icon='◈',layout='wide',initial_sidebar_state='auto')
st.markdown('''<style>
.block-container {max-width:1600px;padding-top:3.5rem;padding-bottom:3rem;}
h1 {font-weight:650;letter-spacing:-0.04em;} h2,h3 {letter-spacing:-0.025em;}
[data-testid="stMetricValue"] {font-size:clamp(1.02rem,1.65vw,1.8rem);font-variant-numeric:tabular-nums;}
[data-testid="stMetricLabel"] {font-size:0.78rem;}
[data-testid="stMetricLabel"] p {white-space:normal;overflow:visible;}
[data-testid="stSidebar"] {border-right:1px solid #E4E9F0;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:10px;}
@media(max-width:750px){.block-container{padding:3.5rem 1rem 1rem;}[data-testid="stMetricValue"]{font-size:1.35rem;}}
</style>''',unsafe_allow_html=True)


@st.cache_resource(show_spinner=False,max_entries=2)
def service_resource(connection_identity):
    # The credential is hashed, never rendered. Engines are resources, not data-cache values.
    return DashboardService(engine_from_env())


def main():
    import hashlib
    url=os.environ.get('DATABASE_URL','')
    if not url:
        st.error('Database configuration is missing. Export DATABASE_URL as described in docs/dashboard_guide.md, then restart the application.')
        return
    service=service_resource(hashlib.sha256(url.encode()).hexdigest())
    config_path=os.environ.get('PROCUREIQ_OPPORTUNITY_CONFIG')
    config=load_config(Path(config_path)) if config_path else load_config()
    version=service.version()
    options=service.options(version)
    if options['months']:
        st.session_state['_period_default']=(options['months'][0],options['months'][-1])
    old=st.session_state.get('_source_version')
    if old and old!=version:
        reset_filters(st.session_state)
        st.info('Active source versions changed. Filters and detail selections have been reset to the new data basis.')
    st.session_state['_source_version']=version
    with st.sidebar:
        st.markdown('## ◈ ProcureIQ')
        st.caption('PROCUREMENT INTELLIGENCE')
        page=st.radio('Workspace',['Spend Overview','Supplier Intelligence','Opportunity Radar','Financial Scenario Lab','Executive Brief'],label_visibility='collapsed',key='navigation')
        st.divider()
        st.markdown('#### Explore a population')
        st.button('Reset Filters',on_click=reset_filters,args=(st.session_state,),width='stretch')
        if not options['months']:
            st.info('No active loaded source files. Initialize and load the database using the documented CLI.');return
        months=options['months']
        # A select slider requires at least two values; one-month installations still work.
        period=st.select_slider('Reporting month range',options=months,value=(months[0],months[-1]),format_func=lambda d:d.strftime('%b %Y'),key='filter_period') if len(months)>1 else (months[0],months[0])
        values={}
        for key,label in [('expense_type','Expense type'),('expense_area','Expense area'),('entity','Entity')]:
            chosen=st.selectbox(label,[ALL]+options[key],format_func=lambda x:'All' if x==ALL else x,key='filter_'+key)
            values[key]=None if chosen==ALL else chosen
        names={r['supplier_id']:r['canonical_name'] for r in options['suppliers']}
        chosen=st.selectbox('Normalized supplier',[ALL]+list(names),format_func=lambda x:'All suppliers' if x==ALL else names[x],key='filter_supplier')
        values['supplier_id']=None if chosen==ALL else chosen
        st.divider()
        st.caption('HMRC · disclosed payments\n\nGBP · gross, VAT-inclusive')
        st.button('Refresh source basis',width='stretch')
    filters=selected_filters(options,period,**values)
    # Reset detail pagination/choices when the population changes without retaining data arrays.
    filter_key=str(filters)
    if st.session_state.get('_filters')!=filter_key:
        for key in list(st.session_state):
            if key.startswith(('detail_','table_','evidence_','radar_')):del st.session_state[key]
    st.session_state['_filters']=filter_key
    st.caption('HMRC EXPENDITURE INTELLIGENCE / '+page.upper())
    st.title(page)
    descriptions={'Spend Overview':'Understand disclosed expenditure, its distribution and payment patterns.',
        'Supplier Intelligence':'Explore supplier exposure, concentration and the published lines behind it.',
        'Opportunity Radar':'Prioritize evidence-backed questions for procurement review.',
        'Executive Brief':'Review selected evidence, management actions and explicit financial illustrations.',
        'Financial Scenario Lab':'Compare explicit hypothetical assumptions for one disclosed expenditure pool.'}
    st.write(descriptions[page])
    with st.spinner('Loading the selected population…'):
        results=service.analytics(filters,version,('overview',))
    row=results['overview'][0] if results['overview'] else dict(positive_gbp=0,credit_gbp=0,net_gbp=0,record_count=0,supplier_count=0)
    st.caption(f"{period[0]:%b %Y} – {period[1]:%b %Y} · {row['record_count']:,} active published lines · source basis {version[:10]}")
    kpis(row)
    st.caption('Published disclosed payments are a subset of HMRC expenditure, not complete organizational procurement spend. Lines are not unique invoices; credits and duplicate candidates are retained.')
    if row.get('unresolved_rows',0) or row.get('unparsed_amounts',0):
        st.warning(f"{row.get('unresolved_rows',0):,} rows have unresolved supplier identities; {row.get('unparsed_amounts',0):,} amounts are unparsed. Invalid amounts are excluded from monetary totals.")
    if not row['record_count'] and page not in ('Financial Scenario Lab','Executive Brief'):
        st.info('No published lines match this combination. Reset Filters or broaden the selection.')
        return
    if page=='Spend Overview':overview.render(service,filters,version)
    elif page=='Supplier Intelligence':suppliers.render(service,filters,version)
    elif page=='Opportunity Radar':radar.render(service,filters,version,config)
    elif page=='Financial Scenario Lab':scenarios.render(service,filters,version,options)
    else:executive.render(service,filters,version,config)
    st.divider()
    st.caption('ProcureIQ · Auditable evidence for human judgment · Milestone 7')


try:
    main()
except SourceChanged:
    st.warning('Source versions changed during this interaction. Refresh source basis to load a consistent population.')
except (SQLAlchemyError,OSError):
    st.error('The database or configured policy file is unavailable. Check the local PostgreSQL service and exported configuration, then refresh. No substitute data is shown.')
except (ValueError,KeyError,StopIteration):
    st.error('The selection or configuration is no longer valid. Reset Filters, check the configuration in the dashboard guide, and refresh.')
