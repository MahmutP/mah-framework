# =============================================================================
# Auxiliary: Service Manager
# =============================================================================
# Sistem servislerini listeleme, başlatma, durdurma ve sorgulama modülü.
# Linux (systemctl), macOS (launchctl) ve Windows (sc) destekler.
#
# KULLANIM:
#   1. use auxiliary/os/service_manager
#   2. set ACTION list
#   3. set FILTER ssh
#   4. run
#
#   5. set ACTION status
#   6. set SERVICE_NAME sshd
#   7. run
# =============================================================================

import re
import subprocess
import sys
from typing import Any

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option


class service_manager(BaseModule):
    """Sistem Servis Yöneticisi

    Çalışan platforma göre (Linux / macOS / Windows) sistem servislerini
    listeleyebilir, durumlarını sorgulayabilir, başlatıp durdurabilir.

    Desteklenen Platformlar:
        - **Linux:** systemctl (systemd)
        - **macOS:** launchctl
        - **Windows:** sc query / net start
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Service Manager"
    Description = "Sistem servislerini listeleme, başlatma, durdurma ve sorgulama"
    Author = "Mahmut P."
    Category = "auxiliary/os"
    Version = "1.0"

    Requirements: dict[str, list[str]] = {}

    def __init__(self):
        super().__init__()
        self.Options = {
            "ACTION": Option(
                name="ACTION",
                value="list",
                required=True,
                description="Yapılacak işlem: list / status / start / stop",
                choices=["list", "status", "start", "stop"],
            ),
            "SERVICE_NAME": Option(
                name="SERVICE_NAME",
                value="",
                required=False,
                description="Hedef servis adı (status/start/stop için gerekli)",
            ),
            "FILTER": Option(
                name="FILTER",
                value="",
                required=False,
                description="Servis adı filtresi (list için, ör: ssh)",
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _run_cmd(cmd: list[str], timeout: int = 15) -> tuple[str, str, int]:
        """Sistem komutunu çalıştırır → (stdout, stderr, returncode)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout, result.stderr, result.returncode
        except FileNotFoundError:
            return "", "Komut bulunamadı", -1
        except subprocess.TimeoutExpired:
            return "", "Zaman aşımı", -1
        except Exception as e:
            return "", str(e), -1

    @staticmethod
    def _detect_platform() -> str:
        """linux / darwin / win32"""
        if sys.platform.startswith("linux"):
            return "linux"
        if sys.platform == "darwin":
            return "darwin"
        return "win32"

    # ── LİSTELEME ────────────────────────────────────────────────────────────

    def _list_linux(self, filt: str) -> list[dict[str, str]]:
        stdout, _, _ = self._run_cmd(
            [
                "systemctl",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--plain",
            ]
        )
        services: list[dict[str, str]] = []
        for line in stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 4 and ".service" in parts[0]:
                name = parts[0]
                load = parts[1]
                active = parts[2]
                sub = parts[3]
                desc = parts[4] if len(parts) > 4 else ""
                if filt and filt.lower() not in name.lower():
                    continue
                services.append(
                    {
                        "name": name,
                        "load": load,
                        "active": active,
                        "sub": sub,
                        "desc": desc.strip(),
                    }
                )
        return services

    def _list_darwin(self, filt: str) -> list[dict[str, str]]:
        stdout, _, _ = self._run_cmd(["launchctl", "list"])
        services: list[dict[str, str]] = []
        for line in stdout.splitlines()[1:]:  # Başlık atla
            parts = line.split("\t")
            if len(parts) >= 3:
                pid = parts[0].strip()
                status = parts[1].strip()
                label = parts[2].strip()
                if filt and filt.lower() not in label.lower():
                    continue
                services.append(
                    {
                        "name": label,
                        "pid": pid if pid != "-" else "-",
                        "status": status,
                    }
                )
        return services

    def _list_win32(self, filt: str) -> list[dict[str, str]]:
        stdout, _, _ = self._run_cmd(
            ["sc", "query", "type=", "service", "state=", "all"]
        )
        services: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("SERVICE_NAME:"):
                if current:
                    services.append(current)
                current = {"name": line.split(":", 1)[1].strip()}
            elif line.startswith("DISPLAY_NAME:"):
                current["desc"] = line.split(":", 1)[1].strip()
            elif line.startswith("STATE"):
                match = re.search(r"\d+\s+(\w+)", line)
                if match:
                    current["state"] = match.group(1)
        if current:
            services.append(current)
        if filt:
            services = [
                s for s in services if filt.lower() in s.get("name", "").lower()
            ]
        return services

    # ── STATUS / START / STOP ────────────────────────────────────────────────

    def _service_action(
        self, platform: str, action: str, service: str
    ) -> tuple[bool, str]:
        """Servis üzerinde status/start/stop işlemi yapar."""
        if platform == "linux":
            cmd = ["systemctl", action, service]
        elif platform == "darwin":
            if action == "status":
                stdout, stderr, rc = self._run_cmd(
                    ["launchctl", "print", f"system/{service}"]
                )
                if rc != 0:
                    stdout, stderr, rc = self._run_cmd(["launchctl", "list", service])
                return rc == 0, stdout or stderr
            elif action == "start":
                cmd = [
                    "launchctl",
                    "load",
                    "-w",
                    f"/Library/LaunchDaemons/{service}.plist",
                ]
            elif action == "stop":
                cmd = ["launchctl", "unload", f"/Library/LaunchDaemons/{service}.plist"]
            else:
                return False, "Bilinmeyen action"
        elif platform == "win32":
            if action == "status":
                cmd = ["sc", "query", service]
            elif action == "start":
                cmd = ["net", "start", service]
            elif action == "stop":
                cmd = ["net", "stop", service]
            else:
                return False, "Bilinmeyen action"
        else:
            return False, "Desteklenmeyen platform"

        stdout, stderr, rc = self._run_cmd(cmd)
        output = stdout.strip() or stderr.strip()
        return rc == 0, output

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        action = str(options.get("ACTION", "list")).lower()
        service_name = str(options.get("SERVICE_NAME", "")).strip()
        filt = str(options.get("FILTER", "")).strip()
        platform = self._detect_platform()

        logger.info(
            f"Service manager çalıştırıldı (action={action}, platform={platform})"
        )

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]⚙️  SERVİS YÖNETİCİSİ[/bold cyan]",
                border_style="cyan",
            )
        )

        platform_label = {
            "linux": "Linux (systemctl)",
            "darwin": "macOS (launchctl)",
            "win32": "Windows (sc)",
        }
        self.console.print(
            f"  [dim]Platform:[/dim] {platform_label.get(platform, platform)}"
        )
        self.console.print()

        # ── LIST ──────────────────────────────────────────────────────────
        if action == "list":
            if platform == "linux":
                svcs = self._list_linux(filt)
                tbl = Table(title="📋 Servis Listesi", border_style="blue")
                tbl.add_column("Servis", style="cyan", max_width=40)
                tbl.add_column("Load", justify="center")
                tbl.add_column("Active", justify="center")
                tbl.add_column("Sub", justify="center")
                tbl.add_column("Açıklama", style="dim", max_width=35)
                for s in svcs:
                    active_clr = "green" if s["active"] == "active" else "red"
                    tbl.add_row(
                        s["name"],
                        s["load"],
                        f"[{active_clr}]{s['active']}[/{active_clr}]",
                        s["sub"],
                        s["desc"],
                    )
            elif platform == "darwin":
                svcs = self._list_darwin(filt)
                tbl = Table(title="📋 Servis Listesi", border_style="blue")
                tbl.add_column("Label", style="cyan", max_width=50)
                tbl.add_column("PID", justify="center")
                tbl.add_column("Status", justify="center")
                for s in svcs:
                    tbl.add_row(s["name"], s["pid"], s["status"])
            else:
                svcs = self._list_win32(filt)
                tbl = Table(title="📋 Servis Listesi", border_style="blue")
                tbl.add_column("Servis", style="cyan", max_width=30)
                tbl.add_column("Durum", justify="center")
                tbl.add_column("Açıklama", style="dim", max_width=35)
                for s in svcs:
                    state = s.get("state", "?")
                    clr = "green" if state == "RUNNING" else "red"
                    tbl.add_row(s["name"], f"[{clr}]{state}[/{clr}]", s.get("desc", ""))

            self.console.print(tbl)
            self.console.print(f"  [bold]Toplam:[/bold] {len(svcs)} servis")
            return True

        # ── STATUS / START / STOP ─────────────────────────────────────────
        if not service_name:
            print(f"[bold red][-] {action} için SERVICE_NAME gereklidir.[/bold red]")
            return False

        ok, output = self._service_action(platform, action, service_name)
        icon = "✔" if ok else "✘"
        color = "green" if ok else "red"
        self.console.print(
            Panel(
                f"[{color}]{output or 'İşlem tamamlandı.'}[/{color}]",
                title=f"[{color}]{icon} {action.upper()} — {service_name}[/{color}]",
                border_style=color,
            )
        )

        return ok
