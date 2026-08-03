# =============================================================================
# Session bridge, workspace, Chimera post modül testleri
# =============================================================================

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.context import set_global_context
from core.session_bridge import (
    is_chimera_session,
    load_and_run_on_chimera,
    resolve_session,
    run_chimera_post_module,
    warn_localhost_without_session,
)
from core.shared_state import shared_state
from core.workspace_manager import WorkspaceManager
from modules.post.chimera.cred_harvest import AGENT_CODE as CRED_AGENT
from modules.post.chimera.cred_harvest import cred_harvest
from modules.post.chimera.enum_system import AGENT_CODE as ENUM_AGENT
from modules.post.chimera.enum_system import enum_system
from modules.post.chimera.env_secrets import env_secrets
from modules.post.chimera.process_av_check import process_av_check
from tests.test_helpers import make_test_context


@pytest.fixture
def ctx():
    context = make_test_context()
    set_global_context(context)
    return context


# ── Session bridge ───────────────────────────────────────────────────────────


class TestSessionBridge:
    def test_resolve_session_missing(self, ctx):
        ctx.session_manager.get_session.return_value = None
        assert resolve_session(99) is None

    def test_resolve_session_ok(self, ctx):
        session = {"id": 1, "type": "Chimera", "handler": MagicMock()}
        ctx.session_manager.get_session.return_value = session
        assert resolve_session("1") is session

    def test_is_chimera_session(self):
        assert is_chimera_session({"type": "Chimera"}) is True
        assert is_chimera_session({"type": "Bind", "info": {"type": "Chimera"}}) is True
        assert is_chimera_session({"type": "Bind", "info": {}}) is False

    def test_load_and_run_on_chimera(self, ctx):
        handler = MagicMock()
        handler.send_data = MagicMock()
        handler.recv_data = MagicMock(side_effect=["[+] loaded", "ENUM_OK"])
        session = {"id": 1, "type": "Chimera", "handler": handler}
        ctx.session_manager.get_session.return_value = session

        result = load_and_run_on_chimera(
            1, "enum_system", agent_source="def run():\n    return 'ok'\n"
        )
        assert result == "ENUM_OK"
        assert handler.send_data.call_count == 2
        first_cmd = handler.send_data.call_args_list[0][0][0]
        assert first_cmd.startswith("loadmodule enum_system ")
        second_cmd = handler.send_data.call_args_list[1][0][0]
        assert second_cmd == "runmodule enum_system run"

    def test_load_rejects_non_chimera(self, ctx):
        handler = MagicMock()
        session = {"id": 2, "type": "Bind", "info": {}, "handler": handler}
        ctx.session_manager.get_session.return_value = session
        assert load_and_run_on_chimera(2, "x", agent_source="def run():\n return 'a'\n") is None
        handler.send_data.assert_not_called()

    def test_run_chimera_post_requires_session(self, ctx):
        assert run_chimera_post_module({}, "enum_system", "def run():\n return 'x'\n") is False

    def test_warn_localhost(self, capsys):
        warn_localhost_without_session("TestMod")
        out = capsys.readouterr().out
        assert "SESSION" in out
        assert "localhost" in out.lower() or "localhost" in out


# ── Workspace manager ────────────────────────────────────────────────────────


class TestWorkspaceManager:
    def test_create_list_use_delete(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path / "workspaces")
        path = wm.create("lab1")
        assert path.is_dir()
        assert (path / "hosts").is_dir()
        assert (path / "loot").is_dir()
        assert "lab1" in wm.list_workspaces()
        assert wm.active_name == "lab1"

        wm.create("lab2")
        wm.use("lab2")
        assert wm.active_name == "lab2"

        loot = wm.write_ports_loot("10.0.0.5", [22, 80])
        assert loot is not None
        data = json.loads(loot.read_text(encoding="utf-8"))
        assert data["open_ports"] == [22, 80]
        assert (wm.get_active_path() / "ports" / "10.0.0.5.json").is_file()

        save = wm.resolve_save_path("shot.png", category="screenshots")
        assert "loot" in str(save)
        assert save.name == "shot.png"

        wm.delete("lab2")
        assert "lab2" not in wm.list_workspaces()
        assert wm.active_name is None

    def test_resolve_without_active(self, tmp_path):
        wm = WorkspaceManager(root=tmp_path / "ws")
        p = wm.resolve_save_path("f.bin", category="downloads")
        assert p == Path.cwd() / "f.bin"


# ── Workspace command ────────────────────────────────────────────────────────


class TestWorkspaceCommand:
    def test_create_and_list(self, tmp_path, ctx):
        from commands.workspace import Workspace

        wm = WorkspaceManager(root=tmp_path / "workspaces")
        ctx.workspace_manager = wm
        cmd = Workspace()
        assert cmd.execute("create", "alpha") is True
        assert cmd.execute("list") is True
        assert cmd.execute("use", "alpha") is True
        assert wm.active_name == "alpha"


# ── Chimera post BaseModules ─────────────────────────────────────────────────


class TestChimeraPostModules:
    def test_enum_system_metadata(self):
        mod = enum_system()
        assert mod.Category == "post/chimera"
        assert "SESSION" in mod.Options
        assert "def run():" in ENUM_AGENT
        assert "import os" in ENUM_AGENT
        assert "from core" not in ENUM_AGENT

    def test_cred_harvest_metadata(self):
        mod = cred_harvest()
        assert mod.Name
        assert "SESSION" in mod.Options
        assert "from core" not in CRED_AGENT

    def test_env_and_av_metadata(self):
        assert "SESSION" in env_secrets().Options
        assert "SESSION" in process_av_check().Options

    def test_enum_run_via_bridge(self, ctx):
        handler = MagicMock()
        handler.send_data = MagicMock()
        handler.recv_data = MagicMock(side_effect=["ok", "report"])
        ctx.session_manager.get_session.return_value = {
            "id": 1,
            "type": "Chimera",
            "handler": handler,
        }
        mod = enum_system()
        assert mod.run({"SESSION": "1", "FUNC": "quick"}) is True
        assert "runmodule enum_system quick" in handler.send_data.call_args_list[1][0][0]

    def test_enum_run_without_session(self):
        mod = enum_system()
        assert mod.run({"SESSION": "", "FUNC": "run"}) is False

    def test_agent_code_executes_locally(self):
        """AGENT_CODE stdlib-only ve run() str döner (ajan simülasyonu)."""
        ns: dict = {}
        exec(ENUM_AGENT, ns)
        out = ns["quick"]()
        assert isinstance(out, str)
        assert "Hostname" in out or "hostname" in out.lower() or "CHIMERA" in out


# ── Port scanner loot ────────────────────────────────────────────────────────


class TestPortScannerLoot:
    def test_writes_loot_when_workspace_active(self, tmp_path, ctx):
        from modules.auxiliary.scanner.port_scanner import PortScanner

        wm = WorkspaceManager(root=tmp_path / "workspaces")
        wm.create("scanlab")
        ctx.workspace_manager = wm

        scanner = PortScanner()
        with patch.object(scanner, "scan_port", side_effect=lambda ip, p: p if p in (80, 443) else None):
            ok = scanner.run(
                {"RHOST": "127.0.0.1", "RPORTS": "80,443,9999", "THREADS": 2}
            )
        assert ok is True
        loot = wm.get_active_path() / "hosts" / "127.0.0.1" / "ports.json"
        assert loot.is_file()
        data = json.loads(loot.read_text(encoding="utf-8"))
        assert data["open_ports"] == [80, 443]
