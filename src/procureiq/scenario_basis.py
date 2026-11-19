"""One explicit baseline pool, read through existing analytics in one snapshot."""
from datetime import date
from decimal import Decimal
from procureiq.analytics import snapshot_metadata
from procureiq.queries import query,validate_filters
from procureiq.financial_model import decimal_input


def period_label(start,end):
    a=date.fromisoformat(str(start));b=date.fromisoformat(str(end))
    if a.day!=1 or b.day!=1 or a>b:raise ValueError('Reporting period must be ordered first-of-month dates')
    n=(b.year-a.year)*12+b.month-a.month+1
    return f'{n}-month same-period scenario ({a:%b %Y}–{b:%b %Y}); not annualized'


def database_baseline(service,filters,version,category=None,origin=None):
    filters=validate_filters(filters)
    if category is not None:
        if not isinstance(category,str):raise ValueError('Choose one category')
        if filters['expense_type'] not in (None,category):raise ValueError('Category conflicts with the selected population')
        filters['expense_type']=category
    with service.snapshot(version) as (conn,_):
        overview=query(conn,'overview',filters)
        calendar=query(conn,'monthly',filters)
        if not calendar:raise ValueError('No reporting period available')
        row=overview[0] if overview else dict(positive_gbp=Decimal('0.00'),credit_gbp=Decimal('0.00'),net_gbp=Decimal('0.00'),record_count=0,unparsed_amounts=0)
        basis=snapshot_metadata(conn,filters)
    start,end=calendar[0]['reporting_month'],calendar[-1]['reporting_month']
    return dict(kind='hmrc',amount_gbp=row['positive_gbp'],start_month=str(start),end_month=str(end),
        period_label=period_label(start,end),scope=filters['expense_type'] or 'Selected expenditure population',
        filters=filters,source_fingerprint=version,population={k:row[k] for k in ('positive_gbp','credit_gbp','net_gbp','record_count','unparsed_amounts')},
        covered_months=sum(r['source_available'] for r in calendar),source_basis=basis,origin=origin,
        limitation='Gross VAT-inclusive disclosed positive payments, not complete procurement spend or proven addressable expenditure.')


def manual_baseline(amount,start,end,scope):
    if not isinstance(scope,str) or not scope.strip() or len(scope)>500:raise ValueError('Describe the user-supplied pool (1–500 characters)')
    return dict(kind='manual',amount_gbp=decimal_input(amount,'manual baseline'),start_month=str(start),end_month=str(end),
        period_label=period_label(start,end),scope=scope.strip(),filters={},source_fingerprint=None,population=None,
        covered_months=None,source_basis=None,origin=None,
        limitation='User-supplied baseline; not HMRC-verified. User must establish period, VAT and eligibility basis.')


def opportunity_request(item,filters,version):
    kind=item['opportunity_type']
    eligible=kind in ('supplier_concentration','purchasing_fragmentation')
    category=item['scope'].get('expense_type') if eligible else None
    return dict(opportunity_id=item['opportunity_id'],opportunity_type=kind,title=item['title'],
        category=category,filters=validate_filters(filters),source_fingerprint=version,
        eligible=eligible and isinstance(category,str),
        note='Offer this single category as a baseline; assumptions must be entered explicitly.' if eligible else
             'Review context only. Historical or disputed exposure is not an automatically addressable procurement savings pool.')


def is_stale(baseline,current_version):
    return baseline['kind']=='hmrc' and baseline['source_fingerprint']!=current_version


def refresh_baseline(service,baseline,current_version):
    if baseline['kind']!='hmrc':raise ValueError('Only database baselines can be refreshed')
    return database_baseline(service,baseline['filters'],current_version,origin=baseline.get('origin'))
