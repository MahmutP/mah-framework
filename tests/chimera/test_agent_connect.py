"""
Chimera Agent - Bağlantı Kurma Testleri (test_agent_connect.py)

Agent'ın bağlantı yönetimi fonksiyonlarını test eder:
  - connect() başarılı/başarısız senaryolar
  - reconnect() mantığı
  - close_socket() güvenli kapatma
  - SSL context oluşturma ve sertifika doğrulama

Çalıştırma:
    pytest tests/chimera/test_agent_connect.py -v
"""
import pytest
import socket
import ssl
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# connect() Testleri
# ============================================================

class TestAgentConnect:
    """Agent.connect() fonksiyonu testleri."""

    def test_connect_returns_false_on_unreachable_host(self, agent):
        """Erişilemez bir hedefe bağlanma girişimi False döner."""
        # Hiçbir şey dinlemediği için bağlantı başarısız olur
        result = agent.connect()
        assert result is False
        assert agent.sock is None

    def test_connect_creates_ssl_context(self, agent):
        """connect() çağrısı SSL context oluşturur."""
        with patch("ssl.create_default_context") as mock_ctx_factory:
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            result = agent.connect()

            # SSL context oluşturulmuş olmalı
            mock_ctx_factory.assert_called_once()
            # Hostname doğrulama kapalı olmalı (self-signed sertifika)
            assert mock_ctx.check_hostname is False
            assert mock_ctx.verify_mode == ssl.CERT_NONE

    def test_connect_wraps_socket_with_ssl(self, agent):
        """connect() ham socket'i SSL ile sarmalar."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket") as mock_socket:
            mock_raw = MagicMock()
            mock_socket.return_value = mock_raw

            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            agent.connect()

            # wrap_socket çağrılmış olmalı
            mock_ctx.wrap_socket.assert_called_once_with(
                mock_raw, server_hostname="127.0.0.1"
            )

    def test_connect_success_returns_true(self, agent):
        """Başarılı bağlantı True döner ve sock atanır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            result = agent.connect()

            assert result is True
            assert agent.sock is mock_wrapped

    def test_connect_sets_timeout_then_clears(self, agent):
        """connect() önce timeout koyar, bağlantı sonrası kaldırır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket") as mock_socket:
            mock_raw = MagicMock()
            mock_socket.return_value = mock_raw

            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            agent.connect()

            # Raw socket'e timeout atanmış olmalı
            mock_raw.settimeout.assert_called_with(30)
            # Bağlantı sonrası None (blocking) olmalı
            mock_wrapped.settimeout.assert_called_with(None)

    def test_connect_exception_sets_sock_none(self, agent):
        """connect() sırasında exception olursa sock None kalır."""
        with patch("ssl.create_default_context") as mock_ctx_factory:
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ssl.SSLError("handshake failed")

            result = agent.connect()

            assert result is False
            assert agent.sock is None


# ============================================================
# close_socket() Testleri
# ============================================================

class TestAgentCloseSocket:
    """Agent.close_socket() fonksiyonu testleri."""

    def test_close_socket_closes_and_nullifies(self, agent):
        """close_socket() kanalı kapatır ve sock None yapar."""
        mock_sock = MagicMock()
        agent.sock = mock_sock

        # ChannelManager üzerinden kapanmalı
        with patch.object(agent.channel_manager, 'close') as mock_close:
            agent.close_socket()
            mock_close.assert_called_once()
        assert agent.sock is None

    def test_close_socket_when_none(self, agent):
        """sock None iken close_socket hata vermez."""
        agent.sock = None
        agent.close_socket()  # Exception fırlatmamalı
        assert agent.sock is None

    def test_close_socket_handles_exception(self, agent):
        """close_socket() exception'ı yakalar ve yine de None yapar."""
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("already closed")
        agent.sock = mock_sock

        agent.close_socket()

        assert agent.sock is None

    def test_close_socket_called_multiple_times(self, agent):
        """close_socket() birden fazla çağrılabilir sorunsuzca."""
        mock_sock = MagicMock()
        agent.sock = mock_sock

        agent.close_socket()
        agent.close_socket()
        agent.close_socket()

        assert agent.sock is None


# ============================================================
# reconnect() Testleri
# ============================================================

class TestAgentReconnect:
    """Agent.reconnect() fonksiyonu testleri."""

    def test_reconnect_calls_close_first(self, agent):
        """reconnect() önce mevcut kanalı kapatır."""
        mock_sock = MagicMock()
        agent.sock = mock_sock
        # İlk connect denemesi başarılı olsun
        with patch.object(agent.channel_manager, 'close') as mock_ch_close, \
             patch.object(agent.channel_manager, 'fallback', return_value=False), \
             patch.object(agent, 'connect', return_value=True), \
             patch.object(agent, 'send_sysinfo'), \
             patch('time.sleep'):
            agent.reconnect()

        mock_ch_close.assert_called()
        
    def test_reconnect_returns_true_on_success(self, agent):
        """Başarılı reconnect True döner."""
        with patch.object(agent, "connect", return_value=True), \
             patch.object(agent, "send_sysinfo"), \
             patch("time.sleep"):
            result = agent.reconnect()

        assert result is True

    def test_reconnect_sends_sysinfo_on_success(self, agent):
        """Reconnect başarılı olunca sysinfo gönderilir."""
        with patch.object(agent, "connect", return_value=True) as _, \
             patch.object(agent, "send_sysinfo") as mock_sysinfo, \
             patch("time.sleep"):
            agent.reconnect()

        mock_sysinfo.assert_called_once()

    def test_reconnect_respects_running_flag(self, agent):
        """running=False ise reconnect döngüsü sonlanır."""
        agent.running = False
        with patch("time.sleep"):
            result = agent.reconnect()
        assert result is False

    def test_reconnect_retries_multiple_times(self, agent):
        """Bağlantı kurulamazsa birden fazla deneme yapılır."""
        call_count = 0

        def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return True
            return False

        with patch.object(agent, "connect", side_effect=mock_connect), \
             patch.object(agent, "send_sysinfo"), \
             patch("time.sleep"):
            result = agent.reconnect()

        assert result is True
        assert call_count == 3


# ============================================================
# SSL/TLS Handshake Testleri
# ============================================================

class TestSSLHandshake:
    """SSL/TLS handshake özel test senaryoları."""

    def test_self_signed_cert_accepted(self, agent):
        """Self-signed sertifikalar kabul edilir (CERT_NONE modu)."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            agent.connect()

            # verify_mode = CERT_NONE olmalı
            assert mock_ctx.verify_mode == ssl.CERT_NONE
            assert mock_ctx.check_hostname is False

    def test_ssl_error_returns_false(self, agent):
        """SSL hatası bağlantı başarısızlığına yol açar."""
        with patch("ssl.create_default_context") as mock_ctx_factory:
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ssl.SSLError("certificate verify failed")

            result = agent.connect()

            assert result is False
            assert agent.sock is None

    def test_connection_timeout_returns_false(self, agent):
        """Bağlantı timeout'u False döner."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.side_effect = socket.timeout("connection timed out")

            result = agent.connect()

            assert result is False
            assert agent.sock is None

    def test_connection_refused_returns_false(self, agent):
        """Bağlantı reddedilirse False döner."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.side_effect = ConnectionRefusedError("refused")

            result = agent.connect()

            assert result is False
