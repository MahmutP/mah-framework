"""
Chimera Multi-Handler - Unit Tests
Checks if the Chimera Handler correctly integrates with the framework:
- Session management registration
- Protocol handling (send/recv)
- Compatibility with BaseHandler
"""
import unittest
from unittest.mock import MagicMock, patch, call
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
        # Disable SSL cert generation for tests
        with patch("modules.payloads.python.chimera.handler.Handler.check_and_generate_cert"):
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
        """send_data uses HTTP Response format (Obfuscation)."""
        mock_sock = MagicMock()
        self.handler.client_sock = mock_sock
        
        test_msg = "test_command"
        self.handler.send_data(test_msg)
        
        # Verify call contains key parts
        args, _ = mock_sock.sendall.call_args
        sent_data = args[0]
        
        self.assertIn(b"HTTP/1.1 200 OK", sent_data)
        self.assertIn(b"Content-Length: " + str(len(test_msg)).encode(), sent_data)
        self.assertIn(test_msg.encode("utf-8"), sent_data)

    @patch("builtins.print")  # Suppress print output during tests
    def test_recv_data_protocol(self, mock_print):
        """recv_data correctly parses HTTP Request body."""
        mock_sock = MagicMock()
        self.handler.client_sock = mock_sock
        
        test_response = "agent_response"
        encoded_resp = test_response.encode("utf-8")
        
        # HTTP Request Simulation
        http_header = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: " + str(len(encoded_resp)).encode() + b"\r\n"
            b"\r\n"
        )
        
        # Mock socket behaviors:
        # First call to recv(1) returns the whole header (Mock ignores bufsize)
        # Second call to recv(content_length) returns the body
        mock_sock.recv.side_effect = [http_header, encoded_resp]
        
        result = self.handler.recv_data()
        self.assertEqual(result, test_response)

    @patch("ssl.SSLContext")
    @patch("builtins.print")
    def test_handle_connection_flow(self, mock_print, mock_ssl_context):
        """handle_connection flow: SSL handshake -> recv sysinfo -> interactive session."""
        mock_client_sock = MagicMock()
        session_id = 101
        
        # SSL Wrappings
        mock_ssl_instance = mock_ssl_context.return_value
        mock_wrapped_sock = MagicMock()
        mock_ssl_instance.wrap_socket.return_value = mock_wrapped_sock
        mock_wrapped_sock.cipher.return_value = ('AES256-GCM', 256, 'TLSv1.3')
        
        # Mock sysinfo response (HTTP format)
        sysinfo_msg = "OS: Linux | User: root"
        encoded_sys = sysinfo_msg.encode("utf-8")
        
        http_header = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Content-Length: " + str(len(encoded_sys)).encode() + b"\r\n"
            b"\r\n"
        )
        
        # Socket recv sequence for the wrapped socket:
        # 1. Header (for sysinfo)
        # 2. Body (sysinfo)
        # 3. Header (for next interactive check - empty to break loop or input wait)
        mock_wrapped_sock.recv.side_effect = [http_header, encoded_sys, b"", b""]
        
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            self.handler.handle_connection(mock_client_sock, session_id)
            
        # Verify session ID was stored
        self.assertEqual(self.handler.session_id, session_id)
        
        # Verify SSL wrapping happened
        mock_ssl_instance.wrap_socket.assert_called_with(mock_client_sock, server_side=True)
        
        # Verify session manager was updated (get_session called to add extra info)
        self.mock_session_manager.get_session.assert_called_with(session_id)

if __name__ == "__main__":
    unittest.main()
