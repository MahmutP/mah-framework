"""
Chimera Multi-Handler - Unit Tests (Faz 1.2)
Checks if the Chimera Handler correctly integrates with the framework:
- Session management registration
- Protocol handling (send/recv)
- Compatibility with BaseHandler
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import struct

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import necessary modules
from modules.payloads.python.chimera.handler import Handler
from core.shared_state import shared_state

class TestChimeraHandler(unittest.TestCase):
    def setUp(self):
        self.options = {"LHOST": "127.0.0.1", "LPORT": 4444}
        self.handler = Handler(self.options)
        
        # Mock session manager
        self.mock_session_manager = MagicMock()
        shared_state.session_manager = self.mock_session_manager

    def test_handler_initialization(self):
        """Handler correctly initializes with options."""
        self.assertEqual(self.handler.lhost, "127.0.0.1")
        self.assertEqual(self.handler.lport, 4444)
        self.assertIsNone(self.handler.session_id)

    def test_send_data_protocol(self):
        """send_data uses length-prefixed format [4-byte][data]."""
        mock_sock = MagicMock()
        self.handler.client_sock = mock_sock
        
        test_msg = "test_command"
        self.handler.send_data(test_msg)
        
        # Expected format: Length (4 bytes) + Data (UTF-8)
        expected_len = struct.pack("!I", len(test_msg.encode("utf-8")))
        expected_payload = expected_len + test_msg.encode("utf-8")
        
        mock_sock.sendall.assert_called_with(expected_payload)

    @patch("builtins.print")  # Suppress print output during tests
    def test_recv_data_protocol(self, mock_print):
        """recv_data correctly parses length-prefixed data."""
        mock_sock = MagicMock()
        self.handler.client_sock = mock_sock
        
        test_response = "agent_response"
        encoded_resp = test_response.encode("utf-8")
        len_resp = struct.pack("!I", len(encoded_resp))
        
        # Mock socket behavior: first recv returns length, second returns data
        mock_sock.recv.side_effect = [len_resp, encoded_resp]
        
        result = self.handler.recv_data()
        self.assertEqual(result, test_response)

    @patch("builtins.print")
    def test_handle_connection_flow(self, mock_print):
        """handle_connection flow: recv sysinfo -> interactive session."""
        mock_sock = MagicMock()
        session_id = 101
        
        # Mock sysinfo response
        sysinfo_msg = "OS: Linux | User: root"
        encoded_sys = sysinfo_msg.encode("utf-8")
        len_sys = struct.pack("!I", len(encoded_sys))
        
        # Socket recv sequence: [len][sysinfo][interactive_session loop check...]
        # interactive_session enters a loop, so we mock input or exception to break it.
        # Here we'll patch `input` to raise KeyboardInterrupt immediately to exit the loop.
        mock_sock.recv.side_effect = [len_sys, encoded_sys, b"", b""] 
        
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            self.handler.handle_connection(mock_sock, session_id)
            
        # Verify session ID was stored
        self.assertEqual(self.handler.session_id, session_id)
        
        # Verify session manager was updated (optional logic in handler)
        # We check if get_session was called to add extra info
        self.mock_session_manager.get_session.assert_called_with(session_id)

if __name__ == "__main__":
    unittest.main()
