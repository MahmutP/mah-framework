# =============================================================================
# Post-Exploitation: System Information Gatherer
# =============================================================================
# Hedef sistemden ayrıntılı donanım ve yazılım bilgisi toplayan modül.
#
# KULLANIM:
#   1. use post/gather/system_info
#   2. set SHOW_PROCESSES true/false
#   3. set PROCESS_COUNT 15
#   4. set SHOW_NETWORK true/false
#   5. set SHOW_DISK true/false
#   6. run
# =============================================================================

import datetime
import getpass
import platform
import socket
from typing import Any

import psutil  # type: ignore
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option


class system_info(BaseModule):
    """Kapsamlı Sistem Bilgisi Toplama Modülü (Post-Exploitation)

    Hedef sistem üzerinde çalıştırılarak ayrıntılı donanım ve yazılım
    envanteri çıkarır. Penetrasyon testlerinde post-exploitation aşamasında
    hedef keşfi için kullanılır.

    Toplanan Bilgiler:
        - İşletim sistemi: Tür, sürüm, mimari, hostname, kullanıcı
        - CPU: Çekirdek sayısı (fiziksel / mantıksal), kullanım oranı, frekans
        - RAM: Toplam, kullanılan, boş, yüzde
        - Disk: Bölümler, boyutlar, doluluk oranları
        - Ağ: Arayüzler, IPv4, MAC, durum
        - Süreçler: En çok kaynak tüketen süreçler
        - Uptime & Boot zamanı
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "System Information Gatherer"
    Description = (
        "Hedef sistemden ayrıntılı bilgi toplar: OS, CPU, RAM, Disk, Ağ, Süreçler"
    )
    Author = "Mahmut P."
    Category = "post/gather"
    Version = "1.0"

    Requirements = {"python": ["psutil"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "SHOW_PROCESSES": Option(
                name="SHOW_PROCESSES",
                value="true",
                required=False,
                description="Çalışan süreçleri göster (true/false)",
                choices=["true", "false"],
            ),
            "PROCESS_COUNT": Option(
                name="PROCESS_COUNT",
                value=10,
                required=False,
                description="Gösterilecek süreç sayısı",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "SHOW_NETWORK": Option(
                name="SHOW_NETWORK",
                value="true",
                required=False,
                description="Ağ arayüzlerini göster (true/false)",
                choices=["true", "false"],
            ),
            "SHOW_DISK": Option(
                name="SHOW_DISK",
                value="true",
                required=False,
                description="Disk bilgilerini göster (true/false)",
                choices=["true", "false"],
            ),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _bytes_to_human(bytes_val: int) -> str:
        """Byte → okunabilir birim (KB / MB / GB …)."""
        val = float(bytes_val)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if val < 1024.0:
                return f"{val:.2f} {unit}"
            val /= 1024.0
        return f"{val:.2f} PB"

    @staticmethod
    def _seconds_to_human(seconds: int) -> str:
        """Saniye → '2 gün, 5 saat, 30 dakika' formatı."""
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{int(days)} gün")
        if hours:
            parts.append(f"{int(hours)} saat")
        if minutes:
            parts.append(f"{int(minutes)} dakika")
        if not parts:
            parts.append(f"{int(secs)} saniye")
        return ", ".join(parts)

    # ── VERİ TOPLAMA ─────────────────────────────────────────────────────────

    def _get_os_info(self) -> dict[str, str]:
        return {
            "Sistem": platform.system(),
            "Sürüm": platform.release(),
            "Derleme": platform.version(),
            "Mimari": " ".join(platform.architecture()),
            "İşlemci": platform.processor() or "Bilinmiyor",
            "Platform": platform.platform(),
            "Hostname": socket.gethostname(),
            "Kullanıcı": getpass.getuser(),
        }

    def _get_cpu_info(self) -> dict[str, Any]:
        try:
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "Bilinmiyor"
        except Exception:
            freq_str = "Bilinmiyor"
        return {
            "Fiziksel Çekirdek": psutil.cpu_count(logical=False) or "?",
            "Mantıksal Çekirdek": psutil.cpu_count(logical=True) or "?",
            "CPU Kullanımı": f"{psutil.cpu_percent(interval=0.5)}%",
            "Frekans": freq_str,
        }

    def _get_ram_info(self) -> dict[str, str]:
        mem = psutil.virtual_memory()
        return {
            "Toplam": self._bytes_to_human(mem.total),
            "Kullanılan": self._bytes_to_human(mem.used),
            "Boş": self._bytes_to_human(mem.available),
            "Kullanım": f"{mem.percent}%",
        }

    def _get_disk_info(self) -> list[dict[str, str]]:
        disks: list[dict[str, str]] = []
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append(
                        {
                            "Bağlama Noktası": part.mountpoint,
                            "Dosya Sistemi": part.fstype,
                            "Toplam": self._bytes_to_human(usage.total),
                            "Kullanılan": self._bytes_to_human(usage.used),
                            "Boş": self._bytes_to_human(usage.free),
                            "Kullanım": f"{usage.percent}%",
                        }
                    )
                except PermissionError:
                    continue
        except Exception:
            pass
        return disks

    def _get_network_info(self) -> list[dict[str, str]]:
        interfaces: list[dict[str, str]] = []
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for name, iface_addrs in addrs.items():
                if name.startswith("lo"):
                    continue
                ipv4 = "-"
                mac = "-"
                for addr in iface_addrs:
                    if addr.family == socket.AF_INET:
                        ipv4 = addr.address
                    elif addr.family == psutil.AF_LINK:
                        mac = addr.address
                is_up = stats.get(name)
                status = "🟢 Aktif" if is_up and is_up.isup else "🔴 Pasif"
                interfaces.append(
                    {
                        "Arayüz": name,
                        "IPv4": ipv4,
                        "MAC": mac,
                        "Durum": status,
                    }
                )
        except Exception:
            pass
        return interfaces

    def _get_top_processes(self, count: int) -> list[dict[str, str]]:
        procs: list[dict[str, str]] = []
        try:
            sorted_procs = sorted(
                psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                key=lambda p: p.info.get("cpu_percent", 0) or 0,
                reverse=True,
            )
            for proc in sorted_procs[:count]:
                try:
                    info = proc.info
                    procs.append(
                        {
                            "PID": str(info.get("pid", "?")),
                            "İsim": (info.get("name", "?") or "?")[:25],
                            "CPU%": f"{info.get('cpu_percent', 0):.1f}%",
                            "RAM%": f"{info.get('memory_percent', 0):.1f}%",
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return procs

    def _get_uptime(self) -> str:
        try:
            boot = psutil.boot_time()
            return self._seconds_to_human(
                int(datetime.datetime.now().timestamp() - boot)
            )
        except Exception:
            return "Bilinmiyor"

    def _get_boot_time(self) -> str:
        try:
            return datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            return "Bilinmiyor"

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        """Sistem bilgilerini toplar ve rich tabloları ile görüntüler."""
        show_processes = str(options.get("SHOW_PROCESSES", "true")).lower() == "true"
        process_count = int(options.get("PROCESS_COUNT", 10))
        show_network = str(options.get("SHOW_NETWORK", "true")).lower() == "true"
        show_disk = str(options.get("SHOW_DISK", "true")).lower() == "true"

        logger.info("Sistem bilgisi toplama başlatıldı")

        # ── Başlık ────────────────────────────────────────────────────────
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]📊 SİSTEM BİLGİLERİ — Post-Exploitation[/bold cyan]",
                border_style="cyan",
            )
        )

        # ── İşletim Sistemi ───────────────────────────────────────────────
        os_info = self._get_os_info()
        tbl = Table(title="🖥️  İşletim Sistemi", show_header=False, border_style="blue")
        tbl.add_column("Özellik", style="cyan")
        tbl.add_column("Değer", style="white")
        for k, v in os_info.items():
            tbl.add_row(k, str(v))
        tbl.add_row("Uptime", self._get_uptime())
        tbl.add_row("Boot Zamanı", self._get_boot_time())
        self.console.print(tbl)
        self.console.print()

        # ── CPU ───────────────────────────────────────────────────────────
        cpu_info = self._get_cpu_info()
        tbl = Table(title="🧮 CPU", show_header=False, border_style="green")
        tbl.add_column("Özellik", style="cyan")
        tbl.add_column("Değer", style="white")
        for k, v in cpu_info.items():
            tbl.add_row(k, str(v))
        self.console.print(tbl)
        self.console.print()

        # ── RAM ───────────────────────────────────────────────────────────
        ram_info = self._get_ram_info()
        tbl = Table(title="🧠 RAM", show_header=False, border_style="yellow")
        tbl.add_column("Özellik", style="cyan")
        tbl.add_column("Değer", style="white")
        for k, v in ram_info.items():
            color = (
                "red" if k == "Kullanım" and float(v.replace("%", "")) > 80 else "white"
            )
            tbl.add_row(k, f"[{color}]{v}[/{color}]")
        self.console.print(tbl)
        self.console.print()

        # ── Disk ──────────────────────────────────────────────────────────
        if show_disk:
            disks = self._get_disk_info()
            if disks:
                tbl = Table(title="💾 Disk Bölümleri", border_style="magenta")
                tbl.add_column("Bağlama", style="cyan")
                tbl.add_column("FS", style="dim")
                tbl.add_column("Toplam", justify="right")
                tbl.add_column("Kullanılan", justify="right")
                tbl.add_column("Boş", justify="right")
                tbl.add_column("Kullanım", justify="right")
                for d in disks:
                    pct = float(d["Kullanım"].replace("%", ""))
                    clr = "red" if pct > 90 else "yellow" if pct > 70 else "green"
                    tbl.add_row(
                        d["Bağlama Noktası"],
                        d["Dosya Sistemi"],
                        d["Toplam"],
                        d["Kullanılan"],
                        d["Boş"],
                        f"[{clr}]{d['Kullanım']}[/{clr}]",
                    )
                self.console.print(tbl)
                self.console.print()

        # ── Ağ ────────────────────────────────────────────────────────────
        if show_network:
            ifaces = self._get_network_info()
            if ifaces:
                tbl = Table(title="🌐 Ağ Arayüzleri", border_style="blue")
                tbl.add_column("Arayüz", style="cyan")
                tbl.add_column("IPv4")
                tbl.add_column("MAC")
                tbl.add_column("Durum")
                for ifc in ifaces:
                    tbl.add_row(ifc["Arayüz"], ifc["IPv4"], ifc["MAC"], ifc["Durum"])
                self.console.print(tbl)
                self.console.print()

        # ── Süreçler ─────────────────────────────────────────────────────
        if show_processes:
            procs = self._get_top_processes(process_count)
            if procs:
                tbl = Table(
                    title=f"⚡ En Aktif {process_count} Süreç", border_style="red"
                )
                tbl.add_column("PID", style="dim")
                tbl.add_column("İsim", style="cyan")
                tbl.add_column("CPU%", justify="right")
                tbl.add_column("RAM%", justify="right")
                for p in procs:
                    tbl.add_row(p["PID"], p["İsim"], p["CPU%"], p["RAM%"])
                self.console.print(tbl)
                self.console.print()

        logger.info("Sistem bilgisi toplama tamamlandı")
        return True
