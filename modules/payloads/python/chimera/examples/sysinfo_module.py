"""
Chimera Örnek Modül - Sistem Bilgisi Toplama
Bu modül, agent'a yüklenip çalıştırılabilecek örnek bir modüldür.
"""

import os
import platform
import socket

def get_system_info():
    """Detaylı sistem bilgisi toplar"""
    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    }
    
    result = "=== Sistem Bilgisi ===\n"
    for key, value in info.items():
        result += f"{key}: {value}\n"
    
    return result

def list_directory(path="."):
    """Belirtilen dizindeki dosyaları listeler"""
    try:
        items = os.listdir(path)
        result = f"=== {path} içeriği ===\n"
        for item in items:
            full_path = os.path.join(path, item)
            item_type = "DIR" if os.path.isdir(full_path) else "FILE"
            result += f"[{item_type}] {item}\n"
        return result
    except Exception as e:
        return f"Hata: {str(e)}"

def get_network_info():
    """Ağ bilgilerini toplar"""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        result = "=== Ağ Bilgisi ===\n"
        result += f"Hostname: {hostname}\n"
        result += f"IP: {ip}\n"
        
        return result
    except Exception as e:
        return f"Hata: {str(e)}"
