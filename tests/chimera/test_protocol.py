"""
Chimera Agent - HTTP Protokol Parser Testleri (test_protocol.py)

Agent'ın HTTP over TLS veri gönderme/alma protokolünü test eder:
  - send_data() HTTP POST formatı doğrulama
  - recv_data() HTTP Response parsing
  - Header doğrulamaları (Content-Length, Host, User-Agent)
  - Edge case'ler (boş veri, büyük payload, encoding)

Çalıştırma:
    pytest tests/chimera/test_protocol.py -v
"""
import pytest
from unittest.mock import MagicMock


# ============================================================
# send_data() Testleri
# ============================================================

class TestSendData:
    """Agent.send_data() HTTP POST protokol testleri."""

    def test_send_data_http_post_format(self, agent_with_mock_sock):
        """send_data, HTTP POST formatında gönderir."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("merhaba")

        mock_sock.sendall.assert_called_once()
        sent = mock_sock.sendall.call_args[0][0]

        # HTTP metod ve yol
        assert b"POST /api/v1/sync HTTP/1.1" in sent

    def test_send_data_includes_host_header(self, agent_with_mock_sock):
        """send_data Host header'ı içerir."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("test")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Host: 127.0.0.1" in sent

    def test_send_data_includes_user_agent(self, agent_with_mock_sock):
        """send_data gerçekçi User-Agent header'ı içerir."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("test")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"User-Agent: Mozilla/5.0" in sent
        assert b"Chrome/" in sent

    def test_send_data_correct_content_length(self, agent_with_mock_sock):
        """Content-Length header'ı body boyutuyla eşleşir."""
        agent, mock_sock = agent_with_mock_sock

        test_msg = "chimera_test_payload"
        agent.send_data(test_msg)

        sent = mock_sock.sendall.call_args[0][0]
        expected_len = len(test_msg.encode("utf-8"))
        assert f"Content-Length: {expected_len}".encode() in sent

    def test_send_data_content_type_formencoded(self, agent_with_mock_sock):
        """Content-Type: application/x-www-form-urlencoded olmalı."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("test")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Content-Type: application/x-www-form-urlencoded" in sent

    def test_send_data_connection_keep_alive(self, agent_with_mock_sock):
        """Connection: keep-alive header'ı olmalı."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("test")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Connection: keep-alive" in sent

    def test_send_data_body_after_double_crlf(self, agent_with_mock_sock):
        """Body, \\r\\n\\r\\n sonrasında gelmelidir."""
        agent, mock_sock = agent_with_mock_sock

        test_msg = "payload_body_content"
        agent.send_data(test_msg)

        sent = mock_sock.sendall.call_args[0][0]
        # Header-body ayrımı
        parts = sent.split(b"\r\n\r\n")
        assert len(parts) == 2
        assert parts[1] == test_msg.encode("utf-8")

    def test_send_data_empty_string(self, agent_with_mock_sock):
        """Boş string gönderme Content-Length: 0 olmalı."""
        agent, mock_sock = agent_with_mock_sock

        agent.send_data("")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Content-Length: 0" in sent

    def test_send_data_unicode_content(self, agent_with_mock_sock):
        """Türkçe karakterler UTF-8 olarak gönderilir."""
        agent, mock_sock = agent_with_mock_sock

        test_msg = "Merhaba Dünya! Çalışıyor μ"
        agent.send_data(test_msg)

        sent = mock_sock.sendall.call_args[0][0]
        encoded_body = test_msg.encode("utf-8")
        assert f"Content-Length: {len(encoded_body)}".encode() in sent
        assert sent.endswith(encoded_body)

    def test_send_data_no_socket_silent(self, agent):
        """Socket None iken send_data exception fırlatmaz."""
        agent.sock = None
        # Exception fırlatmamalı
        agent.send_data("test")

    def test_send_data_large_payload(self, agent_with_mock_sock):
        """Büyük payload doğru Content-Length ile gönderilir."""
        agent, mock_sock = agent_with_mock_sock

        large_msg = "A" * 100_000
        agent.send_data(large_msg)

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Content-Length: 100000" in sent


