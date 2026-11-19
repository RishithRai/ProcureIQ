"""Small shared presentation components; tables paginate before rendering."""
from math import ceil
import streamlit as st
from procureiq.ui.formatting import money, display_rows, csv_bytes


def kpis(row):
    cols=st.columns([1.5,1.4,1.5,1,1])
    for col,label,key in zip(cols,['Positive disclosed payments','Credit magnitude','Net disclosed payments','Transaction lines','Resolved suppliers'],
                             ['positive_gbp','credit_gbp','net_gbp','record_count','supplier_count']):
        with col:
            with st.container(border=True):
                st.metric(label,money(row.get(key)) if key.endswith('_gbp') else f"{row.get(key,0):,}")


def chart(fig, key):
    st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})


def table(rows, key, title='Explore the data', columns=None):
    st.subheader(title)
    if not rows:
        st.info('No rows match this selection. Broaden the filters or reset them.')
        return
    if columns:
        rows=[{k:r.get(k) for k in columns} for r in rows]
    a,b,c=st.columns([2,2,1])
    search=a.text_input('Search table',key='table_'+key+'_search',placeholder='Search names or values')
    sort=b.selectbox('Sort by',list(rows[0]),key='table_'+key+'_sort')
    descending=c.checkbox('Descending',value=False,key='table_'+key+'_desc')
    found=[r for r in rows if not search or search.casefold() in ' '.join(str(v) for v in r.values()).casefold()]
    # Preserve numeric ordering before formatting Decimal values as exact strings.
    found=sorted(found,key=lambda r:(r[sort] is None,r[sort] if r[sort] is not None else ''),reverse=descending)
    if not found:
        st.info('No table rows match this search.');return
    pages=max(1,ceil(len(found)/50))
    pagekey='table_'+key+'_page'
    if st.session_state.get(pagekey,1)>pages:st.session_state[pagekey]=1
    page=st.number_input('Table page',min_value=1,max_value=pages,value=1,key=pagekey)
    st.caption(f'{len(found):,} matching rows · page {page} of {pages} · 50 rows per page. Use Sort by for ordering across all pages.')
    st.dataframe(display_rows(found[(page-1)*50:page*50]),hide_index=True,width='stretch')
    st.download_button('Download matching table CSV',csv_bytes(found),file_name=key+'.csv',mime='text/csv',on_click='ignore',key='table_'+key+'_download')


def evidence_table(service,filters,version,item,config):
    st.subheader('Source-record evidence')
    st.caption(f"{item['primary_count']:,} primary rows · {item['context_count']:,} contextual rows. Context supports interpretation and is excluded from exposure.")
    kind=st.radio('Evidence population',['Primary','Contextual'],horizontal=True,key='evidence_kind_'+item['opportunity_id'])
    count=item['primary_count'] if kind=='Primary' else item['context_count']
    if not count:
        st.info('No contextual source records for this opportunity.')
    else:
        pages=ceil(count/50)
        page=st.number_input('Evidence page',min_value=1,max_value=pages,value=1,key='evidence_page_'+kind+item['opportunity_id'])
        with st.spinner('Fetching this page of source records…'):
            result=service.evidence(filters,version,item['opportunity_id'],context=kind=='Contextual',page=page,config=config)
        st.caption(f'Page {page} of {pages} · at most 50 source rows fetched')
        st.dataframe(display_rows(result['rows']),width='stretch',hide_index=True)
    if st.button('Prepare complete evidence JSON',key='evidence_prepare_'+item['opportunity_id']):
        with st.spinner('Preparing every primary and contextual source record…'):
            payload=service.evidence_download(filters,version,item['opportunity_id'],config)
        st.download_button('Download complete evidence JSON',payload,file_name=item['opportunity_id']+'.json',mime='application/json',on_click='ignore')
