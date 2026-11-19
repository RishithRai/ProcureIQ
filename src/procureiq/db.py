"""Small checksum-verified SQL migration runner; PostgreSQL only."""
import os
from hashlib import sha256
from sqlalchemy import create_engine, MetaData, text

LOCK = 7102026002


def engine_from_env(variable='DATABASE_URL'):
    url = os.environ.get(variable)
    if not url:
        raise ValueError(f'Set {variable}; see .env.example (environment is not loaded automatically)')
    if not url.startswith('postgresql+psycopg://'):
        raise ValueError('Use a postgresql+psycopg:// URL')
    return create_engine(url, hide_parameters=True)


def initialize(engine, root):
    migrations = sorted((root / 'sql').glob('[0-9]*.sql'))
    if not migrations:
        raise ValueError('No SQL migrations found; --root must point to the repository')
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': LOCK})
        conn.exec_driver_sql('CREATE SCHEMA IF NOT EXISTS procureiq')
        conn.exec_driver_sql('SET LOCAL search_path TO procureiq, public')
        conn.exec_driver_sql('CREATE TABLE IF NOT EXISTS schema_migration '
                             '(name TEXT PRIMARY KEY, sha256 CHAR(64) NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        for path in migrations:
            checksum = sha256(path.read_bytes()).hexdigest()
            old = conn.execute(text('SELECT sha256 FROM schema_migration WHERE name=:name'), {'name': path.name}).scalar()
            if old:
                if old != checksum:
                    raise ValueError(f'Applied migration changed: {path.name}')
                continue
            conn.exec_driver_sql(path.read_text())
            conn.execute(text('INSERT INTO schema_migration(name,sha256) VALUES (:name,:sha)'),
                         {'name': path.name, 'sha': checksum})


def tables(engine):
    metadata = MetaData(schema='procureiq')
    metadata.reflect(engine, only=['source_file', 'raw_spend_row', 'spend_line', 'supplier', 'supplier_alias', 'data_quality_issue'])
    return {t.name: t for t in metadata.tables.values()}
