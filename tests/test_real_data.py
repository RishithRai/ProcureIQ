"""Optional integration check against actual files, independently counted in integer pence."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from procureiq.profiling import investigate

ROOT = Path(__file__).resolve().parents[1]


def test_real_dataset_reconciliation_and_determinism():
    sources = json.loads((ROOT / 'manifests/hmrc_sources.json').read_text())
    if not all((ROOT / 'data/raw' / s['filename']).exists() for s in sources):
        pytest.skip('Download official files to run real-data integration verification')
    before = {s['filename']: hashlib.sha256((ROOT / 'data/raw' / s['filename']).read_bytes()).hexdigest() for s in sources}
    investigate(ROOT)
    report_bytes = {p.name: p.read_bytes() for p in (ROOT / 'reports').iterdir() if p.is_file()}
    with (ROOT / 'reports/data_quality_summary.csv').open() as f:
        summaries = {r['reporting_month']: r for r in csv.DictReader(f)}
    for source in sources:
        with (ROOT / 'data/raw' / source['filename']).open(encoding='cp1252', newline='') as f:
            rows = list(csv.DictReader(f))
        # Independent integer-pence calculation also handles the observed currency/grouping symbols.
        pence = []
        for row in rows:
            raw = row['Amount'].strip().replace('£', '').replace(',', '')
            sign = -1 if raw.startswith('-') else 1
            whole, _, fraction = raw.lstrip('-').partition('.')
            assert len(fraction) <= 2
            pence.append(sign * (int(whole) * 100 + int(fraction.ljust(2, '0'))))
        summary = summaries[source['reporting_month']]
        assert len(rows) == int(summary['record_count'])
        def pennies(value):
            return int(value.replace('.', ''))
        assert sum(pence) == pennies(summary['net_disclosed_gbp'])
        assert sum(v for v in pence if v > 0) == pennies(summary['positive_payments_gbp'])
        assert -sum(v for v in pence if v < 0) == pennies(summary['credit_magnitude_gbp'])
        assert hashlib.sha256((ROOT / 'data/raw' / source['filename']).read_bytes()).hexdigest() == before[source['filename']]
    investigate(ROOT)
    assert report_bytes == {p.name: p.read_bytes() for p in (ROOT / 'reports').iterdir() if p.is_file()}
