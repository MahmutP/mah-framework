from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """
    Standart Python Reverse Shell Handler — PTY upgrade destekli.

    handle_connection yalnızca bağlantıyı canlı tutar (stdin çalmaz).
    Etkileşim: MultiHandler ön plan veya `sessions -i <id>`.

    Background alma:
      sessions -i <id>  → interact gir
      CTRL+C            → background (oturum açık kalır)
      background / bg   → aynı
      sessions -u <id>  → PTY'ye yükselt
      sessions -p <id>  → PTY modunda interact
    """

    def handle_connection(self, client_sock, session_id=None):
        self.client_sock = client_sock
        print(f"[*] Shell oturumu hazır (Session: {session_id}).")
        if session_id is not None:
            print(f"[*] Etkileşim:   sessions -i {session_id}")
            print(f"[*] PTY upgrade: sessions -u {session_id}")
        self.keep_connection_alive(client_sock)

    def interact(self, session_id: int):
        """
        Oturumla etkileşime geçer.
        Session PTY'ye upgrade edilmişse PTY modu kullanır.
        CTRL+C veya 'background' komutu → framework'e döner, oturum açık kalır.
        """
        sock = self.resolve_client_sock(session_id)
        if not sock:
            print(f"[!] Session {session_id}: aktif soket yok.")
            return

        from core.shared_state import shared_state

        pty_mode = False
        if shared_state.session_manager:
            session = shared_state.session_manager.get_session(session_id)
            if session and session.get("info", {}).get("pty_upgraded"):
                pty_mode = True

        if pty_mode:
            print(f"[*] Session {session_id}: PTY modu aktif.")
            self.pty_shell_loop(sock, session_id=session_id, auto_upgrade=False)
        else:
            self.raw_shell_loop(sock, session_id=session_id)
