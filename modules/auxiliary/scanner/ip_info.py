from core.module import BaseModule
from typing import Dict, Any, Union, List
import socket
import urllib.request
import ssl


class IPInfoModule(BaseModule):
    """Local ve Public IP adresini gösteren modül."""
    
    Name: str = "IP Address Info"
    Description: str = "Displays local (LAN) and public (WAN) IP addresses."
    Author: str = "Antigravity"
    Category: str = "auxiliary/scanner"
    
    def __init__(self):
        super().__init__()

    def get_local_ip(self) -> str:
        """Local IP adresini döndürür."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Google DNS'e bağlanarak local IP'yi öğren (bağlantı kurulmaz, sadece route bakılır)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_public_ip(self) -> str:
        """Public IP adresini döndürür."""
        try:
            # SSL sertifika doğrulamasını devre dışı bırak (basit kullanım için)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # ident.me basit bir text döndürür
            with urllib.request.urlopen('https://ident.me', context=ctx, timeout=5) as response:
                return response.read().decode('utf-8').strip()
        except Exception as e:
            return f"Error: {str(e)}"

    def run(self, options: Dict[str, Any]) -> Union[str, List[str]]:
        local_ip = self.get_local_ip()
        public_ip = self.get_public_ip()
        
        output = [
            f"[*] IP Information:",
            f"    Local IP (LAN):  {local_ip}",
            f"    Public IP (WAN): {public_ip}"
        ]
        
        # Tek satır string mi yoksa liste mi dönmeli? Core/module.py BaseModule.run docstring Union[str, List[str]] diyor.
        # Genellikle list dönmek daha temiz çıktı sağlayabilir eğer arayüz destekliyorsa.
        # String olarak joinleyip dönelim garanti olsun.
        
        return "\n".join(output)
