"""Exact financial display/export, separate from visualization-only floats."""
import csv
from io import StringIO
from decimal import Decimal

ALL = ('all_values',)  # A real option, distinct from Streamlit's unselected None.


def money(value):
    return 'Not available' if value is None else f'£{value:,.2f}'


def display_rows(rows):
    return [{k: (str(v) if isinstance(v,Decimal) else v) for k,v in row.items()} for row in rows]


def csv_bytes(rows):
    out = StringIO()
    if rows:
        w=csv.DictWriter(out,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    return out.getvalue().encode('utf-8-sig')


def reset_filters(state):
    for key in list(state):
        if key.startswith('filter_'):
            if key == 'filter_period':
                if '_period_default' in state:
                    state[key] = state['_period_default']
                else:
                    del state[key]
            else:
                # Explicit assignment also resets the browser's widget value. Deletion
                # alone can let a later frontend event restore the old selection.
                state[key] = ALL
        elif key == 'radar_minimum':
            state[key] = 0
        elif key == 'radar_type':
            state[key] = None
        elif key.startswith('table_') and key.endswith('_search'):
            state[key] = ''
        elif key.startswith('table_') and key.endswith('_desc'):
            state[key] = False
        elif key.startswith(('detail_', 'table_', 'evidence_', 'radar_')):
            del state[key]


def selected_filters(options, period, expense_type=None, expense_area=None, entity=None, supplier_id=None):
    from procureiq.queries import validate_filters
    # Full available range preserves the CLI's unfiltered opportunity IDs and basis.
    full = (options['months'][0], options['months'][-1])
    return validate_filters(dict(start_month=None if period==full else period[0],
        end_month=None if period==full else period[1],expense_type=expense_type,
        expense_area=expense_area,entity=entity,supplier_id=supplier_id))
