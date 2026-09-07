"""Session Notifier Plugin for Mah Framework.

Yeni oturum açılış/kapanışlarını konsola bildirir ve kısa bir oturum günlüğü tutar.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from rich import print

from core.hooks import HookType
from core.plugin import BasePlugin


class SessionNotifier(BasePlugin):
    """Oturum açılış ve kapanışlarını bildiren eklenti."""

    Name: str = "Session Notifier"
    Description: str = "Oturum açılış/kapanış bildirimleri ve kısa oturum günlüğü"
    Author: str = "Mahmut P."
    Version: str = "1.0.0"
    Enabled: bool = True
    Priority: int = 80

    DefaultConfig: dict = {
        "log_to_file": True,
        "verbose": True,
    }

    def __init__(self) -> None:
        super().__init__()
        self.log_dir = Path("config") / "logs"
        self.log_file = self.log_dir / "sessions.log"
        self._open_count = 0
        self._close_count = 0
        self._active: dict[int, dict[str, Any]] = {}
        self._config: dict[str, Any] = dict(self.DefaultConfig)

    def on_load(self) -> None:
        with contextlib.suppress(Exception):
            self._config = {**self.DefaultConfig, **self.get_config()}
        if self._config.get("log_to_file"):
            with contextlib.suppress(Exception):
                self.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Plugin] {self.Name} aktif")

    def on_unload(self) -> None:
        remaining = len(self._active)
        if remaining:
            print(
                f"[Plugin] {self.Name}: kapanışta {remaining} aktif oturum kaydı temizlendi"
            )
        self._active.clear()
        print(f"[Plugin] {self.Name} kapatıldı")

    def get_hooks(self) -> dict[HookType, Callable[..., Any]]:
        return {
            HookType.ON_SESSION_OPEN: self.on_session_open,
            HookType.ON_SESSION_CLOSE: self.on_session_close,
            HookType.ON_SHUTDOWN: self.on_shutdown,
        }

    def on_session_open(
        self,
        session_id: int | None = None,
        info: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if session_id is None:
            return
        info = info or {}
        host = info.get("host") or info.get("ip") or info.get("rhost") or "?"
        port = info.get("port") or info.get("rport") or "?"
        stype = info.get("type") or "Generic"
        opened_at = datetime.now()

        self._open_count += 1
        self._active[int(session_id)] = {
            "host": host,
            "port": port,
            "type": stype,
            "opened_at": opened_at,
        }

        msg = f"Session #{session_id} açıldı ({stype}) {host}:{port}"
        if self._config.get("verbose", True):
            print(f"[bold green][Session][/bold green] {msg}")
        self._write_log("OPEN", msg)

    def on_session_close(self, session_id: int | None = None, **kwargs: Any) -> None:
        if session_id is None:
            return
        sid = int(session_id)
        meta = self._active.pop(sid, None)
        self._close_count += 1

        duration = ""
        detail = f"Session #{sid} kapandı"
        if meta:
            elapsed = datetime.now() - meta["opened_at"]
            secs = int(elapsed.total_seconds())
            duration = f" ({secs}s)"
            detail = (
                f"Session #{sid} kapandı ({meta['type']}) "
                f"{meta['host']}:{meta['port']}{duration}"
            )

        if self._config.get("verbose", True):
            print(f"[bold yellow][Session][/bold yellow] {detail}")
        self._write_log("CLOSE", detail)

    def on_shutdown(self, **kwargs: Any) -> None:
        summary = (
            f"Özet: {self._open_count} açılış, {self._close_count} kapanış, "
            f"{len(self._active)} hâlâ aktif"
        )
        print(f"[Plugin] {self.Name} — {summary}")
        self._write_log("SUMMARY", summary)

    def _write_log(self, event: str, details: str) -> None:
        if not self._config.get("log_to_file", True):
            return
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            line = f"[{datetime.now().isoformat()}] {event}: {details}\n"
            with open(self.log_file, "a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception as exc:
            print(f"[Session Notifier Hatası] {exc}")
