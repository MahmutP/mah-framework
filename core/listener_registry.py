# Aktif dinleyicileri (multi/handler job'ları) izler.

from __future__ import annotations

import itertools
import threading
from typing import Any


class ListenerRegistry:
    """Çalışan payload handler dinleyicilerini takip eder."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[int, dict[str, Any]] = {}
        self._id_seq = itertools.count(1)

    def register(
        self,
        handler: Any,
        *,
        payload: str,
        lhost: str,
        lport: int,
        thread: threading.Thread | None = None,
        background: bool = True,
    ) -> int:
        job_id = next(self._id_seq)
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "handler": handler,
                "payload": payload,
                "lhost": lhost,
                "lport": lport,
                "thread": thread,
                "background": background,
            }
        return job_id

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            # Bitmiş dinleyicileri temizle
            dead = [
                jid
                for jid, job in self._jobs.items()
                if job.get("handler") is not None
                and not getattr(job["handler"], "running", False)
                and (
                    job.get("thread") is None
                    or not job["thread"].is_alive()
                )
            ]
            for jid in dead:
                self._jobs.pop(jid, None)
            return [dict(j) for j in self._jobs.values()]

    def get(self, job_id: int) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def stop(self, job_id: int) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if not job:
            return False
        handler = job.get("handler")
        if handler is not None and hasattr(handler, "stop"):
            try:
                handler.stop()
            except Exception:
                pass
        return True

    def stop_all(self) -> int:
        with self._lock:
            ids = list(self._jobs.keys())
        stopped = 0
        for jid in ids:
            if self.stop(jid):
                stopped += 1
        return stopped


_registry: ListenerRegistry | None = None


def get_listener_registry() -> ListenerRegistry:
    global _registry
    if _registry is None:
        _registry = ListenerRegistry()
    return _registry
