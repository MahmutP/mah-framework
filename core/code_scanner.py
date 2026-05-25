import ast
from typing import List, Tuple, Optional

EXECUTION_PATTERNS: List[Tuple[str, str, str]] = [
    ("eval",        "execution",  "eval() çağrısı tespit edildi"),
    ("exec",        "execution",  "exec() çağrısı tespit edildi"),
    ("compile",     "execution",  "compile() çağrısı tespit edildi"),
    ("__import__",  "execution",  "__import__() çağrısı tespit edildi"),
]

SHELL_PATTERNS: List[Tuple[str, str, str]] = [
    ("os.system",   "subprocess", "os.system() çağrısı tespit edildi"),
    ("os.popen",    "subprocess", "os.popen() çağrısı tespit edildi"),
    ("os.execl",    "subprocess", "os.execl/p/pe/le() çağrısı tespit edildi"),
]

NATIVE_PATTERNS: List[Tuple[str, str, str]] = [
    ("ctypes.CDLL",     "native",  "ctypes.CDLL() çağrısı tespit edildi"),
    ("ctypes.LoadLibrary", "native", "ctypes.LoadLibrary() çağrısı tespit edildi"),
    ("ctypes.WinDLL",   "native",  "ctypes.WinDLL() çağrısı tespit edildi"),
]


class ScanResult:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.dangerous: List[Tuple[str, str, str, int]] = []
        self.errors: List[str] = []

    @property
    def is_safe(self) -> bool:
        return len(self.dangerous) == 0 and len(self.errors) == 0

    def summary(self) -> str:
        parts = []
        if self.dangerous:
            parts.append(f"{len(self.dangerous)} tehlikeli")
        if self.errors:
            parts.append(f"{len(self.errors)} hata")
        return ", ".join(parts) if parts else "güvenli"


def scan_file(file_path: str, strict: bool = False) -> ScanResult:
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

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_full_func_name(node.func)
        if not func_name:
            continue

        for pattern, category, desc in EXECUTION_PATTERNS:
            if func_name == pattern or func_name.endswith("." + pattern):
                result.dangerous.append((pattern, category, desc, node.lineno))

        for pattern, category, desc in SHELL_PATTERNS:
            if func_name == pattern or func_name.endswith("." + pattern):
                result.dangerous.append((pattern, category, desc, node.lineno))

        for pattern, category, desc in NATIVE_PATTERNS:
            if func_name == pattern or func_name.endswith("." + pattern):
                result.dangerous.append((pattern, category, desc, node.lineno))

        if strict and isinstance(node.func, ast.Attribute) and node.func.attr in ("Popen", "run", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    result.dangerous.append((
                        f"subprocess.{node.func.attr}(shell=True)",
                        "subprocess",
                        f"subprocess.{node.func.attr}() shell=True ile çağrılmış",
                        node.lineno
                    ))

    deduped = []
    seen = set()
    for item in result.dangerous:
        key = (item[0], item[3])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    result.dangerous = deduped

    return result


def _get_full_func_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parts = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        else:
            return None
        return ".".join(reversed(parts))
    return None


def print_scan_report(result: ScanResult) -> None:
    from rich import print
    if result.errors:
        for err in result.errors:
            print(f"  [bold red]✗ Tarama hatası:[/bold red] {err}")
    for _pattern, _category, desc, lineno in result.dangerous:
        print(f"  [bold red]✗ {desc}[/bold red] (satır {lineno})")
