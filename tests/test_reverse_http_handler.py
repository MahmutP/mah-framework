"""
mahpreter/reverse_http Handler — birim testleri

Çalıştırma:
    pytest tests/test_reverse_http_handler.py -q
"""

import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

from core.session_manager import SessionManager
from core.shared_state import shared_state
from modules.payloads.mahpreter.reverse_http.handler import Handler


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def http_handler():
    shared_state.session_manager = SessionManager()
    port = _free_port()
    options = {"LHOST": "127.0.0.1", "LPORT": port}
    handler = Handler(options)
    thread = threading.Thread(target=handler.start, daemon=True)
    thread.start()

    for _ in range(50):
        if handler.sock is not None:
            break
        time.sleep(0.05)
    assert handler.sock is not None, "HTTP dinleyici başlamadı"

    yield handler, port

    handler.stop()
    thread.join(timeout=2)


def test_connect_returns_queued_command(http_handler):
    handler, port = http_handler
    agent_id = "42"
    base = f"http://127.0.0.1:{port}"

    with handler._lock:
        handler.cmd_queue[agent_id] = "whoami"

    with urllib.request.urlopen(f"{base}/connect/{agent_id}", timeout=2) as resp:
        assert resp.read().decode() == "whoami"

    with urllib.request.urlopen(f"{base}/connect/{agent_id}", timeout=2) as resp:
        assert resp.read().decode() == ""

    assert agent_id in handler.client_sessions
    sid = handler.client_sessions[agent_id]
    assert sid in shared_state.session_manager.get_all_sessions()


def test_output_delivers_to_waiting_event(http_handler):
    handler, port = http_handler
    agent_id = "77"
    base = f"http://127.0.0.1:{port}"

    # İlk poll oturumu açar
    with urllib.request.urlopen(f"{base}/connect/{agent_id}", timeout=2) as resp:
        resp.read()

    event = threading.Event()
    with handler._lock:
        handler.output_events[agent_id] = event
        handler.output_data[agent_id] = ""

    req = urllib.request.Request(
        f"{base}/output/{agent_id}",
        data=b"hello-from-agent",
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        assert resp.status == 200

    assert event.wait(timeout=2)
    assert handler.output_data[agent_id] == "hello-from-agent"


def test_unknown_path_404(http_handler):
    _, port = http_handler
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=2)
    assert exc.value.code == 404
