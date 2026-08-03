# Chimera oturumuna interaktif shell'e girmeden loadmodule/runmodule gönderen köprü.

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from rich import print

from core.shared_state import shared_state


def resolve_session(session_id: Any) -> dict[str, Any] | None:
    """SESSION seçeneğinden oturum kaydını çözer."""
    if session_id is None or str(session_id).strip() == "":
        return None

    try:
        sid = int(str(session_id).strip())
    except (TypeError, ValueError):
        print(f"[!] Geçersiz SESSION değeri: {session_id}")
        return None

    sm = shared_state.session_manager
    if not sm:
        print("[!] Session manager başlatılmamış.")
        return None

    session = sm.get_session(sid)
    if not session:
        print(f"[!] Session {sid} bulunamadı.")
        return None
    return session


def is_chimera_session(session: dict[str, Any]) -> bool:
    """Oturumun Chimera olup olmadığını kontrol eder."""
    session_type = str(session.get("type", "") or "")
    if session_type.lower() == "chimera":
        return True
    info = session.get("info") or {}
    return str(info.get("type", "") or "").lower() == "chimera"


def warn_localhost_without_session(module_name: str = "") -> None:
    """Yerel post/gather için SESSION yok uyarısı."""
    prefix = f"[{module_name}] " if module_name else ""
    print(
        f"[yellow][!] {prefix}SESSION ayarlı değil — modül localhost üzerinde çalışacak.[/yellow]"
    )


def _encode_agent_source(source: str) -> str:
    return base64.b64encode(source.encode("utf-8")).decode("utf-8")


def load_and_run_on_chimera(
    session_id: Any,
    module_name: str,
    agent_source: str | None = None,
    agent_file: str | Path | None = None,
    func_name: str = "run",
    func_args: list[str] | None = None,
) -> str | None:
    """
    Chimera oturumuna loadmodule + runmodule gönderir (interaktif shell yok).

    agent_source veya agent_file'dan biri zorunlu.
    Başarılıysa ajan çıktısını (str) döner; hata durumunda None.
    """
    session = resolve_session(session_id)
    if not session:
        return None

    if not is_chimera_session(session):
        print(
            f"[!] Session {session.get('id')} Chimera değil "
            f"(type={session.get('type')}). loadmodule desteklenmiyor."
        )
        return None

    handler = session.get("handler")
    if handler is None:
        print("[!] Oturumda handler yok.")
        return None

    if not hasattr(handler, "send_data") or not hasattr(handler, "recv_data"):
        print("[!] Handler send_data/recv_data desteklemiyor.")
        return None

    source = agent_source
    if source is None and agent_file is not None:
        path = Path(agent_file)
        if not path.is_file():
            print(f"[!] Agent dosyası bulunamadı: {path}")
            return None
        source = path.read_text(encoding="utf-8")
        if not module_name:
            module_name = path.stem

    if not source:
        print("[!] Agent kaynağı boş.")
        return None

    if not module_name:
        module_name = "chimera_module"

    b64 = _encode_agent_source(source)
    load_cmd = f"loadmodule {module_name} {b64}"

    try:
        print(f"[*] Session {session['id']}: loadmodule {module_name} ({len(source)} bytes)")
        handler.send_data(load_cmd)
        load_resp = handler.recv_data() or ""
        if load_resp:
            print(load_resp)

        run_parts = ["runmodule", module_name, func_name]
        if func_args:
            run_parts.extend(str(a) for a in func_args)
        run_cmd = " ".join(run_parts)

        print(f"[*] Session {session['id']}: {run_cmd}")
        handler.send_data(run_cmd)
        run_resp = handler.recv_data() or ""

        sm = shared_state.session_manager
        if sm and hasattr(sm, "update_session_activity"):
            sm.update_session_activity(int(session["id"]))

        return run_resp
    except Exception as exc:
        print(f"[!] Chimera köprü hatası: {exc}")
        return None


def run_chimera_post_module(
    options: dict[str, Any],
    module_name: str,
    agent_source: str,
    func_name: str = "run",
) -> bool:
    """
    BaseModule.run() için kolaylık sarmalayıcı.
    SESSION zorunlu; sonucu yazdırır ve başarı durumu döner.
    """
    session_val = options.get("SESSION", "")
    if session_val is None or str(session_val).strip() == "":
        print(
            "[!] Bu Chimera post modülü SESSION gerektirir. "
            "Örn: set SESSION 1"
        )
        return False

    result = load_and_run_on_chimera(
        session_id=session_val,
        module_name=module_name,
        agent_source=agent_source,
        func_name=func_name,
    )
    if result is None:
        return False
    if result:
        print(result)
    return True
