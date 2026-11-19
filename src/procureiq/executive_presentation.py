"""Editable five-slide executive review, generated locally with python-pptx."""
from io import BytesIO
from decimal import Decimal
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from procureiq.executive import THEMES

NAVY='17324D'; BLUE='2166AC'; GRAY='526174'; PALE='EEF3F8'; WHITE='FFFFFF'
TITLES=('HMRC Procurement Spend Intelligence','Expenditure & Supplier Intelligence','Opportunity Radar','Financial Scenario Illustration','Recommendations & Management Actions')

def gbp(value):return f'£{Decimal(value):,.2f}'

def text(slide,x,y,w,h,value,size=18,bold=False,color=NAVY):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    frame=shape.text_frame; frame.word_wrap=True
    frame.margin_left=frame.margin_right=Inches(.02)
    frame.margin_top=frame.margin_bottom=0
    for i,line in enumerate(str(value).split('\n')):
        p=frame.paragraphs[0] if i==0 else frame.add_paragraph()
        p.text=line;p.font.name='Arial';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
        p.space_after=Pt(9)
    return shape


def table(slide,x,y,w,h,headers,rows,widths=None,font=16):
    shape=slide.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(w),Inches(h))
    t=shape.table
    if widths:
        for col,width in zip(t.columns,widths):col.width=Inches(width)
    for i,row in enumerate([headers]+rows):
        for j,value in enumerate(row):
            cell=t.cell(i,j);cell.text=str(value);cell.margin_left=cell.margin_right=Inches(.12)
            cell.margin_top=cell.margin_bottom=Inches(.10)
            cell.fill.solid();cell.fill.fore_color.rgb=RGBColor.from_string(NAVY if i==0 else (PALE if i%2 else WHITE))
            for p in cell.text_frame.paragraphs:
                p.font.name='Arial';p.font.size=Pt(font);p.font.bold=i==0;p.font.color.rgb=RGBColor.from_string(WHITE if i==0 else NAVY)
    return shape


def bar(slide,x,y,w,h,rows,label):
    chart_data=CategoryChartData();chart_data.categories=[r[0] for r in rows]
    chart_data.add_series(label,[float(r[1]/Decimal('1000000')) for r in rows])
    chart=slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED,Inches(x),Inches(y),Inches(w),Inches(h),chart_data).chart
    # python-pptx templates use signed IDs; OOXML requires unsigned axis IDs.
    for node in chart._chartSpace.xpath('.//c:axId | .//c:crossAx'):
        node.set('val',str(int(node.get('val')) % (2**32)))
    chart.has_legend=False;chart.chart_style=13
    chart.category_axis.tick_labels.font.name='Arial';chart.category_axis.tick_labels.font.size=Pt(12)
    chart.category_axis.reverse_order=True
    chart.value_axis.tick_labels.font.name='Arial';chart.value_axis.tick_labels.font.size=Pt(11)
    chart.value_axis.has_title=True;chart.value_axis.axis_title.text_frame.text='Positive payments (£m)'
    chart.value_axis.axis_title.text_frame.paragraphs[0].font.size=Pt(12)
    series=chart.series[0];series.format.fill.solid();series.format.fill.fore_color.rgb=RGBColor.from_string(BLUE)


