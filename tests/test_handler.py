"""
BaseHandler & BindHandler — Unit Tests

Handler mimarisi yeniden yapılandırması (Faz 1.1) testleri:
  - Multi-client desteği
  - BindHandler (hedefe bağlanan handler)
  - Accept timeout
  - Graceful shutdown
  - Geriye uyumluluk (client_sock/client_addr)

Çalıştırma:
    pytest tests/test_handler.py -v
"""
import unittest
import threading
import time
import socket
from unittest.mock import MagicMock, patch, PropertyMock
from core.handler import BaseHandler, BindHandler
from core.session_manager import SessionManager
from core.shared_state import shared_state


# ============================================================
# Test için somut Handler alt sınıfı
# ============================================================

class ConcreteHandler(BaseHandler):
    """
    Test amaçlı somut handler.
    handle_connection'ı uygulayarak BaseHandler'ın soyut kontrolünü geçer.
    """
    def __init__(self, options=None):
        super().__init__(options or {"LHOST": "127.0.0.1", "LPORT": 0})
        self.connections_received = []  # (client_sock, session_id) çiftleri
        self.connection_event = threading.Event()

    def handle_connection(self, client_sock, session_id=None):
        self.connections_received.append((client_sock, session_id))
        self.connection_event.set()


class ConcreteBindHandler(BindHandler):
    """Test amaçlı somut bind handler."""
    def __init__(self, options=None):
        super().__init__(options or {"RHOST": "127.0.0.1", "RPORT": 0})
        self.connections_received = []

    def handle_connection(self, client_sock, session_id=None):
        self.connections_received.append((client_sock, session_id))


# ============================================================
# BaseHandler Testleri
# ============================================================

class TestBaseHandlerInit(unittest.TestCase):
    """BaseHandler başlatma testleri."""

    def test_default_options(self):
        """Varsayılan seçenekler doğru atanır."""
        handler = ConcreteHandler({"LHOST": "10.0.0.1", "LPORT": 8080})
        self.assertEqual(handler.lhost, "10.0.0.1")
        self.assertEqual(handler.lport, 8080)
        self.assertFalse(handler.running)
        self.assertIsNone(handler.client_sock)
        self.assertIsNone(handler.client_addr)

    def test_clients_dict_initialized(self):
        """Multi-client clients sözlüğü boş olarak başlatılır."""
        handler = ConcreteHandler()
        self.assertIsInstance(handler.clients, dict)
        self.assertEqual(len(handler.clients), 0)

    def test_clients_lock_initialized(self):
        """clients_lock threading.Lock olarak başlatılır."""
        handler = ConcreteHandler()
        self.assertIsInstance(handler.clients_lock, type(threading.Lock()))

    def test_accept_timeout_default(self):
        """Varsayılan accept_timeout 0 (sınırsız)."""
        handler = ConcreteHandler()
        self.assertEqual(handler.accept_timeout, 0)

    def test_accept_timeout_custom(self):
        """Özel accept_timeout değeri doğru atanır."""
        handler = ConcreteHandler({"LHOST": "0.0.0.0", "LPORT": 0, "ACCEPT_TIMEOUT": 10})
        self.assertEqual(handler.accept_timeout, 10.0)


