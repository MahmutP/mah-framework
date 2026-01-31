from core.handler import BaseHandler
import threading
import socket
import sys
import select
from rich import print

class Handler(BaseHandler):
    """
    Standart Reverse Shell Handler (Netcat clone).
    """
    def handle_connection(self, client_sock):
        print("[*] Shell oturumu başlatılıyor...")
        print("-" * 50)
        
        # Basit bir loop yerine select ile hem socket hem stdin dinleyelim
        # Bu sayede non-blocking I/O simüle edebiliriz
        
        try:
            while True:
                # Okunabilir kaynakları belirle: user input (stdin) ve socket
                rlist, _, _ = select.select([client_sock, sys.stdin], [], [])
                
                for r in rlist:
                    if r == client_sock:
                        # Socket'ten veri geldi, ekrana bas
                        data = client_sock.recv(4096)
                        if not data:
                            print("\n[!] Bağlantı karşı taraftan kapatıldı.")
                            return
                        # Gelen ham veriyi olduğu gibi bas (decode etmeye çalışmadan, binary olabilir)
                        sys.stdout.buffer.write(data)
                        sys.stdout.flush()
                        
                    elif r == sys.stdin:
                        # Klavyeden veri geldi, socket'e gönder
                        msg = sys.stdin.readline()
                        if not msg: break # EOF
                        client_sock.sendall(msg.encode())
                        
        except KeyboardInterrupt:
            print("\n[*] Shell oturumu sonlandırılıyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
