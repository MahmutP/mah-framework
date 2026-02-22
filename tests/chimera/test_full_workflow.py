"""
Chimera - End-to-End Workflow Testi (test_full_workflow.py)

Tam bir agent-handler çalışma döngüsünü simüle eder:
  1. Payload üretimi (generate)
  2. Agent sınıfı yükleme
  3. Bağlantı kurulumu (mock)
  4. Sysinfo gönderimi
  5. Komut alımı → çalıştırma → sonuç gönderme
  6. Terminate ile temiz çıkış

Çalıştırma:
    pytest tests/chimera/test_full_workflow.py -v
"""
import pytest
import types
from unittest.mock import MagicMock, patch


# ============================================================
# Payload Üretim Workflow Testleri
# ============================================================

class TestPayloadGeneration:
    """Payload üretim pipeline'ının end-to-end testi."""

    def test_generate_replaces_placeholders(self, payload_generator):
        """generate() LHOST/LPORT placeholder'larını doğru değiştirir."""
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        assert 'LHOST = "192.168.1.100"' in code
        assert "LPORT = 4444" in code
        assert "{{LHOST}}" not in code
        assert "{{LPORT}}" not in code

    def test_generate_produces_valid_python(self, payload_generator):
        """Üretilen payload geçerli Python kodu olmalı."""
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        # compile() ile syntax kontrolü
        try:
            compile(code, "<chimera_payload>", "exec")
            syntax_valid = True
        except SyntaxError as e:
            syntax_valid = False
            pytest.fail(f"Üretilen payload geçersiz Python syntax: {e}")

        assert syntax_valid

    def test_generate_only_stdlib_imports(self, payload_generator):
        """Üretilen payload'ın üst seviye importları stdlib olmalı.
        
        Not: Agent, try/except blokları içinde opsiyonel third-party
        modüller (mss gibi) import edebilir — bunlar kontrol edilmez.
        """
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        # Python stdlib modülleri (agent'ın kullandığı tümü)
        allowed_imports = {
            "socket", "subprocess", "os", "sys", "platform",
            "struct", "time", "ssl", "random", "string",
            "threading", "base64", "ctypes", "re", "types",
            "hashlib", "hmac", "select", "signal", "shutil",
            "multiprocessing", "json", "tempfile", "io",
            "collections", "functools", "itertools", "copy",
            "pathlib", "glob", "fnmatch", "errno", "stat",
            "abc", "gc", "weakref", "textwrap", "inspect",
            "traceback", "logging", "contextlib",
        }

        # Sadece top-level import'ları kontrol et (try blokları içindekileri atla)
        in_try_block = False
        indent_level = 0
        
        for line in code.split("\n"):
            stripped = line.strip()
            leading_spaces = len(line) - len(line.lstrip())
            
            # try bloğu takibi
            if stripped.startswith("try:"):
                in_try_block = True
                indent_level = leading_spaces
                continue
            
            if in_try_block:
                if stripped.startswith("except") or stripped.startswith("finally"):
                    continue
                if leading_spaces <= indent_level and stripped and not stripped.startswith("#"):
                    in_try_block = False
                else:
                    continue  # try/except içindeki importları atla
            
            if stripped.startswith("import ") or stripped.startswith("from "):
                module_name = stripped.replace("import ", "").replace("from ", "").split(".")[0].split(" ")[0]
                assert module_name in allowed_imports, \
                    f"Standart olmayan import tespit edildi: {stripped}"

    def test_generate_contains_chimera_agent_class(self, payload_generator):
        """Üretilen payload ChimeraAgent sınıfını içerir."""
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        assert "class ChimeraAgent" in code

    def test_generate_contains_entry_point(self, payload_generator):
        """Üretilen payload'da __main__ giriş noktası var."""
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        assert '__name__' in code or '__main__' in code

    def test_generate_result_dict_format(self, payload_generator):
        """generate() doğru formatta dict döner."""
        result = payload_generator.generate(quiet=True)

        if isinstance(result, dict):
            assert "success" in result
            assert "code" in result
            assert "stats" in result


# ============================================================
# Agent Run Döngüsü Testleri
# ============================================================

