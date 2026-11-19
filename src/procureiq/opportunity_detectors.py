"""Four transparent review rules. No savings, fraud or inefficiency inference."""
from collections import defaultdict
from decimal import Decimal as D
from statistics import median
from .opportunity_model import Candidate, bounded
from .analytics import amounts


def positive_months(rows):
    return {r['reporting_month'] for r in rows if r['amount_gbp'] is not None and r['amount_gbp'] > 0}


def completeness(rows):
    return D(sum(r['parse_status']=='valid' and r['amount_gbp'] is not None for r in rows))/len(rows) if rows else D('0')


def coverage(data):
    return D(sum(m['source_available'] for m in data['calendar']))/len(data['calendar']) if data['calendar'] else D('0')


def reject(rejections, kind, scope, reason):
    rejections.append(dict(opportunity_type=kind, scope=scope, reason=reason))


def category_detectors(data, cfg):
    candidates, rejected = [], []
    for category in data['categories']:
        name = category['group_value']
        rows = data['by_category'][name]
        months = len(positive_months(rows))
        positive_areas = len({r['expense_area'] for r in rows if r['expense_area'] and r['amount_gbp'] is not None and r['amount_gbp']>0})
        metrics = dict(category, positive_activity_months=months, positive_expense_areas=positive_areas,
                       source_coverage=coverage(data))
        leaders = sorted((r for r in data['category_suppliers'] if r['group_value']==name), key=lambda r:r['supplier_rank'])[:3]
        metrics['top_suppliers'] = [dict(supplier_id=r['supplier_id'], canonical_name=r['canonical_name'],
                                       positive_gbp=r['positive_gbp'], share_resolved_pct=r['share_resolved_positive_pct']) for r in leaders]
        scope = dict(expense_type=name)
        common_reason = None
        if not name:
            common_reason = 'missing_category'
        elif category['positive_gbp'] < cfg.category_min_gbp:
            common_reason = 'below_materiality'
        elif coverage(data) < cfg.min_source_coverage:
            common_reason = 'insufficient_source_coverage'
        elif months < cfg.min_active_months:
            common_reason = 'insufficient_recurring_activity'
        elif category['unparsed_amounts'] or completeness(rows)<1:
            common_reason = 'incomplete_typed_evidence'
        elif category['mapping_coverage_pct'] is None or category['mapping_coverage_pct']/100 < cfg.min_mapping:
            common_reason = 'insufficient_supplier_mapping'
        evidence = coverage(data)*completeness(rows)*D(months)/max(len(data['calendar']),1)*(category['mapping_coverage_pct'] or D('0'))/100
        for kind in ('supplier_concentration','purchasing_fragmentation'):
            reason = common_reason
            if kind == 'supplier_concentration' and data['filters']['supplier_id'] is not None:
                reason = 'disabled_supplier_filtered_population'
            if reason:
                reject(rejected,kind,scope,reason)
                continue
            if kind == 'supplier_concentration':
                hhi = category['hhi']
                if hhi is None or hhi < cfg.concentration_hhi or not (
                    category['top_one_pct']/100 >= cfg.concentration_top_one or category['top_three_pct']/100 >= cfg.concentration_top_three):
                    reject(rejected,kind,scope,'concentration_threshold_not_met')
                    continue
                signal = (hhi/10000 + category['top_one_pct']/100 + category['top_three_pct']/100)/3
                title = f'Supplier dependency review: {name}'
                interpretation = 'Assess dependency and sourcing arrangements; concentration alone does not establish inefficient procurement.'
                next_step = 'Review contract scope, duration, renewal rights, continuity plans and feasible supplier alternatives with the category owner.'
                formula = '(HHI/10000 + top_one_pct/100 + top_three_pct/100) / 3'
                caveat = 'A single disclosed supplier may be appropriate for a specialized requirement or existing contract.'
            else:
                if (category['positive_supplier_count'] < cfg.fragmentation_suppliers or positive_areas < cfg.fragmentation_areas
                    or category['hhi'] is None or category['hhi'] > cfg.fragmentation_max_hhi
                    or category['top_three_pct']/100 > cfg.fragmentation_max_top_three):
                    reject(rejected,kind,scope,'fragmentation_threshold_not_met')
                    continue
                signal = (bounded(D(category['positive_supplier_count'])/(2*cfg.fragmentation_suppliers))
                          + bounded(D(positive_areas)/(2*cfg.fragmentation_areas)) + (1-category['hhi']/10000))/3
                title = f'Purchasing coordination review: {name}'
                interpretation = 'Investigate coordination across purchasing areas; the category label does not establish interchangeable services.'
                next_step = 'Compare specifications, frameworks, contract owners and buying requirements across the named areas before considering coordination.'
                formula = '(min(positive_suppliers/(2*minimum_suppliers),1) + min(positive_areas/(2*minimum_areas),1) + 1-HHI/10000) / 3'
                caveat = 'Broad expense types can contain non-substitutable goods and services; consolidation could increase dependency.'
            candidates.append(Candidate(kind,title,scope,[r['raw_row_id'] for r in rows],metrics,signal,evidence,formula,
                'source_month_coverage × valid_row_fraction × positive_active_months/selected_calendar_months × positive_value_mapping_coverage',
                f"Observed £{category['positive_gbp']:,.2f} positive payments across {months} months; HHI {category['hhi']:.2f}, "
                f"{category['positive_supplier_count']} positive suppliers and {positive_areas} positive purchasing areas.",
                interpretation,[caveat,'These are disclosed gross payments, not addressable spend or savings.'],next_step,
                'All positive payments in the selected category; credits and all supporting source rows are retained.'))
    return candidates,rejected


