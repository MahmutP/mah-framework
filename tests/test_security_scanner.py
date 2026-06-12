import tempfile
from pathlib import Path

from core.code_scanner import ScanResult, _get_full_func_name, scan_file
from core.validation_pipeline import (
    SignatureValidator,
    ValidationPipeline,
    SandboxExecutor,
)


def test_scan_safe_file():
    """Güvenli bir dosya tarandığında tehlikeli kod raporlanmamalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1 + 1\nprint('hello')\ndef foo():\n    return 'bar'\n")
        f.flush()
        result = scan_file(f.name)
        assert result.is_safe
    Path(f.name).unlink(missing_ok=True)


def test_scan_eval_detected():
    """eval() çağrısı tehlikeli olarak raporlanmalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("eval('print(1)')\n")
        f.flush()
        result = scan_file(f.name)
        assert not result.is_safe
        assert any("eval" in item[0] for item in result.dangerous)
    Path(f.name).unlink(missing_ok=True)


def test_scan_exec_detected():
    """exec() çağrısı tespit edilmeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("exec('x = 1')\n")
        f.flush()
        result = scan_file(f.name)
        assert not result.is_safe
        assert any("exec" in item[0] for item in result.dangerous)
    Path(f.name).unlink(missing_ok=True)


def test_scan_os_system_detected():
    """os.system() çağrısı tespit edilmeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import os\nos.system('ls')\n")
        f.flush()
        result = scan_file(f.name)
        assert not result.is_safe
        assert any("os.system" in item[0] for item in result.dangerous)
    Path(f.name).unlink(missing_ok=True)


def test_scan_strict_subprocess_shell_true():
    """strict=True iken subprocess shell=True tespit edilmeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import subprocess\nsubprocess.Popen('ls', shell=True)\n")
        f.flush()
        result = scan_file(f.name, strict=True)
        assert not result.is_safe
        assert any("shell=True" in item[0] for item in result.dangerous)
    Path(f.name).unlink(missing_ok=True)


def test_scan_strict_subprocess_no_shell():
    """strict=True ama shell=False ise tehlikeli raporlanmamalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import subprocess\nsubprocess.run(['ls'], shell=False)\n")
        f.flush()
        result = scan_file(f.name, strict=True)
        assert result.is_safe
    Path(f.name).unlink(missing_ok=True)


def test_scan_ctypes_detected():
    """ctypes.CDLL çağrısı tespit edilmeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import ctypes\nctypes.CDLL('libc.so.6')\n")
        f.flush()
        result = scan_file(f.name)
        assert not result.is_safe
        assert any("ctypes.CDLL" in item[0] for item in result.dangerous)
    Path(f.name).unlink(missing_ok=True)


def test_scan_syntax_error():
    """Syntax hatası olan dosyada hata raporlanmalı ama tehlikeli kod bulunmamalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def foo(:\n    pass\n")
        f.flush()
        result = scan_file(f.name)
        assert len(result.dangerous) == 0
        assert len(result.errors) > 0
    Path(f.name).unlink(missing_ok=True)


def test_scan_nonexistent_file():
    """Var olmayan dosyada hata raporlanmalı ama tehlikeli kod bulunmamalı."""
    result = scan_file("/nonexistent/file.py")
    assert len(result.dangerous) == 0
    assert len(result.errors) > 0


def test_get_full_func_name_simple():
    """_get_full_func_name basit Name node'u için doğru çalışmalı."""
    import ast

    node = ast.Name(id="eval")
    assert _get_full_func_name(node) == "eval"


def test_get_full_func_name_attribute():
    """_get_full_func_name Attribute node'u için doğru çalışmalı."""
    import ast

    node = ast.Attribute(value=ast.Name(id="os"), attr="system")
    assert _get_full_func_name(node) == "os.system"


def test_get_full_func_name_deep():
    """_get_full_func_name derin attribute için doğru çalışmalı."""
    import ast

    node = ast.Attribute(
        value=ast.Attribute(value=ast.Name(id="os"), attr="path"),
        attr="join",
    )
    assert _get_full_func_name(node) == "os.path.join"


def test_scan_result_summary():
    """ScanResult.summary() doğru metin döndürmeli."""
    result = ScanResult("test.py")
    assert result.summary() == "güvenli"

    result.dangerous.append(("eval", "execution", "eval() tespit edildi", 1))
    assert "1 tehlikeli" in result.summary()

    result.errors.append("hata")
    assert "1 hata" in result.summary()


def test_validation_pipeline_module_load():
    """ValidationPipeline geçerli bir modülü doğrulayabilmeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            "class TestModule:\n"
            "    Name = 'test'\n"
            "    Description = 'test modülü'\n"
            "    Author = 'test'\n"
            "    Category = 'test'\n"
            "    Version = '1.0'\n"
            "    Options = {}\n"
            "    def run(self, options):\n"
            "        return 'ok'\n"
        )
        f.flush()
        pipeline = ValidationPipeline()
        result = pipeline.validate_module_file(f.name)
        assert result.is_valid
    Path(f.name).unlink(missing_ok=True)


def test_signature_validator_module_missing_attrs():
    """SignatureValidator eksik attribute'ları tespit etmeli."""
    class BadModule:
        Name = "bad"
        # Description, Author, Category eksik
        Version = "1.0"
        Options = {}
        def run(self, options):
            return "ok"

    validator = SignatureValidator()
    result = type("Result", (), {"errors": [], "warnings": [], "add_error": lambda self, m: self.errors.append(m), "add_warning": lambda self, m: self.warnings.append(m)})()
    validator.validate_module(BadModule, result)
    assert len(result.errors) > 0


def test_sandbox_executor_allowed_builtins():
    """SandboxExecutor izin verilen built-in'lerle çalışabilmeli."""
    sandbox = SandboxExecutor()
    restricted = sandbox.create_restricted_globals()
    assert "len" in restricted["__builtins__"]
    assert "print" not in restricted["__builtins__"]


def test_sandbox_executor_restricted_import():
    """SandboxExecutor izin verilmeyen importları engellemeli."""
    sandbox = SandboxExecutor()
    source = "import os"
    result = sandbox.exec_module_restricted(source, "test.py")
    assert result is None


def test_sandbox_executor_allowed_import():
    """SandboxExecutor izin verilen importlara izin vermeli."""
    sandbox = SandboxExecutor()
    source = "import json\nx = json.dumps({'a': 1})"
    result = sandbox.exec_module_restricted(source, "test.py")
    assert result is not None