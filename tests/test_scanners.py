import pytest
import os
from unittest.mock import MagicMock, patch
from modules.auxiliary.scanner.port_scanner import PortScanner
from modules.auxiliary.scanner.http_dir_buster import HttpDirBuster
from core.option import Option
import urllib.error

class TestPortScanner:
    @pytest.fixture
    def scanner(self):
        return PortScanner()

    def test_init(self, scanner):
        assert scanner.Name == "auxiliary/scanner/port_scanner"
        assert "RHOST" in scanner.Options
        assert "RPORTS" in scanner.Options

    def test_parse_ports_single(self, scanner):
        ports = scanner.parse_ports("80")
        assert ports == [80]

    def test_parse_ports_range(self, scanner):
        ports = scanner.parse_ports("80-82")
        assert ports == [80, 81, 82]

    def test_parse_ports_list(self, scanner):
        ports = scanner.parse_ports("80, 443, 8080")
        assert ports == [80, 443, 8080]

    @patch('socket.socket')
    def test_scan_port_open(self, mock_socket, scanner):
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        result = scanner.scan_port("127.0.0.1", 80)
        assert result == 80

    @patch('socket.socket')
    def test_scan_port_closed(self, mock_socket, scanner):
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        result = scanner.scan_port("127.0.0.1", 80)
        assert result is None

class TestHttpDirBuster:
    @pytest.fixture
    def buster(self):
        return HttpDirBuster()

    def test_init(self, buster):
        assert buster.Name == "auxiliary/scanner/http_dir_buster"
        assert "RHOST" in buster.Options
        assert "WORDLIST" in buster.Options

    @patch('urllib.request.urlopen')
    def test_check_url_200(self, mock_urlopen, buster):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = buster.check_url("http://example.com", "admin")
        assert result == ("admin", 200, "http://example.com/admin")

    @patch('urllib.request.urlopen')
    def test_check_url_404(self, mock_urlopen, buster):
        # 404 raises HTTPError in urllib
        err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = err
        
        result = buster.check_url("http://example.com", "notfound")
        # Assuming check_url returns None for 404 (or handles it if it's interested)
        # Based on implementation: "if e.code in [401, 403]: return (path, e.code, target_url)"
        # So 404 returns None
        assert result is None
    
    @patch('urllib.request.urlopen')
    def test_check_url_403(self, mock_urlopen, buster):
        err = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        mock_urlopen.side_effect = err
        
        result = buster.check_url("http://example.com", "secret")
        assert result == ("secret", 403, "http://example.com/secret")
