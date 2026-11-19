# Milestone 3 — Advanced SQL analytics and supplier intelligence

## Data basis and reconciliation

This report uses **12,973 source lines** from **12 active source versions**, covering 2025-04–2026-03. There are no reporting filters. Month means publication/reporting month; payment dates remain available on source lines.

Positive disclosed payments: **£2,499,145,830.48**; credit magnitude: **£30,802,967.80**; net payments: **£2,468,342,862.68**. Category, expense-area, entity and monthly totals each reconcile independently to the same population. All repeated transaction IDs and duplicate candidates remain included.

Resolved supplier keys: **456**, of which **455** receive positive payments. Positive-payment mapping coverage: **100.00%**; unresolved positive payments **£0.00**. Unparsed amounts: **0**; invalid typed rows: **0**.

Exact file hashes, SQL migration hashes and filters are recorded in `analytics/full/basis.json`. CSV outputs retain unrounded NUMERIC ratios; this report rounds only display values. Supporting SQL is `sql/003_analytical_views.sql`; Python uses its parameterized functions in `src/procureiq/queries.py`.

## Top suppliers by positive payments

Query: `SELECT * FROM procureiq.vw_supplier_ranking ORDER BY supplier_rank LIMIT 10;`

| Rank | Supplier key | Positive GBP | Credits GBP | Net GBP | Share of all positive % | Months |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | capgemini | 410,066,806.54 | 6,486,371.26 | 403,580,435.28 | 16.41 | 12 |
| 2 | fujitsu services ltd | 267,066,790.92 | 0.00 | 267,066,790.92 | 10.69 | 12 |
| 3 | accenture (uk) ltd | 184,106,175.76 | 825,866.97 | 183,280,308.79 | 7.37 | 12 |
| 4 | cognizant technology solutions | 116,481,854.78 | 32,208.00 | 116,449,646.78 | 4.66 | 12 |
| 5 | amazon web services uk | 77,362,389.85 | 2,177,469.18 | 75,184,920.67 | 3.10 | 12 |
| 6 | workman holding account | 77,121,611.46 | 0.00 | 77,121,611.46 | 3.09 | 12 |
| 7 | equal experts uk ltd | 71,941,422.77 | 94,477.52 | 71,846,945.25 | 2.88 | 12 |
| 8 | royal mail group ltd | 67,069,463.45 | 220,047.33 | 66,849,416.12 | 2.68 | 12 |
| 9 | specialist computer ctr (non edi) | 58,161,051.24 | 671,697.81 | 57,489,353.43 | 2.33 | 12 |
| 10 | bytes software services ltd | 55,747,276.78 | 0.00 | 55,747,276.78 | 2.23 | 12 |

## Largest expense types and organizational areas

Queries: `vw_expense_type_spend` and `vw_expense_area_spend`, ordered by positive_gbp descending. These are source classifications, not proof of comparable products or contract scope.

### Expense types

| Expense type | Positive GBP | Credits GBP | Net GBP | Resolved suppliers | Share of positive % |
| --- | --- | --- | --- | --- | --- |
| PROJECT Mandays Supp | 721,458,382.18 | 5,012,458.96 | 716,445,923.22 | 59 | 28.87 |
| Project Development | 112,776,111.66 | 1,897,300.34 | 110,878,811.32 | 7 | 4.51 |
| Virtual Hosting and Infrastructure | 86,691,368.26 | 573,110.16 | 86,118,258.10 | 3 | 3.47 |
| Rent (Irrec VAT) | 83,248,930.45 | 0.00 | 83,248,930.45 | 13 | 3.33 |
| IT Software Licenses and Support | 77,027,574.87 | 113,373.00 | 76,914,201.87 | 8 | 3.08 |
| PROJECT Mandays HMRC | 75,800,808.58 | 339,423.28 | 75,461,385.30 | 27 | 3.03 |
| Physical Hosting and Infrastructure | 73,702,602.00 | 0.00 | 73,702,602.00 | 1 | 2.95 |
| National postal EVAT | 64,639,933.55 | 220,047.33 | 64,419,886.22 | 1 | 2.59 |
| Projects VAT irrec | 56,828,494.27 | 0.00 | 56,828,494.27 | 1 | 2.27 |
| Soft Licen Off shelf | 51,123,822.02 | 9,320.20 | 51,114,501.82 | 26 | 2.05 |

