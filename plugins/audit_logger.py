"""Audit Logger Plugin for Mah Framework."""

import atexit
import contextlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from core.hooks import HookType
from core.plugin import BasePlugin


class AuditLogger(BasePlugin):
    """Tüm komut ve modül çalışmalarını loglayan denetim eklentisi."""

    Name: str = "Audit Logger"
    Description: str = "Tüm komut ve modül çalışmalarını loglar"
    Author: str = "Mahmut P."
    Version: str = "1.0.0"
    Enabled: bool = True
    Priority: int = 100

    def __init__(self) -> None:
        super().__init__()
        self.log_dir = Path("config/logs")
        self.log_file = self.log_dir / "audit.log"
        self._buffer: list[str] = []
        self._buffer_limit = 16
        self._fh: Any = None

        if not self.log_dir.exists():
            with contextlib.suppress(Exception):
                self.log_dir.mkdir(parents=True, exist_ok=True)

        atexit.register(self._flush)

    def on_load(self) -> None:
        print("[Plugin] Audit Logger aktif")
        self._write_log("SYSTEM", "Audit Logger aktif")

    def on_unload(self) -> None:
        print("Audit Logger kapatıldı")
        self._write_log("SYSTEM", "Audit Logger kapatıldı")
        self._flush()
        if self._fh is not None:
            with contextlib.suppress(Exception):
                self._fh.close()
            self._fh = None

    def get_hooks(self) -> dict[HookType, Callable[..., Any]]:
        return {
            HookType.PRE_COMMAND: self.on_pre_command,
            HookType.POST_MODULE_RUN: self.on_post_module_run,
        }

    def on_pre_command(self, command_line: str, **kwargs: Any) -> None:
        self._write_log("COMMAND", f"Exec: {command_line}")

    def on_post_module_run(
        self, module_path: str, success: bool, **kwargs: Any
    ) -> None:
        status = "SUCCESS" if success else "FAILED"
        self._write_log("MODULE", f"Run: {module_path} Status: {status}")

    def _ensure_fh(self) -> Any:
        if self._fh is None or self._fh.closed:
            self._fh = open(self.log_file, "a", encoding="utf-8", buffering=8192)
        return self._fh

    def _write_log(self, event_type: str, details: str) -> None:
        try:
            timestamp = datetime.now().isoformat()
            log_line = f"[{timestamp}] {event_type}: {details}\n"
            self._buffer.append(log_line)
            if len(self._buffer) >= self._buffer_limit:
                self._flush()
        except Exception as e:
            print(f"[Audit Logger Hatası] {e}")

    def _flush(self) -> None:
        if not self._buffer:
            return
        try:
            fh = self._ensure_fh()
            fh.writelines(self._buffer)
            fh.flush()
            self._buffer.clear()
        except Exception as e:
            print(f"[Audit Logger Hatası] {e}")