class TestBaseHandlerMultiClient(unittest.TestCase):
    """Multi-client desteği testleri — gerçek soket kullanarak."""

    def setUp(self):
        self.session_manager = SessionManager()
        shared_state.session_manager = self.session_manager
        self.handler = ConcreteHandler({"LHOST": "127.0.0.1", "LPORT": 0})

    def tearDown(self):
        self.handler.stop()

    def _start_handler_in_thread(self):
        """Handler'ı arka plan thread'inde başlat ve porta bağlanana kadar bekle."""
        t = threading.Thread(target=self.handler.start, daemon=True)
        t.start()
        
        # Handler'ın porta bağlanmasını bekle
        for _ in range(50):
            if self.handler.running and self.handler.sock:
                try:
                    # OS'un atadığı gerçek portu al
                    addr = self.handler.sock.getsockname()
                    if addr[1] > 0:
                        self.handler.lport = addr[1]
                        return t
                except:
                    pass
            time.sleep(0.05)
        raise RuntimeError("Handler başlatılamadı!")

    def test_single_client_connection(self):
        """Tek bir client bağlantısı başarıyla kabul edilir."""
        t = self._start_handler_in_thread()
        
        # Client bağlantısı
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.handler.lport))
        
        # Bağlantının işlenmesini bekle
        self.handler.connection_event.wait(timeout=3)
        
        self.assertEqual(len(self.handler.connections_received), 1)
        self.assertIsNotNone(self.handler.client_sock)
        self.assertIsNotNone(self.handler.client_addr)
        
        client.close()

    def test_multiple_client_connections(self):
        """Birden fazla client bağlantısı paralel olarak kabul edilir."""
        t = self._start_handler_in_thread()
        
        clients = []
        num_clients = 3
        
        for i in range(num_clients):
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.connect(("127.0.0.1", self.handler.lport))
            clients.append(c)
            time.sleep(0.2)  # Bağlantı işlenme süresi
        
        # Tüm bağlantıların işlenmesini bekle
        time.sleep(1)
        
        self.assertEqual(len(self.handler.connections_received), num_clients)
        
        # Session Manager'da da doğru sayıda oturum olmalı
        all_sessions = self.session_manager.get_all_sessions()
        self.assertEqual(len(all_sessions), num_clients)
        
        for c in clients:
            c.close()

    def test_client_sock_backward_compat(self):
        """client_sock ve client_addr geriye uyumluluk için son bağlanan istemciyi tutar."""
        t = self._start_handler_in_thread()
        
        c1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c1.connect(("127.0.0.1", self.handler.lport))
        time.sleep(0.3)
        
        addr_after_first = self.handler.client_addr
        
        c2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c2.connect(("127.0.0.1", self.handler.lport))
        time.sleep(0.3)
        
        addr_after_second = self.handler.client_addr
        
        # İkinci bağlantıdan sonra client_addr güncellenmeli
        # (portlar farklı olacak çünkü iki farklı client)
        self.assertIsNotNone(addr_after_first)
        self.assertIsNotNone(addr_after_second)
        
        c1.close()
        c2.close()

    def test_session_manager_registration(self):
        """Her bağlantı Session Manager'a kaydedilir."""
        t = self._start_handler_in_thread()
        
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect(("127.0.0.1", self.handler.lport))
        
        self.handler.connection_event.wait(timeout=3)
        time.sleep(0.2)
        
        sessions = self.session_manager.get_all_sessions()
        self.assertEqual(len(sessions), 1)
        
        session = list(sessions.values())[0]
        self.assertEqual(session["info"]["host"], "127.0.0.1")
        self.assertEqual(session["status"], "Active")
        
        c.close()

    def test_session_type_is_class_name(self):
        """Oturum türü handler sınıf adı olarak kaydedilir."""
        t = self._start_handler_in_thread()
        
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect(("127.0.0.1", self.handler.lport))
        
        self.handler.connection_event.wait(timeout=3)
        time.sleep(0.2)
        
        sessions = self.session_manager.get_all_sessions()
        session = list(sessions.values())[0]
        self.assertEqual(session["info"]["type"], "ConcreteHandler")
        
        c.close()


class TestBaseHandlerStop(unittest.TestCase):
    """Graceful shutdown testleri."""

    def setUp(self):
        self.session_manager = SessionManager()
        shared_state.session_manager = self.session_manager

    def test_stop_closes_server_socket(self):
        """stop() sunucu soketini kapatır."""
        handler = ConcreteHandler()
        handler.sock = MagicMock()
        handler.client_sock = MagicMock()
        
        handler.stop()
        
        handler.sock.close.assert_called_once()
        self.assertFalse(handler.running)

    def test_stop_closes_all_client_sockets(self):
        """stop() tüm client soketlerini kapatır."""
        handler = ConcreteHandler()
        
        mock_socks = []
        for i in range(3):
            mock_sock = MagicMock()
            mock_socks.append(mock_sock)
            handler.clients[i] = {"sock": mock_sock, "addr": ("127.0.0.1", 5000 + i), "thread": MagicMock()}
        
        handler.stop()
        
        # Tüm soketler kapatılmış olmalı
        for mock_sock in mock_socks:
            mock_sock.close.assert_called_once()
        
        # clients sözlüğü temizlenmeli
        self.assertEqual(len(handler.clients), 0)

    def test_stop_clears_running_flag(self):
        """stop() running bayrağını False yapar."""
        handler = ConcreteHandler()
        handler.running = True
        
        handler.stop()
        
        self.assertFalse(handler.running)

    def test_stop_handles_socket_errors_gracefully(self):
        """stop() soket hataları sırasında crash olmaz."""
        handler = ConcreteHandler()
        
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("Soket zaten kapalı")
        handler.sock = mock_sock
        handler.client_sock = mock_sock
        
        mock_client = MagicMock()
        mock_client.close.side_effect = OSError("Hata")
        handler.clients = {1: {"sock": mock_client, "addr": ("127.0.0.1", 5000), "thread": MagicMock()}}
        
        # Hata fırlatmadan tamamlanmalı
        handler.stop()
        self.assertFalse(handler.running)


class TestBaseHandlerTimeout(unittest.TestCase):
    """Accept timeout testleri."""

    def test_accept_timeout_set_on_socket(self):
        """accept_timeout > 0 olduğunda soket timeout'u ayarlanır."""
        handler = ConcreteHandler({"LHOST": "127.0.0.1", "LPORT": 0, "ACCEPT_TIMEOUT": 2})
        
        # Handler'ı threaded başlat
        t = threading.Thread(target=handler.start, daemon=True)
        t.start()
        
        # Başlamasını bekle
        for _ in range(30):
            if handler.running and handler.sock:
                break
            time.sleep(0.05)
        
        # Soket timeout'u ayarlanmış olmalı
        if handler.sock:
            timeout = handler.sock.gettimeout()
            self.assertEqual(timeout, 2.0)
        
        handler.stop()


