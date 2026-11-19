import pytest
from procureiq.supplier_identity import matching_key, identity, punctuation_candidates
from procureiq.ingestion import typed_row, row_hash


def test_conservative_matching():
    assert matching_key('  Acme\t LTD ') == matching_key('ACME LTD') == 'acme ltd'
    assert matching_key('Straße') == matching_key('STRASSE')
    assert matching_key('Acme Ltd.') != matching_key('Acme Ltd')
    assert matching_key('Acme Limited') != matching_key('Acme Ltd')
    groups = punctuation_candidates(['ACME LTD', 'Acme Ltd.', ' Acme LTD '])
    assert len(groups) == 1
    assert groups[0]['reason'] == 'punctuation_similarity_no_merge'


@pytest.mark.parametrize('name', ['', '   ', 'N/A', 'Redacted', '[REDACTED]', 'Redacted - personal', '***', 'UNKNOWN', 'Private Individual'])
def test_unknown_identity_unresolved(name):
    assert identity(name)['review_status'] == 'unresolved'
    assert identity(name)['mapping_method'] == 'placeholder_v1'


def test_person_name_not_automatically_redacted():
    assert identity('JAMES ABERNETHY')['review_status'] == 'auto_resolved'
    assert identity('UNKNOWN TECHNOLOGIES LTD')['review_status'] == 'auto_resolved'


def test_typed_validation_and_hash():
    row, issues = typed_row({'Date': 'bad', 'Amount': '1.234', 'Transaction number': '00001'})
    assert row['amount_gbp'] is None and row['payment_date'] is None
    assert row['transaction_number'] == '00001' and row['parse_status'] == 'invalid'
    assert len(issues) == 2
    row, issues = typed_row({'Date': '01/04/2025', 'Amount': '1000000000000000000.00'})
    assert row['amount_gbp'] is None
    assert row_hash({'A': '1', 'B': '2'}) == row_hash({'B': '2', 'A': '1'})
    assert row_hash({'A': ' 1'}) != row_hash({'A': '1'})
