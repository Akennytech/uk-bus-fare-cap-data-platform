"""Unit tests for the NaPTAN ingestion script.

Uses `responses`-style mocking via monkeypatch so tests never hit the real
network — this is what the CI workflow runs on every pull request.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "ingestion"))

import naptan_ingest  # noqa: E402


class DummyResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_naptan_returns_bytes(monkeypatch):
    fake_csv = b"ATCOCode,CommonName,Status\n1800001,Test Stop,active\n"

    def fake_get(url, timeout):
        assert "naptan" in url.lower()
        return DummyResponse(fake_csv)

    monkeypatch.setattr(naptan_ingest.requests, "get", fake_get)

    result = naptan_ingest.fetch_naptan()
    assert result == fake_csv


def test_fetch_naptan_raises_on_http_error(monkeypatch):
    def fake_get(url, timeout):
        return DummyResponse(b"", status_code=500)

    monkeypatch.setattr(naptan_ingest.requests, "get", fake_get)

    try:
        naptan_ingest.fetch_naptan()
        assert False, "expected an exception on HTTP 500"
    except RuntimeError:
        pass
