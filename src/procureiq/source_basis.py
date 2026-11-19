"""Framework-independent active analytical source identity."""
from hashlib import sha256
from procureiq.analytics import snapshot_metadata
from procureiq.opportunities import canonical
from procureiq.queries import validate_filters


class SourceChanged(RuntimeError):
    """Reject mixed snapshots; refresh the source basis."""


def fingerprint(conn):
    return sha256(canonical(snapshot_metadata(conn, validate_filters())).encode()).hexdigest()
