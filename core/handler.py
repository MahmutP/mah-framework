import socket
import threading
from typing import Optional

class BaseHandler:
    """Temel Handler Sınıfı.
    Tüm payload dinleyicileri (TCP, HTTP vb.) bu sınıftan türetilmelidir.
    """
    def __init__(self, lhost: str, lport: int):
        self.lhost = lhost
        self.lport = lport
        self.server_socket: Optional[socket.socket] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Dinleyiciyi başlatır."""
        raise NotImplementedError("Bu metot alt sınıflar tarafından doldurulmalıdır.")

    def stop(self):
        """Dinleyiciyi durdurur."""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print(f"[*] Handler durduruldu: {self.lhost}:{self.lport}")

    def handle_connection(self, client_sock, addr):
        """Gelen bağlantıyı işler."""
        raise NotImplementedError("Bu metot alt sınıflar tarafından doldurulmalıdır.")
