"""Lossless CSV strings, physical line provenance and strict typed parsing."""
import csv
import io
import re
from datetime import datetime
from decimal import Decimal
import pandas as pd


def money(value):
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r'-?£?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?', value):
        raise ValueError(f'Invalid money or precision: {value!r}')
    return Decimal(value.replace('£', '').replace(',', '')).quantize(Decimal('0.01'))


def payment_date(value):
    if not value.strip():
        return None, None
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date(), fmt
        except ValueError:
            pass
    raise ValueError(f'Unrecognized date: {value!r}')


def read_csv(path):
    data = path.read_bytes()
    if data.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    else:
        try:
            data.decode('utf-8')
            encoding = 'utf-8'  # ASCII-only data cannot distinguish compatible encodings.
        except UnicodeDecodeError:
            encoding = 'cp1252'
    text = data.decode(encoding, errors='strict')
    dialect = csv.Sniffer().sniff(text[:32768], delimiters=',;\t|')
    reader = csv.reader(io.StringIO(text, newline=''), dialect, strict=True)
    columns = next(reader)
    if len(set(columns)) != len(columns):
        raise ValueError('Duplicate headers require explicit positional mapping')
    rows, refs, issues = [], [], []
    previous_line = reader.line_num
    for record_number, row in enumerate(reader, 1):
        refs.append({'source_record_number': record_number, 'source_line_start': previous_line + 1,
                     'source_line_end': reader.line_num})
        previous_line = reader.line_num
        if len(row) != len(columns):
            issues.append({'source_record_number': record_number, 'code': 'ragged_row',
                           'expected': len(columns), 'actual': len(row), 'raw_values': row})
        rows.append(row)
    # Retain extra fields explicitly; never drop malformed records.
    width = max([len(columns)] + [len(r) for r in rows])
    extended = columns + [f'__extra_{i}' for i in range(width - len(columns))]
    frame = pd.DataFrame([r + [''] * (width - len(r)) for r in rows], columns=extended, dtype=str)
    return frame, columns, refs, issues, {'encoding': encoding, 'delimiter': dialect.delimiter,
                                        'ascii_only': data.isascii()}
