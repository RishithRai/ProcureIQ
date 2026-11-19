"""Deterministic same-period scenarios. No database, UI, forecast or score inference."""
from dataclasses import dataclass, asdict, replace
from decimal import Decimal, ROUND_HALF_UP, localcontext

D=Decimal
MODEL_VERSION='same_period_decimal_v1'
NAMES=('Conservative','Base','Ambitious')
MAX_MONEY=D('999999999999.99')
CONVENTIONS={
    'money':'GBP; nonnegative inputs with at most two decimal places; no implicit VAT adjustment',
    'rates':'Percent units 0–100 inclusive; at most four decimal places',
    'arithmetic':'Decimal precision 50; unrounded intermediate products; final money ROUND_HALF_UP to 0.01',
    'roi':'Rounded net benefit / total costs × 100, rounded HALF_UP to four percentage decimals; unavailable at zero cost',
    'period':'Same selected reporting period; no annualization or assumed recurrence',
    'interpretation':'Hypothetical assumptions, not predicted or realized savings; one pool only; never sum overlapping scenarios',
}


def decimal_input(value, name, maximum=MAX_MONEY, places=2):
    if isinstance(value, (float,bool)) or not isinstance(value,(str,int,Decimal)):
        raise ValueError(f'{name}: use an exact decimal value')
    if isinstance(value,str) and len(value)>40:
        raise ValueError(f'{name}: value too long')
    try:v=D(value)
    except Exception as exc:raise ValueError(f'{name}: enter a number') from exc
    if not v.is_finite() or v<0 or v>maximum or v.as_tuple().exponent < -places:
        raise ValueError(f'{name}: must be 0–{maximum}, with at most {places} decimal places')
    return v


def money_round(value):
    return value.quantize(D('0.01'),rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Assumptions:
    addressable_pct: Decimal=D('0')
    adoption_pct: Decimal=D('0')
    improvement_pct: Decimal=D('0')
    implementation_cost: Decimal=D('0.00')
    operating_cost: Decimal=D('0.00')

    def __post_init__(self):
        for name,value in asdict(self).items():
            checked=decimal_input(value,name,D('100') if name.endswith('_pct') else MAX_MONEY,4 if name.endswith('_pct') else 2)
            object.__setattr__(self,name,checked)


def calculate(baseline, assumptions):
    baseline=decimal_input(baseline,'baseline')
    if not isinstance(assumptions,Assumptions):raise ValueError('Validated assumptions required')
    with localcontext() as ctx:
        ctx.prec=50
        addressable=baseline*assumptions.addressable_pct/100
        affected=addressable*assumptions.adoption_pct/100
        gross=affected*assumptions.improvement_pct/100
        costs=assumptions.implementation_cost+assumptions.operating_cost
        net=money_round(gross-costs)
        roi=(net/costs*100).quantize(D('0.0001'),rounding=ROUND_HALF_UP) if costs>0 else None
        return dict(addressable_gbp=money_round(addressable),affected_gbp=money_round(affected),
                    gross_benefit_gbp=money_round(gross),implementation_cost_gbp=assumptions.implementation_cost,
                    operating_cost_gbp=assumptions.operating_cost,total_costs_gbp=money_round(costs),
                    net_benefit_gbp=net,roi_pct=roi)


def comparison(baseline, scenarios):
    if set(scenarios)!=set(NAMES):raise ValueError('Exactly Conservative, Base and Ambitious are required')
    return {name:calculate(baseline,scenarios[name]) for name in NAMES}


def break_even(baseline, assumptions, adoption=None):
    baseline=decimal_input(baseline,'baseline')
    adoption=assumptions.adoption_pct if adoption is None else decimal_input(adoption,'adoption',D('100'),4)
    with localcontext() as ctx:
        ctx.prec=50
        costs=assumptions.implementation_cost+assumptions.operating_cost
        affected=baseline*assumptions.addressable_pct/100*adoption/100
        required= D('0') if costs==0 else costs/affected*100 if affected else None
        return dict(improvement_pct=required,feasible=required is not None and required<=100,
                    reason='Zero costs: zero improvement breaks even' if costs==0 else
                    'No affected expenditure: positive costs cannot be recovered' if not affected else
                    'Required improvement exceeds 100%' if required>100 else 'Unrounded gross benefit equals total costs')


def sensitivity(baseline, assumptions, adoption_values=None, improvement_values=None):
    adoptions=list(adoption_values) if adoption_values is not None else [D(i) for i in range(0,101,10)]
    improvements=list(improvement_values) if improvement_values is not None else [D(i) for i in range(11)]
    if not adoptions or not improvements or len(adoptions)>51 or len(improvements)>51:
        raise ValueError('Sensitivity requires 1–51 values per axis')
    adoptions=[decimal_input(v,'adoption',D('100'),4) for v in adoptions]
    improvements=[decimal_input(v,'improvement',D('100'),4) for v in improvements]
    if len(set(adoptions))!=len(adoptions) or len(set(improvements))!=len(improvements):
        raise ValueError('Sensitivity axis values must be unique')
    return [dict(adoption_pct=a,improvement_pct=i,
                 net_benefit_gbp=calculate(baseline,replace(assumptions,adoption_pct=a,improvement_pct=i))['net_benefit_gbp'])
            for a in sorted(adoptions) for i in sorted(improvements)]


def illustrative():
    """Explicit optional examples only; never selected at initialization."""
    return {name:Assumptions(D('20'),D(adoption),D(improvement),D('100000'),D('50000'))
            for name,adoption,improvement in [('Conservative','25','1'),('Base','50','2'),('Ambitious','75','3')]}
