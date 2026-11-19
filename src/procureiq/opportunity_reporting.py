"""Lossless JSON/CSV evidence exports and a factual Markdown review report."""
import csv
import json
from hashlib import sha256
from .opportunities import canonical
from .opportunity_model import OpportunityConfig
from dataclasses import asdict


def cell(v):
    return str(v).replace('|','\\|').replace('\n',' ')


def findings(result):
    pop = result['population']
    lines = ['# Milestone 4 — Procurement Opportunity Radar','',
        '## Scope and observed evidence','',
        f"Evaluated **{pop['record_count']:,} active source rows**, with **£{pop['positive_gbp']:,.2f} positive disclosed payments**, "
        f"**£{pop['credit_gbp']:,.2f} credit magnitude** and **£{pop['net_gbp']:,.2f} net payments**. "
        'Reporting months, source hashes, filters, scoring configuration and full source references are embedded in `opportunities.json` and `opportunities.csv`.', '',
        'Rule version: `'+result['rule_version']+'`. Filters: `'+canonical(result['basis']['filters'])+'`.', '',
        'These are deterministic **review opportunities**, not confirmed inefficiency, recoverable overpayments or savings. '
        'Exposure is disclosed positive-payment context; overlapping opportunities must not be added together.', '',
        '## Counts and selection','',
        '| Detector | Qualified before cap | Exported |','|---|---:|---:|']
    for kind,count in result['counts_by_type'].items():
        lines.append(f"| {kind} | {result['qualified_before_cap'][kind]} | {count} |")
    lines += ['',f"Each detector is capped at {result['configuration']['max_per_type']} candidates after scoring; all exclusions and cap decisions remain in the JSON audit trail.", '',
        '## Top-ranked review opportunities','',
        '| Rank | Review opportunity | Exposure GBP | Materiality | Signal | Evidence | Priority /100 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for n,c in enumerate(result['opportunities'][:10],1):
        s = c['scoring']; parts=s['components']
        lines.append(f"| {n} | {cell(c['title'])} | {c['positive_exposure_gbp']:,.2f} | {parts['materiality']:.4f} | {parts['signal']:.4f} | {parts['evidence']:.4f} | {s['priority_score']:.2f} |")
    lines += ['', '## Evidence and interpretation for the top five','']
    for n,c in enumerate(result['opportunities'][:5],1):
        lines += [f"### {n}. {c['title']}", '', f"ID: `{c['opportunity_id']}`", '',
            '**Observed:** '+c['evidence_summary'], '',
            '**Exposure definition:** '+c['exposure_definition'], '',
            '**Reason for priority:** '+', '.join(f'{name} {value:.2f}' for name,value in c['scoring']['weighted_points'].items())+' weighted points. '
            'The complete metric values and formulas are in both exports.', '',
            '**Hypothesis to investigate:** '+c['business_interpretation'], '',
            '**Next step:** '+c['next_investigation_step'], '',
            '**Caveats:** '+' '.join(c['caveats']), '',
            f"Evidence: {len(c['source_references'])} distinct primary source rows plus {len(c['context_source_references'])} additional context rows; all references were verified against the filtered active snapshot.", '']
    lines += ['## Rejected or deferred patterns','', '| Reason | Evaluated scopes |','|---|---:|']
    for reason,count in result['rejection_counts'].items():
        lines.append(f'| {reason} | {count} |')
    lines += ['', 'Rejection counts refer to detector/category or detector/category/month evaluations, not distinct transactions. '
        'The first failed safeguard is recorded. For repeated identifiers alone, the scope includes a separate row count; this is not a missing-data error. '
        'Cap exclusions are qualified candidates deferred for review, rather than failed evidence thresholds.', '',
        '## Configuration and score definitions','',
        'Default materiality component is `min(exposure / £100,000,000, 1)`. Signal and evidence are independently bounded to [0,1]. '
        'Priority is `100 × (0.45 × materiality + 0.35 × signal + 0.20 × evidence)` under the default configuration. '
        'These are transparent analyst priorities, not calibrated probabilities or predicted financial benefits.', '',
        '```json',json.dumps(result['configuration'],indent=2,default=str),'```','',
        'See `docs/opportunity_methodology.md` for detector-specific formulas. Category patterns require recurring material expenditure and mapping coverage. '
        'Payment patterns need covered prior observations; March receives a lower evidence score because year-end timing is plausible. '
        'Quality flags count the union of affected rows, preserving all original records.', '',
        '## Limitations and review decisions','',
        '- The public disclosure subset is not complete procurement expenditure, unit pricing or contract/performance data.',
        '- High concentration can be appropriate. Fragmentation does not establish interchangeable goods/services.',
        '- Short payment histories cannot establish seasonality. MAD=0 uses an explicit ratio-and-absolute-change fallback, not a claim of statistical significance.',
        '- A payment-change candidate includes contextual historical payments in its exposure; this is not the amount of an error.',
        '- Supplier aliases and duplicate-looking rows require external confirmation before any correction.',
        '- Reference materiality and thresholds are configurable review assumptions. Large exposures can saturate the materiality component; scores are not comparable to estimated savings.',
        '- Candidate exposures overlap across detector types and rolling windows. The exports intentionally contain no summed opportunity exposure or savings total.', '',
        '## Reproduce','', '```sh','procureiq opportunities detect','procureiq opportunities verify',
        'procureiq opportunities export','procureiq db verify','procureiq analytics verify','python -m pytest -q','```','',
        'The engine uses a read-only repeatable-read snapshot and preserves existing ingestion and financial results. '
        'No Streamlit dashboard, financial scenario model or AI functionality is implemented.','']
    return '\n'.join(lines)


def export(root,result,output_dir=None):
    default = (not any(v is not None for v in result['basis']['filters'].values()) and result['configuration']==asdict(OpportunityConfig()))
    directory = output_dir or (root/'reports' if default else root/'reports/opportunity_runs'/sha256(canonical(dict(filters=result['basis']['filters'],config=result['configuration'])).encode()).hexdigest()[:12])
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'opportunities.json').write_text(json.dumps(result,indent=2,default=str,ensure_ascii=False)+'\n',encoding='utf-8')
    # Nested values remain JSON cells so CSV retains the same provenance and scoring detail.
    columns = list(result['opportunities'][0]) if result['opportunities'] else [
        'opportunity_id','opportunity_type','title','scope','positive_exposure_gbp','metrics','scoring',
        'evidence_summary','business_interpretation','caveats','next_investigation_step','source_references',
        'context_source_references','rule_version','basis','configuration']
    with (directory/'opportunities.csv').open('w',newline='',encoding='utf-8') as output:
        writer = csv.DictWriter(output,fieldnames=columns)
        writer.writeheader()
        for item in result['opportunities']:
            writer.writerow({k:canonical(v) if isinstance(v,(list,dict)) else v for k,v in item.items()})
    (directory/'milestone4_findings.md').write_text(findings(result),encoding='utf-8')
    return directory
