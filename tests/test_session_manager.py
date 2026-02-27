import unittest
import threading
import time
from unittest.mock import MagicMock
from core.session_manager import SessionManager
from core.shared_state import shared_state

class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.session_manager = SessionManager()
        shared_state.session_manager = self.session_manager

    def test_add_session(self):
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        
        session_id = self.session_manager.add_session(mock_handler, info)
        
        self.assertEqual(session_id, 1)
        self.assertIn(1, self.session_manager.sessions)
        self.assertEqual(self.session_manager.sessions[1]["info"]["host"], "127.0.0.1")

    def test_remove_session(self):
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        session_id = self.session_manager.add_session(mock_handler, info)
        
        self.session_manager.remove_session(session_id)
        
        self.assertNotIn(session_id, self.session_manager.sessions)
        mock_handler.stop.assert_called_once()

    def test_get_session(self):
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        session_id = self.session_manager.add_session(mock_handler, info)
        
        session = self.session_manager.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["id"], session_id)

    def test_thread_safety(self):
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        
        def add_sessions():
            for _ in range(100):
                self.session_manager.add_session(mock_handler, info)
                
        threads = []
        for _ in range(5):
            t = threading.Thread(target=add_sessions)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertEqual(len(self.session_manager.sessions), 500)

    def test_add_session_metadata(self):
        """Metadata'nın (connected_at, last_active) eklendiğini doğrula."""
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        
        session_id = self.session_manager.add_session(mock_handler, info)
        session = self.session_manager.get_session(session_id)
        
        self.assertIn("connected_at", session)
        self.assertIn("last_active", session)
        self.assertGreater(session["connected_at"], 0)
        self.assertEqual(session["connected_at"], session["last_active"])

    def test_update_session_activity(self):
        """Son aktivite zamanının güncellendiğini doğrula."""
        mock_handler = MagicMock()
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        
        session_id = self.session_manager.add_session(mock_handler, info)
        session = self.session_manager.get_session(session_id)
        initial_time = session["last_active"]
        
        # Zamanın değişmesi için ufak bi bekleme
        time.sleep(0.01)
        self.session_manager.update_session_activity(session_id)
        
        updated_session = self.session_manager.get_session(session_id)
        self.assertGreater(updated_session["last_active"], initial_time)

    def test_shutdown_all(self):
        """Tüm oturumların kapatıldığını ve listenin temizlendiğini doğrula."""
        mock_handlers = [MagicMock(), MagicMock(), MagicMock()]
        info = {"host": "127.0.0.1", "port": 4444, "type": "Test"}
        
        for handler in mock_handlers:
            self.session_manager.add_session(handler, info)
            
        self.assertEqual(len(self.session_manager.sessions), 3)
        
        self.session_manager.shutdown_all()
        
        # Tüm handler'ların stop() fonksiyonu çağrılmış olmalı
        for handler in mock_handlers:
            handler.stop.assert_called_once()
            
        # Session listesi boş olmalı
        self.assertEqual(len(self.session_manager.sessions), 0)

if __name__ == '__main__':
    unittest.main()
