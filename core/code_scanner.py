import ast
import os
from pathlib import Path
from typing import List, Tuple, Optional

DANGEROUS_PATTERNS: List[Tuple[str, str, str]] = [
    ("eval",        "execution",  "eval() çağrısı tespit edildi"),
    ("exec",        "execution",  "exec() çağrısı tespit edildi"),
    ("compile",     "execution",  "compile() çağrısı tespit edildi"),
    ("__import__",  "execution",  "__import__() çağrısı tespit edildi"),
    ("os.system",   "subprocess", "os.system() çağrısı tespit edildi"),
    ("os.popen",    "subprocess", "os.popen() çağrısı tespit edildi"),
    ("os.execl",    "subprocess", "os.execl/p/pe/le() çağrısı tespit edildi"),
    ("ctypes.CDLL",     "native",  "ctypes.CDLL() çağrısı tespit edildi"),
    ("ctypes.LoadLibrary", "native", "ctypes.LoadLibrary() çağrısı tespit edildi"),
    ("ctypes.WinDLL",   "native",  "ctypes.WinDLL() çağrısı tespit edildi"),
]

SUSPICIOUS_IMPORTS = [
    "ctypes", "winreg", "msvcrt", "socket",
]

class ScanResult:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.dangerous: List[Tuple[str, str, str, int]] = []
        self.suspicious: List[Tuple[str, str, int]] = []
        self.errors: List[str] = []

    @property
    def is_safe(self) -> bool:
        return len(self.dangerous) == 0 and len(self.errors) == 0

    def has_warnings(self) -> bool:
        return len(self.suspicious) > 0

    def summary(self) -> str:
        parts = []
        if self.dangerous:
            parts.append(f"{len(self.dangerous)} tehlikeli")
        if self.suspicious:
            parts.append(f"{len(self.suspicious)} şüpheli")
        if self.errors:
            parts.append(f"{len(self.errors)} hata")
        return ", ".join(parts) if parts else "güvenli"


def scan_file(file_path: str) -> ScanResult:
    result = ScanResult(file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except Exception as e:
        result.errors.append(f"Dosya okunamadı: {e}")
        return result

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        result.errors.append(f"AST ayrıştırma hatası: {e}")
        return result

    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        if isinstance(node, ast.Call):
            func_name = _get_full_func_name(node.func)
            if func_name:
                for pattern, category, desc in DANGEROUS_PATTERNS:
                    if func_name == pattern or func_name.endswith("." + pattern):
                        result.dangerous.append((
                            pattern, category, desc, node.lineno
                        ))

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("system", "popen", "Popen", "run", "call", "check_call", "check_output"):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        result.dangerous.append((
                            f"subprocess.{node.func.attr}(shell=True)",
                            "subprocess",
                            f"subprocess.{node.func.attr}() shell=True ile çağrılmış",
                            node.lineno
                        ))

    for imp in imports:
        imp_base = imp.split(".")[0]
        if imp_base in SUSPICIOUS_IMPORTS:
            result.suspicious.append((imp, "import", 0))

    dangerous_set = set()
    filtered_dangerous = []
    for item in result.dangerous:
        key = (item[0], item[3])
        if key not in dangerous_set:
            dangerous_set.add(key)
            filtered_dangerous.append(item)
    result.dangerous = filtered_dangerous

    return result


def _get_full_func_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        elif isinstance(current, ast.Call):
            return None
        else:
            return None
        return ".".join(reversed(parts))
    return None


def print_scan_report(result: ScanResult) -> None:
    from rich import print
    if result.errors:
        for err in result.errors:
            print(f"  [bold red]✗ Tarama hatası:[/bold red] {err}")
    for pattern, category, desc, lineno in result.dangerous:
        print(f"  [bold red]✗ {desc}[/bold red] (satır {lineno})")
    for imp, _typ, _lineno in result.suspicious:
        print(f"  [bold yellow]⚠ Şüpheli import:[/bold yellow] '{imp}'")