def payment_detector(data,cfg):
    candidates,rejected = [],[]
    calendar = data['calendar']
    for name,rows in sorted(data['by_category'].items(), key=lambda item:item[0] or ''):
        if not name:
            reject(rejected,'payment_pattern',{'expense_type':name},'missing_category')
            continue
        by_month = defaultdict(list)
        for r in rows:
            by_month[r['reporting_month']].append(r)
        total_positive = amounts(rows)['positive_gbp']
        for i,current in enumerate(calendar):
            month = current['reporting_month']
            scope = dict(expense_type=name,reporting_month=month)
            if i < cfg.history_months:
                reject(rejected,'payment_pattern',scope,'insufficient_prior_history')
                continue
            window = calendar[i-cfg.history_months:i+1]
            if not all(m['source_available'] for m in window):
                reject(rejected,'payment_pattern',scope,'missing_source_period')
                continue
            history = [amounts(by_month[m['reporting_month']]) for m in window[:-1]]
            history_active = sum(h['positive_gbp']>0 or h['credit_gbp']>0 for h in history)
            if history_active < cfg.history_active_months:
                reject(rejected,'payment_pattern',scope,'sparse_prior_activity')
                continue
            supporting = [r for m in window for r in by_month[m['reporting_month']]]
            if completeness(supporting)<1:
                reject(rejected,'payment_pattern',scope,'incomplete_typed_evidence')
                continue
            observed = amounts(by_month[month])
            current_pos, credit = observed['positive_gbp'],observed['credit_gbp']
            values = [h['positive_gbp'] for h in history]
            centre = median(values)
            mad = median([abs(v-centre) for v in values])
            delta = current_pos-centre
            ratio = current_pos/centre if centre else None
            deviation = abs(delta)/mad if mad else None
            prev = values[-1]
            mom = (current_pos-prev)/prev if prev else None
            share = current_pos/total_positive if total_positive else None
            credit_fraction = credit/(current_pos+credit) if current_pos+credit else None
            triggers, strengths = [],[]
            if centre>0 and current_pos>=cfg.payment_min_gbp and delta>=cfg.payment_min_gbp and ratio>=cfg.spike_ratio and (mad==0 or deviation>=cfg.mad_multiple):
                triggers.append('historical_positive_spike')
                strengths.append(bounded((ratio-1)/2))
            if centre>0 and abs(delta)>=cfg.payment_min_gbp and mom is not None and abs(current_pos-prev)>=cfg.payment_min_gbp and abs(mom)>=cfg.payment_change_ratio:
                triggers.append('material_monthly_change')
                strengths.append(bounded(abs(mom)))
            if centre>0 and share is not None and share>=cfg.month_share and ratio>=cfg.spike_ratio and delta>=cfg.payment_min_gbp:
                triggers.append('concentrated_payment_month')
                strengths.append(bounded(share/cfg.month_share/2))
            if credit>=cfg.payment_min_gbp and credit_fraction is not None and credit_fraction>=cfg.credit_ratio:
                triggers.append('material_credit_activity')
                strengths.append(bounded(credit_fraction/(2*cfg.credit_ratio)))
            if not triggers:
                reject(rejected,'payment_pattern',scope,'no_material_pattern_or_zero_baseline')
                continue
            year_end = month.month == 3
            metrics = dict(triggers=triggers, current_positive_gbp=current_pos,current_credit_gbp=credit,current_net_gbp=observed['net_gbp'],
                           prior_positive_gbp=prev,mom_change_fraction=mom,prior_median_gbp=centre,prior_mad_gbp=mad,
                           deviation_in_mad_units=deviation,ratio_to_median=ratio,delta_to_median_gbp=delta,
                           month_share_of_selected_category=share,credit_fraction_of_unsigned_payments=credit_fraction,
                           history_months=cfg.history_months,history_active_months=history_active,
                           history_positive_gbp=values,history_reporting_months=[m['reporting_month'] for m in window[:-1]],
                           march_year_end_context=year_end,zero_mad_ratio_fallback=mad==0,
                           trigger_strengths=dict(zip(triggers,strengths)))
            evidence = D(history_active)/cfg.history_months * (D('0.75') if year_end else D('1'))
            candidates.append(Candidate('payment_pattern',f'Payment timing review: {name} ({month:%Y-%m})',scope,
                [r['raw_row_id'] for r in supporting],metrics,max(strengths),evidence,
                'max(trigger strengths): spike=min((ratio-1)/2,1); change=min(abs(MoM),1); month concentration=min(share/(2*threshold),1); credits=min(credit_fraction/(2*threshold),1)',
                'active_prior_months/history_months × (0.75 for March, otherwise 1); complete source coverage and valid typed rows required',
                f"Observed £{current_pos:,.2f} positive payments and £{credit:,.2f} credits in {month:%Y-%m}; "
                f"prior {cfg.history_months}-month median £{centre:,.2f}. Triggers: {', '.join(triggers)}.",
                'Review payment timing and credit context; a material change is not proof of fraud, overpayment or an accounting error.',
                ['Short histories do not establish seasonality or statistical significance.',
                 'Annual renewals, milestones and billing cadence can explain payment changes.',
                 'A covered file with no matching category lines means zero disclosed payments, not proof that purchases stopped.'] +
                (['March is a financial year-end month; evidence confidence is reduced because year-end timing is a plausible explanation.'] if year_end else []),
                'Reconcile the current month and historical window to invoice schedules, credit notes, contract milestones and year-end postings.',
                'Positive payments over the current month plus the prior history window; history is contextual exposure, not estimated loss.'))
    return candidates,rejected