class TestAgentRunLoop:
    """Agent.run() tam döngü simülasyonu."""

    def test_run_connect_sysinfo_terminate(self, agent, mock_socket_data):
        """run(): Connect → Sysinfo → Komut Al → Terminate."""
        # Mock: connect başarılı
        with patch.object(agent, "connect", return_value=True):
            # Sysinfo gönderimi mock
            with patch.object(agent, "send_sysinfo"):
                # İlk recv: "terminate" komutu
                agent.sock = mock_socket_data("terminate")

                # send_data mock (output gönderimi)
                with patch.object(agent, "send_data"):
                    agent.run()

        # Agent durdurulmuş olmalı
        assert agent.running is False

    def test_run_executes_command_and_sends_output(self, agent, mock_socket_data):
        """run(): Komut çalıştırılır ve sonuç gönderilir."""
        call_log = []

        def mock_send_data(data):
            call_log.append(data)

        # İlk recv: "echo test123", ikinci recv: "terminate"
        class MultiCommandSocket:
            def __init__(self):
                self.commands = [
                    self._make_http_response("echo test_workflow_123"),
                    self._make_http_response("terminate"),
                ]
                self.cmd_idx = 0
                self.pos = 0
                self.current_data = b""

            def _make_http_response(self, body_text):
                body = body_text.encode("utf-8")
                return (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"\r\n"
                    + body
                )

            def recv(self, size):
                if not self.current_data or self.pos >= len(self.current_data):
                    if self.cmd_idx >= len(self.commands):
                        return b""
                    self.current_data = self.commands[self.cmd_idx]
                    self.cmd_idx += 1
                    self.pos = 0

                chunk = self.current_data[self.pos:self.pos + size]
                self.pos += len(chunk)
                return chunk

            def sendall(self, d):
                pass

            def settimeout(self, t):
                pass

            def close(self):
                pass

        with patch.object(agent, "connect", return_value=True), \
             patch.object(agent, "send_sysinfo"), \
             patch.object(agent, "send_data", side_effect=mock_send_data):
            agent.sock = MultiCommandSocket()
            agent.run()

        # İlk output: echo sonucu (test_workflow_123 içermeli)
        assert any("test_workflow_123" in msg for msg in call_log)
        # Son output: terminate mesajı
        assert any("sonlandırılıyor" in msg for msg in call_log)

    def test_run_reconnects_on_disconnect(self, agent):
        """run(): Bağlantı koparsa yeniden bağlanmaya çalışır."""
        reconnect_called = False

        def mock_reconnect():
            nonlocal reconnect_called
            reconnect_called = True
            agent.running = False  # Sonsuz döngüyü kırmak için
            return False

        with patch.object(agent, "connect", return_value=True), \
             patch.object(agent, "send_sysinfo"), \
             patch.object(agent, "recv_data", return_value=""), \
             patch.object(agent, "reconnect", side_effect=mock_reconnect):
            agent.run()

        assert reconnect_called

    def test_run_initial_connect_failure_triggers_reconnect(self, agent):
        """İlk bağlantı başarısız olursa reconnect denenir."""
        with patch.object(agent, "connect", return_value=False), \
             patch.object(agent, "reconnect", return_value=False):
            agent.run()

        # Reconnect başarısız olunca run() sonlanmalı
        # (agent.running hala True ama döngüye girilmeden çıkılmış)


# ============================================================
# Builder → Agent → Handler Pipeline Testi
# ============================================================

class TestBuilderPipeline:
    """Builder → Payload üretimi → Agent yükleme pipeline testi."""

    def test_builder_produces_loadable_agent(self):
        """Builder ile üretilen kod, çalıştırılabilir bir agent sınıfı içerir."""
        from modules.payloads.python.chimera.generate import Payload

        gen = Payload()
        gen.set_option_value("LHOST", "10.0.0.1")
        gen.set_option_value("LPORT", 5555)

        result = gen.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        # Kodu modül olarak yükle
        module = types.ModuleType("test_pipeline_agent")
        exec(compile(code, "<pipeline_test>", "exec"), module.__dict__)

        # ChimeraAgent sınıfı mevcut olmalı
        assert hasattr(module, "ChimeraAgent")

        # Instance oluşturulabilmeli
        agent = module.ChimeraAgent("10.0.0.1", 5555)
        assert agent.host == "10.0.0.1"
        assert agent.port == 5555
        assert agent.running is True

    def test_strip_comments_produces_valid_code(self):
        """STRIP_COMMENTS ile üretilen kod hala geçerli."""
        from modules.payloads.python.chimera.generate import Payload

        gen = Payload()
        gen.set_option_value("LHOST", "10.0.0.1")
        gen.set_option_value("LPORT", 5555)
        gen.set_option_value("STRIP_COMMENTS", True)

        result = gen.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        # Geçerli Python syntax olmalı
        compile(code, "<stripped_payload>", "exec")

    def test_custom_reconnect_values_embedded(self):
        """Özel RECONNECT_DELAY ve MAX_RECONNECT değerleri gömülür."""
        from modules.payloads.python.chimera.generate import Payload

        gen = Payload()
        gen.set_option_value("LHOST", "10.0.0.1")
        gen.set_option_value("LPORT", 5555)
        gen.set_option_value("RECONNECT_DELAY", 10)
        gen.set_option_value("MAX_RECONNECT", 5)

        result = gen.generate(quiet=True)

        if isinstance(result, dict):
            code = result.get("code", "")
        else:
            code = result

        assert "RECONNECT_DELAY = 10" in code
        assert "MAX_RECONNECT = 5" in code
