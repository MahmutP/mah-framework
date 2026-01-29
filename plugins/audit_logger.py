"""Audit Logger Plugin for Mah Framework."""

import os
from datetime import datetime
from typing import Dict, Any, Callable
from pathlib import Path

from core.plugin import BasePlugin
from core.hooks import HookType

class AuditLogger(BasePlugin):
    """Tüm komut ve modül çalışmalarını loglayan denetim eklentisi."""
    
    Name: str = "Audit Logger"
    Description: str = "Tüm komut ve modül çalışmalarını loglar"
    Author: str = "Mahmut P."
    Version: str = "1.0.0"
    Enabled: bool = True
    Priority: int = 100
    
    def __init__(self):
        super().__init__()
        # Log dosyasının konumu: config/logs/audit.log
        self.log_dir = Path("config/logs")
        self.log_file = self.log_dir / "audit.log"
        
        # Log klasörü yoksa oluştur
        if not self.log_dir.exists():
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
    
    def on_load(self) -> None:
        """Plugin yüklendiğinde çalışır."""
        print("[Plugin] Audit Logger aktif")
        self._write_log("SYSTEM", "Audit Logger aktif")

    def on_unload(self) -> None:
        """Plugin kapatıldığında çalışır."""
        print("Audit Logger kapatıldı")
        self._write_log("SYSTEM", "Audit Logger kapatıldı")
        
    def get_hooks(self) -> Dict[HookType, Callable[..., Any]]:
        return {
            HookType.PRE_COMMAND: self.on_pre_command,
            HookType.POST_MODULE_RUN: self.on_post_module_run
        }
    
    def on_pre_command(self, command_line: str, **kwargs: Any) -> None:
        """Komut çalıştırılmadan önce loglar."""
        self._write_log("COMMAND", f"Exec: {command_line}")
            
    def on_post_module_run(self, module_path: str, success: bool, **kwargs: Any) -> None:
        """Modül çalıştırıldıktan sonra loglar."""
        status = "SUCCESS" if success else "FAILED"
        self._write_log("MODULE", f"Run: {module_path} Status: {status}")
    
    def _write_log(self, event_type: str, details: str) -> None:
        """Log dosyasına kendi formatında yazar (Core Logger'dan bağımsız)."""
        try:
            timestamp = datetime.now().isoformat()
            # Örn: [2023-10-27T10:00:00.123456] COMMAND: Exec: help
            log_line = f"[{timestamp}] {event_type}: {details}\n"
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            # Hata durumunda sessiz kal veya konsola bas (döngüyü önlemek için dikkatli ol)
            print(f"[Audit Logger Hatası] {e}")
