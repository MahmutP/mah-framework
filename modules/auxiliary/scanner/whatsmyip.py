import socket
import ssl
import urllib.request
from typing import Any

from core.module import BaseModule


class WhatsMyIPModule(BaseModule):
    """Mevcut makinenin Local (LAN) ve Public (WAN) IP adresini gösterir."""

    Name: str = "What's My IP"
    Description: str = "Shows your local (LAN) and public (WAN) IP address."
    Author: str = "Mahmut P."
    Category: str = "auxiliary/scanner"

    def __init__(self):
        super().__init__()

    def get_local_ip(self) -> str:
        """Local IP adresini döndürür."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Google DNS'e bağlanarak local IP'yi öğren (bağlantı kurulmaz, sadece route bakılır)
            s.connect(("8.8.8.8", 80))
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
            with urllib.request.urlopen(
                "https://ident.me", context=ctx, timeout=5
            ) as response:
                return response.read().decode("utf-8").strip()
        except Exception as e:
            return f"Error: {e!s}"

    def run(self, options: dict[str, Any]) -> str | list[str]:
        local_ip = self.get_local_ip()
        public_ip = self.get_public_ip()

        output = [
            "[*] Your IP Addresses:",
            f"    Local IP (LAN):  {local_ip}",
            f"    Public IP (WAN): {public_ip}",
        ]

        return "\n".join(output)
