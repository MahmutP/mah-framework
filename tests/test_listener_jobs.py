"""Listener registry and jobs command tests."""

from unittest.mock import MagicMock

from core.listener_registry import ListenerRegistry, get_listener_registry
from commands.jobs import Jobs


def test_registry_register_and_stop():
    reg = ListenerRegistry()
    handler = MagicMock()
    handler.running = True
    jid = reg.register(
        handler, payload="payloads/python/chimera", lhost="0.0.0.0", lport=4444
    )
    assert jid == 1
    assert len(reg.list_jobs()) == 1
    assert reg.stop(jid) is True
    handler.stop.assert_called_once()
    assert reg.list_jobs() == []


def test_registry_stop_all():
    reg = ListenerRegistry()
    h1, h2 = MagicMock(), MagicMock()
    h1.running = h2.running = True
    reg.register(h1, payload="a", lhost="0.0.0.0", lport=1)
    reg.register(h2, payload="b", lhost="0.0.0.0", lport=2)
    assert reg.stop_all() == 2
    assert reg.list_jobs() == []


def test_jobs_command_list_empty(capsys):
    # Izole registry için yeni instance kullan — get_listener_registry singleton
    # yerine Jobs doğrudan _list'e mock registry
    cmd = Jobs()
    reg = ListenerRegistry()
    assert cmd._list(reg) is True
    out = capsys.readouterr().out
    assert "Aktif dinleyici yok" in out


def test_jobs_command_kill():
    cmd = Jobs()
    # Gerçek singleton'a yazıp temizle
    reg = get_listener_registry()
    reg.stop_all()
    handler = MagicMock()
    handler.running = True
    jid = reg.register(
        handler, payload="payloads/x", lhost="127.0.0.1", lport=9
    )
    assert cmd.execute("-k", str(jid)) is True
    handler.stop.assert_called()