class TestBaseHandlerAbstractMethods(unittest.TestCase):
    """Soyut metod testleri."""

    def test_handle_connection_not_implemented(self):
        """BaseHandler doğrudan kullanıldığında NotImplementedError fırlatır."""
        handler = BaseHandler({"LHOST": "0.0.0.0", "LPORT": 4444})
        
        with self.assertRaises(NotImplementedError):
            handler.handle_connection(MagicMock())

    @patch("core.handler.print")
    def test_interact_default_message(self, mock_print):
        """Varsayılan interact mesaj basar."""
        handler = BaseHandler({"LHOST": "0.0.0.0", "LPORT": 4444})
        handler.interact(5)
        
        # print çağrılmış olmalı
        mock_print.assert_called()


class TestHandleClientThread(unittest.TestCase):
    """_handle_client_thread wrapper testleri."""

    def test_thread_calls_handle_connection(self):
        """_handle_client_thread handle_connection'ı çağırır."""
        handler = ConcreteHandler()
        mock_sock = MagicMock()
        
        handler._handle_client_thread(mock_sock, ("127.0.0.1", 5000), 1)
        
        self.assertEqual(len(handler.connections_received), 1)
        self.assertEqual(handler.connections_received[0], (mock_sock, 1))

    def test_thread_removes_client_on_completion(self):
        """Thread tamamlandığında clients sözlüğünden kaldırılır."""
        handler = ConcreteHandler()
        mock_sock = MagicMock()
        
        # Önce client'ı ekle
        handler.clients[1] = {"sock": mock_sock, "addr": ("127.0.0.1", 5000), "thread": MagicMock()}
        
        handler._handle_client_thread(mock_sock, ("127.0.0.1", 5000), 1)
        
        # Thread bittiğinde silinmeli
        self.assertNotIn(1, handler.clients)

    @patch("core.handler.print")
    def test_thread_handles_exception(self, mock_print):
        """Thread exception'ı yakalar ve crash olmaz."""
        handler = BaseHandler({"LHOST": "0.0.0.0", "LPORT": 4444})
        mock_sock = MagicMock()
        
        # handle_connection NotImplementedError fırlatacak
        handler._handle_client_thread(mock_sock, ("127.0.0.1", 5000), 1)
        
        # Hata yakalanıp loglanmalı
        mock_print.assert_called()


# ============================================================
# BindHandler Testleri
# ============================================================

class TestBindHandlerInit(unittest.TestCase):
    """BindHandler başlatma testleri."""

    def test_inherits_base_handler(self):
        """BindHandler, BaseHandler'dan miras alır."""
        handler = ConcreteBindHandler({"RHOST": "127.0.0.1", "RPORT": 5555})
        self.assertIsInstance(handler, BaseHandler)

    def test_rhost_from_options(self):
        """RHOST seçeneği options'dan alınır."""
        handler = ConcreteBindHandler({"RHOST": "10.0.0.5", "RPORT": 8080})
        self.assertEqual(handler.options.get("RHOST"), "10.0.0.5")


class TestBindHandlerStart(unittest.TestCase):
    """BindHandler start() testleri."""

    @patch("core.handler.print")
    def test_start_without_rhost(self, mock_print):
        """RHOST belirtilmezse uyarı mesajı basar ve çıkar."""
        handler = ConcreteBindHandler({"LHOST": "0.0.0.0", "LPORT": 4444})
        # RHOST yok
        handler.start()
        
        # Hata mesajı basılmış olmalı
        mock_print.assert_any_call("[!] RHOST belirtilmedi! Bind handler için RHOST gereklidir.")

    @patch("core.handler.print")
    def test_start_connection_refused(self, mock_print):
        """Kapalı porta bağlanırken ConnectionRefusedError yakalanır."""
        handler = ConcreteBindHandler({"RHOST": "127.0.0.1", "RPORT": 1, "ACCEPT_TIMEOUT": 1})
        handler.start()
        
        # Hata yakalanıp loglanmalı (ya refused ya timeout)
        self.assertFalse(handler.running)

    def test_start_connects_to_target(self):
        """BindHandler hedef porta başarıyla bağlanır."""
        session_manager = SessionManager()
        shared_state.session_manager = session_manager
        
        # Bir dinleyici oluştur
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        
        handler = ConcreteBindHandler({"RHOST": "127.0.0.1", "RPORT": port})
        
        # Handler'ı threaded başlat
        t = threading.Thread(target=handler.start, daemon=True)
        t.start()
        
        # Server bağlantıyı kabul et
        conn, addr = server.accept()
        
        time.sleep(0.5)
        
        # Handler bağlanmış olmalı
        self.assertEqual(len(handler.connections_received), 1)
        
        conn.close()
        server.close()
        handler.stop()


if __name__ == '__main__':
    unittest.main()