# ============================================================
# recv_data() Testleri
# ============================================================

class TestRecvData:
    """Agent.recv_data() HTTP Response parsing testleri."""

    def test_recv_data_parses_body_correctly(self, agent, mock_socket_data):
        """recv_data HTTP Response body'sini doğru parse eder."""
        test_msg = "chimera response test"
        agent.sock = mock_socket_data(test_msg)

        result = agent.recv_data()

        assert result == test_msg

    def test_recv_data_empty_on_disconnect(self, agent):
        """Bağlantı koparsa recv_data boş string döner."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b""
        agent.sock = mock_sock

        result = agent.recv_data()

        assert result == ""

    def test_recv_data_no_socket_returns_empty(self, agent):
        """Socket None iken recv_data boş string döner."""
        agent.sock = None

        result = agent.recv_data()

        assert result == ""

    def test_recv_data_unicode_body(self, agent, mock_socket_data):
        """UTF-8 encoded Türkçe metin doğru okunur."""
        test_msg = "Türkçe karakter testi: ğüşiöç"
        agent.sock = mock_socket_data(test_msg)

        result = agent.recv_data()

        assert result == test_msg

    def test_recv_data_multiline_body(self, agent, mock_socket_data):
        """Çok satırlı body doğru parse edilir."""
        test_msg = "satır1\nsatır2\nsatır3"
        agent.sock = mock_socket_data(test_msg)

        result = agent.recv_data()

        assert result == test_msg

    def test_recv_data_json_like_body(self, agent, mock_socket_data):
        """JSON benzeri body bozulmadan okunur."""
        test_msg = '{"status": "ok", "data": [1, 2, 3]}'
        agent.sock = mock_socket_data(test_msg)

        result = agent.recv_data()

        assert result == test_msg

    def test_recv_data_exception_returns_empty(self, agent):
        """recv sırasında exception boş string döner."""
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = ConnectionResetError("peer reset")
        agent.sock = mock_sock

        result = agent.recv_data()

        assert result == ""

    def test_recv_data_content_length_zero(self, agent):
        """Content-Length: 0 durumu boş body döner."""
        class ZeroLengthSocket:
            def __init__(self):
                self.data = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                self.pos = 0

            def recv(self, size):
                if self.pos >= len(self.data):
                    return b""
                chunk = self.data[self.pos:self.pos + size]
                self.pos += len(chunk)
                return chunk

        agent.sock = ZeroLengthSocket()

        result = agent.recv_data()

        assert result == ""


# ============================================================
# Protokol Uyumluluk Testleri
# ============================================================

class TestProtocolCompatibility:
    """Agent-Handler protokol uyumluluk testleri."""

    def test_send_recv_roundtrip_format(self, agent):
        """send_data'nın gönderdiği format, Handler'ın recv_data'sıyla uyumlu."""
        mock_sock = MagicMock()
        agent.sock = mock_sock

        test_msg = "roundtrip test message"
        agent.send_data(test_msg)

        # Gönderilen veriyi al
        sent = mock_sock.sendall.call_args[0][0]

        # POST request formatı doğrulama
        assert sent.startswith(b"POST /api/v1/sync HTTP/1.1\r\n")

        # Header ve body ayrımı
        header_end = sent.find(b"\r\n\r\n")
        assert header_end > 0

        body = sent[header_end + 4:]
        assert body.decode("utf-8") == test_msg

    def test_http_traffic_obfuscation(self, agent):
        """Trafik normal HTTP isteğine benziyor olmalı."""
        mock_sock = MagicMock()
        agent.sock = mock_sock

        agent.send_data("command output")

        sent = mock_sock.sendall.call_args[0][0]

        # Normal web trafiğine benzeme kontrolleri
        assert b"HTTP/1.1" in sent
        assert b"Mozilla/5.0" in sent
        assert b"Content-Type:" in sent
        assert b"Connection: keep-alive" in sent
