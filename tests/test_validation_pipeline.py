"""Validation Pipeline birim testleri."""

import tempfile
from pathlib import Path

from core.validation_pipeline import (
    SignatureValidator,
    SandboxExecutor,
    ValidationPipeline,
    print_validation_report,
)


def test_validator_module_ok():
    """Geçerli bir modül sınıfı doğrulamadan geçmeli."""
    class ValidModule:
        Name = "test"
        Description = "test"
        Author = "test"
        Category = "test"
        Version = "1.0"
        Options = {}
        def run(self, options):
            return "ok"

    result_type = type("Result", (), {
        "errors": [],
        "warnings": [],
        "add_error": lambda self, m: self.errors.append(m),
        "add_warning": lambda self, m: self.warnings.append(m),
    })

    validator = SignatureValidator()
    result = result_type()
    validator.validate_module(ValidModule, result)
    assert len(result.errors) == 0


def test_validator_module_missing_name():
    """Name attribute'u eksik modül doğrulamadan geçmemeli."""
    class BadModule:
        Description = "test"
        Author = "test"
        Category = "test"
        Version = "1.0"
        Options = {}
        def run(self, options):
            return "ok"

    result_type = type("Result", (), {
        "errors": [],
        "warnings": [],
        "add_error": lambda self, m: self.errors.append(m),
        "add_warning": lambda self, m: self.warnings.append(m),
    })

    validator = SignatureValidator()
    result = result_type()
    validator.validate_module(BadModule, result)
    assert len(result.errors) > 0
    assert any("Name" in e for e in result.errors)


def test_validator_module_missing_run():
    """run() metodu eksik modül doğrulamadan geçmemeli."""
    class BadModule:
        Name = "test"
        Description = "test"
        Author = "test"
        Category = "test"
        Version = "1.0"
        Options = {}
        # run metodu yok

    result_type = type("Result", (), {
        "errors": [],
        "warnings": [],
        "add_error": lambda self, m: self.errors.append(m),
        "add_warning": lambda self, m: self.warnings.append(m),
    })

    validator = SignatureValidator()
    result = result_type()
    validator.validate_module(BadModule, result)
    assert len(result.errors) > 0
    assert any("run" in e for e in result.errors)


def test_validator_plugin_ok():
    """Geçerli bir plugin sınıfı doğrulamadan geçmeli."""
    class ValidPlugin:
        Name = "test"
        Description = "test"
        Author = "test"
        Version = "1.0"
        Enabled = True
        Priority = 100
        def on_load(self):
            pass
        def on_unload(self):
            pass

    result_type = type("Result", (), {
        "errors": [],
        "warnings": [],
        "add_error": lambda self, m: self.errors.append(m),
        "add_warning": lambda self, m: self.warnings.append(m),
    })

    validator = SignatureValidator()
    result = result_type()
    validator.validate_plugin(ValidPlugin, result)
    assert len(result.errors) == 0


def test_validator_plugin_missing_methods():
    """on_load/on_unload metotları eksik plugin doğrulamadan geçmemeli."""
    class BadPlugin:
        Name = "test"
        Description = "test"
        Author = "test"
        Version = "1.0"
        Enabled = True
        Priority = 100

    result_type = type("Result", (), {
        "errors": [],
        "warnings": [],
        "add_error": lambda self, m: self.errors.append(m),
        "add_warning": lambda self, m: self.warnings.append(m),
    })

    validator = SignatureValidator()
    result = result_type()
    validator.validate_plugin(BadPlugin, result)
    assert len(result.errors) == 2  # on_load + on_unload


def test_sandbox_restricted_builtins():
    """SandboxExecutor kısıtlı built-in'leri doğru oluşturmalı."""
    sandbox = SandboxExecutor()
    restricted = sandbox.create_restricted_globals()

    builtins = restricted["__builtins__"]
    assert "print" not in builtins
    assert "exec" not in builtins
    assert "eval" not in builtins
    assert "__import__" in builtins  # Import mekanizması için gerekli
    assert "open" not in builtins

    assert builtins.get("len") is len
    assert builtins.get("int") is int
    assert builtins.get("str") is str
    assert builtins.get("list") is list
    assert builtins.get("True") is True
    assert builtins.get("False") is False


def test_sandbox_exec_safe_code():
    """SandboxExecutor güvenli kodu çalıştırabilmeli."""
    sandbox = SandboxExecutor()
    source = "x = 1 + 1\nresult = x * 2"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is not None
    assert module.__dict__.get("result") == 4


