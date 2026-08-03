"""Aktif payload dinleyicilerini listele / durdur."""

from typing import Any

from rich import print

from core.command import Command
from core.listener_registry import get_listener_registry


class Jobs(Command):
    Name = "jobs"
    Description = "Arka plan dinleyicilerini (handler job) listeler ve durdurur."
    Category = "core"
    Aliases = ["listeners"]
    Usage = "jobs [-l | -k <id> | -K]"
    Examples = [
        "jobs                 # Aktif dinleyicileri listele",
        "jobs -l              # Aynı",
        "jobs -k 1            # Job 1'i durdur (CTRL+C yerine bunu kullan)",
        "jobs -K              # Tüm dinleyicileri durdur",
    ]

    def execute(self, *args: str, **kwargs: Any) -> bool:
        registry = get_listener_registry()

        if not args or args[0] in ("-l", "list", "ls"):
            return self._list(registry)

        sub = args[0]
        if sub in ("-k", "kill") and len(args) > 1:
            try:
                job_id = int(args[1])
            except ValueError:
                print("[!] Geçersiz job ID.")
                return False
            if registry.stop(job_id):
                print(f"[*] Job {job_id} durduruldu.")
                return True
            print(f"[!] Job {job_id} bulunamadı.")
            return False

        if sub in ("-K", "killall"):
            n = registry.stop_all()
            print(f"[*] {n} dinleyici durduruldu.")
            return True

        print(f"Kullanım: {self.Usage}")
        return False

    def _list(self, registry) -> bool:
        jobs = registry.list_jobs()
        if not jobs:
            print("Aktif dinleyici yok.")
            return True

        print()
        print(f"{'Id':<4} {'Payload':<40} {'Bind':<22} {'BG'}")
        print("-" * 75)
        for job in jobs:
            bind = f"{job.get('lhost')}:{job.get('lport')}"
            bg = "yes" if job.get("background") else "no"
            handler = job.get("handler")
            alive = ""
            if handler is not None and not getattr(handler, "running", False):
                alive = " (stopped)"
            print(
                f"{job['id']:<4} {str(job.get('payload', '')):<40} "
                f"{bind:<22} {bg}{alive}"
            )
        print()
        print("[*] Durdurmak: jobs -k <id>   |   hepsi: jobs -K")
        return True
