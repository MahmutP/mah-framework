"""
Chimera Test Suite - Ortak Fixtures ve Yardımcı Fonksiyonlar

Bu dosya tüm Chimera testleri tarafından paylaşılan pytest fixture'larını,
mock nesnelerini ve yardımcı fonksiyonları içerir.
"""
import pytest
import sys
import os
import types
from unittest.mock import MagicMock, patch

# Proje kökünü path'e ekle
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.shared_state import shared_state


# ============================================================
# Agent Yükleme Yardımcıları
# ============================================================

def _load_chimera_agent_class():
    """
    Chimera agent template dosyasını generate.py ile üretip
    ChimeraAgent sınıfını döndürür.
    """
    from modules.payloads.python.chimera.generate import Payload
    gen = Payload()
    gen.set_option_value("LHOST", "127.0.0.1")
    gen.set_option_value("LPORT", 9999)
    result = gen.generate(quiet=True)

    if isinstance(result, dict):
        code = result.get("code", "")
    else:
        code = result

    if not code:
        raise RuntimeError("Chimera agent kodu üretilemedi!")

    module = types.ModuleType("chimera_agent_test")
    exec(compile(code, "<chimera_agent>", "exec"), module.__dict__)
    sys.modules["chimera_agent_test"] = module  # Testlerin sınıfları bulabilmesi için
    return module.ChimeraAgent


# Agent sınıfını modül yüklenirken bir kez oluştur (performans)
try:
    ChimeraAgent = _load_chimera_agent_class()
except Exception as e:
    import warnings
    warnings.warn(f"ChimeraAgent yüklenemedi, agent testleri skip edilecek: {e}")
    ChimeraAgent = None


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_shared_state():
    """Her test öncesi shared state'i sıfırlar."""
    shared_state._initialize()
    yield


@pytest.fixture
def agent():
    """Temiz bir ChimeraAgent instance'ı döndürür."""
    if ChimeraAgent is None:
        pytest.skip("ChimeraAgent yüklenemedi")
    a = ChimeraAgent("127.0.0.1", 9999)
    yield a
    a.close_socket()


@pytest.fixture
def agent_with_mock_sock(agent):
    """Mock socket'e sahip bir agent döndürür."""
    mock_sock = MagicMock()
    agent.sock = mock_sock
    return agent, mock_sock


@pytest.fixture
def mock_socket_data():
    """HTTP Response formatında mock veri oluşturan yardımcı döndürür."""
    class MockSocketFromBuffer:
        """Buffer'dan okuyan mock socket."""
        def __init__(self, data: bytes):
            self.data = data
            self.pos = 0

        def recv(self, size):
            if self.pos >= len(self.data):
                return b""
            chunk = self.data[self.pos:self.pos + size]
            self.pos += len(chunk)
            return chunk

        def sendall(self, d):
            pass

        def settimeout(self, t):
            pass

        def close(self):
            pass

    def _create(body_text: str):
        body = body_text.encode("utf-8")
        headers = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n"
        )
        return MockSocketFromBuffer(headers + body)

    return _create


@pytest.fixture
def handler_options():
    """Handler başlatmak için varsayılan seçenekler."""
    return {"LHOST": "127.0.0.1", "LPORT": 4444}


@pytest.fixture
def chimera_handler(handler_options):
    """Mock SSL sertifikaları ile bir Handler instance'ı döndürür."""
    from modules.payloads.python.chimera.handler import Handler
    with patch("modules.payloads.python.chimera.handler.Handler.check_and_generate_cert"):
        h = Handler(handler_options)
    mock_session_manager = MagicMock()
    shared_state.session_manager = mock_session_manager
    return h


@pytest.fixture
def payload_generator():
    """Yapılandırılmış bir Payload generator instance'ı döndürür."""
    from modules.payloads.python.chimera.generate import Payload
    gen = Payload()
    gen.set_option_value("LHOST", "192.168.1.100")
    gen.set_option_value("LPORT", 4444)
    return gen


@pytest.fixture
def mock_socket_data():
    """HTTP response formatında veri dönen mock socket oluşturur.
    
    Kullanım:
        mock_sock = mock_socket_data("hello")
        # mock_sock.recv() çağrıları HTTP/1.1 200 OK + body döner
    """
    def _create(body_str: str):
        body_bytes = body_str.encode('utf-8')
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"\r\n"
        ).encode('utf-8') + body_bytes
        
        pos = [0]
        
        def mock_recv(n=1):
            if pos[0] >= len(response):
                return b""
            data = response[pos[0]:pos[0] + n]
            pos[0] += n
            return data
        
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = mock_recv
        mock_sock.getpeername.return_value = ("127.0.0.1", 4444)
        return mock_sock
    
    return _create
