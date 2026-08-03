# Workspace / loot yönetimi — config/workspaces/<name>/ altında hosts, ports, files, notes, loot.

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


DEFAULT_WORKSPACES_ROOT = Path("config/workspaces")
WORKSPACE_SUBDIRS = ("hosts", "ports", "files", "notes", "loot")
ACTIVE_MARKER = ".active"


class WorkspaceManager:
    """Aktif workspace seçimi ve loot yolları."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_WORKSPACES_ROOT
        self._lock = threading.Lock()
        self._active: str | None = None
        self.root.mkdir(parents=True, exist_ok=True)
        self._restore_active()

    def _restore_active(self) -> None:
        marker = self.root / ACTIVE_MARKER
        if marker.is_file():
            name = marker.read_text(encoding="utf-8").strip()
            if name and (self.root / name).is_dir():
                self._active = name

    def _persist_active(self) -> None:
        marker = self.root / ACTIVE_MARKER
        if self._active:
            marker.write_text(self._active, encoding="utf-8")
        elif marker.exists():
            marker.unlink()

    def _workspace_path(self, name: str) -> Path:
        return self.root / name

    def list_workspaces(self) -> list[str]:
        if not self.root.is_dir():
            return []
        names = [
            p.name
            for p in sorted(self.root.iterdir())
            if p.is_dir() and not p.name.startswith(".")
        ]
        return names

    def create(self, name: str) -> Path:
        name = name.strip()
        if not name or "/" in name or "\\" in name or name.startswith("."):
            raise ValueError(f"Geçersiz workspace adı: {name!r}")

        path = self._workspace_path(name)
        with self._lock:
            path.mkdir(parents=True, exist_ok=True)
            for sub in WORKSPACE_SUBDIRS:
                (path / sub).mkdir(exist_ok=True)
            if self._active is None:
                self._active = name
                self._persist_active()
        return path

    def use(self, name: str) -> Path:
        name = name.strip()
        path = self._workspace_path(name)
        if not path.is_dir():
            raise FileNotFoundError(f"Workspace bulunamadı: {name}")
        with self._lock:
            self._active = name
            self._persist_active()
        return path

    def delete(self, name: str) -> None:
        import shutil

        name = name.strip()
        path = self._workspace_path(name)
        if not path.is_dir():
            raise FileNotFoundError(f"Workspace bulunamadı: {name}")
        with self._lock:
            shutil.rmtree(path)
            if self._active == name:
                self._active = None
                self._persist_active()

    @property
    def active_name(self) -> str | None:
        return self._active

    def get_active_path(self) -> Path | None:
        if not self._active:
            return None
        path = self._workspace_path(self._active)
        return path if path.is_dir() else None

    def get_loot_dir(self, ensure: bool = True) -> Path | None:
        """Aktif workspace loot/ dizini; yoksa None."""
        base = self.get_active_path()
        if base is None:
            return None
        loot = base / "loot"
        if ensure:
            loot.mkdir(parents=True, exist_ok=True)
        return loot

    def get_host_dir(self, host: str, ensure: bool = True) -> Path | None:
        base = self.get_active_path()
        if base is None:
            return None
        # Güvenli dizin adı
        safe = host.replace("/", "_").replace("\\", "_").replace("..", "_")
        host_dir = base / "hosts" / safe
        if ensure:
            host_dir.mkdir(parents=True, exist_ok=True)
        return host_dir

    def write_ports_loot(
        self, host: str, open_ports: list[int], extra: dict[str, Any] | None = None
    ) -> Path | None:
        """hosts/<ip>/ports.json yazar; aktif workspace yoksa None."""
        host_dir = self.get_host_dir(host, ensure=True)
        if host_dir is None:
            return None
        payload: dict[str, Any] = {
            "host": host,
            "open_ports": sorted(open_ports),
        }
        if extra:
            payload.update(extra)
        out = host_dir / "ports.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # ports/ altına da kopya (plan: ports)
        ports_dir = self.get_active_path()
        if ports_dir is not None:
            ports_root = ports_dir / "ports"
            ports_root.mkdir(exist_ok=True)
            (ports_root / f"{host.replace('/', '_')}.json").write_text(
                out.read_text(encoding="utf-8"), encoding="utf-8"
            )
        return out

    def resolve_save_path(
        self, filename: str, category: str = "loot"
    ) -> Path:
        """
        Aktif workspace varsa category/filename, yoksa CWD.
        category: loot | files | notes | screenshots (loot altında)
        """
        base = self.get_active_path()
        if base is None:
            return Path.cwd() / filename

        if category in ("screenshots", "media", "logs", "downloads"):
            target = base / "loot" / category
        elif category in WORKSPACE_SUBDIRS:
            target = base / category
        else:
            target = base / "loot"

        target.mkdir(parents=True, exist_ok=True)
        return target / filename


def get_workspace_manager() -> WorkspaceManager | None:
    """shared_state / AppContext üzerinden WorkspaceManager."""
    try:
        from core.shared_state import shared_state

        wm = getattr(shared_state, "workspace_manager", None)
        if wm is not None:
            return wm
    except Exception:
        pass
    return None
