"""Session Notifier plugin birim testleri."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from core.hooks import HookType
from plugins.session_notifier import SessionNotifier


def test_hooks_registered():
    plugin = SessionNotifier()
    hooks = plugin.get_hooks()
    assert HookType.ON_SESSION_OPEN in hooks
    assert HookType.ON_SESSION_CLOSE in hooks
    assert HookType.ON_SHUTDOWN in hooks


def test_session_open_close_tracking(tmp_path: Path):
    plugin = SessionNotifier()
    plugin.log_dir = tmp_path
    plugin.log_file = tmp_path / "sessions.log"
    plugin._config = {"log_to_file": True, "verbose": False}

    plugin.on_session_open(
        session_id=1,
        info={"host": "127.0.0.1", "port": 4444, "type": "reverse_tcp"},
    )
    assert plugin._open_count == 1
    assert 1 in plugin._active
    assert plugin._active[1]["host"] == "127.0.0.1"

    plugin.on_session_close(session_id=1)
    assert plugin._close_count == 1
    assert 1 not in plugin._active
    assert plugin.log_file.exists()
    text = plugin.log_file.read_text(encoding="utf-8")
    assert "OPEN" in text
    assert "CLOSE" in text
    assert "127.0.0.1:4444" in text


def test_session_close_without_open():
    plugin = SessionNotifier()
    plugin._config = {"log_to_file": False, "verbose": False}
    plugin.on_session_close(session_id=99)
    assert plugin._close_count == 1
    assert plugin._active == {}


def test_on_shutdown_summary():
    plugin = SessionNotifier()
    plugin._config = {"log_to_file": False, "verbose": False}
    plugin._open_count = 2
    plugin._close_count = 1
    plugin._active[7] = {
        "host": "10.0.0.1",
        "port": 5555,
        "type": "http",
        "opened_at": datetime.now(),
    }
    with patch("plugins.session_notifier.print") as mock_print:
        plugin.on_shutdown()
    mock_print.assert_called()
    msg = str(mock_print.call_args[0][0])
    assert "2 açılış" in msg
    assert "1 kapanış" in msg
