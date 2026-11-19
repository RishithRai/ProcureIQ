"""Immutable source acquisition with a separate, auditable receipt ledger."""
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def fetch(url, attempts=3, timeout=45):
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'ProcureIQ/0.1'}), timeout=timeout) as response:
                body = response.read()
            if not body or body.lstrip().lower().startswith((b'<!doctype html', b'<html')):
                raise ValueError('Empty response or HTML instead of source CSV')
            return body
        except (URLError, TimeoutError, OSError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)


def acquire(root, offline=False):
    sources = json.loads((root / 'manifests/hmrc_sources.json').read_text())
    ledger = root / 'manifests/download_manifest.json'
    receipts = json.loads(ledger.read_text()) if ledger.exists() else []
    indexed = {r['reporting_month']: r for r in receipts}
    results = []
    for source in sources:
        path = root / 'data/raw' / source['filename']
        path.parent.mkdir(parents=True, exist_ok=True)
        previous = indexed.get(source['reporting_month'])
        receipt = dict(source)
        try:
            if path.exists():
                body = path.read_bytes()
                if previous and previous.get('sha256'):
                    if (digest(body) != previous['sha256'] or len(body) != previous['size_bytes']
                            or previous['url'] != source['url']):
                        raise ValueError('Existing source differs from receipt; preserve and investigate')
                    receipt = dict(previous)
                    if previous['status'] == 'manual_unverified':
                        if not offline and body != fetch(source['url']):
                            raise ValueError('Manual source differs from official download')
                        receipt['status'] = 'manual_unverified' if offline else 'verified'
                    else:
                        receipt['status'] = 'verified'
                else:
                    # Offline imports establish local integrity, not official byte equivalence.
                    if not offline and body != fetch(source['url']):
                        raise ValueError('Unregistered local file differs from official download')
                    receipt.update(status='manual_unverified' if offline else 'verified',
                                   downloaded_at=None, registered_at=datetime.now(timezone.utc).isoformat())
            elif offline:
                raise FileNotFoundError('Place the official file at ' + str(path))
            else:
                body = fetch(source['url'])
                if previous and previous.get('sha256') and digest(body) != previous['sha256']:
                    raise ValueError('Official bytes changed since frozen receipt; explicit new source version required')
                # Exclusive creation: never replace a source, even during a concurrent run.
                with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as output:
                    temporary = Path(output.name)
                    try:
                        output.write(body)
                        output.flush()
                        os.fsync(output.fileno())
                        os.link(temporary, path)
                    finally:
                        temporary.unlink(missing_ok=True)
                receipt.update(status='downloaded', downloaded_at=datetime.now(timezone.utc).isoformat())
            receipt.update(sha256=digest(body), size_bytes=len(body))
            indexed[source['reporting_month']] = receipt
        except (OSError, ValueError) as error:
            receipt.update(status='failed', error=str(error))
        results.append(receipt)
        save_json(ledger, list(indexed.values()))
    save_json(root / 'manifests/acquisition_status.json', results)
    return results
