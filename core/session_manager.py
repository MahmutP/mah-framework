# Framework'ün oturum (session) yönetiminden sorumlu modül.
# Bağlantı kurulan hedef sistemlerle (exploit sonrası) olan etkileşimleri merkezi olarak yönetir.

from typing import Dict, Any, Optional
import threading
import time

class SessionManager:
    """
    Oturum (Session) Yönetim Sınıfı.
    
    Bu sınıf, framework tarafından açılan tüm aktif bağlantıları izler.
    Reverse shell, bind shell veya diğer iletişim kanalları birer 'oturum' olarak burada saklanır.
    """
    
    def __init__(self):
        """
        SessionManager başlatıcı.
        """
        # Aktif oturumları tutan sözlük.
        # Key: Session ID (int), Value: Oturum bilgilerini içeren sözlük.
        self.sessions: Dict[int, Any] = {}
        
        # Bir sonraki oturuma verilecek ID numarası. 1'den başlar.
        self.next_session_id = 1
        
        # Thread güvenliği (Thread Safety) için kilit mekanizması.
        # Birden fazla handler aynı anda oturum eklemeye çalışırsa veri karışıklığını önler.
        self.lock = threading.Lock()

    def add_session(self, handler_instance, connection_info: Dict[str, Any]) -> int:
        """
        Yeni bir oturumu sisteme kaydeder.
        Bir handler (dinleyici) başarılı bir bağlantı aldığında bu metodu çağırır.

        Args:
            handler_instance: Bağlantıyı yöneten handler nesnesi (örn: ShellHandler).
            connection_info (Dict): Bağlantı detayları (IP, Port, Tür vb.).

        Returns:
            int: Yeni oluşturulan oturumun benzersiz ID'si.
        """
        # Kilidi al (başka thread'lerin araya girmesini engelle)
        with self.lock:
            session_id = self.next_session_id
            
            # Oturum bilgilerini sözlüğe kaydet
            self.sessions[session_id] = {
                "id": session_id,
                "handler": handler_instance, # Oturumu yöneten nesne (komut göndermek için kullanılır)
                "info": connection_info,     # Bağlantı bilgileri (gösterim için)
                "status": "Active",          # Oturum durumu
                "type": connection_info.get("type", "Generic"), # Oturum türü
                # Metadata
                "connected_at": time.time(),
                "last_active": time.time()
            }
            
            # Bir sonraki ID'yi hazırla
            self.next_session_id += 1
            
            return session_id

    def remove_session(self, session_id: int):
        """
        Belirtilen oturumu sonlandırır ve listeden siler.
        """
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                
                # Handler'ın bağlantıyı düzgün kapatması için stop() metodunu çağır.
                try:
                    session["handler"].stop()
                except:
                    pass # Zaten kapanmışsa hata verme
                
                # Listeden kaydı sil
                del self.sessions[session_id]

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        ID'si verilen oturumun bilgilerini döndürür.
        """
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> Dict[int, Any]:
        """
        Aktif tüm oturumları döndürür.
        'sessions' komutu tarafından listeleme yapmak için kullanılır.
        """
        return self.sessions

    def update_session_activity(self, session_id: int):
        """
        Belirtilen oturumun son aktivite zamanını günceller.
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["last_active"] = time.time()

    def shutdown_all(self):
        """
        Tüm aktif oturumları güvenli bir şekilde kapatır ve listeyi temizler.
        Framework kapanırken çağrılır.
        """
        with self.lock:
            # Iterasyon sırasında silme yapmamak için list() kullanılır
            for session_id, session in list(self.sessions.items()):
                try:
                    if hasattr(session["handler"], "stop"):
                        session["handler"].stop()
                except Exception:
                    pass
            self.sessions.clear()
