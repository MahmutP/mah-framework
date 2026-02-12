"""Resource Monitor Plugin for Mah Framework."""

import threading
import time
import psutil
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable

from core.plugin import BasePlugin
from core.hooks import HookType

class ResourceMonitor(BasePlugin):
    """Sistem kaynak kullanımı (CPU, RAM, Disk, Ağ) izleyen eklenti."""
    
    Name: str = "Resource Monitor"
    Description: str = "Sistem kaynaklarını (CPU, RAM, Disk, Ağ) sürekli loglar"
    Author: str = "Mahmut P."
    Version: str = "1.0.0"
    Enabled: bool = False  # Varsayılan olarak kapalı: Kullanıcı açmalı
    Priority: int = 90     # Loglama olduğu için yüksek öncelik
    
    def __init__(self):
        super().__init__()
        # Log dosyasının konumu: config/logs/resources.log
        self.log_dir = Path("config/logs")
        self.log_file = self.log_dir / "resources.log"
        
        # Thread yönetimi
        self._stop_event = threading.Event()
        self._thread = None
        
        # Log klasörü yoksa oluştur
        if not self.log_dir.exists():
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    def on_load(self) -> None:
        """Plugin yüklendiğinde çalışır."""
        # Eğer config dosyasından 'enabled' geldiyse (gelecekte config desteği gelirse)
        # veya disable/enable yapıldıysa, durumu kontrol et
        if self.Enabled:
            self._start_monitoring(silent=False)

    def on_unload(self) -> None:
        """Plugin kapatıldığında veya devre dışı bırakıldığında çalışır."""
        self._stop_monitoring()
        
    def get_hooks(self) -> Dict[HookType, Callable[..., Any]]:
        return {
            HookType.PRE_COMMAND: self.on_pre_command
        }
    
    def on_pre_command(self, **kwargs: Any) -> None:
        """
        Herhangi bir komut çalışmadan önce kontrol et.
        Plugin enable edildikten sonra henüz thread başlamadıysa buradan tetikleriz.
        """
        if self.Enabled and (not self._thread or not self._thread.is_alive()):
            self._start_monitoring(silent=True)
            
    def _start_monitoring(self, silent: bool = False):
        """İzleme thread'ini başlatır."""
        if self._thread and self._thread.is_alive():
            return
        
        if not silent:
            print(f"[Plugin] [{self.Name}] Kaynak izleme başlatıldı. Log: {self.log_file}")
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _stop_monitoring(self):
        """İzleme thread'ini durdurur."""
        if self._thread:
            print("[Resource Monitor] Kaynak izleme durduruluyor...")
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            self._thread = None
            print("[Resource Monitor] Durduruldu.")

    def _monitor_loop(self):
        """Arka planda çalışan izleme döngüsü."""
        # Ağ kullanımı için başlangıç değerlerini al
        last_net = psutil.net_io_counters()
        last_time = time.time()
        
        # Mevcut process (mah-framework)
        current_process = psutil.Process()
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                time_diff = current_time - last_time
                if time_diff < 0.1: time_diff = 0.1 # Sıfıra bölünme hatasını önle
                
                # --- CPU (Sistem Geneli vs Process) ---
                sys_cpu_percent = psutil.cpu_percent(interval=None)
                # Process CPU kullanımı %100'ü geçebilir (çok çekirdekli sistemlerde), bu yüzden çekirdek sayısına bölmek mantıklı olabilir
                # ama standart top çıktısı gibi bırakalım.
                proc_cpu_percent = current_process.cpu_percent(interval=None)
                
                # --- RAM (Sistem Geneli vs Process) ---
                # Sistem
                sys_memory = psutil.virtual_memory()
                sys_ram_percent = sys_memory.percent
                sys_ram_used_gb = round(sys_memory.used / (1024**3), 2)
                sys_ram_total_gb = round(sys_memory.total / (1024**3), 2)
                
                # Process (RSS - Resident Set Size: RAM'deki fiziksel kullanımı)
                proc_memory_info = current_process.memory_info()
                proc_ram_mb = round(proc_memory_info.rss / (1024**2), 2) # MB cinsinden
                
                # --- Disk ---
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                
                # --- Network (Sistem Geneli) ---
                current_net = psutil.net_io_counters()
                bytes_sent = current_net.bytes_sent - last_net.bytes_sent
                bytes_recv = current_net.bytes_recv - last_net.bytes_recv
                
                # Hızı hesapla (KB/s)
                sent_kbps = round((bytes_sent / 1024) / time_diff, 1)
                recv_kbps = round((bytes_recv / 1024) / time_diff, 1)
                
                last_net = current_net
                last_time = current_time
                
                # --- GPU (Placeholder) ---
                gpu_info = "N/A"
                
                # Log formatı
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Format: [Zaman] SYS_CPU: %x | PROC_CPU: %y | SYS_RAM: %a | PROC_RAM: b MB ...
                log_line = (
                    f"[{timestamp}] "
                    f"SYS_CPU: {sys_cpu_percent}% | "
                    f"PROC_CPU: {proc_cpu_percent}% | "
                    f"SYS_RAM: {sys_ram_percent}% ({sys_ram_used_gb}/{sys_ram_total_gb} GB) | "
                    f"PROC_RAM: {proc_ram_mb} MB | "
                    f"Disk: {disk_percent}% | "
                    f"Net: ↑{sent_kbps} KB/s ↓{recv_kbps} KB/s | "
                    f"GPU: {gpu_info}\n"
                )
                
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_line)
                
            except Exception as e:
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] ERROR: {str(e)}\n")
                except:
                    pass
                
            # 5 saniye bekle
            self._stop_event.wait(5.0)
