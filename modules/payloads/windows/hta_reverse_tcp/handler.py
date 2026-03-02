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
    def handle_connection(self, client_sock, session_id=None):
        print(f"[*] Shell oturumu başlatılıyor... (Session: {session_id})")
        print("-" * 50)
        
        try:
            while True:
                rlist, _, _ = select.select([client_sock, sys.stdin], [], [])
                
                for r in rlist:
                    if r == client_sock:
                        data = client_sock.recv(4096)
                        if not data:
                            print("\n[!] Bağlantı karşı taraftan kapatıldı.")
                            return
                        sys.stdout.buffer.write(data)
                        sys.stdout.flush()
                        
                    elif r == sys.stdin:
                        msg = sys.stdin.readline()
                        if not msg: break
                        client_sock.sendall(msg.encode())
                        
        except KeyboardInterrupt:
            print("\n[*] Shell oturumu sonlandırılıyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
