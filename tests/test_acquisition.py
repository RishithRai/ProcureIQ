import json
from urllib.error import URLError
import pytest
from procureiq import acquisition as a


@pytest.fixture
def root(tmp_path):
    (tmp_path / 'manifests').mkdir()
    (tmp_path / 'manifests/hmrc_sources.json').write_text(json.dumps([
        dict(reporting_month='2025-04', filename='test.csv', url='https://example.invalid/test.csv')]))
    return tmp_path


def test_download_rerun_and_tampering(root, monkeypatch):
    body = b'A,B\n1,2\n'
    monkeypatch.setattr(a, 'fetch', lambda url: body)
    assert a.acquire(root)[0]['status'] == 'downloaded'
    path = root / 'data/raw/test.csv'
    stat = path.stat().st_mtime_ns
    monkeypatch.setattr(a, 'fetch', lambda url: pytest.fail('Verified rerun must not download'))
    assert a.acquire(root)[0]['status'] == 'verified'
    assert path.stat().st_mtime_ns == stat
    path.write_bytes(b'changed')
    assert a.acquire(root)[0]['status'] == 'failed'
    assert path.read_bytes() == b'changed'
    assert json.loads((root / 'manifests/download_manifest.json').read_text())[0]['sha256'] == a.digest(body)


def test_manual_placement_is_not_claimed_as_official_verification(root):
    assert a.acquire(root, offline=True)[0]['status'] == 'failed'
    path = root / 'data/raw/test.csv'
    path.write_bytes(b'A,B\n1,2\n')
    receipt = a.acquire(root, offline=True)[0]
    assert receipt['status'] == 'manual_unverified'
    assert receipt['downloaded_at'] is None
    assert a.acquire(root, offline=True)[0]['status'] == 'manual_unverified'


def test_unregistered_conflict_preserves_original(root, monkeypatch):
    path = root / 'data/raw/test.csv'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'local')
    monkeypatch.setattr(a, 'fetch', lambda url: b'official')
    assert a.acquire(root)[0]['status'] == 'failed'
    assert path.read_bytes() == b'local'


def test_failure_is_recorded_and_retry_bounded(root, monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(kwargs['timeout'])
        raise URLError('network unavailable')
    monkeypatch.setattr(a, 'urlopen', fail)
    monkeypatch.setattr(a.time, 'sleep', lambda _: None)
    assert a.acquire(root)[0]['status'] == 'failed'
    assert calls == [45, 45, 45]
    assert not (root / 'data/raw/test.csv').exists()


def test_revised_remote_file_requires_new_version(root, monkeypatch):
    monkeypatch.setattr(a, 'fetch', lambda url: b'A,B\n1,2\n')
    a.acquire(root)
    path = root / 'data/raw/test.csv'
    path.unlink()
    monkeypatch.setattr(a, 'fetch', lambda url: b'A,B\n3,4\n')
    assert a.acquire(root)[0]['status'] == 'failed'
    assert not path.exists()
