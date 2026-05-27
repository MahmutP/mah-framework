# =============================================================================
# Auxiliary: Process Manager
# =============================================================================
# psutil tabanlı gelişmiş süreç yönetim modülü.
#
# KULLANIM:
#   1. use auxiliary/os/process_manager
#   2. set ACTION list
#   3. set SORT_BY cpu
#   4. set COUNT 20
#   5. run
#
#   6. set ACTION search
#   7. set FILTER python
#   8. run
#
#   9. set ACTION kill
#  10. set PID 12345
#  11. run
# =============================================================================

from typing import Any

import psutil  # type: ignore
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option


class process_manager(BaseModule):
    """Gelişmiş Süreç Yöneticisi

    Çalışan süreçleri listeler, filtreler, detaylı bilgi alır
    veya sonlandırır. psutil kütüphanesi kullanır.

    Desteklenen İşlemler:
        - **list**   : Süreçleri CPU/RAM/PID'ye göre sıralı listeler.
        - **search** : İsim filtresine göre süreç arar.
        - **info**   : Tek bir PID hakkında detaylı bilgi verir.
        - **kill**   : Belirtilen PID'li süreci sonlandırır.
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Process Manager"
    Description = "Gelişmiş süreç listeleme, filtreleme ve sonlandırma"
    Author = "Mahmut P."
    Category = "auxiliary/os"
    Version = "1.0"

    Requirements = {"python": ["psutil"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "ACTION": Option(
                name="ACTION",
                value="list",
                required=True,
                description="Yapılacak işlem: list / search / info / kill",
                choices=["list", "search", "info", "kill"],
            ),
            "PID": Option(
                name="PID",
                value="",
                required=False,
                description="Hedef süreç ID (info/kill için)",
                regex_check=True,
                regex=r"^\d*$",
            ),
            "FILTER": Option(
                name="FILTER",
                value="",
                required=False,
                description="Süreç isim filtresi (search için)",
            ),
            "SORT_BY": Option(
                name="SORT_BY",
                value="cpu",
                required=False,
                description="Sıralama kriteri: cpu, memory, pid",
                choices=["cpu", "memory", "pid"],
            ),
            "COUNT": Option(
                name="COUNT",
                value=25,
                required=False,
                description="Gösterilecek süreç sayısı",
                regex_check=True,
                regex=r"^\d+$",
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get_processes() -> list[dict[str, Any]]:
        """Çalışan tüm süreçleri toplar."""
        procs: list[dict[str, Any]] = []
        attrs = [
            "pid",
            "name",
            "username",
            "cpu_percent",
            "memory_percent",
            "status",
            "create_time",
            "cmdline",
        ]
        for proc in psutil.process_iter(attrs):
            try:
                info = proc.info
                cmdline = info.get("cmdline") or []
                procs.append(
                    {
                        "pid": info.get("pid", 0),
                        "name": (info.get("name") or "?")[:30],
                        "user": (info.get("username") or "-")[:15],
                        "cpu": info.get("cpu_percent", 0.0) or 0.0,
                        "mem": info.get("memory_percent", 0.0) or 0.0,
                        "status": info.get("status", "?"),
                        "cmd": " ".join(cmdline)[:60] if cmdline else "-",
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return procs

    # ── ACTIONS ──────────────────────────────────────────────────────────────

    def _action_list(self, sort_by: str, count: int) -> bool:
        """Süreçleri sıralayarak listeler."""
        procs = self._get_processes()
        sort_key = {"cpu": "cpu", "memory": "mem", "pid": "pid"}.get(sort_by, "cpu")
        procs.sort(key=lambda p: p[sort_key], reverse=(sort_key != "pid"))

        tbl = Table(
            title=f"📋 Süreç Listesi (Top {count}, sıra: {sort_by})",
            border_style="blue",
        )
        tbl.add_column("PID", style="dim", justify="right")
        tbl.add_column("İsim", style="cyan", max_width=30)
        tbl.add_column("Kullanıcı", style="dim", max_width=15)
        tbl.add_column("CPU%", justify="right")
        tbl.add_column("RAM%", justify="right")
        tbl.add_column("Durum", justify="center")
        tbl.add_column("Komut", style="dim", max_width=40)

        for p in procs[:count]:
            cpu_clr = "red" if p["cpu"] > 50 else "yellow" if p["cpu"] > 10 else "white"
            mem_clr = "red" if p["mem"] > 50 else "yellow" if p["mem"] > 10 else "white"
            tbl.add_row(
                str(p["pid"]),
                p["name"],
                p["user"],
                f"[{cpu_clr}]{p['cpu']:.1f}%[/{cpu_clr}]",
                f"[{mem_clr}]{p['mem']:.1f}%[/{mem_clr}]",
                p["status"],
                p["cmd"],
            )

        self.console.print(tbl)
        self.console.print(f"  [bold]Toplam çalışan süreç:[/bold] {len(procs)}")
        return True

    def _action_search(self, filt: str) -> bool:
        """İsim filtresine göre süreç arar."""
        if not filt:
            print("[bold red][-] FILTER seçeneği gereklidir.[/bold red]")
            return False

        procs = self._get_processes()
        matches = [
            p
            for p in procs
            if filt.lower() in p["name"].lower() or filt.lower() in p["cmd"].lower()
        ]

        tbl = Table(
            title=f"🔍 Arama: '{filt}' ({len(matches)} sonuç)", border_style="yellow"
        )
        tbl.add_column("PID", style="dim", justify="right")
        tbl.add_column("İsim", style="cyan", max_width=30)
        tbl.add_column("Kullanıcı", style="dim")
        tbl.add_column("CPU%", justify="right")
        tbl.add_column("RAM%", justify="right")
        tbl.add_column("Komut", style="dim", max_width=45)

        for p in matches:
            tbl.add_row(
                str(p["pid"]),
                p["name"],
                p["user"],
                f"{p['cpu']:.1f}%",
                f"{p['mem']:.1f}%",
                p["cmd"],
            )

        self.console.print(tbl)
        return True

    def _action_info(self, pid: int) -> bool:
        """Tek bir süreç hakkında detaylı bilgi verir."""
        try:
            proc = psutil.Process(pid)
            info = proc.as_dict(
                attrs=[
                    "pid",
                    "name",
                    "username",
                    "status",
                    "cpu_percent",
                    "memory_percent",
                    "memory_info",
                    "create_time",
                    "exe",
                    "cmdline",
                    "num_threads",
                    "ppid",
                    "connections",
                    "open_files",
                ]
            )
        except psutil.NoSuchProcess:
            print(f"[bold red][-] PID {pid} bulunamadı.[/bold red]")
            return False
        except psutil.AccessDenied:
            print(f"[bold red][-] PID {pid} için erişim reddedildi.[/bold red]")
            return False

        tbl = Table(
            title=f"🔎 Süreç Detayı — PID {pid}",
            show_header=False,
            border_style="green",
        )
        tbl.add_column("Alan", style="cyan")
        tbl.add_column("Değer", style="white")

        tbl.add_row("PID", str(info.get("pid", "?")))
        tbl.add_row("İsim", str(info.get("name", "?")))
        tbl.add_row("Kullanıcı", str(info.get("username", "?")))
        tbl.add_row("Durum", str(info.get("status", "?")))
        tbl.add_row("PPID", str(info.get("ppid", "?")))
        tbl.add_row("Thread Sayısı", str(info.get("num_threads", "?")))
        tbl.add_row("CPU%", f"{info.get('cpu_percent', 0):.1f}%")
        tbl.add_row("RAM%", f"{info.get('memory_percent', 0):.1f}%")

        mem_info = info.get("memory_info")
        if mem_info:
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)
            tbl.add_row("RSS", f"{rss_mb:.1f} MB")
            tbl.add_row("VMS", f"{vms_mb:.1f} MB")

        tbl.add_row("Exe", str(info.get("exe", "-") or "-"))
        cmdline = info.get("cmdline") or []
        tbl.add_row("Komut", " ".join(cmdline)[:80] if cmdline else "-")

        conns = info.get("connections") or []
        tbl.add_row("Bağlantılar", str(len(conns)))

        files = info.get("open_files") or []
        tbl.add_row("Açık Dosyalar", str(len(files)))

        self.console.print(tbl)
        return True

    def _action_kill(self, pid: int) -> bool:
        """Belirtilen PID'li süreci sonlandırır."""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()

            print(
                f"[bold green][+] PID {pid} ({proc_name}) sonlandırıldı.[/bold green]"
            )
            return True
        except psutil.NoSuchProcess:
            print(f"[bold red][-] PID {pid} bulunamadı.[/bold red]")
            return False
        except psutil.AccessDenied:
            print(
                f"[bold red][-] PID {pid} için erişim reddedildi. Yetki gerekiyor.[/bold red]"
            )
            return False

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        action = str(options.get("ACTION", "list")).lower()
        sort_by = str(options.get("SORT_BY", "cpu")).lower()
        count = int(options.get("COUNT", 25))
        filt = str(options.get("FILTER", "")).strip()
        pid_str = str(options.get("PID", "")).strip()

        logger.info(f"Process manager çalıştırıldı (action={action})")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]📊 SÜREÇ YÖNETİCİSİ[/bold cyan]",
                border_style="cyan",
            )
        )

        if action == "list":
            return self._action_list(sort_by, count)
        elif action == "search":
            return self._action_search(filt)
        elif action == "info":
            if not pid_str:
                print("[bold red][-] PID seçeneği gereklidir.[/bold red]")
                return False
            return self._action_info(int(pid_str))
        elif action == "kill":
            if not pid_str:
                print("[bold red][-] PID seçeneği gereklidir.[/bold red]")
                return False
            return self._action_kill(int(pid_str))
        else:
            print(f"[bold red][-] Bilinmeyen action: {action}[/bold red]")
            return False
