# Shell oturumunu PTY'ye yükseltme (upgrade) post modülü.
# Mevcut bir reverse shell oturumunu tam etkileşimli PTY terminaline dönüştürür.
#
# Kullanım:
#   use post/shell/pty_upgrade
#   set SESSION <id>
#   set METHOD python3    (opsiyonel: python3, python2, script, socat, perl, expect)
#   set INTERACT true     (opsiyonel: upgrade sonrası PTY oturumuna gir)
#   run
#
# Bu modül tamamen etik siber güvenlik amaçlıdır.

from typing import Any

from rich import print

from core.module import BaseModule
from core.option import Option
from core.shared_state import shared_state


class PTYUpgrade(BaseModule):
    """
    Shell → PTY Upgrade Post Modülü.

    Mevcut bir raw reverse shell oturumunu tam etkileşimli PTY
    terminaline yükseltir. Penelope tarzı upgrade teknikleri kullanır.

    Yükseltme sonrası:
      - Ctrl+C uzak işlemi durdurur (framework'ü değil)
      - Tab tamamlama çalışır
      - Vim, nano, top gibi araçlar kullanılabilir
      - Ok tuşları, komut geçmişi aktif olur
    """

    Name = "Shell to PTY Upgrade"
    Description = (
        "Mevcut reverse shell oturumunu tam etkileşimli PTY terminaline yükseltir."
    )
    Author = "Mahmut P."
    Category = "post"
    Version = "1.0"

    def __init__(self) -> None:
        super().__init__()
        self.Options = {
            "SESSION": Option(
                "SESSION",
                "",
                True,
                "Yükseltilecek oturum ID'si.",
            ),
            "METHOD": Option(
                "METHOD",
                "auto",
                False,
                "Upgrade yöntemi: auto, python3, python2, script, socat, perl, expect.",
            ),
            "INTERACT": Option(
                "INTERACT",
                "true",
                False,
                "Upgrade sonrası otomatik olarak PTY oturumuna gir (true/false).",
            ),
        }

    def run(self, options: dict[str, Any]) -> bool:
        """
        Oturumu PTY'ye yükseltir ve (opsiyonel olarak) etkileşimli moda girer.
        """
        session_id_raw = options.get("SESSION", "")
        if not session_id_raw or str(session_id_raw).strip() == "":
            print("[!] SESSION belirtilmedi. Kullanım: set SESSION <id>")
            return False

        try:
            session_id = int(str(session_id_raw).strip())
        except ValueError:
            print(f"[!] Geçersiz SESSION değeri: {session_id_raw}")
            return False

        method_raw = str(options.get("METHOD", "auto")).strip().lower()
        method = None if method_raw in ("auto", "", "none") else method_raw

        interact_flag = str(options.get("INTERACT", "true")).strip().lower() in (
            "true",
            "1",
            "yes",
            "y",
        )

        # Oturumu bul
        if not shared_state.session_manager:
            print("[!] Session manager başlatılmamış.")
            return False

        session = shared_state.session_manager.get_session(session_id)
        if not session:
            print(f"[!] Session {session_id} bulunamadı.")
            return False

        handler = session.get("handler")
        if not handler:
            print(f"[!] Session {session_id}: handler yok.")
            return False

        # Soket bul
        client_sock = None
        if hasattr(handler, "resolve_client_sock"):
            client_sock = handler.resolve_client_sock(session_id)
        if not client_sock:
            client_sock = getattr(handler, "client_sock", None)
        if not client_sock:
            print(f"[!] Session {session_id}: aktif soket bulunamadı.")
            return False

        print(f"[*] Session {session_id} PTY'ye yükseltiliyor...")
        print(f"[*] Yöntem: {method or 'otomatik (sırayla deneme)'}")

        try:
            from core.pty_handler import send_upgrade_payload, PTYSession
        except ImportError:
            print("[!] core/pty_handler modülü yüklenemedi!")
            return False

        # Upgrade payload'u gönder
        success = send_upgrade_payload(client_sock, method=method)

        if success:
            print("[+] PTY upgrade komutu gönderildi.")

            # Session bilgisini güncelle
            session["info"]["pty_upgraded"] = True
            session["info"]["upgrade_method"] = method or "auto"
            shared_state.session_manager.update_session_activity(session_id)

            if interact_flag:
                print("[*] PTY oturumuna giriliyor...")
                print("[*] Çıkış: Ctrl+] | Ctrl+C artık uzak tarafa gider!")
                pty_session = PTYSession(client_sock, session_id=session_id)
                pty_session.start()
            else:
                print(
                    f"[*] Etkileşime geçmek için: sessions -i {session_id}"
                )
                print(
                    "[*] Veya PTY modunda girmek için: sessions -u "
                    f"{session_id}"
                )
        else:
            print("[!] PTY upgrade başarısız. Olası nedenler:")
            print("    - Hedef sistemde python/script/socat yok")
            print("    - Bağlantı kopmuş olabilir")
            print("[*] Manuel upgrade deneyebilirsiniz:")
            print("    python3 -c 'import pty; pty.spawn(\"/bin/bash\")'")
            return False

        return True
