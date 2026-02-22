"""
Chimera - Çoklu Oturum Yönetimi Testleri (test_multi_session.py)

Handler'ın birden fazla agent bağlantısını yönetme yeteneğini test eder:
  - Session ID yönetimi
  - Handler başlatma ve yapılandırma
  - Protokol uyumluluğu (send/recv)
  - Session Manager entegrasyonu

Çalıştırma:
    pytest tests/chimera/test_multi_session.py -v
"""
import pytest
import ssl
from unittest.mock import MagicMock, patch, call

from core.shared_state import shared_state


# ============================================================
# Handler Başlatma Testleri
# ============================================================

class TestHandlerInitialization:
    """Handler başlatma ve yapılandırma testleri."""

    def test_handler_stores_options(self, chimera_handler):
        """Handler options değerlerini doğru saklar."""
        assert chimera_handler.lhost == "127.0.0.1"
        assert chimera_handler.lport == 4444

    def test_handler_initial_session_none(self, chimera_handler):
        """Handler başlangıçta session_id None olmalı."""
        assert chimera_handler.session_id is None

    def test_handler_inherits_base_handler(self, chimera_handler):
        """Handler, BaseHandler'dan miras alır."""
        from core.handler import BaseHandler
        assert isinstance(chimera_handler, BaseHandler)


# ============================================================
# Handler Protokol Testleri
# ============================================================

class TestHandlerProtocol:
    """Handler send_data / recv_data protokol testleri."""

    def test_send_data_http_response_format(self, chimera_handler):
        """Handler.send_data HTTP Response formatında gönderir."""
        mock_sock = MagicMock()
        chimera_handler.client_sock = mock_sock

        test_msg = "handler_command"
        chimera_handler.send_data(test_msg)

        args, _ = mock_sock.sendall.call_args
        sent_data = args[0]

        assert b"HTTP/1.1 200 OK" in sent_data
        assert f"Content-Length: {len(test_msg)}".encode() in sent_data
        assert test_msg.encode("utf-8") in sent_data

    def test_send_data_includes_server_header(self, chimera_handler):
        """Handler response'u sunucu header'ları içerir."""
        mock_sock = MagicMock()
        chimera_handler.client_sock = mock_sock

        chimera_handler.send_data("test")

        sent = mock_sock.sendall.call_args[0][0]
        # HTTP Response formatında olmalı
        assert b"HTTP/1.1 200 OK" in sent

    @patch("builtins.print")
    def test_recv_data_parses_http_request(self, mock_print, chimera_handler):
        """Handler.recv_data HTTP Request body'sini doğru parse eder."""
        mock_sock = MagicMock()
        chimera_handler.client_sock = mock_sock

        test_response = "agent_sysinfo_data"
        encoded_resp = test_response.encode("utf-8")

        http_request = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Length: " + str(len(encoded_resp)).encode() + b"\r\n"
            b"\r\n"
        )

        mock_sock.recv.side_effect = [http_request, encoded_resp]

        result = chimera_handler.recv_data()
        assert result == test_response


# ============================================================
# Session Yönetimi Testleri
# ============================================================

