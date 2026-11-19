"""Versioned configuration, auditable priority arithmetic and typed candidates."""
from dataclasses import dataclass, asdict, fields
from decimal import Decimal
import json

RULE_VERSION = 'opportunity_rules_v1'
D = Decimal


@dataclass(frozen=True)
class OpportunityConfig:
    category_min_gbp: Decimal = D('5000000')
    min_active_months: int = 6
    min_mapping: Decimal = D('0.95')
    min_source_coverage: Decimal = D('0.90')
    concentration_hhi: Decimal = D('2500')
    concentration_top_one: Decimal = D('0.50')
    concentration_top_three: Decimal = D('0.80')
    fragmentation_suppliers: int = 10
    fragmentation_areas: int = 3
    fragmentation_max_hhi: Decimal = D('2500')
    fragmentation_max_top_three: Decimal = D('0.80')
    history_months: int = 6
    history_active_months: int = 4
    payment_min_gbp: Decimal = D('1000000')
    payment_change_ratio: Decimal = D('0.50')
    spike_ratio: Decimal = D('2')
    mad_multiple: Decimal = D('6')
    month_share: Decimal = D('0.35')
    credit_ratio: Decimal = D('0.20')
    quality_min_gbp: Decimal = D('25000')
    quality_min_missing_rows: int = 3
    materiality_reference_gbp: Decimal = D('100000000')
    materiality_weight: Decimal = D('0.45')
    signal_weight: Decimal = D('0.35')
    evidence_weight: Decimal = D('0.20')
    max_per_type: int = 10

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if f.type is Decimal and (not isinstance(v, Decimal) or not v.is_finite()):
                raise ValueError(f'{f.name} must be a finite Decimal')
            if f.type is int and (type(v) is not int or v < 1):
                raise ValueError(f'{f.name} must be a positive integer')
        for name in ('category_min_gbp','payment_min_gbp','quality_min_gbp','materiality_reference_gbp','spike_ratio','mad_multiple'):
            if getattr(self, name) <= 0:
                raise ValueError(name + ' must be positive')
        for name in ('min_mapping','min_source_coverage','concentration_top_one','concentration_top_three','fragmentation_max_top_three',
                     'payment_change_ratio','month_share','credit_ratio','materiality_weight','signal_weight','evidence_weight'):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(name + ' must be in [0,1]')
        if not 0 < self.concentration_hhi <= 10000 or not 0 < self.fragmentation_max_hhi <= 10000:
            raise ValueError('HHI thresholds must be in (0,10000]')
        if self.materiality_weight + self.signal_weight + self.evidence_weight != 1:
            raise ValueError('Priority weights must sum exactly to one')
        if not 3 <= self.history_months <= 24 or self.history_active_months > self.history_months:
            raise ValueError('History must span 3–24 months and cover the active-month minimum')
        if self.month_share <= 0 or self.credit_ratio <= 0 or self.payment_change_ratio <= 0:
            raise ValueError('Payment ratio thresholds must be positive')
        if self.spike_ratio <= 1 or self.max_per_type > 100:
            raise ValueError('Spike ratio must exceed one; output cap must not exceed 100 per type')


def load_config(path=None):
    if path is None:
        return OpportunityConfig()
    values = json.loads(path.read_text(), parse_float=Decimal)
    types = {f.name: f.type for f in fields(OpportunityConfig)}
    if not isinstance(values, dict) or set(values) - set(types):
        raise ValueError('Configuration must be an object of known threshold/weight names')
    return OpportunityConfig(**{k: Decimal(str(v)) if types[k] is Decimal else v for k,v in values.items()})


def bounded(value):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError('Score components must be finite Decimal values')
    return max(D('0'), min(D('1'), value))


def score(exposure, signal, evidence, config):
    if exposure < 0 or not exposure.is_finite():
        raise ValueError('Positive expenditure exposure must be nonnegative and finite')
    materiality = bounded(exposure / config.materiality_reference_gbp)
    signal, evidence = bounded(signal), bounded(evidence)
    components = dict(materiality=materiality, signal=signal, evidence=evidence)
    contributions = {k: D('100')*v*getattr(config, k+'_weight') for k,v in components.items()}
    return dict(components=components, weighted_points=contributions,
                priority_score=sum(contributions.values(), D('0')),
                explanation='100 × (materiality_weight × materiality + signal_weight × signal + evidence_weight × evidence)',
                materiality_formula='min(positive_exposure_gbp / materiality_reference_gbp, 1)',
                materiality_reference_gbp=config.materiality_reference_gbp)


@dataclass
class Candidate:
    opportunity_type: str
    title: str
    scope: dict
    row_ids: list[int]
    metrics: dict
    signal: Decimal
    evidence: Decimal
    signal_formula: str
    evidence_formula: str
    evidence_summary: str
    business_interpretation: str
    caveats: list[str]
    next_step: str
    exposure_definition: str