def test_sandbox_block_import_os():
    """SandboxExecutor os import'ını engellemeli."""
    sandbox = SandboxExecutor()
    source = "import os"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is None


def test_sandbox_block_subprocess():
    """SandboxExecutor subprocess import'ını engellemeli."""
    sandbox = SandboxExecutor()
    source = "import subprocess"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is None


def test_sandbox_allow_json():
    """SandboxExecutor json import'ına izin vermeli."""
    sandbox = SandboxExecutor()
    source = "import json\ndata = json.dumps({'a': 1})"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is not None
    assert module.__dict__.get("data") == '{"a": 1}'


def test_sandbox_block_from_os():
    """SandboxExecutor from os import'ını engellemeli."""
    sandbox = SandboxExecutor()
    source = "from os import system"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is None


def test_sandbox_syntax_error():
    """SandboxExecutor syntax hatasında None dönmeli."""
    sandbox = SandboxExecutor()
    source = "def foo(:\n    pass"
    module = sandbox.exec_module_restricted(source, "test.py")
    assert module is None


def test_pipeline_valid_module():
    """ValidationPipeline geçerli modül dosyasını doğrulamalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            "class TestModule:\n"
            "    Name = 'test'\n"
            "    Description = 'test module'\n"
            "    Author = 'tester'\n"
            "    Category = 'test'\n"
            "    Version = '1.0'\n"
            "    Options = {}\n"
            "    Requirements = {}\n"
            "    def run(self, options):\n"
            "        return 'ok'\n"
        )
        f.flush()
        pipeline = ValidationPipeline()
        result = pipeline.validate_module_file(f.name)
        assert result.is_valid
        assert len(result.errors) == 0
    Path(f.name).unlink(missing_ok=True)


def test_pipeline_safe_file_no_module():
    """Modül sınıfı olmayan güvenli dosya doğrulamadan geçerli sayılmalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\ny = x + 2\n")
        f.flush()
        pipeline = ValidationPipeline()
        result = pipeline.validate_module_file(f.name)
        assert result.is_valid
    Path(f.name).unlink(missing_ok=True)


def test_pipeline_plugin_valid_file():
    """ValidationPipeline geçerli plugin dosyasını doğrulamalı."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            "class TestPlugin:\n"
            "    Name = 'test_plugin'\n"
            "    Description = 'test plugin'\n"
            "    Author = 'tester'\n"
            "    Version = '1.0'\n"
            "    Enabled = True\n"
            "    Priority = 100\n"
            "    def on_load(self):\n"
            "        pass\n"
            "    def on_unload(self):\n"
            "        pass\n"
        )
        f.flush()
        pipeline = ValidationPipeline()
        result = pipeline.validate_plugin_file(f.name)
        assert result.is_valid
    Path(f.name).unlink(missing_ok=True)


def test_pipeline_unsafe_module():
    """Tehlikeli kod içeren modül dosyası doğrulamadan geçmemeli."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("eval('print(1)')\n")
        f.flush()
        pipeline = ValidationPipeline()
        result = pipeline.validate_module_file(f.name, strict_scan=True)
        assert not result.is_valid
        assert len(result.errors) > 0
    Path(f.name).unlink(missing_ok=True)


def test_validation_result_warnings():
    """ValidationResult uyarıları doğru yönetmeli."""
    from core.validation_pipeline import ValidationResult
    result = ValidationResult("test.py")
    assert result.is_valid
    result.add_warning("test uyarısı")
    assert result.is_valid
    assert len(result.warnings) == 1
    result.add_error("test hatası")
    assert not result.is_valid


def test_print_validation_report():
    """print_validation_report hata vermeden çalışmalı."""
    from io import StringIO
    import sys

    from core.validation_pipeline import ValidationResult

    result = ValidationResult("test.py")
    result.add_error("hata 1")

    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        print_validation_report(result)
        output = captured.getvalue()
        assert "test.py" in output
        assert "hata 1" in output
    finally:
        sys.stdout = old_stdout


def test_sandbox_strict_default():
    """SandboxExecutor varsayılan strict=True olmalı."""
    sandbox = SandboxExecutor()
    assert sandbox.strict is True


def test_sandbox_strict_custom():
    """SandboxExecutor strict parametresi ayarlanabilmeli."""
    sandbox = SandboxExecutor(strict=False)
    assert sandbox.strict is False