def quality_detector(data,cfg):
    flags = defaultdict(set)
    row_by_id = {r['raw_row_id']:r for r in data['lines']}
    # Persisted observations keep their row lineage; repeated identifiers alone are excluded.
    for issue in data['issues']:
        code = issue['issue_code']
        if code=='repeated_identifier':
            continue
        ids = [issue['raw_row_id']] if issue['raw_row_id'] is not None else [r['raw_row_id'] for r in data['lines'] if r['file_id']==issue['file_id']]
        for rid in ids:
            if rid in row_by_id:
                flags[rid].add(code)
    repeats = defaultdict(list)
    for r in data['lines']:
        if r['transaction_number'] and r['transaction_number'].strip():
            repeats[(r['file_id'],r['transaction_number'])].append(r)
        if r['supplier_id'] is None or r['amount_gbp'] is None or r['parse_status']!='valid' or any(not r.get(k) or not str(r[k]).strip() for k in ('expense_type','expense_area','entity','department_family','transaction_number','payment_date')):
            flags[r['raw_row_id']].add('missing_or_unresolved_information')
    repeated_only = 0
    for rows in repeats.values():
        if len(rows)>1:
            contextual = len({r['supplier_id'] for r in rows if r['supplier_id'] is not None})>1 or len({r['payment_date'] for r in rows if r['payment_date'] is not None})>1
            if contextual:
                for row in rows:
                    flags[row['raw_row_id']].add('identifier_context_review')
            else:
                repeated_only += len(rows)
    for group in data['alias_candidates']:
        for r in data['lines']:
            if r['supplier_raw'] in group['original_names']:
                flags[r['raw_row_id']].add('supplier_alias_candidate')
    candidates,rejected = [],[]
    if repeated_only:
        reject(rejected,'data_quality',{'row_count':repeated_only},'repeated_identifier_alone_not_an_error')
    for name,category_rows in sorted(data['by_category'].items(),key=lambda item:item[0] or ''):
        rows = [r for r in category_rows if flags[r['raw_row_id']]]
        if not rows:
            reject(rejected,'data_quality',{'expense_type':name},'no_additional_quality_evidence')
            continue
        exposure = amounts(rows)['positive_gbp']
        missing = sum('missing_or_unresolved_information' in flags[r['raw_row_id']] for r in rows)
        if exposure<cfg.quality_min_gbp and missing<cfg.quality_min_missing_rows:
            reject(rejected,'data_quality',{'expense_type':name},'below_quality_materiality')
            continue
        counts = defaultdict(int)
        for row in rows:
            for code in flags[row['raw_row_id']]:
                counts[code]+=1
        severity = max(D('1') if code.startswith(('invalid_','missing_')) or code in ('unresolved_supplier','ragged_row','schema_drift') else
                       D('0.8') if code=='exact_duplicate_candidate' else D('0.5') if code=='identifier_context_review' else D('0.4') for code in counts)
        fraction = D(len(rows))/len(category_rows)
        signal = (severity+bounded(fraction/D('0.10')))/2
        evidence = coverage(data) * D('0.8') # complete lineage, unresolved interpretation; not a correctness probability
        alias_groups = [g for g in data['alias_candidates'] if any(r['supplier_raw'] in g['original_names'] for r in rows)]
        candidates.append(Candidate('data_quality',f'Source/master-data review: {name or "unclassified"}',{'expense_type':name},
            [r['raw_row_id'] for r in rows],dict(affected_rows=len(rows),category_rows=len(category_rows),
                affected_row_fraction=fraction,flag_counts=dict(sorted(counts.items())),
                affected_credit_gbp=amounts(rows)['credit_gbp'],missing_or_unresolved_rows=missing,
                source_flags={str(r['raw_row_id']):sorted(flags[r['raw_row_id']]) for r in rows},alias_candidates=alias_groups),
            signal,evidence,'(maximum flag strength + min(affected_row_fraction/0.10,1)) / 2',
            'selected_source_coverage × 0.8; row provenance is known but issue interpretation is unreviewed',
            f'Observed {len(rows)} distinct affected source rows with £{exposure:,.2f} positive payments. Flag counts may overlap.',
            'Inspect source/master-data consistency; flags are review candidates, not confirmed duplicate payments or supplier equivalence.',
            ['Repeated identifiers can be legitimate invoice splits; duplicate-looking rows must not be removed without external evidence.',
             'Alias resemblance does not establish a shared legal identity. Unknown monetary amounts are excluded from the measurable exposure, not replaced with zero.'],
            'Inspect the referenced source lines and accounting evidence, verify supplier legal identities, and record any reviewed correction separately.',
            'Positive amounts on the union of affected rows; each row counted once even if multiple flags apply.'))
    return candidates,rejected
