import streamlit as st
from procureiq.ui import charts
from procureiq.ui.components import chart, table


def render(service,filters,version):
    data=service.analytics(filters,version,('monthly','expense_types','expense_areas','suppliers'))
    metric=st.radio('Chart amount',['Positive payments','Net payments'],horizontal=True,key='overview_amount')
    metric='positive_gbp' if metric=='Positive payments' else 'net_gbp'
    with st.container(border=True):
        st.subheader('Monthly disclosed payments')
        st.caption('Reporting months · gaps indicate unavailable source months, not zero spending.')
        chart(charts.trend(data['monthly'],metric),'overview_trend')
    left,right=st.columns(2)
    with left,st.container(border=True):
        st.subheader('Expense categories');st.caption('Ten largest categories in this selection')
        chart(charts.bar(data['expense_types'],'group_value',metric),'overview_categories')
    with right,st.container(border=True):
        st.subheader('Purchasing areas');st.caption('Ten largest expense areas in this selection')
        chart(charts.bar(data['expense_areas'],'group_value',metric),'overview_areas')
    left,right=st.columns(2)
    with left,st.container(border=True):
        st.subheader('Largest suppliers')
        chart(charts.bar(data['suppliers'],'canonical_name',metric),'overview_suppliers')
    with right,st.container(border=True):
        st.subheader('Category contribution')
        st.caption('Share of all selected positive payments, regardless of the chart amount toggle')
        chart(charts.bar(data['expense_types'],'group_value','materiality_pct',percent=True),'overview_contribution')
    dimension=st.selectbox('Expenditure table',['Expense categories','Expense areas','Monthly payments'])
    name={'Expense categories':'expense_types','Expense areas':'expense_areas','Monthly payments':'monthly'}[dimension]
    table(data[name],'spend_'+name,'Expenditure explorer')