def presentation_bytes(brief,scenario=None):
    """Input is a service snapshot; caller must validate scenario compatibility first."""
    if scenario:
        b=scenario['baseline']
        if b['kind']!='hmrc' or b['source_fingerprint']!=brief['source_fingerprint'] or (b['start_month'],b['end_month'])!=(brief['start_month'],brief['end_month']):
            raise ValueError('Incompatible scenario source or period')
        from procureiq.scenario_io import load_json,export_json
        scenario,_=load_json(export_json(scenario))
        for key in ('expense_area','entity','supplier_id','expense_type'):
            expected=brief['filters'].get(key); actual=scenario['baseline']['filters'].get(key)
            if (key!='expense_type' or expected is not None) and expected!=actual:raise ValueError('Incompatible scenario filters')
    prs=Presentation();prs.slide_width=Inches(40/3);prs.slide_height=Inches(7.5)
    prs.core_properties.title='ProcureIQ executive review';prs.core_properties.author='ProcureIQ'
    slides=[]
    scope=', '.join(f'{k}: {v}' for k,v in brief['filters'].items() if v is not None and k not in ('start_month','end_month')) or 'All active disclosed payments'
    for number,title in enumerate(TITLES,1):
        s=prs.slides.add_slide(prs.slide_layouts[6]);slides.append(s)
        text(s,.55,.36,12.2,.65,title,30,True)
        text(s,.55,1.12,12.2,.45,brief['period']+' / '+scope,12,color=GRAY)
        text(s,.55,6.95,12.2,.4,f"HMRC spending-over-£25,000 disclosures · {brief['period']} · source {brief['source_fingerprint'][:12]} · {number}/5",10,color=GRAY)
        s.notes_slide.notes_text_frame.text=(brief['attribution']+'\n'+brief['dataset_url']+'\nFull source fingerprint: '+brief['source_fingerprint']+'\nFilters: '+str(brief['filters'])+'\n'+brief['caveat'])
    s=slides[0];o=brief['overview']
    text(s,.6,1.85,8,.85,gbp(o['positive_gbp']),42,True,BLUE)
    text(s,.6,2.77,11,.5,'Positive disclosed payments · gross VAT-inclusive',20)
    table(s,.6,3.42,12.1,.95,['Credit magnitude','Net disclosed payments','Published lines'],[[gbp(o['credit_gbp']),gbp(o['net_gbp']),f"{o['record_count']:,}"]],font=17)
    for i,finding in enumerate(brief['findings'][:2]):text(s,.6,4.72+i*.7,12,.65,finding,17)
    text(s,.6,6.3,12,.45,'Payment disclosures are a subset of expenditure. They do not establish achievable savings.',15,color=GRAY)
    s=slides[1];data=brief['analytics']
    text(s,.6,1.65,6,.4,'Leading expense categories (£m)',19,True);text(s,6.9,1.65,5.8,.4,'Leading suppliers (£m)',19,True)
    if data['expense_types']:bar(s,.55,2.15,6.15,3.25,[(r['group_value'] or 'Unclassified',r['positive_gbp']) for r in data['expense_types'][:4]],'Categories')
    if data['suppliers']:bar(s,6.75,2.15,6,3.25,[(r['canonical_name'],r['positive_gbp']) for r in data['suppliers'][:4]],'Suppliers')
    if data['concentration']:
        c=data['concentration'][0]
        if c['hhi'] is not None:
            text(s,.6,5.55,12.1,.55,f"HHI {c['hhi']:,.2f}    Top-three share {c['top_three_pct']:.2f}%    80% threshold: {c['suppliers_to_80']} suppliers",19,True)
    text(s,.6,6.25,12,.5,'Shares use resolved positive payments. Observed supplier concentration is not market concentration or proof of inefficiency.',15,color=GRAY)
    s=slides[2];counts=brief['counts']
    text(s,.6,1.65,12,.5,f"{counts['qualified']} qualified candidates    {counts['exported']} exported reviews    {counts['deferred']} deferred by caps",23,True)
    recs=brief['recommendations']
    rows=[]
    for r in recs:
        theme=THEMES[r['opportunity_type']][0]
        m=r['measurements'];kind=r['opportunity_type']
        if kind=='supplier_concentration':metric=f"HHI {Decimal(m['hhi']):,.0f}; {m['positive_supplier_count']} positive suppliers"
        elif kind=='purchasing_fragmentation':metric=f"{m['positive_supplier_count']} suppliers; {m['positive_expense_areas']} purchasing areas"
        elif kind=='payment_pattern':metric=f"Current period positives {gbp(m['current_positive_gbp'])}"
        else:metric=f"{m['affected_rows']} flagged source rows"
        rows.append([theme,r['title'].split(': ',1)[-1]+'\n'+metric,f"{Decimal(r['priority_score']):.2f}",gbp(r['positive_exposure_gbp'])])
    if rows:table(s,.6,2.3,12.1,3.25,['Investigation theme','Selected scope','Priority /100','Positive exposure'],rows,[2.6,4.7,1.65,3.15],15)
    else:text(s,.6,2.5,12,1,'No eligible reviews in this selection. Short history or materiality gates can exclude candidates.',22)
    text(s,.6,5.92,12,.35,'Four detectors: supplier concentration, purchasing fragmentation, payment patterns and data quality.',16)
    overlap=sum(bool(r['overlaps']) for r in recs)
    text(s,.6,6.42,12,.35,f'Investigation candidates, not validated financial opportunities. {overlap} selected reviews overlap another. Never sum exposures.',15,color=GRAY)
    for r in recs:s.notes_slide.notes_text_frame.text+='\n'+r['reference']+' '+r['observed_evidence']+'\nOpportunity '+r['opportunity_ids'][0]+'\nOverlaps: '+str(r['overlaps'])
    s=slides[3]
    if scenario:
        b=scenario['baseline'];text(s,.6,1.65,12, .8,f"Baseline: {b['scope']}\n{gbp(b['amount_gbp'])} positive disclosed payments",20,True)
        rows=[]
        for name,a in scenario['scenarios'].items():
            out=scenario['outputs'][name]
            rows.append([name,f"{a['addressable_pct']}% / {a['adoption_pct']}% / {a['improvement_pct']}%",gbp(a['implementation_cost']),gbp(a['operating_cost']),gbp(out['gross_benefit_gbp']),gbp(out['net_benefit_gbp'])])
        table(s,.6,2.8,12.1,2.65,['Case','Address / adopt / improve','Implementation','Period operating','Gross benefit','Net benefit'],rows,[1.45,2.4,2,1.95,2.15,2.15],14)
        text(s,.6,5.75,12,.65,'Hypothetical financial illustrations, not predicted or realized savings.\nIndependent alternatives: never add their benefits together.',18,True)
        text(s,.6,6.45,12,.35,'Same-period assumptions; no annualization. VAT, contractual constraints and eligibility require validation.',13,color=GRAY)
    else:
        text(s,.6,1.85,12,1,'No matching scenario has been explicitly selected.',28,True)
        text(s,.6,3,12,1.8,'Define one positive-expenditure pool in Financial Scenario Lab.\nEnter addressability, adoption, improvement and same-period costs.\nReview the source version and explicitly include the scenario in this brief.',23)
        text(s,.6,5.55,12,.9,'Gross benefit = baseline × addressability × adoption × improvement\nNet benefit = gross benefit − implementation and operating costs',21)
        text(s,.6,6.45,12,.35,'Any future benefit outputs are hypothetical. No assumptions or financial results have been inserted.',14,color=GRAY)
    s=slides[4]
    short_actions={
        'purchasing_fragmentation':('Compare specifications across purchasing areas before coordinating sourcing.', 'Service comparability, contract rates and buying authority.'),
        'supplier_concentration':('Review continuity arrangements and feasible sourcing alternatives.', 'Contract scope, expiry dates and qualified alternatives.'),
        'payment_pattern':('Reconcile the highlighted period to invoices, milestones and credits.', 'Invoice schedules, accrual explanations and credit notes.'),
        'data_quality':('Check flagged records against original documents before corrections.', 'Invoices, ledger records and verified supplier identities.')}
    for i,r in enumerate(recs[:4]):
        y=1.65+i*1.16
        text(s,.6,y,3.2,.85,f"{i+1}. {THEMES[r['opportunity_type']][0]}\nPriority {Decimal(r['priority_score']):.2f}",17,True)
        text(s,3.9,y,8.8,.4,r['title'].split(': ',1)[-1]+' · '+gbp(r['positive_exposure_gbp'])+' exposure',14,True)
        action,required=short_actions[r['opportunity_type']]
        text(s,3.9,y+.38,8.8,.72,'Action: '+action+'\nValidate: '+required,14)
    if not recs:text(s,.6,2,12,2,'No eligible recommendations. Broaden the selection or collect more history before drawing procurement conclusions.',24)
    text(s,.6,6.45,12,.35,'Validate contracts and source evidence before commercial decisions. Exposures overlap; no portfolio savings estimate.',14,color=GRAY)
    stream=BytesIO();prs.save(stream);return stream.getvalue()
