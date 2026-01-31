from typing import Dict, Any
import socket
import threading
from rich import print

class BaseHandler:
    """
    Tüm payload handler'ları için temel sınıf.
    """
    def __init__(self, options: Dict[str, Any]):
        self.options = options
        self.lhost = options.get("LHOST", "0.0.0.0")
        self.lport = int(options.get("LPORT", 4444))
        self.sock = None
        self.client_sock = None
        self.client_addr = None
        self.running = False

    def start(self):
        """
        Dinleyiciyi başlatır.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.lhost, self.lport))
            self.sock.listen(1)
            self.running = True
            print(f"[*] Dinleniyor: {self.lhost}:{self.lport} (Çıkmak için CTRL+C)")
            
            # Bağlantı bekleme döngüsü
            while self.running:
                try:
                    self.client_sock, self.client_addr = self.sock.accept()
                    print(f"[+] Bağlantı geldi: {self.client_addr[0]}:{self.client_addr[1]}")
                    self.handle_connection(self.client_sock)
                    break # Şimdilik tek bağlantı sonrası duralım veya handler logic'i karar versin
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    if self.running:
                        print(f"[!] Bağlantı kabul hatası: {e}")
        except KeyboardInterrupt:
            print("\n[*] Dinleyici durduruluyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Dinleyiciyi ve bağlantıları kapatır.
        """
        self.running = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

    def handle_connection(self, client_sock: socket.socket):
        """
        Gelen bağlantıyı yönetecek fonksiyon.
        Alt sınıflar bunu override etmeli.
        """
        raise NotImplementedError("Alt sınıflar handle_connection metodunu uygulamalıdır.")
