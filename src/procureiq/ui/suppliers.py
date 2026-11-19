from math import ceil
import streamlit as st
from procureiq.ui import charts
from procureiq.ui.components import chart, table, kpis
from procureiq.ui.formatting import money,display_rows


def render(service,filters,version):
    data=service.analytics(filters,version,('suppliers','concentration','category_concentration','category_suppliers'))
    ranking=data['suppliers']
    concentration=data['concentration'][0] if data['concentration'] else {}
    st.info('HHI describes concentration of observed disclosed payments. A single supplier or a high HHI does not establish procurement inefficiency.')
    st.caption(f"All selected positive payments: {money(concentration.get('positive_gbp'))} · Resolved-supplier denominator: {money(concentration.get('resolved_positive_gbp'))} · Unresolved positive payments: {money(concentration.get('unresolved_positive_gbp'))}")
    columns=st.columns(3)
    for c,label,key in zip(columns,['Observed HHI','Top-one share · resolved','Top-three share · resolved'],['hhi','top_one_pct','top_three_pct']):
        v=concentration.get(key)
        c.metric(label,'Not available' if v is None else f'{v:,.2f}'+('%' if key.endswith('pct') else ''))
    categories=[r['group_value'] for r in data['category_concentration']]
    choice=st.selectbox('Pareto scope',[('all',None)]+[('category',c) for c in categories],
        format_func=lambda x:'Overall selected population' if x[0]=='all' else (x[1] or '(Unclassified category)'),key='detail_pareto')
    pareto_rows=ranking if choice[0]=='all' else [r for r in data['category_suppliers'] if r['group_value']==choice[1]]
    with st.container(border=True):
        st.subheader('Supplier Pareto')
        st.caption('Cumulative share uses resolved positive payments. Credit-only and zero-payment suppliers are excluded from this curve; retained in the ranking below.')
        if any(r['positive_gbp']>0 for r in pareto_rows):
            chart(charts.pareto(pareto_rows),'supplier_pareto')
        else:st.info('No resolved positive payments for this Pareto selection.')
    table(ranking,'supplier_ranking','Supplier rankings',columns=['supplier_rank','canonical_name','positive_gbp','credit_gbp','net_gbp','share_all_positive_pct','share_resolved_positive_pct','cumulative_resolved_pct','expense_area_count','active_months'])
    with st.container(border=True):
        st.subheader('Category concentration')
        st.caption('HHI ranges from 0 to 10,000 on resolved positive payments. NULL means no valid positive denominator.')
        chart(charts.bar(data['category_concentration'],'group_value','hhi',limit=10,unit='HHI'),'category_hhi')
        table(data['category_concentration'],'concentration','Category metrics',columns=['group_value','positive_gbp','positive_supplier_count','expense_area_count','hhi','top_one_pct','top_three_pct','mapping_coverage_pct','suppliers_to_80'])
    st.subheader('Supplier detail')
    if not ranking:
        st.info('No resolved suppliers match this population. Unresolved payments remain in the overview.');return
    names={r['supplier_id']:r['canonical_name'] for r in ranking}
    sid=st.selectbox('Inspect normalized supplier',list(names),format_func=names.get,key='detail_supplier')
    detail=service.supplier_detail(filters,version,sid)
    row=detail['overview'][0] if detail['overview'] else {}
    st.caption('Detail applies this supplier within the current sidebar selection; the selected-population rankings above remain unchanged.')
    kpis(row)
    a,b=st.columns(2)
    with a,st.container(border=True):
        st.subheader('Supplier payment pattern');chart(charts.trend(detail['monthly']),'supplier_trend')
    with b,st.container(border=True):
        st.subheader('Supplier categories');chart(charts.bar(detail['expense_types'],'group_value','positive_gbp'),'supplier_categories')
    table(detail['expense_areas'],'supplier_areas','Supplier purchasing areas')
    st.write('Original supplier aliases in this selection')
    st.dataframe({'Original published name':service.aliases(filters,version,sid)},hide_index=True,width='stretch')
    with st.expander('Supporting transaction lines'):
        count=row.get('record_count',0)
        page=st.number_input('Supplier transaction page',min_value=1,max_value=max(1,ceil(count/50)),value=1,key=f'detail_transactions_{sid}_{version}_{str(filters)}')
        st.caption(f'{count:,} lines · at most 50 source rows fetched')
        st.dataframe(display_rows(service.supplier_records(filters,version,sid,page)),hide_index=True,width='stretch')