### Expense areas

| Expense area | Positive GBP | Credits GBP | Net GBP |
| --- | --- | --- | --- |
| CDIO - Core | 1,090,999,186.45 | 11,645,000.62 | 1,079,354,185.83 |
| Estates | 281,516,394.04 | 10,477,097.68 | 271,039,296.36 |
| Change Delivery Group | 195,092,684.04 | 350,607.97 | 194,742,076.07 |
| Customs Services & Operations | 111,540,720.05 | 0.00 | 111,540,720.05 |
| Customs Change Delivery | 102,915,524.17 | 690,029.60 | 102,225,494.57 |
| Operational Excellence & Output Mgmt | 91,934,198.26 | 327,047.33 | 91,607,150.93 |
| Unity Business Services | 69,454,776.84 | 736,844.74 | 68,717,932.10 |
| Change Delivery Making Tax Digital | 66,815,072.03 | 1,251,742.70 | 65,563,329.33 |
| Change Delivery DG & Programme Office | 52,907,733.99 | 51,994.59 | 52,855,739.40 |
| Debt Management | 51,495,053.41 | 989,489.00 | 50,505,564.41 |

## Overall Pareto and concentration

The first **32 suppliers** account for at least 80% of resolved positive payments: **7.03%** of the 455 positive-payment suppliers. The crossing supplier is included. Suppliers with only credits/zero amounts are retained in intelligence outputs but excluded from the Pareto supplier-count denominator.

Overall observed HHI: **541.13** on a 0–10,000 scale; largest-supplier share: **16.41%**; top-three share: **34.46%** of resolved positive payments.

Queries: `vw_supplier_concentration` and `vw_supplier_ranking`. Cumulative GBP and percentages use ordered SQL windows. Ties are resolved by normalized supplier key under C collation, then supplier ID.

## Categories with highest observed HHI

**139 categories** have exactly one resolved supplier receiving positive payments. The following are ordered by HHI, then positive-payment materiality. High HHI describes the disclosed allocation; it does not establish inefficient procurement, overpayment or an antitrust market.

Query: `SELECT * FROM procureiq.vw_category_concentration ORDER BY hhi DESC NULLS LAST, positive_gbp DESC;`

| Expense type | Positive GBP | Positive suppliers | HHI | Top one % | Top three % | Mapping % |
| --- | --- | --- | --- | --- | --- | --- |
| Physical Hosting and Infrastructure | 73,702,602.00 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| National postal EVAT | 64,639,933.55 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Projects VAT irrec | 56,828,494.27 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Debt coll serv (DEL) | 40,911,187.12 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Utility Payments - electricity | 29,611,004.42 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Oth PFI unitary chrg | 23,917,146.29 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Projects | 21,884,249.32 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Desktop Services | 21,648,527.16 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| Accommodation Security Services | 17,175,937.11 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |
| GCO Costs | 10,885,660.05 | 1 | 10,000.00 | 100.00 | 100.00 | 100.00 |

## Categories with the most suppliers

Fragmentation is described jointly by supplier count, HHI, area count and positive-payment materiality; no opportunity score is assigned. This table orders by resolved positive-payment supplier count, then positive payments. Broad categories can naturally contain many non-substitutable services.

Query: `SELECT * FROM procureiq.vw_category_concentration ORDER BY positive_supplier_count DESC, positive_gbp DESC;`

| Expense type | Positive suppliers | Areas | Positive GBP | Materiality % | HHI | Top three % |
| --- | --- | --- | --- | --- | --- | --- |
| PROJECT Mandays Supp | 59 | 40 | 721,458,382.18 | 28.87 | 1,754.94 | 65.31 |
| Tribunal appellant costs | 54 | 1 | 18,642,155.21 | 0.75 | 784.79 | 37.30 |
| SW Lic Sup Off shlf | 48 | 18 | 32,764,847.64 | 1.31 | 840.83 | 39.59 |
| PROJECT Mandays HMRC | 27 | 17 | 75,800,808.58 | 3.03 | 1,408.88 | 60.18 |
| Soft Licen Off shelf | 26 | 10 | 51,123,822.02 | 2.05 | 1,846.48 | 65.76 |
| Business Rates | 25 | 2 | 41,124,370.37 | 1.65 | 698.70 | 30.41 |
| Counsel Fee VAT Irre | 24 | 1 | 1,957,911.04 | 0.08 | 665.97 | 31.87 |
| Soft Licen Integral | 22 | 4 | 25,071,712.09 | 1.00 | 1,379.40 | 59.66 |
| Contin Labor Build | 19 | 10 | 39,414,419.94 | 1.58 | 6,235.71 | 87.49 |
| SW Lic Sup mngd Serv | 18 | 3 | 34,465,471.10 | 1.38 | 1,523.98 | 57.90 |