class TestSessionManagement:
    """Oturum yönetimi entegrasyon testleri."""

    @patch("ssl.SSLContext")
    @patch("builtins.print")
    def test_handle_connection_assigns_session_id(self, mock_print, mock_ssl_ctx, chimera_handler):
        """handle_connection session_id'yi doğru atar."""
        mock_client = MagicMock()
        session_id = 42

        # SSL setup
        mock_ssl_instance = mock_ssl_ctx.return_value
        mock_wrapped = MagicMock()
        mock_ssl_instance.wrap_socket.return_value = mock_wrapped
        mock_wrapped.cipher.return_value = ('AES256-GCM', 256, 'TLSv1.3')

        # Sysinfo mock
        sysinfo = "OS: Darwin | User: test"
        encoded_sys = sysinfo.encode("utf-8")
        http_header = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Content-Length: " + str(len(encoded_sys)).encode() + b"\r\n"
            b"\r\n"
        )
        mock_wrapped.recv.side_effect = [http_header, encoded_sys, b"", b""]

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            chimera_handler.handle_connection(mock_client, session_id)

        assert chimera_handler.session_id == session_id

    @patch("ssl.SSLContext")
    @patch("builtins.print")
    def test_handle_connection_performs_ssl_wrap(self, mock_print, mock_ssl_ctx, chimera_handler):
        """handle_connection SSL sarmalaması yapar."""
        mock_client = MagicMock()

        mock_ssl_instance = mock_ssl_ctx.return_value
        mock_wrapped = MagicMock()
        mock_ssl_instance.wrap_socket.return_value = mock_wrapped
        mock_wrapped.cipher.return_value = ('AES256-GCM', 256, 'TLSv1.3')

        sysinfo = "OS: Linux | User: root"
        encoded_sys = sysinfo.encode("utf-8")
        http_header = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Content-Length: " + str(len(encoded_sys)).encode() + b"\r\n"
            b"\r\n"
        )
        mock_wrapped.recv.side_effect = [http_header, encoded_sys, b"", b""]

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            chimera_handler.handle_connection(mock_client, 1)

        mock_ssl_instance.wrap_socket.assert_called_with(mock_client, server_side=True)

    @patch("ssl.SSLContext")
    @patch("builtins.print")
    def test_handle_connection_updates_session_info(self, mock_print, mock_ssl_ctx, chimera_handler):
        """handle_connection session manager'daki oturum bilgisini günceller."""
        mock_client = MagicMock()
        session_id = 99

        mock_ssl_instance = mock_ssl_ctx.return_value
        mock_wrapped = MagicMock()
        mock_ssl_instance.wrap_socket.return_value = mock_wrapped
        mock_wrapped.cipher.return_value = ('AES256-GCM', 256, 'TLSv1.3')

        sysinfo = "OS: Windows 10 | User: admin"
        encoded_sys = sysinfo.encode("utf-8")
        http_header = (
            b"POST /api/v1/sync HTTP/1.1\r\n"
            b"Content-Length: " + str(len(encoded_sys)).encode() + b"\r\n"
            b"\r\n"
        )
        mock_wrapped.recv.side_effect = [http_header, encoded_sys, b"", b""]

        mock_sm = MagicMock()
        shared_state.session_manager = mock_sm

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            chimera_handler.handle_connection(mock_client, session_id)

        # Session manager'dan get_session çağrılmış olmalı
        mock_sm.get_session.assert_called_with(session_id)


# ============================================================
# Çoklu Agent Simülasyonu
# ============================================================

class TestMultipleAgents:
    """Birden fazla agent instance'ının bağımsız çalışması."""

    def test_agents_have_independent_state(self, agent):
        """Farklı agent instance'ları bağımsız duruma sahiptir."""
        from tests.chimera.conftest import ChimeraAgent

        if ChimeraAgent is None:
            pytest.skip("ChimeraAgent yüklenemedi")

        agent1 = ChimeraAgent("10.0.0.1", 4444)
        agent2 = ChimeraAgent("10.0.0.2", 5555)

        agent1.running = False

        # Agent1 durması agent2'yi etkilememeli
        assert agent2.running is True
        assert agent1.host != agent2.host
        assert agent1.port != agent2.port

        agent1.close_socket()
        agent2.close_socket()

    def test_agents_have_separate_modules(self, agent):
        """Her agent'ın kendi modül listesi var."""
        from tests.chimera.conftest import ChimeraAgent

        if ChimeraAgent is None:
            pytest.skip("ChimeraAgent yüklenemedi")

        agent1 = ChimeraAgent("10.0.0.1", 4444)
        agent2 = ChimeraAgent("10.0.0.2", 5555)

        agent1.loaded_modules["test_mod"] = "dummy"

        assert "test_mod" not in agent2.loaded_modules

        agent1.close_socket()
        agent2.close_socket()
