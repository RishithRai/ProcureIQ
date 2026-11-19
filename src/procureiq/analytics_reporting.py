"""Generate the milestone report from one verified analytical snapshot."""
from decimal import Decimal


def display(value):
    if value is None:
        return 'NULL'
    if isinstance(value, Decimal):
        return f'{value:,.2f}'
    return str(value).replace('|', '\\|').replace('\n', ' ')


def table(rows, columns):
    labels = [label for _, label in columns]
    return ['| ' + ' | '.join(labels) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |'] + [
        '| ' + ' | '.join(display(row[key]) for key, _ in columns) + ' |' for row in rows]


def findings(data, basis):
    overview = data['overview'][0] if data['overview'] else None
    if overview is None:
        return '# Milestone 3 — no active matching records\n\nNo expenditure findings can be reported.\n'
    overall = data['concentration'][0]
    categories = data['category_concentration']
    single = [r for r in categories if r['positive_supplier_count'] == 1]
    fragmented = sorted(categories, key=lambda r: (-r['positive_supplier_count'], -r['positive_gbp'], r['group_value'] or ''))
    sources = basis['sources']
    lines = ['# Milestone 3 — Advanced SQL analytics and supplier intelligence', '',
             '## Data basis and reconciliation', '',
             f"This report uses **{overview['record_count']:,} source lines** from **{len(sources)} active source versions**, "
             f"covering {min(r['reporting_month'] for r in sources):%Y-%m}–{max(r['reporting_month'] for r in sources):%Y-%m}. "
             'There are no reporting filters. Month means publication/reporting month; payment dates remain available on source lines.', '',
             f"Positive disclosed payments: **£{overview['positive_gbp']:,.2f}**; credit magnitude: "
             f"**£{overview['credit_gbp']:,.2f}**; net payments: **£{overview['net_gbp']:,.2f}**. "
             'Category, expense-area, entity and monthly totals each reconcile independently to the same population. '
             'All repeated transaction IDs and duplicate candidates remain included.', '',
             f"Resolved supplier keys: **{overview['supplier_count']}**, of which **{overview['positive_supplier_count']}** "
             f"receive positive payments. Positive-payment mapping coverage: **{display(overview['mapping_coverage_pct'])}%**; "
             f"unresolved positive payments **£{overview['unresolved_positive_gbp']:,.2f}**. "
             f"Unparsed amounts: **{overview['unparsed_amounts']}**; invalid typed rows: **{overview['invalid_rows']}**.", '',
             'Exact file hashes, SQL migration hashes and filters are recorded in `analytics/full/basis.json`. '
             'CSV outputs retain unrounded NUMERIC ratios; this report rounds only display values. '
             'Supporting SQL is `sql/003_analytical_views.sql`; Python uses its parameterized functions in `src/procureiq/queries.py`.', '',
             '## Top suppliers by positive payments', '',
             'Query: `SELECT * FROM procureiq.vw_supplier_ranking ORDER BY supplier_rank LIMIT 10;`', '']
    lines += table(data['suppliers'][:10], [('supplier_rank','Rank'),('canonical_name','Supplier key'),('positive_gbp','Positive GBP'),
                    ('credit_gbp','Credits GBP'),('net_gbp','Net GBP'),('share_all_positive_pct','Share of all positive %'),('active_months','Months')])
    lines += ['', '## Largest expense types and organizational areas', '',
              'Queries: `vw_expense_type_spend` and `vw_expense_area_spend`, ordered by positive_gbp descending. These are source classifications, not proof of comparable products or contract scope.', '',
              '### Expense types', '']
    lines += table(data['expense_types'][:10], [('group_value','Expense type'),('positive_gbp','Positive GBP'),('credit_gbp','Credits GBP'),
                    ('net_gbp','Net GBP'),('supplier_count','Resolved suppliers'),('materiality_pct','Share of positive %')])
    lines += ['', '### Expense areas', '']
    lines += table(data['expense_areas'][:10], [('group_value','Expense area'),('positive_gbp','Positive GBP'),('credit_gbp','Credits GBP'),('net_gbp','Net GBP')])
    lines += ['', '## Overall Pareto and concentration', '',
              f"The first **{overall['suppliers_to_80']} suppliers** account for at least 80% of resolved positive payments: "
              f"**{display(overall['suppliers_to_80_pct'])}%** of the {overall['positive_supplier_count']} positive-payment suppliers. "
              'The crossing supplier is included. Suppliers with only credits/zero amounts are retained in intelligence outputs but excluded from the Pareto supplier-count denominator.', '',
              f"Overall observed HHI: **{display(overall['hhi'])}** on a 0–10,000 scale; largest-supplier share: "
              f"**{display(overall['top_one_pct'])}%**; top-three share: **{display(overall['top_three_pct'])}%** "
              'of resolved positive payments.', '',
              'Queries: `vw_supplier_concentration` and `vw_supplier_ranking`. Cumulative GBP and percentages use ordered SQL windows. '
              'Ties are resolved by normalized supplier key under C collation, then supplier ID.', '',
              '## Categories with highest observed HHI', '',
              f"**{len(single)} categories** have exactly one resolved supplier receiving positive payments. "
              'The following are ordered by HHI, then positive-payment materiality. High HHI describes the disclosed allocation; it does not establish inefficient procurement, overpayment or an antitrust market.', '',
              'Query: `SELECT * FROM procureiq.vw_category_concentration ORDER BY hhi DESC NULLS LAST, positive_gbp DESC;`', '']
    lines += table(categories[:10], [('group_value','Expense type'),('positive_gbp','Positive GBP'),('positive_supplier_count','Positive suppliers'),
                    ('hhi','HHI'),('top_one_pct','Top one %'),('top_three_pct','Top three %'),('mapping_coverage_pct','Mapping %')])
    lines += ['', '## Categories with the most suppliers', '',
              'Fragmentation is described jointly by supplier count, HHI, area count and positive-payment materiality; no opportunity score is assigned. '
              'This table orders by resolved positive-payment supplier count, then positive payments. Broad categories can naturally contain many non-substitutable services.', '',
              'Query: `SELECT * FROM procureiq.vw_category_concentration ORDER BY positive_supplier_count DESC, positive_gbp DESC;`', '']
    lines += table(fragmented[:10], [('group_value','Expense type'),('positive_supplier_count','Positive suppliers'),('expense_area_count','Areas'),
                    ('positive_gbp','Positive GBP'),('materiality_pct','Materiality %'),('hhi','HHI'),('top_three_pct','Top three %')])
    lines += ['', '## Monthly disclosed payment trends', '',
              'Query: `SELECT * FROM procureiq.vw_monthly_disclosed_spend ORDER BY reporting_month;` '
              'Month-on-month changes use positive payments. The first selected month has no prior in-window comparison. '
              'Missing source months or a zero prior denominator yield NULL, rather than a fabricated percentage.', '']
    lines += table(data['monthly'], [('reporting_month','Reporting month'),('record_count','Lines'),('positive_gbp','Positive GBP'),
                    ('credit_gbp','Credits GBP'),('net_gbp','Net GBP'),('mom_positive_pct','Positive MoM %')])
    largest = max((r for r in data['monthly'] if r['positive_gbp'] is not None), key=lambda r:r['positive_gbp'])
    lines += ['', '## Observations for later human investigation', '',
              f"- The largest published positive-payment month is **{largest['reporting_month']:%Y-%m}**, at **£{largest['positive_gbp']:,.2f}**. "
              'Examine payment timing, annual renewals and one-off projects before interpreting a change as cost inflation.',
              '- Review concentration alongside category materiality and contract scope. A sole disclosed supplier may reflect a legitimate contract or a narrow disclosure sample.',
              '- For the categories with many suppliers, establish whether goods/services are substitutable and whether expense areas share sourcing requirements before proposing coordination.',
              '- Preserve separate supplier identities for unresolved punctuation variants; the approved case/whitespace policy does not establish corporate-group relationships.', '',
              '## Limitations and dynamic filtering', '',
              'These are gross VAT-inclusive disclosed payments, not all HMRC procurement expenditure, addressable spend, unit prices or realized savings. '
              'Material-group descriptions may combine unrelated services. Timing variation is payment variation, not measured price change. '
              'HHI is computed only over resolved identities and renormalized to their positive payments; unresolved expenditure and coverage are disclosed separately. '
              'No unknown-supplier bucket is inserted into HHI. Credits are not netted into share denominators.', '',
              'Month, type, area, entity and supplier filters apply to underlying active lines before every aggregate. '
              'In particular, selecting one supplier measures concentration within that selection and will normally produce HHI 10,000; it does not describe the wider category. '
              'No averaging or summing of monthly/category HHIs is used. NULL ratios mean an undefined denominator, not zero concentration.', '',
              '## Reproduce', '',
              '```sh', 'procureiq db init', 'procureiq db verify', 'procureiq analytics summary',
              'procureiq analytics verify', 'procureiq analytics export', 'python -m pytest -q', '```', '',
              'The export is generated from one read-only repeatable-read database snapshot and independently checked using Python Decimal. '
              'See `docs/analytical_methodology.md` for formulas and tests. This milestone implements descriptive analytics only; '
              'Opportunity Radar, Streamlit and scenario modelling remain out of scope.', '']
    return '\n'.join(lines)
