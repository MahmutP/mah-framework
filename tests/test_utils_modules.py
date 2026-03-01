# =============================================================================
# Yardımcı Araç Modülleri — Birim Testleri
# =============================================================================

import pytest
import hashlib
from unittest.mock import MagicMock, patch, PropertyMock

# ── Web Crawler ──────────────────────────────────────────────────────────────
from modules.auxiliary.utils.web_crawler import web_crawler

# ── Hash Cracker ─────────────────────────────────────────────────────────────
from modules.auxiliary.utils.hash_cracker import hash_cracker

# ── Service Manager ──────────────────────────────────────────────────────────
from modules.auxiliary.os.service_manager import service_manager

# ── Process Manager ──────────────────────────────────────────────────────────
from modules.auxiliary.os.process_manager import process_manager


# =============================================================================
# TestWebCrawler
# =============================================================================
class TestWebCrawler:
    @pytest.fixture
    def mod(self):
        return web_crawler()

    def test_init_metadata(self, mod):
        assert mod.Name == "Web Crawler"
        assert mod.Category == "auxiliary/utils"
        assert mod.Version == "1.0"

    def test_init_options(self, mod):
        assert "TARGET_URL" in mod.Options
        assert "MAX_DEPTH" in mod.Options
        assert "MAX_PAGES" in mod.Options
        assert "TIMEOUT" in mod.Options
        assert "USER_AGENT" in mod.Options
        assert "CHECK_ROBOTS" in mod.Options

    def test_same_domain_true(self, mod):
        assert mod._same_domain("http://example.com/a", "http://example.com/b") is True

    def test_same_domain_false(self, mod):
        assert mod._same_domain("http://example.com", "http://other.com") is False

    def test_normalize_url(self, mod):
        result = mod._normalize_url("http://example.com/page#section")
        assert "#" not in result
        assert "example.com/page" in result

    def test_extract_links(self, mod):
        html = '<html><body><a href="/about">About</a><a href="http://external.com">Ext</a></body></html>'
        links = mod._extract_links(html, "http://example.com")
        assert any("about" in l for l in links)
        assert any("external.com" in l for l in links)

    def test_extract_forms(self, mod):
        html = '<html><body><form action="/login" method="POST"><input name="user" type="text"></form></body></html>'
        forms = mod._extract_forms(html, "http://example.com")
        assert len(forms) == 1
        assert forms[0]["method"] == "POST"
        assert "/login" in forms[0]["action"]
        assert len(forms[0]["inputs"]) == 1

    def test_extract_meta(self, mod):
        html = '<html><head><title>Test Page</title><meta name="description" content="A test"></head></html>'
        meta = mod._extract_meta(html)
        assert meta.get("title") == "Test Page"
        assert meta.get("description") == "A test"

    def test_run_invalid_url(self, mod):
        result = mod.run({"TARGET_URL": "not-a-url"})
        assert result is False

    @patch("modules.auxiliary.utils.web_crawler.requests.get")
    def test_run_basic(self, mock_get, mod):
        mock_resp = MagicMock()
        mock_resp.text = "<html><head><title>Hi</title></head><body></body></html>"
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = mod.run({
            "TARGET_URL": "http://example.com",
            "MAX_DEPTH": 0,
            "MAX_PAGES": 1,
            "TIMEOUT": 2,
            "USER_AGENT": "Test",
            "CHECK_ROBOTS": "false",
        })
        assert result is True


# =============================================================================
# TestHashCracker
# =============================================================================
class TestHashCracker:
    @pytest.fixture
    def mod(self):
        return hash_cracker()

    def test_init_metadata(self, mod):
        assert mod.Name == "Hash Cracker"
        assert mod.Category == "auxiliary/utils"

    def test_init_options(self, mod):
        assert "HASH" in mod.Options
        assert "HASH_FILE" in mod.Options
        assert "HASH_TYPE" in mod.Options
        assert "WORDLIST" in mod.Options

    def test_detect_hash_type_md5(self, mod):
        assert mod.detect_hash_type("d" * 32) == "md5"

    def test_detect_hash_type_sha1(self, mod):
        assert mod.detect_hash_type("a" * 40) == "sha1"

    def test_detect_hash_type_sha256(self, mod):
        assert mod.detect_hash_type("b" * 64) == "sha256"

    def test_detect_hash_type_sha512(self, mod):
        assert mod.detect_hash_type("c" * 128) == "sha512"

    def test_detect_hash_type_unknown(self, mod):
        assert mod.detect_hash_type("abc") is None

    def test_compute_hash_md5(self, mod):
        expected = hashlib.md5(b"hello").hexdigest()
        assert mod.compute_hash("hello", "md5") == expected

    def test_compute_hash_sha256(self, mod):
        expected = hashlib.sha256(b"test").hexdigest()
        assert mod.compute_hash("test", "sha256") == expected

    def test_crack_known_hash(self, mod):
        target = hashlib.md5(b"password").hexdigest()
        result = mod._crack_hash(target, "md5", ["admin", "root", "password", "test"])
        assert result == "password"

    def test_crack_unknown_hash(self, mod):
        target = hashlib.md5(b"xyzzy_not_in_list").hexdigest()
        result = mod._crack_hash(target, "md5", ["admin", "root", "password"])
        assert result is None

    def test_run_no_hash(self, mod):
        result = mod.run({"HASH": "", "HASH_FILE": "", "WORDLIST": "irrelevant"})
        assert result is False


