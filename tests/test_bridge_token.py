"""The Python client must send the same bearer token the bridge creates in bridge.cfg."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from astra import bridge as bridge_module
from astra.bridge import Bridge
from astra.errors import BridgeError


def test_token_is_read_from_the_plugin_config(tmp_path, monkeypatch):
    gamedata = tmp_path / "GameData"
    plugin = gamedata / "KspAutomationBridge" / "PluginData"
    plugin.mkdir(parents=True)
    (plugin / "bridge.cfg").write_text("port = 48500\nauthToken = abc123def456\n", encoding="utf-8")
    monkeypatch.delenv("ASTRA_BRIDGE_TOKEN", raising=False)
    monkeypatch.setattr(bridge_module, "CONFIG", SimpleNamespace(gamedata_dir=gamedata))
    assert Bridge._read_token() == "abc123def456"


def test_missing_config_keeps_legacy_unauthenticated_bridge_working(tmp_path, monkeypatch):
    monkeypatch.delenv("ASTRA_BRIDGE_TOKEN", raising=False)
    monkeypatch.setattr(bridge_module, "CONFIG", SimpleNamespace(gamedata_dir=tmp_path))
    assert Bridge._read_token() is None


def test_explicit_token_environment_variable_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTRA_BRIDGE_TOKEN", "env-token")
    monkeypatch.setattr(bridge_module, "CONFIG", SimpleNamespace(gamedata_dir=tmp_path))
    assert Bridge._read_token() == "env-token"


@pytest.fixture
def local_http():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.seen_authorization = self.headers.get("Authorization")
            body = json.dumps({"ok": True, "value": 42}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def test_requests_carry_the_bearer_header(local_http, monkeypatch):
    monkeypatch.setenv("ASTRA_BRIDGE_TOKEN", "test-token")
    monkeypatch.setattr(bridge_module, "CONFIG", SimpleNamespace(gamedata_dir=None))
    client = Bridge(f"http://127.0.0.1:{local_http.server_port}")
    assert client.get("/value") == {"value": 42}
    assert local_http.seen_authorization == "Bearer test-token"


def test_nonlocal_bridge_url_is_refused():
    with pytest.raises(BridgeError):
        Bridge("http://example.com:48500")
