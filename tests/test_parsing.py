"""Synthetic unit examples are not evidence for the real-data findings."""
from decimal import Decimal
import pytest
from procureiq.parsing import money, read_csv, payment_date
from procureiq.profiling import profile


@pytest.mark.parametrize('raw,expected', [('£1,234.56', '1234.56'), ('-0.01', '-0.01'), ('12', '12.00'), ('0', '0.00'), (' 1.2 ', '1.20')])
def test_money(raw, expected):
    assert money(raw) == Decimal(expected)


@pytest.mark.parametrize('raw', ['1.001', '1.230', '1,23', 'NaN', 'Infinity', '1e6', '--1', '£'])
def test_money_rejects_invalid_or_extra_precision(raw):
    with pytest.raises(ValueError):
        money(raw)


def test_missing_and_precision():
    assert money(' ') is None
    assert money('0.10') + money('0.20') == Decimal('0.30')
    assert payment_date('') == (None, None)
    with pytest.raises(ValueError):
        payment_date('31/02/2025')


def test_quoted_multiline_bom_and_ids(tmp_path):
    p = tmp_path / 'fixture.csv'
    p.write_bytes('\ufeffSupplier,Transaction number,Amount\r\n"A, B\nLtd",001,"£1,234.56"\r\nNA,002,0\r\n'.encode())
    df, cols, refs, issues, meta = read_csv(p)
    assert df.iloc[0]['Supplier'] == 'A, B\nLtd'
    assert df.iloc[0]['Transaction number'] == '001'
    assert df.iloc[1]['Supplier'] == 'NA'
    assert refs[0]['source_line_start'] == 2 and refs[0]['source_line_end'] == 3
    assert refs[1]['source_line_start'] == 4
    assert meta['encoding'] == 'utf-8-sig'
    assert not issues


def test_cp1252_semicolon_and_ragged_rows(tmp_path):
    p = tmp_path / 'fixture.csv'
    p.write_bytes('Supplier;Amount\nCafé;12\nB;3\nC;4\nD;5\nE;6\nF;7\nG;8\nH;9\nI;10\nJ;11\nK;12;extra\n'.encode('cp1252'))
    df, _, _, issues, meta = read_csv(p)
    assert meta['delimiter'] == ';'
    assert meta['encoding'] == 'cp1252'
    assert len(df) == 11
    assert df.iloc[-1]['__extra_0'] == 'extra'
    assert issues[0]['actual'] == 3


def test_profile_retains_credits_duplicates_missing_and_schema(tmp_path):
    p = tmp_path / 'fixture.csv'
    p.write_text('Date,Amount,Transaction number,Supplier,Expense type,Expense area\n'
                 '01/04/2025,100.10,001,A,Type,Area\n'
                 '01/04/2025,100.10,001,A,Type,Area\n'
                 '31/03/2025,-0.20,001,A,Type,Area\n'
                 ',,002, ,Type,Area\n'
                 'bad,1.001,003,B,Type,Area\n')
    original = p.read_bytes()
    df, cols, refs, issues, s = profile(p, '2025-04')
    assert len(df) == 5 and p.read_bytes() == original
    assert s['positive_payments_gbp'] == '200.20'
    assert s['credit_magnitude_gbp'] == '0.20'
    assert s['net_disclosed_gbp'] == '200.00'
    assert s['repeated_identifier_rows'] == 3
    assert s['repeated_identifier_groups'] == 1
    assert s['exact_duplicate_rows'] == 2 and s['exact_duplicate_excess'] == 1
    assert s['outside_reporting_month'] == 1
    assert s['missing:Supplier'] == 1
    assert s['missing_amounts'] == s['invalid_amounts'] == 1
    assert not s['financial_totals_complete']
    assert 'Supplier Type' not in cols
    p.write_text(p.read_text().replace('Expense area\n', 'Expense area,Supplier Type\n').replace('Type,Area\n', 'Type,Area,\n'))
    _, cols2, _, _, s2 = profile(p, '2025-04')
    assert 'Supplier Type' in cols2 and s2['missing:Supplier Type'] == 5
