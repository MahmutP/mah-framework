"""
Chimera Agent - SSL/TLS Handshake Testleri (test_encryption.py)

SSL/TLS şifreleme altyapısını test eder:
  - SSL context yapılandırması
  - Sertifika doğrulama modları
  - TLS versiyonu uyumluluğu
  - Şifreleme çifti (cipher) kontrolü

Çalıştırma:
    pytest tests/chimera/test_encryption.py -v
"""
import pytest
import ssl
import socket
from unittest.mock import MagicMock, patch


# ============================================================
# SSL Context Oluşturma Testleri
# ============================================================

class TestSSLContextCreation:
    """SSL context yapılandırma testleri."""

    def test_creates_default_ssl_context(self, agent):
        """Agent, ssl.create_default_context() kullanır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            agent.connect()

            mock_ctx_factory.assert_called_once()

    def test_disables_hostname_check(self, agent):
        """Self-signed sertifika için hostname kontrolü kapatılır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            agent.connect()

            assert mock_ctx.check_hostname is False

    def test_sets_cert_none_mode(self, agent):
        """Sertifika doğrulama kapatılır (CERT_NONE)."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            agent.connect()

            assert mock_ctx.verify_mode == ssl.CERT_NONE

    def test_wraps_with_server_hostname(self, agent):
        """wrap_socket'e doğru server_hostname geçilir."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            agent.connect()

            call_kwargs = mock_ctx.wrap_socket.call_args
            assert call_kwargs[1].get("server_hostname") == "127.0.0.1" or \
                   (len(call_kwargs[0]) > 1 or call_kwargs[1].get("server_hostname") == agent.host)


# ============================================================
# SSL Hata Senaryoları
# ============================================================

class TestSSLErrorScenarios:
    """SSL/TLS hata durumu testleri."""

    def test_ssl_error_on_wrap(self, agent):
        """SSL wrap hatası graceful şekilde ele alınır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ssl.SSLError("SSL_ERROR_SYSCALL")

            result = agent.connect()

            assert result is False
            assert agent.sock is None

    def test_ssl_certificate_verify_failed(self, agent):
        """Sertifika doğrulama hatası bağlantıyı başarısız yapar."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ssl.SSLCertVerificationError(
                "certificate verify failed"
            )

            result = agent.connect()

            assert result is False

    def test_protocol_version_error(self, agent):
        """Protokol versiyonu uyuşmazlığı ele alınır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ssl.SSLError("WRONG_VERSION_NUMBER")

            result = agent.connect()

            assert result is False
            assert agent.sock is None

    def test_handshake_timeout(self, agent):
        """Handshake sırasında timeout ele alınır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.side_effect = socket.timeout("handshake timed out")

            result = agent.connect()

            assert result is False


# ============================================================
# Veri Şifreleme Doğrulama Testleri
# ============================================================

class TestDataEncryption:
    """Veri transferinin şifreli olduğunu doğrulayan testler."""

    def test_data_sent_over_ssl_socket(self, agent):
        """Veri SSL socket üzerinden gönderilir (düz socket değil)."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            agent.connect()

            # Agent'ın sock'u, SSL sarmalanmış socket olmalı
            assert agent.sock is mock_wrapped

            # Veri gönder
            agent.send_data("secret data")

            # sendall, mock_wrapped (SSL socket) üzerinde çağrılmalı
            mock_wrapped.sendall.assert_called_once()

    def test_raw_socket_not_used_after_connect(self, agent):
        """Bağlantı sonrası raw socket değil, SSL socket kullanılır."""
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket") as mock_socket_cls:
            mock_raw = MagicMock()
            mock_socket_cls.return_value = mock_raw

            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped
            mock_wrapped.connect.return_value = None

            agent.connect()
            agent.send_data("test")

            # Sadece wrapped (SSL) socket kullanılmalı, raw socket değil
            mock_raw.sendall.assert_not_called()
            mock_wrapped.sendall.assert_called_once()