# =============================================================================
# TestServiceManager
# =============================================================================
class TestServiceManager:
    @pytest.fixture
    def mod(self):
        return service_manager()

    def test_init_metadata(self, mod):
        assert mod.Name == "Service Manager"
        assert mod.Category == "auxiliary/os"

    def test_init_options(self, mod):
        assert "ACTION" in mod.Options
        assert "SERVICE_NAME" in mod.Options
        assert "FILTER" in mod.Options

    @patch("modules.auxiliary.os.service_manager.subprocess.run")
    def test_run_cmd_success(self, mock_run, mod):
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)
        stdout, stderr, rc = mod._run_cmd(["echo", "hello"])
        assert rc == 0
        assert stdout == "output"

    @patch("modules.auxiliary.os.service_manager.subprocess.run")
    def test_run_cmd_not_found(self, mock_run, mod):
        mock_run.side_effect = FileNotFoundError()
        _, stderr, rc = mod._run_cmd(["nonexistent"])
        assert rc == -1

    def test_detect_platform(self, mod):
        plat = mod._detect_platform()
        assert plat in ("linux", "darwin", "win32")

    @patch.object(service_manager, "_list_darwin", return_value=[
        {"name": "com.apple.sshd", "pid": "123", "status": "0"},
    ])
    @patch.object(service_manager, "_detect_platform", return_value="darwin")
    def test_run_list(self, mock_plat, mock_list, mod):
        result = mod.run({"ACTION": "list", "SERVICE_NAME": "", "FILTER": ""})
        assert result is True

    def test_run_status_no_service(self, mod):
        result = mod.run({"ACTION": "status", "SERVICE_NAME": "", "FILTER": ""})
        assert result is False

    @patch.object(service_manager, "_service_action", return_value=(True, "active"))
    @patch.object(service_manager, "_detect_platform", return_value="linux")
    def test_run_status_ok(self, mock_plat, mock_action, mod):
        result = mod.run({"ACTION": "status", "SERVICE_NAME": "sshd", "FILTER": ""})
        assert result is True


# =============================================================================
# TestProcessManager
# =============================================================================
class TestProcessManager:
    @pytest.fixture
    def mod(self):
        return process_manager()

    def test_init_metadata(self, mod):
        assert mod.Name == "Process Manager"
        assert mod.Category == "auxiliary/os"

    def test_init_options(self, mod):
        assert "ACTION" in mod.Options
        assert "PID" in mod.Options
        assert "FILTER" in mod.Options
        assert "SORT_BY" in mod.Options
        assert "COUNT" in mod.Options

    @patch("modules.auxiliary.os.process_manager.psutil.process_iter")
    def test_get_processes(self, mock_iter, mod):
        mock_proc = MagicMock()
        mock_proc.info = {
            "pid": 1, "name": "test", "username": "root",
            "cpu_percent": 5.0, "memory_percent": 2.0,
            "status": "running", "cmdline": ["test"],
        }
        mock_iter.return_value = [mock_proc]
        procs = mod._get_processes()
        assert len(procs) == 1
        assert procs[0]["pid"] == 1

    @patch.object(process_manager, "_get_processes", return_value=[
        {"pid": 1, "name": "init", "user": "root", "cpu": 0.0,
         "mem": 0.1, "status": "running", "cmd": "/sbin/init"},
    ])
    def test_action_list(self, mock_procs, mod):
        result = mod._action_list("cpu", 10)
        assert result is True

    def test_action_search_no_filter(self, mod):
        result = mod._action_search("")
        assert result is False

    @patch.object(process_manager, "_get_processes", return_value=[
        {"pid": 100, "name": "python3", "user": "user", "cpu": 10.0,
         "mem": 5.0, "status": "running", "cmd": "python3 app.py"},
        {"pid": 200, "name": "bash", "user": "user", "cpu": 0.0,
         "mem": 0.1, "status": "sleeping", "cmd": "/bin/bash"},
    ])
    def test_action_search_found(self, mock_procs, mod):
        result = mod._action_search("python")
        assert result is True

    @patch("modules.auxiliary.os.process_manager.psutil.Process")
    def test_action_kill_success(self, mock_proc_cls, mod):
        mock_proc = MagicMock()
        mock_proc.name.return_value = "test_proc"
        mock_proc_cls.return_value = mock_proc
        result = mod._action_kill(12345)
        assert result is True
        mock_proc.terminate.assert_called_once()

    def test_run_kill_no_pid(self, mod):
        result = mod.run({"ACTION": "kill", "PID": "", "FILTER": "", "SORT_BY": "cpu", "COUNT": 10})
        assert result is False