## Monthly disclosed payment trends

Query: `SELECT * FROM procureiq.vw_monthly_disclosed_spend ORDER BY reporting_month;` Month-on-month changes use positive payments. The first selected month has no prior in-window comparison. Missing source months or a zero prior denominator yield NULL, rather than a fabricated percentage.

| Reporting month | Lines | Positive GBP | Credits GBP | Net GBP | Positive MoM % |
| --- | --- | --- | --- | --- | --- |
| 2025-04-01 | 1116 | 217,220,774.13 | 2,263,741.14 | 214,957,032.99 | NULL |
| 2025-05-01 | 946 | 187,871,937.71 | 2,734,879.94 | 185,137,057.77 | -13.51 |
| 2025-06-01 | 962 | 243,706,737.72 | 1,087,793.90 | 242,618,943.82 | 29.72 |
| 2025-07-01 | 1013 | 188,451,137.50 | 2,239,344.99 | 186,211,792.51 | -22.67 |
| 2025-08-01 | 907 | 157,385,698.65 | 577,649.46 | 156,808,049.19 | -16.48 |
| 2025-09-01 | 1057 | 198,514,838.22 | 1,552,338.10 | 196,962,500.12 | 26.13 |
| 2025-10-01 | 1038 | 202,023,018.71 | 2,241,452.11 | 199,781,566.60 | 1.77 |
| 2025-11-01 | 1015 | 172,072,109.00 | 2,237,833.53 | 169,834,275.47 | -14.83 |
| 2025-12-01 | 1197 | 241,421,719.34 | 2,168,448.44 | 239,253,270.90 | 40.30 |
| 2026-01-01 | 1022 | 201,247,311.09 | 1,075,997.85 | 200,171,313.24 | -16.64 |
| 2026-02-01 | 1117 | 179,685,339.33 | 5,907,443.31 | 173,777,896.02 | -10.71 |
| 2026-03-01 | 1583 | 309,545,209.08 | 6,716,045.03 | 302,829,164.05 | 72.27 |

## Observations for later human investigation

- The largest published positive-payment month is **2026-03**, at **£309,545,209.08**. Examine payment timing, annual renewals and one-off projects before interpreting a change as cost inflation.
- Review concentration alongside category materiality and contract scope. A sole disclosed supplier may reflect a legitimate contract or a narrow disclosure sample.
- For the categories with many suppliers, establish whether goods/services are substitutable and whether expense areas share sourcing requirements before proposing coordination.
- Preserve separate supplier identities for unresolved punctuation variants; the approved case/whitespace policy does not establish corporate-group relationships.

## Limitations and dynamic filtering

These are gross VAT-inclusive disclosed payments, not all HMRC procurement expenditure, addressable spend, unit prices or realized savings. Material-group descriptions may combine unrelated services. Timing variation is payment variation, not measured price change. HHI is computed only over resolved identities and renormalized to their positive payments; unresolved expenditure and coverage are disclosed separately. No unknown-supplier bucket is inserted into HHI. Credits are not netted into share denominators.

Month, type, area, entity and supplier filters apply to underlying active lines before every aggregate. In particular, selecting one supplier measures concentration within that selection and will normally produce HHI 10,000; it does not describe the wider category. No averaging or summing of monthly/category HHIs is used. NULL ratios mean an undefined denominator, not zero concentration.

## Reproduce

```sh
procureiq db init
procureiq db verify
procureiq analytics summary
procureiq analytics verify
procureiq analytics export
python -m pytest -q
```

The export is generated from one read-only repeatable-read database snapshot and independently checked using Python Decimal. See `docs/analytical_methodology.md` for formulas and tests. This milestone implements descriptive analytics only; Opportunity Radar, Streamlit and scenario modelling remain out of scope.
