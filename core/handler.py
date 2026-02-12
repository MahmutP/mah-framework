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
        
        # İstemci soketi (gelen bağlantı)
        self.client_sock = None
        
        # İstemci adresi (IP, Port)
        self.client_addr = None
        
        # Handler'ın çalışıp çalışmadığını kontrol eden bayrak
        self.running = False

    def start(self):
        """
        Soketi oluşturur, bağlar (bind) ve dinlemeye (listen) başlar.
        Gelen bağlantıları kabul eder ve oturum yöneticisine (SessionManager) kaydeder.
        """
        try:
            # TCP/IPv4 soketi oluştur
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # "Address already in use" hatasını önlemek için soket ayarını yap.
            # Bu, program kapatılıp hemen açıldığında portun tekrar kullanılabilmesini sağlar.
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Soketi belirtilen IP ve Port'a bağla
            self.sock.bind((self.lhost, self.lport))
            
            # Bağlantıları dinlemeye başla (maksimum 1 bekleyen bağlantı kuyruğu)
            self.sock.listen(1)
            
            self.running = True
            print(f"[*] Dinleniyor: {self.lhost}:{self.lport} (Çıkmak için CTRL+C)")
            
            # Ana döngü: Bağlantı bekle
            while self.running:
                try:
                    # accept() bloklayıcıdır, bağlantı gelene kadar bekler.
                    self.client_sock, self.client_addr = self.sock.accept()
                    print(f"[+] Bağlantı geldi: {self.client_addr[0]}:{self.client_addr[1]}")
                    
                    # Bağlantıyı Session Manager'a (Oturum Yöneticisi) kaydet
                    # Bu sayede bağlantılar merkezi bir yerden yönetilebilir, listelenebilir ve etkileşime girilebilir.
                    from core.shared_state import shared_state
                    session_id = None
                    if shared_state.session_manager:
                        connection_info = {
                            "host": self.client_addr[0],
                            "port": self.client_addr[1],
                            "type": "Generic" # Bağlantı türü (ileride Meterpreter, Shell vb. olabilir)
                        }
                        # Yeni oturum oluştur ve ID'sini al
                        session_id = shared_state.session_manager.add_session(self, connection_info)
                        print(f"[*] Oturum açıldı: Session {session_id}")

                    # Gelen bağlantıyı işlemesi için alt sınıfların implemente edeceği metodu çağır.
                    # Eğer BaseHandler direkt kullanılıyorsa bu metot hata fırlatabilir (NotImplementedError).
                    self.handle_connection(self.client_sock, session_id)
                    
                    # BaseHandler varsayılan olarak tek bir bağlantıyı kabul edip döngüden çıkar.
                    # MultiHandler gibi gelişmiş sınıflar bu davranışı değiştirebilir (break'i kaldırarak).
                    break 
                    
                except KeyboardInterrupt:
                    # Kullanıcı CTRL+C ile keserse hatayı yukarı fırlat (dışarıdaki catch yakalar)
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

    def stop(self):
        """
        Dinleyiciyi durdurur ve açık olan soketleri güvenli bir şekilde kapatır.
        """
        self.running = False
        
        # İstemci soketini kapat
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
