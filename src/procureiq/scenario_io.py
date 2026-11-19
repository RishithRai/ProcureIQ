"""Versioned JSON interchange. Loaded results are recomputed, never trusted."""
import json
from dataclasses import asdict
from decimal import Decimal
from datetime import date
from procureiq.financial_model import MODEL_VERSION,CONVENTIONS,NAMES,Assumptions,comparison,decimal_input
from procureiq.scenario_basis import manual_baseline,period_label
from procureiq.queries import validate_filters


def canonical(value):
    return json.dumps(value,sort_keys=True,default=str,ensure_ascii=False)


def document(baseline,scenarios,selected='Base',adoptions=None,improvements=None):
    if selected not in NAMES:raise ValueError('Unknown selected scenario')
    return dict(model_version=MODEL_VERSION,currency='GBP',baseline=baseline,
        scenarios={n:asdict(scenarios[n]) for n in NAMES},outputs=comparison(baseline['amount_gbp'],scenarios),
        conventions=CONVENTIONS,sensitivity=dict(selected=selected,
        adoption_values=adoptions or [Decimal(i) for i in range(0,101,10)],
        improvement_values=improvements or [Decimal(i) for i in range(11)]))


def export_json(doc):
    return json.dumps(doc,indent=2,default=str,ensure_ascii=False).encode('utf-8')


def load_json(content):
    if len(content)>2_000_000:raise ValueError('Scenario JSON exceeds 2 MB')
    try:
        def unique(pairs):
            result={}
            for k,v in pairs:
                if k in result:raise ValueError('Duplicate JSON key')
                result[k]=v
            return result
        raw=json.loads(content,parse_float=Decimal,object_pairs_hook=unique)
        if set(raw)!={'model_version','currency','baseline','scenarios','outputs','conventions','sensitivity'}:
            raise ValueError('Unexpected scenario document fields')
        if raw['model_version']!=MODEL_VERSION or raw['currency']!='GBP' or raw['conventions']!=CONVENTIONS:
            raise ValueError('Unsupported model, currency or conventions')
        b=raw['baseline']
        required={'kind','amount_gbp','start_month','end_month','period_label','scope','filters','source_fingerprint','population','covered_months','source_basis','origin','limitation'}
        if set(b)!=required or b['kind'] not in ('manual','hmrc'):raise ValueError('Invalid baseline schema')
        b['amount_gbp']=decimal_input(b['amount_gbp'],'baseline')
        if b['period_label']!=period_label(b['start_month'],b['end_month']):raise ValueError('Period label mismatch')
        if not isinstance(b['scope'],str) or not 1<=len(b['scope'])<=500:raise ValueError('Invalid scope')
        if b['kind']=='manual':
            expected=manual_baseline(b['amount_gbp'],b['start_month'],b['end_month'],b['scope'])
            if canonical(b)!=canonical(expected):raise ValueError('Manual baseline must not claim HMRC provenance')
        else:
            fp=b['source_fingerprint']
            if not isinstance(fp,str) or len(fp)!=64 or any(c not in '0123456789abcdef' for c in fp):raise ValueError('Invalid source fingerprint')
            b['filters']=dict(b['filters'])
            for key in ('start_month','end_month'):
                if isinstance(b['filters'].get(key),str) and len(b['filters'][key])==10:
                    b['filters'][key]=date.fromisoformat(b['filters'][key])
            b['filters']=validate_filters(b['filters'])
            if not isinstance(b['population'],dict) or not isinstance(b['source_basis'],dict):raise ValueError('Missing HMRC provenance')
            for key in ('positive_gbp','credit_gbp'):
                b['population'][key]=decimal_input(b['population'][key],key)
            net=Decimal(b['population']['net_gbp'])
            if not net.is_finite() or b['population']['positive_gbp']-b['population']['credit_gbp']!=net:raise ValueError('Invalid population reconciliation')
            b['population']['net_gbp']=net
            if b['amount_gbp']!=b['population']['positive_gbp']:raise ValueError('Baseline must equal positive payments')
            if type(b['population']['record_count']) is not int or b['population']['record_count']<0:raise ValueError('Invalid population size')
        if set(raw['scenarios'])!=set(NAMES):raise ValueError('Three named scenarios required')
        cases={n:Assumptions(**raw['scenarios'][n]) for n in NAMES}
        sens=raw['sensitivity']
        if set(sens)!={'selected','adoption_values','improvement_values'}:raise ValueError('Invalid sensitivity configuration')
        from procureiq.financial_model import sensitivity
        sensitivity(b['amount_gbp'],cases[sens['selected']],sens['adoption_values'],sens['improvement_values'])
        result=document(b,cases,sens['selected'],sens['adoption_values'],sens['improvement_values'])
        if canonical(raw['outputs'])!=canonical(result['outputs']):raise ValueError('Saved outputs disagree with assumptions')
        return result,cases
    except (KeyError,TypeError,ArithmeticError,json.JSONDecodeError) as exc:
        raise ValueError('Invalid scenario JSON') from exc


def validate_database_claim(service,baseline,version):
    """An uploaded fingerprint alone is not proof of its claimed amount or population."""
    from procureiq.scenario_basis import refresh_baseline,is_stale
    if baseline['kind']=='manual' or is_stale(baseline,version):return
    current=refresh_baseline(service,baseline,version)
    if canonical(current)!=canonical(baseline):
        raise ValueError('Saved HMRC baseline does not match current database evidence. Choose a fresh baseline.')
