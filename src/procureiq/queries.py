"""Parameterized analytical access, independent of any UI.

SQL functions are the single formula implementation shared by views and filters.
A caller can reuse one Connection to keep multiple results in the same snapshot.
"""
import re
from datetime import date
from sqlalchemy import text

FILTER_TYPES = {'start_month': 'date', 'end_month': 'date', 'expense_type': 'text',
                'expense_area': 'text', 'entity': 'text', 'supplier_id': 'bigint'}
ARGS = ','.join(f'CAST(:{key} AS {kind})' for key, kind in FILTER_TYPES.items())
# These are trusted constants, never interpolated user SQL or identifiers.
QUERIES = {
    'overview': ("analytics_groups('overall',", 'group_value'),
    'expense_types': ("analytics_groups('expense_type',", 'positive_gbp DESC,group_value COLLATE "C" NULLS LAST'),
    'expense_areas': ("analytics_groups('expense_area',", 'positive_gbp DESC,group_value COLLATE "C" NULLS LAST'),
    'entities': ("analytics_groups('entity',", 'positive_gbp DESC,group_value COLLATE "C" NULLS LAST'),
    'suppliers': ('analytics_suppliers(FALSE,', 'supplier_rank'),
    'category_suppliers': ('analytics_suppliers(TRUE,', 'group_value COLLATE "C" NULLS LAST,supplier_rank'),
    'concentration': ('analytics_concentration(FALSE,', 'group_value'),
    'category_concentration': ('analytics_concentration(TRUE,', 'hhi DESC NULLS LAST,positive_gbp DESC,group_value COLLATE "C" NULLS LAST'),
    'monthly': ('analytics_monthly(', 'reporting_month'),
    'supplier_monthly': ('analytics_supplier_monthly(', 'canonical_name COLLATE "C",supplier_id,reporting_month'),
}


def validate_filters(filters=None):
    supplied = dict(filters or {})
    if set(supplied) - set(FILTER_TYPES):
        raise ValueError('Unsupported analytics filter')
    values = {key: supplied.get(key) for key in FILTER_TYPES}
    for key in ('start_month', 'end_month'):
        value = values[key]
        if value is not None:
            if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}', value):
                value = date.fromisoformat(value + '-01')
            if type(value) is not date or value.day != 1:
                raise ValueError(f'{key} must be YYYY-MM or a first-of-month date')
            values[key] = value
    if values['start_month'] and values['end_month'] and values['start_month'] > values['end_month']:
        raise ValueError('Start month must not follow end month')
    supplier_id = values['supplier_id']
    if supplier_id is not None and (type(supplier_id) is not int or supplier_id <= 0):
        raise ValueError('supplier_id must be a positive integer')
    for key in ('expense_type', 'expense_area', 'entity'):
        if values[key] is not None and not isinstance(values[key], str):
            raise ValueError(f'{key} must be text')
    return values


def execute_query(conn, name, filters=None):
    if name not in QUERIES:
        raise ValueError('Unknown analytical output')
    function, order = QUERIES[name]
    return conn.execute(text(f'SELECT * FROM procureiq.{function}{ARGS}) ORDER BY {order}'), validate_filters(filters))


def query(conn, name, filters=None):
    return [dict(row) for row in execute_query(conn, name, filters).mappings()]


def source_lines(conn, filters=None):
    return [dict(row) for row in conn.execute(text(
        f'SELECT a.*,s.normalized_key FROM procureiq.analytics_lines({ARGS}) a '
        'LEFT JOIN procureiq.supplier s USING(supplier_id) ORDER BY a.spend_line_id'),
        validate_filters(filters)).mappings()]
