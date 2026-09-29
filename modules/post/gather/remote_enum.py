# =============================================================================
# Post-Exploitation: Penelope Tarzı Uzak Sistem Keşfi (Remote Enumeration)
# =============================================================================
# Aktif PTY veya raw shell oturumu üzerinden komut çalıştırarak hedef
# sistemi keşfeden modül.  Penelope (brightio/penelope) benzeri akış:
#   1. OS algılama  (uname -s / ver)
#   2. OS'a uygun keşif komutlarını sırayla çalıştırma
#   3. Çıktıları parse edip zengin tablo halinde sunma
#
# KULLANIM:
#   use post/gather/remote_enum
#   set SESSION 1
#   set SECTIONS all        (os,user,network,system,security,files,software)
#   set TIMEOUT 10
#   run
#
# Bu modül tamamen etik siber güvenlik ve yetkili penetrasyon testi
# amaçlıdır. Yalnızca yazılı izin alınmış sistemlerde kullanılmalıdır.
# =============================================================================

from __future__ import annotations

import time
import uuid
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger, shell_exec
from core.module import BaseModule
from core.option import Option
from core.shared_state import shared_state


class RemoteEnum(BaseModule):
    """
    Penelope Tarzı Uzak Sistem Keşfi.

    Aktif bir shell oturumu (PTY veya raw) üzerinden komut çalıştırarak
    hedef sistemden bilgi toplar. Penelope'nin session.exec() mantığını
    taklit eder — socket üzerinden marker tabanlı güvenilir komut çalıştırma.
    """

    Name = "Remote System Enumeration"
    Description = (
        "Aktif shell oturumu üzerinden Penelope tarzı uzak sistem keşfi yapar"
    )
    Author = "Mahmut P."
    Category = "post/gather"
    Version = "1.0"

    def __init__(self) -> None:
        super().__init__()
        self.Options = {
            "SESSION": Option(
                "SESSION", "", True,
                "Hedef oturum ID'si (sessions -l ile listele).",
            ),
            "SECTIONS": Option(
                "SECTIONS", "all", False,
                "Toplanacak bölümler: os,user,network,system,security,files,software,all",
                choices=["all", "os", "user", "network", "system",
                         "security", "files", "software"],
            ),
            "TIMEOUT": Option(
                "TIMEOUT", 10, False,
                "Her komut için zaman aşımı (saniye).",
            ),
            "SAVE_OUTPUT": Option(
                "SAVE_OUTPUT", "", False,
                "Çıktıyı dosyaya kaydet (yol).",
                completion_dir=".",
            ),
        }
        self.console = Console()
        self._collected_lines: list[str] = []

    # ─── Socket üzerinden komut çalıştırma (Penelope tarzı) ──────────────

    @staticmethod
    def _flush_recv(sock: Any) -> None:
        """Soketteki bekleyen veriyi temizler."""
        sock.setblocking(False)
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
        except (BlockingIOError, OSError):
            pass
        finally:
            sock.setblocking(True)

    @staticmethod
    def _exec_on_session(sock: Any, command: str, timeout: float = 10.0) -> str:
        """Shell oturumuna komut gönderir ve marker tabanlı çıktıyı yakalar.

        Protokolün tek uygulaması core/shell_exec.py'de: PTY prompt'u ve
        terminal echo'su temizlenir, hata durumunda "[Hata: ...]" döner.
        """
        return shell_exec.exec_on_session(sock, command, timeout)

    def _detect_os(self, sock: Any, timeout: float) -> str:
        """Uzak hedefin OS'unu algılar (linux/windows/macos)."""
        result = self._exec_on_session(sock, "uname -s", timeout=timeout)
        result_lower = result.lower().strip()

        if "linux" in result_lower:
            return "linux"
        if "darwin" in result_lower:
            return "macos"

        # uname yoksa Windows olabilir
        win_check = self._exec_on_session(sock, "echo %OS%", timeout=timeout)
        if "windows" in win_check.lower():
            return "windows"

        # Varsayılan
        if result_lower:
            return "linux"  # BSD vb. de Unix-like
        return "unknown"

    # ─── Bölüm Toplayıcılar ────────────────────────────────────────────────

    def _gather_os_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """İşletim sistemi bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            raw = self._exec_on_session(sock, "systeminfo", timeout=30)
            info["systeminfo"] = raw
        else:
            info["uname"] = self._exec_on_session(sock, "uname -a", timeout=timeout)
            info["hostname"] = self._exec_on_session(sock, "hostname", timeout=timeout)
            info["kernel"] = self._exec_on_session(sock, "uname -r", timeout=timeout)
            info["arch"] = self._exec_on_session(sock, "uname -m", timeout=timeout)
            # Distro bilgisi
            info["distro"] = self._exec_on_session(
                sock,
                # Süzgeci komutun BASARISIZ oldugunu gizlemez; bu yüzden
                # zincir süzgeçten ÖNCE kurulur, aksi halde `||` dallari hic
                # çalışmaz (head bos cikti ile basarili sayilir).
                "{ cat /etc/os-release 2>/dev/null || "
                "cat /etc/issue 2>/dev/null || "
                "sw_vers 2>/dev/null; } | head -5",
                timeout=timeout,
            )
        return info

    def _gather_user_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """Kullanıcı bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            info["whoami"] = self._exec_on_session(sock, "whoami /all", timeout=timeout)
            info["users"] = self._exec_on_session(sock, "net user", timeout=timeout)
            info["admins"] = self._exec_on_session(
                sock, "net localgroup administrators", timeout=timeout
            )
        else:
            info["whoami"] = self._exec_on_session(sock, "whoami", timeout=timeout)
            info["id"] = self._exec_on_session(sock, "id", timeout=timeout)
            info["groups"] = self._exec_on_session(sock, "groups", timeout=timeout)
            info["sudo"] = self._exec_on_session(
                sock, "sudo -l -n 2>/dev/null || echo 'sudo bilgisi alınamadı'",
                timeout=timeout,
            )
            info["users"] = self._exec_on_session(
                sock,
                "cat /etc/passwd 2>/dev/null | grep -v nologin | grep -v /bin/false | "
                "cut -d: -f1,3,6,7",
                timeout=timeout,
            )
        return info

    def _gather_network_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """Ağ bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            info["ipconfig"] = self._exec_on_session(sock, "ipconfig /all", timeout=timeout)
            info["netstat"] = self._exec_on_session(sock, "netstat -an", timeout=timeout)
            info["arp"] = self._exec_on_session(sock, "arp -a", timeout=timeout)
        else:
            info["interfaces"] = self._exec_on_session(
                sock, "ip addr 2>/dev/null || ifconfig 2>/dev/null", timeout=timeout
            )
            info["routes"] = self._exec_on_session(
                sock, "ip route 2>/dev/null || route -n 2>/dev/null || netstat -rn 2>/dev/null",
                timeout=timeout,
            )
            info["listening"] = self._exec_on_session(
                sock,
                "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || "
                "netstat -an 2>/dev/null | grep LISTEN",
                timeout=timeout,
            )
            info["dns"] = self._exec_on_session(
                sock, "cat /etc/resolv.conf 2>/dev/null | grep nameserver",
                timeout=timeout,
            )
            info["arp"] = self._exec_on_session(
                sock, "arp -a 2>/dev/null || ip neigh 2>/dev/null",
                timeout=timeout,
            )
        return info

    def _gather_system_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """Sistem kaynakları bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            info["tasklist"] = self._exec_on_session(sock, "tasklist", timeout=timeout)
        else:
            info["uptime"] = self._exec_on_session(sock, "uptime", timeout=timeout)
            info["cpu"] = self._exec_on_session(
                sock,
                "cat /proc/cpuinfo 2>/dev/null | head -20 || "
                "sysctl -n machdep.cpu.brand_string 2>/dev/null",
                timeout=timeout,
            )
            info["memory"] = self._exec_on_session(
                sock, "free -h 2>/dev/null || vm_stat 2>/dev/null", timeout=timeout
            )
            info["disk"] = self._exec_on_session(
                sock, "df -h 2>/dev/null", timeout=timeout
            )
            info["processes"] = self._exec_on_session(
                sock,
                "ps aux --sort=-%mem 2>/dev/null | head -20 || "
                "ps aux 2>/dev/null | head -20",
                timeout=timeout,
            )
        return info

    def _gather_security_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """Güvenlik yapılandırma bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            info["firewall"] = self._exec_on_session(
                sock, "netsh advfirewall show allprofiles state", timeout=timeout
            )
            info["av"] = self._exec_on_session(
                sock,
                'tasklist /FI "IMAGENAME eq MsMpEng.exe" 2>nul & '
                'tasklist /FI "IMAGENAME eq avp.exe" 2>nul',
                timeout=timeout,
            )
        else:
            info["selinux"] = self._exec_on_session(
                sock, "getenforce 2>/dev/null || echo 'SELinux yok'", timeout=timeout
            )
            info["apparmor"] = self._exec_on_session(
                sock, "aa-status 2>/dev/null | head -5 || echo 'AppArmor yok'",
                timeout=timeout,
            )
            info["firewall"] = self._exec_on_session(
                sock,
                "iptables -L -n 2>/dev/null | head -20 || "
                "ufw status 2>/dev/null || "
                "pfctl -sr 2>/dev/null | head -10 || "
                "echo 'Firewall bilgisi alınamadı'",
                timeout=timeout,
            )
            # Güvenlik ile ilgili süreçler
            av_procs = [
                "clamd", "freshclam",  # ClamAV
                "falcon-sensor",  # CrowdStrike
                "ossec", "wazuh",  # OSSEC/Wazuh
                "snort", "suricata",  # IDS
            ]
            grep_pattern = "\\|".join(av_procs)
            info["security_procs"] = self._exec_on_session(
                sock,
                f"ps aux 2>/dev/null | grep -i '{grep_pattern}' | grep -v grep || "
                "echo 'Güvenlik süreci bulunamadı'",
                timeout=timeout,
            )
        return info

    def _exec_backgrounded(
        self,
        sock: Any,
        command: str,
        timeout: float,
        max_wait: float = 45.0,
        poll: float = 2.0,
    ) -> str:
        """
        Yavaş komutu arka planda çalıştırıp sonucu yoklayarak toplar.

        `find /` gibi komutlar uzak sistemde onlarca saniye sürebilir. Tek
        seferde çalıştırılırsa komut süresi dolar, kabuk hâlâ meşgul
        olduğu için sonraki HER komut da kuyrukta kalır. Bu yüzden komut
        arka planda çalışır, bitim işaretiyle haber verir; oturum serbest
        kalır ve kısa yoklama komutlarıyla sonuç alınır.
        """
        token = uuid.uuid4().hex[:10]
        out_path = f"/tmp/.mah_{token}.out"
        done_path = f"/tmp/.mah_{token}.done"
        pid_path = f"/tmp/.mah_{token}.pid"

        started = self._exec_on_session(
            sock,
            f"rm -f {out_path} {done_path} {pid_path}; "
            f"( {command} > {out_path} 2>/dev/null & echo $! > {pid_path}; "
            f"wait; echo done > {done_path} ) >/dev/null 2>&1 &",
            timeout=timeout,
        )
        if started.startswith("[Hata"):
            return started

        deadline = time.time() + max_wait
        while time.time() < deadline:
            time.sleep(poll)
            status = self._exec_on_session(
                sock, f"test -f {done_path} && echo BITTIM || echo BEKLIYOR",
                timeout=timeout,
            )
            if "BITTIM" in status:
                result = self._exec_on_session(
                    sock, f"cat {out_path} 2>/dev/null", timeout=timeout
                )
                self._exec_on_session(
                    sock, f"rm -f {out_path} {done_path} {pid_path}", timeout=timeout
                )
                return result
            if status.startswith("[Hata"):
                return "[Hata: arka plan komutu baslatilamadi]"

        # Süre doldu: kısmi sonucu al, dosyaları temizle ve ARTA PLANDA
        # KALAN TARAMA SÜRECİNİ ÖLDÜR. Aksi halde `find /` hedefte sonsuza
        # kadar çalışmaya devam eder; dosyaları silmek süreci durdurmaz
        # (açık fd silinen inode'a yazmaya devam eder) ve hedef gereksiz
        # I/O ile yüklenir.
        partial = self._exec_on_session(
            sock, f"cat {out_path} 2>/dev/null", timeout=timeout
        )
        self._exec_on_session(
            sock,
            f"kill $(cat {pid_path} 2>/dev/null) 2>/dev/null; "
            f"rm -f {out_path} {done_path} {pid_path}",
            timeout=timeout,
        )
        if partial and not partial.startswith("[Hata"):
            return partial + "\n[dim]... (zaman asimi, liste kisaltildi)[/dim]"
        return "[Hata: komut zaman asimi] " + partial

    def _gather_files_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """İlginç dosya ve dizin bilgilerini toplar."""
        info = {}
        if target_os != "windows":
            info["suid"] = self._exec_backgrounded(
                sock,
                "find / -perm -4000 -type f 2>/dev/null | head -25",
                timeout=timeout,
            )
            info["writable_dirs"] = self._exec_backgrounded(
                sock,
                "find / -writable -type d 2>/dev/null | head -15",
                timeout=timeout,
            )
            info["cron_user"] = self._exec_on_session(
                sock, "crontab -l 2>/dev/null || echo 'Kullanıcı cron yok'",
                timeout=timeout,
            )
            info["cron_system"] = self._exec_on_session(
                sock, "ls -la /etc/cron* 2>/dev/null | head -20",
                timeout=timeout,
            )
            info["ssh_keys"] = self._exec_on_session(
                sock,
                "ls -la ~/.ssh/ 2>/dev/null || echo 'SSH dizini yok'",
                timeout=timeout,
            )
        else:
            info["shares"] = self._exec_on_session(
                sock, "net share", timeout=timeout
            )
        return info

    def _gather_software_info(self, sock: Any, target_os: str, timeout: float) -> dict:
        """Yüklü yazılım bilgilerini toplar."""
        info = {}
        if target_os == "windows":
            info["installed"] = self._exec_on_session(
                sock, "wmic product get name,version 2>nul | head -30",
                timeout=timeout,
            )
        else:
            info["pkg_manager"] = self._exec_on_session(
                sock,
                "which dpkg apt yum rpm brew pacman 2>/dev/null",
                timeout=timeout,
            )
            info["languages"] = self._exec_on_session(
                sock,
                "python3 --version 2>/dev/null; "
                "python --version 2>/dev/null; "
                "perl --version 2>/dev/null | head -2; "
                "ruby --version 2>/dev/null; "
                "gcc --version 2>/dev/null | head -1; "
                "java -version 2>/dev/null | head -1; "
                "node --version 2>/dev/null; "
                "go version 2>/dev/null",
                timeout=timeout,
            )
            info["docker"] = self._exec_on_session(
                sock, "docker --version 2>/dev/null || echo 'Docker yok'",
                timeout=timeout,
            )
        return info

    # ─── Görüntüleme ───────────────────────────────────────────────────────

    def _display_section(self, title: str, data: dict, icon: str = "📋") -> None:
        """Bir bölümü rich panel olarak görüntüler."""
        self._collected_lines.append(f"\n{'='*60}")
        self._collected_lines.append(f"  {icon} {title}")
        self._collected_lines.append(f"{'='*60}")

        tbl = Table(
            title=f"{icon}  {title}",
            show_header=True,
            border_style="cyan",
            expand=True,
        )
        tbl.add_column("Alan", style="cyan bold", width=20)
        tbl.add_column("Değer", style="white")

        for key, value in data.items():
            if not value or value.strip() == "":
                value = "[dim]—[/dim]"
            # Uzun çıktıları kısalt (tablo için)
            display_val = value
            if len(value) > 500:
                display_val = value[:500] + "\n[dim]... (kırpıldı)[/dim]"
            tbl.add_row(key, display_val)

            # Dosya kayıt için tam çıktı
            self._collected_lines.append(f"\n  [{key}]")
            self._collected_lines.append(f"  {value}")

        self.console.print(tbl)
        self.console.print()

    # ─── Ana Çalıştırma ────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        """Shell oturumu üzerinden uzak sistem keşfi yapar."""
        session_id_raw = options.get("SESSION", "")
        if not session_id_raw or str(session_id_raw).strip() == "":
            self.console.print("[bold red][!] SESSION belirtilmedi.[/bold red]")
            self.console.print("[*] Kullanım: set SESSION <id>")
            return False

        try:
            session_id = int(str(session_id_raw).strip())
        except ValueError:
            self.console.print(f"[bold red][!] Geçersiz SESSION: {session_id_raw}[/bold red]")
            return False

        timeout = float(options.get("TIMEOUT", 10))
        sections_raw = str(options.get("SECTIONS", "all")).lower().strip()
        save_output = str(options.get("SAVE_OUTPUT", "") or "")

        sections = (
            {"os", "user", "network", "system", "security", "files", "software"}
            if sections_raw == "all"
            else set(s.strip() for s in sections_raw.split(","))
        )

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

        # Soketi al
        sock = None
        if hasattr(handler, "resolve_client_sock"):
            sock = handler.resolve_client_sock(session_id)
        if not sock:
            sock = getattr(handler, "client_sock", None)
        if not sock:
            self.console.print(f"[bold red][!] Session {session_id}: aktif soket yok.[/bold red]")
            return False

        logger.info(f"Remote enum başlatılıyor (Session {session_id})")

        # PTY oturumlarda echo'yu kapat: readline uzun satırlari yeniden
        # cizer ve marker'lari bozar (cikti "[Hata: komut tamamlanmadi]" olur).
        shell_exec.prepare_remote(
            sock, min(timeout, 10),
            warn=lambda: self.console.print(
                "[yellow][!] Terminal echo'su kapatilamadi; "
                "uzak oturumda bazi ciktilar eksik gelebilir.[/yellow]"
            ),
        )

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold cyan]🔍 UZAK SİSTEM KEŞFİ — Session {session_id}[/bold cyan]\n"
            f"[dim]Penelope tarzı shell-over-socket enumeration[/dim]",
            border_style="cyan",
        ))

        self._collected_lines = [
            f"mah-framework — Remote Enumeration (Session {session_id})",
            f"Tarih: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # 1. OS Algılama
        self.console.print("[bold cyan][*] Hedef OS algılanıyor...[/bold cyan]")
        target_os = self._detect_os(sock, timeout)
        os_label = {"linux": "🐧 Linux", "macos": "🍎 macOS", "windows": "🪟 Windows"}.get(
            target_os, f"❓ {target_os}"
        )
        self.console.print(f"[bold green][+] Hedef OS: {os_label}[/bold green]\n")
        self._collected_lines.append(f"Hedef OS: {target_os}")

        # 2. Bölüm bölüm topla
        section_map = {
            "os": ("🖥️  İşletim Sistemi", self._gather_os_info),
            "user": ("👤 Kullanıcı Bilgileri", self._gather_user_info),
            "network": ("🌐 Ağ Bilgileri", self._gather_network_info),
            "system": ("⚙️  Sistem Kaynakları", self._gather_system_info),
            "security": ("🛡️  Güvenlik", self._gather_security_info),
            "files": ("📁 Dosyalar & Dizinler", self._gather_files_info),
            "software": ("📦 Yazılımlar", self._gather_software_info),
        }

        for section_key, (title, gather_fn) in section_map.items():
            if section_key not in sections:
                continue
            self.console.print(f"[cyan][*] {title} toplanıyor...[/cyan]")
            try:
                data = gather_fn(sock, target_os, timeout)
                if data:
                    self._display_section(title, data)
            except Exception as e:
                self.console.print(f"[yellow][!] {title} hatası: {e}[/yellow]")

        # Oturum aktivitesini güncelle
        if shared_state.session_manager:
            shared_state.session_manager.update_session_activity(session_id)

        # Çıktıyı dosyaya kaydet
        if save_output:
            try:
                with open(save_output, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._collected_lines))
                self.console.print(f"[bold green][+] Çıktı kaydedildi: {save_output}[/bold green]")
            except Exception as e:
                self.console.print(f"[bold red][!] Dosya yazma hatası: {e}[/bold red]")

        self.console.print(Panel.fit(
            "[bold green]✓ Uzak sistem keşfi tamamlandı.[/bold green]",
            border_style="green",
        ))
        logger.info("Remote enum tamamlandı")
        return True
