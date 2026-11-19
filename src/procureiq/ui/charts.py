"""Reusable Plotly figures. Numeric conversion is restricted to chart coordinates."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE='#2463A6'
NAVY='#172E50'


def style(fig, height=350):
    fig.update_layout(template='plotly_white',height=height,margin=dict(l=10,r=20,t=25,b=20),
                      font=dict(family='Arial, sans-serif',color=NAVY),paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)',colorway=[BLUE,'#58A4B0','#8F9DB3'],
                      legend=dict(orientation='h',y=1.15),hoverlabel=dict(bgcolor='white'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#E9EDF3',zerolinecolor='#CDD5E0')
    return fig


def bar(rows, label, metric, limit=10, percent=False, unit='GBP'):
    chosen=sorted((r for r in rows if r.get(metric) is not None),key=lambda r:r[metric],reverse=True)[:limit][::-1]
    fig=go.Figure(go.Bar(y=[r[label] or '(Unclassified)' for r in chosen],x=[float(r[metric]) for r in chosen],
        orientation='h',marker_color=BLUE,customdata=[str(r[metric]) for r in chosen],
        hovertemplate='%{y}<br>%{customdata}'+('%' if percent else ' '+unit)+'<extra></extra>'))
    fig.update_xaxes(title='Share of selected positive payments (%)' if percent else unit)
    return style(fig,390)


def trend(rows, metric='positive_gbp'):
    fig=go.Figure(go.Scatter(x=[r['reporting_month'] for r in rows],
        y=[float(r[metric]) if r.get(metric) is not None else None for r in rows],
        customdata=[str(r.get(metric)) for r in rows],mode='lines+markers',line=dict(color=BLUE,width=3),
        fill='tozeroy',fillcolor='rgba(36,99,166,0.07)',connectgaps=False,
        hovertemplate='%{x|%b %Y}<br>£%{customdata}<extra></extra>'))
    fig.update_yaxes(title='GBP')
    return style(fig,310)


def pareto(rows):
    rows=[r for r in rows if r['positive_gbp']>0]
    fig=make_subplots(specs=[[{'secondary_y':True}]])
    labels=[r['canonical_name'] for r in rows]
    fig.add_trace(go.Bar(x=labels,y=[float(r['positive_gbp']) for r in rows],name='Positive GBP',marker_color=BLUE),secondary_y=False)
    fig.add_trace(go.Scatter(x=labels,y=[float(r['cumulative_resolved_pct']) for r in rows],
        name='Cumulative resolved %',line=dict(color='#A26636',width=2)),secondary_y=True)
    fig.add_hline(y=80,line_dash='dash',line_color='#A26636',secondary_y=True,annotation_text='80%')
    fig.update_yaxes(title_text='Positive GBP',secondary_y=False)
    fig.update_yaxes(title_text='Cumulative resolved %',range=[0,105],secondary_y=True,showgrid=False)
    fig.update_xaxes(showticklabels=False,title='Suppliers in backend rank order · hover for name')
    return style(fig,350)


def scores(items):
    return style(go.Figure(go.Histogram(x=[float(i['scoring']['priority_score']) for i in items],
        xbins=dict(start=0,end=100,size=10),marker_color=BLUE)).update_layout(xaxis_title='Priority /100',yaxis_title='Review count'),260)


def contributions(item):
    points=item['scoring']['weighted_points']
    return style(go.Figure(go.Bar(x=list(points),y=[float(v) for v in points.values()],marker_color=[BLUE,'#58A4B0','#8F9DB3'])).update_layout(yaxis_title='Weighted score points'),260)
