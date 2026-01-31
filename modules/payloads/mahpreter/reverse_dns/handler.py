from core.handler import BaseHandler
import socket
from rich import print
import struct

class Handler(BaseHandler):
    """
    Mahpreter Reverse DNS Handler.
    UDP port 53 üzerinde DNS tünelleme isteklerini dinler.
    """
    def __init__(self, options):
        super().__init__(options)
        self.sock = None

    def start(self):
        """
        UDP Dinleyici başlatır.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.lhost, self.lport))
            self.running = True
            print(f"[*] DNS Dinleyici başlatıldı: {self.lhost}:{self.lport} (UDP)")
            print("[*] DNS Tüneli üzerinden sinyal bekleniyor...")
            
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    self.handle_dns_packet(data, addr)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    if self.running:
                        print(f"[!] Paket okuma hatası: {e}")
        except KeyboardInterrupt:
            print("\n[*] Dinleyici durduruluyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

    def handle_dns_packet(self, data: bytes, addr: tuple):
        """
        Basit DNS paketi analizi.
        Gerçek bir DNS sunucusu gibi davranmaz, sadece tünellenmiş veriyi (heartbeat/data) arar.
        """
        try:
            # DNS Header (12 bytes) atla ve Question bölümünü oku
            if len(data) < 12: return
            
            # Basitçe ascii karakterleri filtreleyip domaine bakabiliriz
            # veya scapy/dnslib gerekmeden ham veriyi basabiliriz.
            try:
                content = data[12:].decode('utf-8', errors='ignore')
                # Temizlenebilir karakterler
                clean_content = "".join([c for c in content if c.isprintable()])
                
                print(f"[+] DNS İsteği Geldi ({addr[0]}): {clean_content}")
                
            except:
                print(f"[+] Ham veri ({addr[0]}): {data!r}")
                
        except Exception as e:
            print(f"[!] Paket işleme hatası: {e}")
