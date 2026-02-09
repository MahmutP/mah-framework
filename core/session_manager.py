from typing import Dict, Any, Optional
import threading

class SessionManager:
    """Oturum (Session) yönetim sınıfı.
    
    Aktif bağlantıları, shell oturumlarını ve payload etkileşimlerini yönetir.
    """
    def __init__(self):
        self.sessions: Dict[int, Any] = {}
        self.next_session_id = 1
        self.lock = threading.Lock()

    def add_session(self, handler_instance, connection_info: Dict[str, Any]) -> int:
        """Yeni bir oturum ekler."""
        with self.lock:
            session_id = self.next_session_id
            self.sessions[session_id] = {
                "id": session_id,
                "handler": handler_instance,
                "info": connection_info,
                "status": "Active",
                "type": connection_info.get("type", "Generic")
            }
            self.next_session_id += 1
            return session_id

    def remove_session(self, session_id: int):
        """Oturumu sonlandırır ve listeden siler."""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                # Handler'ın stop veya close metodunu çağırabiliriz
                try:
                    session["handler"].stop()
                except:
                    pass
                del self.sessions[session_id]

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """ID ile oturum bilgilerini döner."""
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> Dict[int, Any]:
        """Tüm oturumları döner."""
        return self.sessions
