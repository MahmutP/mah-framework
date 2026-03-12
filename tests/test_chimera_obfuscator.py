import ast
import pytest
from build.chimera_obfuscator import (
    _ast_rename, _encrypt_strings, _inject_junk, 
    _control_flow_flatten, _inject_opaque_predicates, 
    _inject_dead_code, obfuscate
)

SAMPLE_CODE = """
import os
import sys

def hello_world(name):
    greeting = "Hello " + name
    print(greeting)
    return True

if __name__ == '__main__':
    hello_world("admin")
"""

def verify_syntax(code):
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in obfuscated code: {e}\\nCode:\\n{code}")

def test_ast_rename():
    code, mapping = _ast_rename(SAMPLE_CODE, seed=42)
    verify_syntax(code)
    # Check if original names are gone
    assert "hello_world" not in code
    assert "greeting" not in code

def test_encrypt_strings():
    code, count = _encrypt_strings(SAMPLE_CODE)
    verify_syntax(code)
    assert "Hello " not in code
    assert count > 0

def test_inject_junk():
    code, count = _inject_junk(SAMPLE_CODE, density=0.8)
    verify_syntax(code)
    # The density guarantees some insertions on sample code size
    # Check length
    assert len(code.split("\\n")) >= len(SAMPLE_CODE.split("\\n"))

def test_control_flow_flatten():
    flat_sample = """
def simple_func():
    a = 1
    b = 2
    c = a + b
    return c
"""
    code, count = _control_flow_flatten(flat_sample)
    verify_syntax(code)
    assert count > 0
    assert "while" in code

def test_inject_opaque_predicates():
    code, count = _inject_opaque_predicates(SAMPLE_CODE, density=0.8)
    verify_syntax(code)

def test_inject_dead_code():
    code, count = _inject_dead_code(SAMPLE_CODE, count=2)
    verify_syntax(code)
    assert count > 0
    assert "def " in code

def test_full_obfuscation():
    result = obfuscate(SAMPLE_CODE)
    assert result["success"] is True
    verify_syntax(result["code"])
    assert "stats" in result
    assert "original_size" in result["stats"]
