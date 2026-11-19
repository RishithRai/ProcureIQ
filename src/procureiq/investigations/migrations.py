"""Separate application ledger: never changes analytical migration fingerprints."""
from hashlib import sha256
from sqlalchemy import text


def initialize_app(engine, root):
    paths=sorted((root/'sql/app').glob('[0-9]*.sql'))
    if not paths:raise ValueError('Application migrations missing; run from repository root')
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(7102026010)'))
        conn.exec_driver_sql('CREATE SCHEMA IF NOT EXISTS procureiq_app')
        conn.exec_driver_sql('SET LOCAL search_path TO procureiq_app, public')
        conn.exec_driver_sql('CREATE TABLE IF NOT EXISTS schema_migration (name TEXT PRIMARY KEY, sha256 CHAR(64) NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        for path in paths:
            digest=sha256(path.read_bytes()).hexdigest()
            old=conn.execute(text('SELECT sha256 FROM schema_migration WHERE name=:name'),dict(name=path.name)).scalar()
            if old and old!=digest:raise ValueError('Applied application migration changed: '+path.name)
            if old:continue
            conn.exec_driver_sql(path.read_text())
            conn.execute(text('INSERT INTO schema_migration(name,sha256) VALUES (:name,:sha)'),dict(name=path.name,sha=digest))
