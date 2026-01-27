# =============================================================================
# System Information Module
# =============================================================================
# Kapsamlı sistem bilgisi toplayan modül
#
# AÇIKLAMA:
#   Bu modül, çalıştırıldığı sistemin detaylı donanım ve yazılım bilgilerini
#   toplar ve görsel olarak sunar. Penetrasyon testlerinde hedef sistem
#   keşfi için kullanılabilir.
#
# ÖZELLİKLER:
#   - İşletim sistemi bilgileri
#   - CPU detayları ve kullanım oranı
#   - RAM kullanımı
#   - Disk bölümleri ve kullanım oranları
#   - Ağ arayüzleri ve IP adresleri
#   - Çalışan süreçler (en çok kaynak tüketen)
#   - Sistem çalışma süresi (uptime)
#
# KULLANIM:
#   1. use post/systeminfo
#   2. set SHOW_PROCESSES true/false
#   3. set PROCESS_COUNT 10
#   4. run
# =============================================================================

import platform
import os
import getpass
import socket
import psutil
import datetime
from typing import Dict, Any, List

from core.module import BaseModule
from core.option import Option
from core import logger
from rich import print
from rich.table import Table
from rich.console import Console
from rich.panel import Panel


class systeminfo(BaseModule):
    """Kapsamlı Sistem Bilgisi Modülü
    
    Bu modül, çalıştırıldığı sistemin donanım ve yazılım bilgilerini
    detaylı şekilde toplar ve rich kütüphanesi ile görsel olarak sunar.
    
    Toplanan Bilgiler:
        - İşletim sistemi: Tür, sürüm, mimari
        - CPU: Çekirdek sayısı, kullanım oranı
        - RAM: Toplam, kullanılan, boş
        - Disk: Bölümler, boyutlar, kullanım oranları
        - Ağ: Arayüzler, IP adresleri
        - Süreçler: En çok CPU/RAM kullanan süreçler
        - Uptime: Sistem çalışma süresi
    """
    
    # =========================================================================
    # MODÜL META BİLGİLERİ
    # =========================================================================
    Name = "System Information"
    Description = "Kapsamlı sistem bilgisi toplar: OS, CPU, RAM, Disk, Ağ, Süreçler"
    Author = "Mahmut P."
    Category = "uncategorized"
    
    def __init__(self):
        """Modül başlatıcı - Options tanımlaması"""
        super().__init__()
        
        self.Options = {
            "SHOW_PROCESSES": Option(
                name="SHOW_PROCESSES",
                value="true",
                required=False,
                description="Çalışan süreçleri göster (true/false)"
            ),
            "PROCESS_COUNT": Option(
                name="PROCESS_COUNT",
                value=10,
                required=False,
                description="Gösterilecek süreç sayısı",
                regex_check=True,
                regex=r"^\d+$"
            ),
            "SHOW_NETWORK": Option(
                name="SHOW_NETWORK",
                value="true",
                required=False,
                description="Ağ arayüzlerini göster (true/false)"
            ),
            "SHOW_DISK": Option(
                name="SHOW_DISK",
                value="true",
                required=False,
                description="Disk bilgilerini göster (true/false)"
            ),
        }
        
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
        
        self.console = Console()
    
    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    
    def _bytes_to_human(self, bytes_val: int) -> str:
        """Byte değerini okunabilir formata çevirir.
        
        Args:
            bytes_val: Byte cinsinden değer
            
        Returns:
            Okunabilir string (örn: "4.5 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    def _seconds_to_human(self, seconds: int) -> str:
        """Saniye değerini okunabilir süreye çevirir.
        
        Args:
            seconds: Saniye cinsinden süre
            
        Returns:
            Okunabilir string (örn: "2 gün, 5 saat, 30 dakika")
        """
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{int(days)} gün")
        if hours > 0:
            parts.append(f"{int(hours)} saat")
        if minutes > 0:
            parts.append(f"{int(minutes)} dakika")
        if not parts:
            parts.append(f"{int(seconds)} saniye")
        
        return ", ".join(parts)
    
    def _get_os_info(self) -> Dict[str, str]:
        """İşletim sistemi bilgilerini toplar."""
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
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """CPU bilgilerini toplar."""
        try:
            freq = psutil.cpu_freq()
            freq_current = f"{freq.current:.0f} MHz" if freq else "Bilinmiyor"
        except Exception:
            freq_current = "Bilinmiyor"
        
        return {
            "Fiziksel Çekirdek": psutil.cpu_count(logical=False) or "?",
            "Mantıksal Çekirdek": psutil.cpu_count(logical=True) or "?",
            "CPU Kullanımı": f"{psutil.cpu_percent(interval=0.5)}%",
            "Frekans": freq_current,
        }
    
    def _get_ram_info(self) -> Dict[str, str]:
        """RAM bilgilerini toplar."""
        mem = psutil.virtual_memory()
        return {
            "Toplam": self._bytes_to_human(mem.total),
            "Kullanılan": self._bytes_to_human(mem.used),
            "Boş": self._bytes_to_human(mem.available),
            "Kullanım": f"{mem.percent}%",
        }
    
    def _get_disk_info(self) -> List[Dict[str, str]]:
        """Disk bölümlerini ve kullanım bilgilerini toplar."""
        disks = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        "Bağlama Noktası": partition.mountpoint,
                        "Dosya Sistemi": partition.fstype,
                        "Toplam": self._bytes_to_human(usage.total),
                        "Kullanılan": self._bytes_to_human(usage.used),
                        "Boş": self._bytes_to_human(usage.free),
                        "Kullanım": f"{usage.percent}%",
                    })
                except PermissionError:
                    continue
        except Exception:
            pass
        return disks
    
    def _get_network_info(self) -> List[Dict[str, str]]:
        """Ağ arayüzlerini ve IP adreslerini toplar."""
        interfaces = []
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for iface_name, iface_addrs in addrs.items():
                if iface_name.startswith('lo'):  # Loopback atla
                    continue
                
                ipv4 = "-"
                mac = "-"
                
                for addr in iface_addrs:
                    if addr.family == socket.AF_INET:
                        ipv4 = addr.address
                    elif addr.family == psutil.AF_LINK:
                        mac = addr.address
                
                is_up = stats.get(iface_name, None)
                status = "🟢 Aktif" if is_up and is_up.isup else "🔴 Pasif"
                
                interfaces.append({
                    "Arayüz": iface_name,
                    "IPv4": ipv4,
                    "MAC": mac,
                    "Durum": status,
                })
        except Exception:
            pass
        return interfaces
    
    def _get_top_processes(self, count: int) -> List[Dict[str, str]]:
        """En çok kaynak tüketen süreçleri toplar."""
        processes = []
        try:
            for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                             key=lambda x: x.info.get('cpu_percent', 0) or 0,
                             reverse=True)[:count]:
                try:
                    info = proc.info
                    processes.append({
                        "PID": str(info.get('pid', '?')),
                        "İsim": (info.get('name', '?') or '?')[:25],
                        "CPU%": f"{info.get('cpu_percent', 0):.1f}%",
                        "RAM%": f"{info.get('memory_percent', 0):.1f}%",
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return processes
    
    def _get_uptime(self) -> str:
        """Sistem çalışma süresini hesaplar."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = int(datetime.datetime.now().timestamp() - boot_time)
            return self._seconds_to_human(uptime_seconds)
        except Exception:
            return "Bilinmiyor"
    
    def _get_boot_time(self) -> str:
        """Sistem açılış zamanını döndürür."""
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            return boot_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Bilinmiyor"
    
    # =========================================================================
    # ANA ÇALIŞTIRMA METODU
    # =========================================================================
    
    def run(self, options: Dict[str, Any]) -> bool:
        """Sistem bilgilerini toplar ve görüntüler.
        
        Args:
            options: Kullanıcı ayarları
            
        Returns:
            Başarılı ise True
        """
        show_processes = str(options.get("SHOW_PROCESSES", "true")).lower() == "true"
        process_count = int(options.get("PROCESS_COUNT", 10))
        show_network = str(options.get("SHOW_NETWORK", "true")).lower() == "true"
        show_disk = str(options.get("SHOW_DISK", "true")).lower() == "true"
        
        logger.info("Sistem bilgisi toplama başlatıldı")
        
        # =====================================================================
        # BAŞLIK
        # =====================================================================
        self.console.print()
        self.console.print(Panel.fit(
            "[bold cyan]📊 SİSTEM BİLGİLERİ[/bold cyan]",
            border_style="cyan"
        ))
        
        # =====================================================================
        # İŞLETİM SİSTEMİ
        # =====================================================================
        os_info = self._get_os_info()
        
        table = Table(title="🖥️  İşletim Sistemi", show_header=False, border_style="blue")
        table.add_column("Özellik", style="cyan")
        table.add_column("Değer", style="white")
        
        for key, value in os_info.items():
            table.add_row(key, str(value))
        
        # Uptime ekle
        table.add_row("Uptime", self._get_uptime())
        table.add_row("Boot Zamanı", self._get_boot_time())
        
        self.console.print(table)
        self.console.print()
        
        # =====================================================================
        # CPU
        # =====================================================================
        cpu_info = self._get_cpu_info()
        
        table = Table(title="🧮 CPU", show_header=False, border_style="green")
        table.add_column("Özellik", style="cyan")
        table.add_column("Değer", style="white")
        
        for key, value in cpu_info.items():
            table.add_row(key, str(value))
        
        self.console.print(table)
        self.console.print()
        
        # =====================================================================
        # RAM
        # =====================================================================
        ram_info = self._get_ram_info()
        
        table = Table(title="🧠 RAM", show_header=False, border_style="yellow")
        table.add_column("Özellik", style="cyan")
        table.add_column("Değer", style="white")
        
        for key, value in ram_info.items():
            color = "red" if key == "Kullanım" and float(value.replace('%', '')) > 80 else "white"
            table.add_row(key, f"[{color}]{value}[/{color}]")
        
        self.console.print(table)
        self.console.print()
        
        # =====================================================================
        # DİSK
        # =====================================================================
        if show_disk:
            disks = self._get_disk_info()
            
            if disks:
                table = Table(title="💾 Disk Bölümleri", border_style="magenta")
                table.add_column("Bağlama", style="cyan")
                table.add_column("FS", style="dim")
                table.add_column("Toplam", justify="right")
                table.add_column("Kullanılan", justify="right")
                table.add_column("Boş", justify="right")
                table.add_column("Kullanım", justify="right")
                
                for disk in disks:
                    usage = float(disk["Kullanım"].replace('%', ''))
                    color = "red" if usage > 90 else "yellow" if usage > 70 else "green"
                    table.add_row(
                        disk["Bağlama Noktası"],
                        disk["Dosya Sistemi"],
                        disk["Toplam"],
                        disk["Kullanılan"],
                        disk["Boş"],
                        f"[{color}]{disk['Kullanım']}[/{color}]"
                    )
                
                self.console.print(table)
                self.console.print()
        
        # =====================================================================
        # AĞ
        # =====================================================================
        if show_network:
            interfaces = self._get_network_info()
            
            if interfaces:
                table = Table(title="🌐 Ağ Arayüzleri", border_style="blue")
                table.add_column("Arayüz", style="cyan")
                table.add_column("IPv4")
                table.add_column("MAC")
                table.add_column("Durum")
                
                for iface in interfaces:
                    table.add_row(
                        iface["Arayüz"],
                        iface["IPv4"],
                        iface["MAC"],
                        iface["Durum"]
                    )
                
                self.console.print(table)
                self.console.print()
        
        # =====================================================================
        # SÜREÇLER
        # =====================================================================
        if show_processes:
            processes = self._get_top_processes(process_count)
            
            if processes:
                table = Table(title=f"⚡ En Aktif {process_count} Süreç", border_style="red")
                table.add_column("PID", style="dim")
                table.add_column("İsim", style="cyan")
                table.add_column("CPU%", justify="right")
                table.add_column("RAM%", justify="right")
                
                for proc in processes:
                    table.add_row(
                        proc["PID"],
                        proc["İsim"],
                        proc["CPU%"],
                        proc["RAM%"]
                    )
                
                self.console.print(table)
                self.console.print()
        
        logger.info("Sistem bilgisi toplama tamamlandı")
        return True