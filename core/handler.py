# Ağ bağlantılarını ve payload iletişimini yöneten temel sınıfın bulunduğu modül.
# Reverse Shell veya Bind Shell bağlantılarını karşılamak için kullanılır.

from typing import Dict, Any
import socket
import threading
from rich import print

class BaseHandler:
    """
    Tüm payload dinleyicileri (handlers) için temel sınıf.
    TCP/UDP soket oluşturma, dinleme ve bağlantı kabul etme işlemlerini yönetir.
    Özel handler türleri (örn: HTTP, HTTPS) bu sınıftan türetilebilir.

    Multi-client desteği: Birden fazla bağlantıyı paralel olarak kabul edebilir.
    Her bağlantı kendi thread'inde çalışır ve `self.clients` sözlüğünde izlenir.
    """
    
    def __init__(self, options: Dict[str, Any]):
        """
        Handler'ı başlatır ve ayarları yükler.

        Args:
            options (Dict[str, Any]): Kullanıcı tarafından ayarlanan seçenekler (LHOST, LPORT vb.).
        """
        self.options = options
        
        # Dinlenecek IP adresi (Local Host). Varsayılan: 0.0.0.0 (Tüm arayüzler)
        self.lhost = options.get("LHOST", "0.0.0.0")
        
        # Dinlenecek Port numarası (Local Port). Varsayılan: 4444
        self.lport = int(options.get("LPORT", 4444))
        
        # Sunucu soketi (dinleyici)
        self.sock = None
        
        # İstemci soketi (gelen bağlantı) — Geriye uyumluluk: son bağlanan istemciyi tutar
        self.client_sock = None
        
        # İstemci adresi (IP, Port) — Geriye uyumluluk: son bağlanan istemciyi tutar
        self.client_addr = None
        
        # Handler'ın çalışıp çalışmadığını kontrol eden bayrak
        self.running = False
        
        # --- Multi-client desteği ---
        # Tüm bağlı client'ları tutan sözlük.
        # Key: session_id (veya socket id), Value: {"sock": socket, "addr": (ip, port), "thread": Thread}
        self.clients: Dict[Any, Dict] = {}
        
        # clients sözlüğü için thread güvenliği kilidi
        self.clients_lock = threading.Lock()
        
        # Accept timeout süresi (saniye). 0 = sınırsız bekle.
        self.accept_timeout = float(options.get("ACCEPT_TIMEOUT", 0))

    def start(self):
        """
        Soketi oluşturur, bağlar (bind) ve dinlemeye (listen) başlar.
        Gelen bağlantıları kabul eder ve her birini kendi thread'inde çalıştırır.
        Tüm bağlantılar Session Manager'a kaydedilir.
        """
        try:
            # TCP/IPv4 soketi oluştur
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # "Address already in use" hatasını önlemek için soket ayarını yap.
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Soketi belirtilen IP ve Port'a bağla
            self.sock.bind((self.lhost, self.lport))
            
            # Bağlantıları dinlemeye başla (maksimum 5 bekleyen bağlantı kuyruğu)
            self.sock.listen(5)
            
            # Accept timeout ayarla (0 = sınırsız)
            if self.accept_timeout > 0:
                self.sock.settimeout(self.accept_timeout)
            
            self.running = True
            print(f"[*] Dinleniyor: {self.lhost}:{self.lport} (Çıkmak için CTRL+C)")
            
            # Ana döngü: Bağlantılar gelene kadar bekle (multi-client)
            while self.running:
                try:
                    # accept() bloklayıcıdır, bağlantı gelene kadar bekler.
                    client_sock, client_addr = self.sock.accept()
                    print(f"[+] Bağlantı geldi: {client_addr[0]}:{client_addr[1]}")
                    
                    # Geriye uyumluluk: son bağlanan istemciyi instance değişkenlerinde tut
                    self.client_sock = client_sock
                    self.client_addr = client_addr
                    
                    # Session Manager'a kaydet
                    from core.shared_state import shared_state
                    session_id = None
                    if shared_state.session_manager:
                        connection_info = {
                            "host": client_addr[0],
                            "port": client_addr[1],
                            "type": self.__class__.__name__
                        }
                        session_id = shared_state.session_manager.add_session(self, connection_info)
                        print(f"[*] Oturum açıldı: Session {session_id}")

                    # Her bağlantıyı kendi thread'inde çalıştır
                    client_thread = threading.Thread(
                        target=self._handle_client_thread,
                        args=(client_sock, client_addr, session_id),
                        daemon=True
                    )
                    
                    # Client'ı izleme sözlüğüne ekle
                    client_key = session_id if session_id is not None else id(client_sock)
                    with self.clients_lock:
                        self.clients[client_key] = {
                            "sock": client_sock,
                            "addr": client_addr,
                            "thread": client_thread
                        }
                    
                    client_thread.start()
                    
                except socket.timeout:
                    # Accept timeout'u doldu, döngüye devam et
                    continue
                except KeyboardInterrupt:
                    # Kullanıcı CTRL+C ile keserse hatayı yukarı fırlat
                    raise
                except Exception as e:
                    if self.running:
                        print(f"[!] Bağlantı kabul hatası: {e}")
                        
        except KeyboardInterrupt:
            print("\n[*] Dinleyici durduruluyor...")
        except Exception as e:
            print(f"[!] Hata: {e}")
        finally:
            # Her durumda temizlik yap ve kapat
            self.stop()

    def _handle_client_thread(self, client_sock: socket.socket, client_addr: tuple, session_id: int = None):
        """
        Bağlantı thread'i wrapper'ı. handle_connection'ı çağırır ve
        thread sonlandığında clients sözlüğünden temizlik yapar.
        
        Args:
            client_sock (socket.socket): Bağlanan istemcinin soket nesnesi.
            client_addr (tuple): İstemci adresi (IP, Port).
            session_id (int, optional): Atanan oturum ID'si.
        """
        try:
            self.handle_connection(client_sock, session_id)
        except Exception as e:
            print(f"[!] Bağlantı işleme hatası ({client_addr[0]}:{client_addr[1]}): {e}")
        finally:
            # Thread bittiğinde clients sözlüğünden kaldır
            client_key = session_id if session_id is not None else id(client_sock)
            with self.clients_lock:
                self.clients.pop(client_key, None)

    def stop(self):
        """
        Dinleyiciyi durdurur ve açık olan tüm soketleri güvenli bir şekilde kapatır.
        Multi-client modda tüm bağlı client soketlerini de kapatır.
        """
        self.running = False
        
        # Tüm client soketlerini kapat
        with self.clients_lock:
            for key, client_info in list(self.clients.items()):
                try:
                    client_info["sock"].close()
                except:
                    pass
            self.clients.clear()
        
        # Eski tek-istemci soketini de kapat (geriye uyumluluk)
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass
                
        # Sunucu (dinleyici) soketini kapat
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

    def handle_connection(self, client_sock: socket.socket, session_id: int = None):
        """
        Gelen bağlantıyı yönetecek soyut metod.
        Bu sınıf tek başına kullanılmaz, bir alt sınıf (örn: ShellHandler) tarafından
        bu metodun ezilmesi (override edilmesi) gerekir.
        
        Args:
            client_sock (socket.socket): Bağlanan istemcinin soket nesnesi.
            session_id (int, optional): Atanan oturum ID'si.
        """
        raise NotImplementedError("Alt sınıflar handle_connection metodunu uygulamalıdır.")

    def interact(self, session_id: int):
        """
        Oturumla etkileşime geçen (Interactive Shell) soyut metod.
        Kullanıcı 'sessions -i ID' dediğinde burası çalışır.
        Alt sınıflar bunu override ederek kendi kabuk (shell) mantığını uygulamalıdır.
        
        Args:
            session_id (int): Etkileşime girilecek oturum ID'si.
        """
        print(f"[*] {session_id} numaralı oturum interaktif modu desteklemiyor.")


