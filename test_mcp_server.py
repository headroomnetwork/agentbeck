"""Agent Beck — MCP server (plug) test suite.

Mocks the HTTP backend so no real Agent Beck instance needs to be running.
Run: pytest test_mcp_server.py -v
"""
from unittest.mock import patch, MagicMock

import pytest

import mcp_server as mcp


class _FakeResponse:
    """Stand-in for httpx.Response."""

    def __init__(self, json_data=None, status_code=200, text=""):
        self._json = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class FakeClient:
    """Context-manager mock for httpx.Client."""

    def __init__(self, responses):
        # responses: list of _FakeResponse, consumed in order
        self._responses = list(responses)
        self._idx = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, path, **kwargs):
        r = self._responses[self._idx]
        self._idx += 1
        return r

    def post(self, path, **kwargs):
        r = self._responses[self._idx]
        self._idx += 1
        return r


def _fake_client(responses):
    return FakeClient(responses)


# ---------------------------------------------------------------------------
# agentbeck_search
# ---------------------------------------------------------------------------


def test_search_found():
    resp = _FakeResponse(
        json_data={
            "results": [
                {
                    "id": 1,
                    "error": "database is locked",
                    "fix": "enable WAL mode",
                    "environment": "Python sqlite3",
                    "tags": "sqlite wal",
                    "confirmations": 5,
                }
            ]
        }
    )
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_search("database locked")
        assert "Found 1 known fix" in result
        assert "database is locked" in result
        assert "enable WAL mode" in result
        assert '"confirmations": 5' in result
        assert "agentbeck_confirm" in result


def test_search_not_found():
    resp = _FakeResponse(json_data={"results": []})
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_search("xyznonexistent")
        assert "No known fix" in result
        assert "agentbeck_share" in result


def test_search_backend_down():
    def boom():
        raise RuntimeError("connection refused")

    with patch.object(mcp, "_client", side_effect=boom):
        result = mcp.agentbeck_search("anything")
        assert "Could not reach Agent Beck" in result


# ---------------------------------------------------------------------------
# agentbeck_share
# ---------------------------------------------------------------------------


def test_share_success():
    resp = _FakeResponse(json_data={"report": {"id": 42}})
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_share(
            error="new bug", fix="new fix", environment="Python 3.13", tags="python"
        )
        assert "Shared to Agent Beck as report #42" in result


def test_share_backend_down():
    def boom():
        raise RuntimeError("connection refused")

    with patch.object(mcp, "_client", side_effect=boom):
        result = mcp.agentbeck_share("e", "f")
        assert "Could not share" in result


# ---------------------------------------------------------------------------
# agentbeck_confirm
# ---------------------------------------------------------------------------


def test_confirm_success():
    resp = _FakeResponse(json_data={"report": {"id": 1, "confirmations": 7}})
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_confirm(1)
        assert "Confirmed report #1" in result
        assert "7" in result


def test_confirm_not_found():
    resp = _FakeResponse(status_code=404)
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_confirm(999)
        assert "No report #999" in result


def test_confirm_backend_down():
    def boom():
        raise RuntimeError("connection refused")

    with patch.object(mcp, "_client", side_effect=boom):
        result = mcp.agentbeck_confirm(1)
        assert "Could not confirm" in result


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# agentbeck_should_share
# ---------------------------------------------------------------------------


def test_should_share_already_exists():
    resp = _FakeResponse(
        json_data={
            "results": [
                {
                    "id": 7,
                    "error": "database is locked",
                    "fix": "enable WAL mode",
                    "confirmations": 3,
                }
            ]
        }
    )
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_should_share("database is locked", "enable WAL mode")
        assert "already in Agent Beck" in result
        assert "report #7" in result


def test_should_share_not_found():
    resp = _FakeResponse(json_data={"results": []})
    with patch.object(mcp, "_client", lambda: _fake_client([resp])):
        result = mcp.agentbeck_should_share("brand new error xyz", "restart everything")
        assert "Would you mind if I shared this fix back" in result
        assert "brand new error xyz" in result
        assert "restart everything" in result
        assert "anonymous" in result.lower()


def test_should_share_backend_down():
    def boom():
        raise RuntimeError("connection refused")

    with patch.object(mcp, "_client", side_effect=boom):
        result = mcp.agentbeck_should_share("e", "f")
        assert "Could not reach Agent Beck" in result


def test_url_from_env(monkeypatch):
    monkeypatch.setenv("AGENTBECK_URL", "https://beck.example.com")
    # reload the module-level constant by re-import logic
    import importlib
    import mcp_server as ms
    importlib.reload(ms)
    assert ms.AGENTBECK_URL == "https://beck.example.com"
    # restore default
    monkeypatch.delenv("AGENTBECK_URL", raising=False)
    importlib.reload(ms)
