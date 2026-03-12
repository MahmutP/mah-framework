import os
import tempfile
import ast
import pytest
from build.chimera_builder import build_payload, validate_host, validate_port

MOCK_AGENT_CODE = """
import time
LHOST = "{{LHOST}}"
LPORT = {{LPORT}}
RECONNECT_DELAY = 5
MAX_RECONNECT = -1
CHANNEL_TYPE = "{{CHANNEL_TYPE}}"
DNS_DOMAIN = "{{DNS_DOMAIN}}"
FRONTING_DOMAIN = "{{FRONTING_DOMAIN}}"

def main():
    print(f"Connecting to {LHOST}:{LPORT}")

if __name__ == '__main__':
    main()
"""

@pytest.fixture
def mock_agent_file():
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, 'w') as f:
        f.write(MOCK_AGENT_CODE)
    yield path
    os.remove(path)

def test_validate_host():
    assert validate_host("192.168.1.1") is True
    assert validate_host("example.com") is True
    assert validate_host("") is False
    assert validate_host("invalid..host") is False

def test_validate_port():
    assert validate_port(80) is True
    assert validate_port("443") is True
    assert validate_port(0) is False
    assert validate_port(70000) is False
    assert validate_port("abc") is False

def test_build_payload_success(mock_agent_file):
    result = build_payload(
        lhost="10.10.10.10",
        lport=4444,
        agent_source_path=mock_agent_file,
        quiet=True
    )
    assert result["success"] is True
    code = result["code"]
    assert 'LHOST = "10.10.10.10"' in code
    assert 'LPORT = 4444' in code
    
    # Verify syntax automatically
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax error: {e}")

def test_build_payload_strip_comments(mock_agent_file):
    with open(mock_agent_file, 'a') as f:
        f.write("\n# This is a comment\n")

    result = build_payload(
        lhost="127.0.0.1",
        lport=8080,
        agent_source_path=mock_agent_file,
        strip_comments=True,
        quiet=True
    )
    assert result["success"] is True
    code = result["code"]
    assert "# This is a comment" not in code
    
    # Verify syntax automatically
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Generated code has syntax error: {e}")

def test_build_payload_invalid_inputs(mock_agent_file):
    res_host = build_payload("invalid..", 4444, agent_source_path=mock_agent_file, quiet=True)
    assert res_host["success"] is False
    
    res_port = build_payload("127.0.0.1", 99999, agent_source_path=mock_agent_file, quiet=True)
    assert res_port["success"] is False
