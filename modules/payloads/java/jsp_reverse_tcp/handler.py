from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """JSP Reverse Shell Handler — keep-alive + sessions -i / MultiHandler interact."""

    def handle_connection(self, client_sock, session_id=None):
        self.client_sock = client_sock
        print(f"[*] Shell oturumu hazır (Session: {session_id}).")
        if session_id is not None:
            print(f"[*] Etkileşim için: sessions -i {session_id}")
        self.keep_connection_alive(client_sock)

    def interact(self, session_id: int):
        sock = self.resolve_client_sock(session_id)
        if not sock:
            print(f"[!] Session {session_id}: aktif soket yok.")
            return
        self.raw_shell_loop(sock, session_id=session_id)
