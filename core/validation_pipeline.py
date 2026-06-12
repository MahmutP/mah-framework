# Modül ve Plugin yükleme pipeline'ı: Doğrulama katmanı
# Pipeline: Dosya → AST Analizi → İmza Doğrulama → Sandbox (opsiyonel) → Yükle

import ast
import importlib.util
import types
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from core.code_scanner import ScanResult, scan_file


@runtime_checkable
class HasModuleProtocol(Protocol):
    Name: str
    Description: str
    Author: str
    Category: str
    Version: str
    Options: dict

    def run(self, options: dict[str, Any]) -> Any: ...


@runtime_checkable
class HasPluginProtocol(Protocol):
    Name: str
    Description: str
    Author: str
    Version: str
    Enabled: bool
    Priority: int

    def on_load(self) -> None: ...
    def on_unload(self) -> None: ...


class ValidationResult:
    """Doğrulama sonucu."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.scan_result: ScanResult | None = None

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


class SignatureValidator:
    """Modül/Plugin imza doğrulayıcı."""

    MODULE_REQUIRED_ATTRS = {"Name", "Description", "Author", "Category", "Version"}
    MODULE_REQUIRED_METHODS = {"run"}

    PLUGIN_REQUIRED_ATTRS = {"Name", "Description", "Author", "Version"}
    PLUGIN_REQUIRED_METHODS = {"on_load", "on_unload"}

    def validate_module(self, module_class: type, result: ValidationResult) -> None:
        """BaseModule türevi bir sınıfın imzasını doğrular."""
        for attr in self.MODULE_REQUIRED_ATTRS:
            if not hasattr(module_class, attr):
                result.add_error(f"Eksik modül attribute: {attr}")

        for method in self.MODULE_REQUIRED_METHODS:
            if not hasattr(module_class, method) or not callable(
                getattr(module_class, method)
            ):
                result.add_error(f"Eksik modül metodu: {method}()")

        # run() metod imzası kontrolü
        if hasattr(module_class, "run") and callable(module_class.run):
            import inspect

            try:
                sig = inspect.signature(module_class.run)
                if "options" not in sig.parameters:
                    result.add_warning(
                        "run() metodu 'options' parametresi almıyor"
                    )
            except (ValueError, TypeError):
                pass

    def validate_plugin(self, plugin_class: type, result: ValidationResult) -> None:
        """BasePlugin türevi bir sınıfın imzasını doğrular."""
        for attr in self.PLUGIN_REQUIRED_ATTRS:
            if not hasattr(plugin_class, attr):
                result.add_error(f"Eksik plugin attribute: {attr}")

        for method in self.PLUGIN_REQUIRED_METHODS:
            if not hasattr(plugin_class, method) or not callable(
                getattr(plugin_class, method)
            ):
                result.add_error(f"Eksik plugin metodu: {method}()")


class SandboxExecutor:
    """Kısıtlı (sandbox) modül çalıştırıcı.

    Güvenilmeyen modülleri kısıtlı bir ortamda çalıştırmak için kullanılır.
    """

    # İzin verilen built-in'ler
    ALLOWED_BUILTINS = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
        "float", "format", "frozenset", "getattr", "hasattr", "hash",
        "hex", "id", "int", "isinstance", "issubclass", "iter", "len",
        "list", "map", "max", "min", "next", "object", "oct", "ord",
        "pow", "range", "repr", "reversed", "round", "set", "slice",
        "sorted", "str", "sum", "super", "tuple", "type", "vars", "zip",
        "True", "False", "None",
    }

    # İzin verilen modüller
    ALLOWED_MODULES = {
        "re", "json", "math", "datetime", "typing", "enum",
        "collections", "itertools", "functools", "pathlib",
    }

    # İzin verilen ek built-in'ler (import mekanizması için gerekli)
    EXTRA_ALLOWED_BUILTINS = {"__import__"}

    def __init__(self, strict: bool = True) -> None:
        self.strict = strict

    def create_restricted_globals(self) -> dict:
        """Kısıtlı global namespace oluşturur."""
        restricted_builtins: dict[str, Any] = {}

        builtins_dict: dict[str, Any] = {}
        if isinstance(__builtins__, dict):
            builtins_dict = __builtins__
        elif hasattr(__builtins__, "__dict__"):
            builtins_dict = __builtins__.__dict__

        for name in self.ALLOWED_BUILTINS | self.EXTRA_ALLOWED_BUILTINS:
            if name in builtins_dict:
                restricted_builtins[name] = builtins_dict[name]

        return {
            "__builtins__": restricted_builtins,
            "__name__": "__restricted__",
        }

    def exec_module_restricted(self, source: str, filename: str) -> types.ModuleType | None:
        """Kaynak kodu kısıtlı ortamda çalıştırır."""
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError:
            return None

        # AST'yi analiz et - tehlikeli node'ları engelle
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.ALLOWED_MODULES:
                        return None
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in self.ALLOWED_MODULES:
                    return None

        # Kısıtlı globals ile compile et
        restricted_globals = self.create_restricted_globals()
        restricted_locals: dict[str, Any] = {}

        try:
            exec(compile(tree, filename, "exec"), restricted_globals, restricted_locals)
        except Exception:
            return None

        mod = types.ModuleType(filename)
        for key, value in restricted_locals.items():
            setattr(mod, key, value)
        return mod


class ValidationPipeline:
    """Modül/Plugin doğrulama pipeline'ı.

    Pipeline adımları:
    1. AST Analizi (güvenlik taraması)
    2. İmza Doğrulama (zorunlu attr/metot kontrolü)
    3. Sandbox (opsiyonel - güvenilmeyen modüller için)
    """

    def __init__(self) -> None:
        self.signature_validator = SignatureValidator()
        self.sandbox = SandboxExecutor()

    def validate_module_file(
        self, file_path: str, strict_scan: bool = False, sandbox: bool = False
    ) -> ValidationResult:
        """Bir modül dosyasını pipeline'dan geçirir."""
        result = ValidationResult(file_path)

        # 1. AST Analizi
        result.scan_result = scan_file(file_path, strict=strict_scan)
        if not result.scan_result.is_safe:
            for pattern, cat, desc, lineno in result.scan_result.dangerous:
                result.add_error(f"{desc} (satır {lineno})")
            if strict_scan:
                return result

        # 2. Modül yükle
        try:
            spec = importlib.util.spec_from_file_location(
                Path(file_path).stem, file_path
            )
            if spec is None or spec.loader is None:
                result.add_error("Modül spesifikasyonu alınamadı")
                return result

            if sandbox:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                module = self.sandbox.exec_module_restricted(source, file_path)
                if module is None:
                    result.add_error("Sandbox çalıştırma başarısız")
                    return result
            else:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # 3. Sınıfları tara ve imza doğrula
            for name, obj in module.__dict__.items():
                if isinstance(obj, type):
                    # BaseModule benzeri sınıfları kontrol et
                    if hasattr(obj, "Name") and hasattr(obj, "run"):
                        self.signature_validator.validate_module(obj, result)

            return result

        except SyntaxError as e:
            result.add_error(f"Sözdizimi hatası: {e}")
            return result
        except ImportError as e:
            result.add_error(f"İçe aktarma hatası: {e}")
            return result
        except Exception as e:
            result.add_error(f"Beklenmeyen hata: {e}")
            return result

    def validate_plugin_file(
        self, file_path: str, sandbox: bool = False
    ) -> ValidationResult:
        """Bir plugin dosyasını pipeline'dan geçirir."""
        result = ValidationResult(file_path)

        # 1. AST Analizi (strict=True - plugin'ler daha sıkı denetlenir)
        result.scan_result = scan_file(file_path, strict=True)
        if not result.scan_result.is_safe:
            for pattern, cat, desc, lineno in result.scan_result.dangerous:
                result.add_error(f"{desc} (satır {lineno})")
            return result

        # 2. Plugin yükle
        try:
            if sandbox:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                module = self.sandbox.exec_module_restricted(source, file_path)
                if module is None:
                    result.add_error("Sandbox çalıştırma başarısız")
                    return result
            else:
                spec = importlib.util.spec_from_file_location(
                    Path(file_path).stem, file_path
                )
                if spec is None or spec.loader is None:
                    result.add_error("Plugin spesifikasyonu alınamadı")
                    return result
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # 3. Sınıfları tara ve imza doğrula
            for name, obj in module.__dict__.items():
                if isinstance(obj, type):
                    if hasattr(obj, "Name") and hasattr(obj, "on_load"):
                        self.signature_validator.validate_plugin(obj, result)

            return result

        except SyntaxError as e:
            result.add_error(f"Sözdizimi hatası: {e}")
            return result
        except ImportError as e:
            result.add_error(f"İçe aktarma hatası: {e}")
            return result
        except Exception as e:
            result.add_error(f"Beklenmeyen hata: {e}")
            return result


def print_validation_report(result: ValidationResult) -> None:
    """Doğrulama raporunu ekrana basar."""
    from rich import print as rprint

    if result.is_valid:
        rprint(f"[green]✓[/green] {result.file_path}: Geçerli")
    else:
        rprint(f"[red]✗[/red] {result.file_path}: Geçersiz")
        for err in result.errors:
            rprint(f"  [red]  ✗ {err}[/red]")

    if result.warnings:
        for warn in result.warnings:
            rprint(f"  [yellow]  ⚠ {warn}[/yellow]")