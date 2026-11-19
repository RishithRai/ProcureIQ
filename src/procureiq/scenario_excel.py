"""Formula-driven XLSX export for the Python application; cached values are labeled."""
from io import BytesIO
from decimal import Decimal
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
from procureiq.financial_model import NAMES,Assumptions,sensitivity,CONVENTIONS
from procureiq.scenario_io import canonical

MONEY='"£"#,##0.00;("£"#,##0.00);"£"0.00'


def workbook_bytes(doc):
    out=BytesIO()
    wb=xlsxwriter.Workbook(out,{'in_memory':True,'strings_to_formulas':False,'strings_to_urls':False})
    wb.set_calc_mode('auto')
    sheets=[wb.add_worksheet(n) for n in ('Model Inputs','Scenario Comparison','Sensitivity Analysis','Methodology & Limitations')]
    inputs,comparison,grid,notes=sheets
    def fmt(**kw):return wb.add_format({'font_name':'Arial','font_size':10,'font_color':'#172E50','valign':'vcenter',**kw})
    title=fmt(bold=True,font_size=16)
    head=fmt(bold=True,bg_color='#172E50',font_color='white',text_wrap=True)
    textfmt=fmt(text_wrap=True)
    num=fmt(num_format=MONEY)
    rate=fmt(num_format='0.00%',italic=True)
    edit=fmt(num_format=MONEY,font_color='#1D4ED8',bg_color='#FFF5D6',locked=False)
    editrate=fmt(num_format='0.0000%',font_color='#1D4ED8',bg_color='#FFF5D6',locked=False)
    inputint=fmt(font_color='#1D4ED8',bg_color='#FFF5D6',locked=False)
    formula=fmt(num_format=MONEY,font_color='#00804A')
    rawfmt=fmt(num_format='0.000000',font_color='#111111')
    total=fmt(num_format=MONEY,bold=True,top=1,top_color='#CBD5E1')
    red=fmt(bg_color='#FDE8E7',font_color='#9D2924')
    green=fmt(bg_color='#E6F3EB',font_color='#17623A')
    neutral=fmt(bg_color='#EEF2F6')
    for ws in sheets:
        ws.hide_gridlines(2);ws.set_column('A:A',3);ws.set_column('B:B',42,textfmt)
        ws.set_column('C:E',25,textfmt);ws.set_default_row(24)
        ws.set_landscape();ws.fit_to_pages(1,0);ws.set_paper(9);ws.set_tab_color('#2463A6')
    def write_formula(ws,cell,expr,value,style=num):
        ws.write_formula(cell,expr,style,float(value) if isinstance(value,Decimal) else value)
    b=doc['baseline'];cases={n:Assumptions(**doc['scenarios'][n]) for n in NAMES}
    inputs.write('B2','ProcureIQ financial scenario inputs',title)
    inputs.write('B4','Yellow cells are editable. All benefit rates are hypothetical user assumptions.',textfmt)
    inputs.set_row(3,42)
    meta=[(6,'Expenditure pool',b['scope']),(7,'Source type',b['kind']+'; '+b['limitation']),
          (9,'Reporting period',b['period_label']),(10,'Model version',doc['model_version']),
          (11,'Source fingerprint',b['source_fingerprint'] or 'User-supplied; no HMRC verification'),
          (12,'Hypothesis','Same period only. Exposure is not savings. Never sum overlapping pools.'),
          (13,'Recalculation','Formula caches are Python results. Recalculate in Excel after editing inputs.')]
    for row,label,value in meta:
        inputs.write(row-1,1,label,textfmt)
        inputs.write(row-1,2,value,textfmt)
        inputs.set_row(row-1,60 if row in (7,9,11,12,13) else 42)
    inputs.write('B8','Baseline positive expenditure (GBP)',textfmt)
    inputs.write_number('C8',float(b['amount_gbp']),edit if b['kind']=='manual' else num)
    inputs.write('B16','Assumption for selected period',head)
    fields=('addressable_pct','adoption_pct','improvement_pct','implementation_cost','operating_cost')
    labels=('Addressable share','Adoption share','Improvement rate','Implementation cost (one-time)','Operating cost (same period)')
    for r,label in enumerate(labels,16):inputs.write(r,1,label,textfmt)
    for col,name in enumerate(NAMES,2):
        inputs.write(15,col,name,head)
        for r,field in enumerate(fields,16):
            v=getattr(cases[name],field)
            inputs.write_number(r,col,float(v/100 if field.endswith('_pct') else v),editrate if field.endswith('_pct') else edit)
    inputs.data_validation('C17:E19',dict(validate='decimal',criteria='between',minimum=0,maximum=1,ignore_blank=False,error_message='Enter a percentage between 0% and 100%.'))
    inputs.data_validation('C20:E21',dict(validate='decimal',criteria='between',minimum=0,maximum=999999999999.99,ignore_blank=False,error_message='Enter a nonnegative same-period cost.'))
    inputs.data_validation('C8',dict(validate='decimal',criteria='between',minimum=0,maximum=999999999999.99,ignore_blank=False))
    inputs.write('B24','Sensitivity case: 1 / 2 / 3',textfmt)
    inputs.write_number('C24',NAMES.index(doc['sensitivity']['selected'])+1,inputint)
    inputs.data_validation('C24',dict(validate='integer',criteria='between',minimum=1,maximum=3,ignore_blank=False))
    inputs.write('B25','1 Conservative; 2 Base; 3 Ambitious',textfmt)
    pop=b['population'] or {}
    for r,label,key in [(27,'Source positive payments','positive_gbp'),(28,'Source credit magnitude','credit_gbp'),(29,'Source net payments','net_gbp'),(30,'Source line count','record_count')]:
        inputs.write(r-1,1,label,textfmt)
        value=pop.get(key)
        inputs.write(r-1,2,float(value) if value is not None else 'Not HMRC-verified',num if key.endswith('_gbp') else textfmt)
    inputs.write('B32','Source: HMRC official spending disclosure catalogue',textfmt)
    inputs.write_url('C32','https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc',string='Official HMRC catalogue')
    inputs.set_row(31,42)
    inputs.protect('',{'select_locked_cells':True,'select_unlocked_cells':True})
    comparison.write('B2','Same-period scenario comparison',title)
    comparison.write('B3','Independent cases, one expenditure pool. Hypothetical benefits only.',textfmt);comparison.set_row(2,36)
    for r,label in {4:'Input validation',5:'Scenario',6:'Baseline positive expenditure',7:'Addressable share',8:'Adoption share',9:'Improvement rate',
        11:'Addressable calculation (unrounded)',12:'Affected calculation (unrounded)',13:'Gross calculation (unrounded)',
        15:'Addressable expenditure',16:'Affected expenditure',17:'Gross hypothetical benefit',18:'Implementation cost',19:'Operating cost',20:'Total costs',21:'Net hypothetical benefit',22:'ROI (net / costs)',24:'Zero-cost ROI is unavailable, not zero.'}.items():comparison.write(r-1,1,label,textfmt)
    for col,name in enumerate(NAMES,2):
        c=xl_col_to_name(col);a=cases[name];results=doc['outputs'][name]
        comparison.write(4,col,name,head)
        # Input validation is local to each case and prevents blanks/invalid edits becoming plausible zero outputs.
        guard=f'AND(ISNUMBER(\'Model Inputs\'!$C$8),\'Model Inputs\'!$C$8>=0,\'Model Inputs\'!$C$8<=999999999999.99,ROUND(\'Model Inputs\'!$C$8,2)=\'Model Inputs\'!$C$8,COUNT(\'Model Inputs\'!{c}17:{c}21)=5,MIN(\'Model Inputs\'!{c}17:{c}21)>=0,MAX(\'Model Inputs\'!{c}17:{c}19)<=1,MAX(\'Model Inputs\'!{c}20:{c}21)<=999999999999.99)'
        precision_checks=','.join(f"ROUND('Model Inputs'!{c}{r},{6 if r<20 else 2})='Model Inputs'!{c}{r}" for r in range(17,22))
        guard=f'AND({guard},{precision_checks})'
        numeric_check=f"AND(COUNT('Model Inputs'!$C$8)=1,COUNT('Model Inputs'!{c}17:{c}21)=5)"
        write_formula(comparison,f'{c}4',f'=IF({numeric_check},IF({guard},"Valid","Invalid inputs"),"Invalid inputs")','Valid',textfmt)
        expressions={6:"'Model Inputs'!$C$8",7:f"'Model Inputs'!{c}17",8:f"'Model Inputs'!{c}18",9:f"'Model Inputs'!{c}19",
            11:f'{c}6*{c}7',12:f'{c}11*{c}8',13:f'{c}12*{c}9',15:f'ROUND({c}11,2)',16:f'ROUND({c}12,2)',17:f'ROUND({c}13,2)',
            18:f"'Model Inputs'!{c}20",19:f"'Model Inputs'!{c}21",20:f'SUM({c}18:{c}19)',21:f'ROUND({c}13-{c}20,2)',
            22:f'IF({c}20>0,ROUND({c}21/{c}20*100,4)/100,"n.a.")'}
        values={6:b['amount_gbp'],7:a.addressable_pct/100,8:a.adoption_pct/100,9:a.improvement_pct/100,
                11:b['amount_gbp']*a.addressable_pct/100,12:b['amount_gbp']*a.addressable_pct/100*a.adoption_pct/100,
                13:b['amount_gbp']*a.addressable_pct/100*a.adoption_pct/100*a.improvement_pct/100,
                **{r:results[k] for r,k in [(15,'addressable_gbp'),(16,'affected_gbp'),(17,'gross_benefit_gbp'),(18,'implementation_cost_gbp'),(19,'operating_cost_gbp'),(20,'total_costs_gbp'),(21,'net_benefit_gbp')]},
                22:results['roi_pct']/100 if results['roi_pct'] is not None else 'n.a.'}
        for r,expr in expressions.items():
            write_formula(comparison,f'{c}{r}',f'=IF({c}$4="Valid",{expr},"n.a.")',values[r],
                          rate if r in (7,8,9,22) else rawfmt if r in (11,12,13) else total if r in (20,21) else num)
    comparison.conditional_format('C21:E21',{'type':'cell','criteria':'<','value':0,'format':red})
    comparison.protect()
    selected=doc['sensitivity']['selected'];a=cases[selected]
    grid.write('B2','Net-benefit sensitivity',title)
    grid.write('B3','Adoption down rows, improvement across columns. Other inputs fixed to selected case.',textfmt);grid.set_row(2,42)
    grid.set_column('C:BA',19)
    write_formula(grid,'C4','=INDEX(\'Scenario Comparison\'!C4:E4,1,\'Model Inputs\'!C24)','Valid',textfmt)
    write_formula(grid,'C5',"='Model Inputs'!C8",b['amount_gbp'])
    write_formula(grid,'C6',"=INDEX('Model Inputs'!C17:E17,1,'Model Inputs'!C24)",a.addressable_pct/100,rate)
    write_formula(grid,'C7',"=INDEX('Model Inputs'!C20:E20,1,'Model Inputs'!C24)",a.implementation_cost)
    write_formula(grid,'D7',"=INDEX('Model Inputs'!C21:E21,1,'Model Inputs'!C24)",a.operating_cost)
    for cell,label in [('B4','Selected case input validation'),('B5','Baseline positive expenditure'),('B6','Addressable share'),('B7','Implementation / operating cost'),('B8','Adoption / improvement')]:grid.write(cell,label,textfmt)
    ads=sorted(Decimal(str(v)) for v in doc['sensitivity']['adoption_values']);imps=sorted(Decimal(str(v)) for v in doc['sensitivity']['improvement_values'])
    truth={(r['adoption_pct'],r['improvement_pct']):r['net_benefit_gbp'] for r in sensitivity(b['amount_gbp'],a,ads,imps)}
    for col,i in enumerate(imps,2):grid.write_number(7,col,float(i/100),rate)
    for row,ad in enumerate(ads,8):
        grid.write_number(row,1,float(ad/100),rate)
        for col,i in enumerate(imps,2):
            c=xl_col_to_name(col);r=row+1
            write_formula(grid,f'{c}{r}',f'=IF($C$4="Valid",ROUND($C$5*$C$6*$B{r}*{c}$8-SUM($C$7:$D$7),2),"n.a.")',truth[ad,i])
    for criteria,value,style in [('<',0,red),('=',0,neutral),('>',0,green)]:
        grid.conditional_format(8,2,7+len(ads),1+len(imps),dict(type='cell',criteria=criteria,value=value,format=style))
    end=10+len(ads)
    grid.write(end,1,'Red: negative. Neutral: zero. Green: positive. Rounded same-period GBP.',textfmt);grid.set_row(end,42)
    grid.freeze_panes(8,2);grid.protect()
    notes.set_column('B:B',35);notes.set_column('C:C',105)
    notes.write('B2','Methodology and limitations',title)
    entries=[('Purpose','Hypothetical scenario comparison. Not realized savings, a forecast, contract terms or a prediction.'),
        ('Formula sequence','Baseline × addressable share = addressable; × adoption = affected; × improvement = gross benefit. Total costs = implementation + operating. Net = gross − total costs.'),
        ('Rounding',CONVENTIONS['arithmetic']),('ROI',CONVENTIONS['roi']),('Period',b['period_label']),
        ('VAT and eligibility','HMRC payments are gross VAT-inclusive. Match cost and benefit VAT treatment. Addressability must exclude contractual constraints and ineligible expenditure. No automatic VAT recovery assumption.'),
        ('Overlap','One explicitly defined pool. Three alternative cases are not additive. Never sum overlapping opportunities.'),
        ('Source limitation',b['limitation']),('Workbook inputs','Yellow cells are editable. A database baseline is locked to its exported evidence; create a new manual-baseline model to change it. Worksheet protection prevents accidental edits, not tampering.'),
        ('Recalculation','Live formulas reference inputs. Export caches are Python-calculated values, not evidence of Excel evaluation. Excel must recalculate after edits. Binary spreadsheet arithmetic may differ at half-penny boundaries; Python Decimal JSON is authoritative.'),
        ('Sensitivity','Grid uses the same unrounded products and final ROUND as the main calculation. Changing Model Inputs C24 selects the case. Changing either cost shifts the grid by the cost difference.'),
        ('Break-even','For positive affected expenditure, required improvement = total costs / affected × 100. Zero costs break even at 0%; positive costs with zero affected expenditure cannot break even. Rates above 100% are infeasible. Rounded zero outcomes occupy a half-penny band.'),
        ('Data version',b['source_fingerprint'] or 'User-supplied manual pool'),('Filters',canonical(b['filters'])),
        ('Opportunity origin',canonical(b['origin'])),('Example assumptions','No rate is empirically validated. If examples were loaded, they remain illustrative user choices.'),
        ('Currency',doc['currency'])]
    for row,(label,value) in enumerate(entries,4):
        notes.write(row,1,label,textfmt);notes.write(row,2,value,textfmt);notes.set_row(row,60 if len(value)>180 else 42)
    row=23
    for source in (b['source_basis'] or {}).get('sources',[]):
        notes.write(row,1,str(source['reporting_month']),textfmt)
        notes.write(row,2,source['filename']+' | SHA-256 '+source['sha256'],textfmt);notes.set_row(row,42);row+=1
    notes.protect()
    wb.close()
    return out.getvalue()
