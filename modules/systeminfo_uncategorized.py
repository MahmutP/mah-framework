# katagorize edilmemiş örnek modül
# sistemle alakalı temel bilgileri ekrana basacak.
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
import platform
import os
import getpass
import socket
import psutil
import datetime

class systeminfo(BaseModule):
    Name = "systeminfo"
    Description = "Sistemle ilgili temel bilgileri ekrana basan, katagorize edilmemiş modül."
    Author = "Mahmut P."
    Category = "uncategorized"
    def __init__(self):
        super().__init__()
        self.Options = {
            "message": Option("message", "Selamlar olsun!", False, "Modül çalıştığında ekrana basılacak öylesine bir yazı.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)# objeye değer atama için kullanıyor.
    def run(self, options: Dict[str, Any]):
        print(options.get("message"))
        def bytes_to_gb(bytes_val):
            return round(bytes_val / (1024 ** 3), 2)

        def get_boot_time():
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            return boot_time.strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 40)
        print("📋 SİSTEM BİLGİLERİ".center(40))
        print("=" * 40)
        print(f"👤 Kullanıcı              : {getpass.getuser()}")
        print(f"💻 Bilgisayar Adı         : {socket.gethostname()}")
        print("\n🖥️  İşletim Sistemi")
        print(f"   Sistem                : {platform.system()}")
        print(f"   Sürüm                 : {platform.version()}")
        print(f"   Yayın Adı             : {platform.release()}")
        print(f"   Mimari                : {' '.join(platform.architecture())}")
        print(f"   İşlemci               : {platform.processor()}")
        print(f"   Platform Detayı       : {platform.platform()}")
        print(f"   Boot Zamanı           : {get_boot_time()}")
        print("\n🧠 RAM")
        virtual_mem = psutil.virtual_memory()
        print(f"   Toplam RAM            : {bytes_to_gb(virtual_mem.total)} GB")
        print(f"   Kullanılan RAM        : {bytes_to_gb(virtual_mem.used)} GB")
        print(f"   Boş RAM               : {bytes_to_gb(virtual_mem.available)} GB")
        print(f"   RAM Kullanım Yüzdesi  : {virtual_mem.percent}%")

        print("\n🧮 CPU")
        print(f"   Fiziksel Çekirdek     : {psutil.cpu_count(logical=False)}")
        print(f"   Mantıksal Çekirdek    : {psutil.cpu_count(logical=True)}")
        print(f"   CPU Kullanımı         : {psutil.cpu_percent(interval=1)}%")

        print("=" * 40)
            