class BindHandler(BaseHandler):
    """
    Bind TCP Handler.
    Hedef sistemdeki porta bağlanan handler tipi.
    Reverse shell yerine hedef üzerindeki dinleyen porta bağlanır.
    
    Kullanım:
        options = {"RHOST": "192.168.1.10", "RPORT": 4444}
        handler = BindHandler(options)
        handler.start()
    """
    
    def start(self):
        """
        Bind handler için özel start metodu.
        Dinlemek yerine, hedefe (RHOST:RPORT) bağlanır.
        """
        rhost = self.options.get("RHOST")
        rport = int(self.options.get("RPORT", self.lport))
        
        if not rhost:
            print("[!] RHOST belirtilmedi! Bind handler için RHOST gereklidir.")
            return
        
        # Bağlantı timeout'u (varsayılan: 30 saniye)
        connect_timeout = self.accept_timeout if self.accept_timeout > 0 else 30

        print(f"[*] Hedefe bağlanılıyor: {rhost}:{rport}...")
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(connect_timeout)
            self.sock.connect((rhost, rport))
            self.sock.settimeout(None)  # Bağlantı kurulduktan sonra timeout'u kaldır
            
            self.running = True
            self.client_sock = self.sock
            self.client_addr = (rhost, rport)
            print(f"[+] Bağlantı sağlandı: {rhost}:{rport}")
            
            # Session kaydı
            from core.shared_state import shared_state
            session_id = None
            if shared_state.session_manager:
                connection_info = {
                    "host": rhost,
                    "port": rport,
                    "type": "Bind"
                }
                session_id = shared_state.session_manager.add_session(self, connection_info)
                print(f"[*] Oturum açıldı: Session {session_id}")
            
            # Bağlantıyı işle
            self.handle_connection(self.sock, session_id)
            
        except socket.timeout:
            print(f"[!] Bağlantı zaman aşımı: {rhost}:{rport}")
        except ConnectionRefusedError:
            print(f"[!] Bağlantı reddedildi. Hedef port kapalı olabilir veya henüz açılmamış.")
        except Exception as e:
            print(f"[!] Bağlantı hatası: {e}")
        finally:
            self.stop()
