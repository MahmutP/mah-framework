"""
Chimera Obfuscator - AST Tabanlı Python Kod Karıştırıcı

Üç katmanlı obfuscation pipeline:
    1. AST Rename   : Değişken, fonksiyon, sınıf ve parametre isimlerini
                      rastgele UUID-benzeri stringlerle değiştirir.
    2. String XOR   : Tüm string literallerini XOR ile şifreler; runtime'da
                      decode eden sarmalayıcı lambda ile değiştirir.
    3. Junk Code    : AV imza taramalarını yanıltmak için rastgele, anlamsız
                      ama sözdizimsel olarak geçerli Python blokları ekler.

Kullanım (generate.py içinden):
    from build.chimera_obfuscator import obfuscate

    obfuscated_code = obfuscate(source_code)
"""

import ast
import random
import string
import hashlib
import textwrap
from typing import Optional


# ============================================================
# Sabitler
# ============================================================

# Korunacak Python built-in ve anahtar kelimeler (rename edilmeyecek)
_PROTECTED_NAMES = frozenset({
    # Builtins
    "None", "True", "False", "print", "len", "range", "int", "str", "float",
    "bool", "list", "dict", "set", "tuple", "bytes", "bytearray", "type",
    "object", "super", "isinstance", "issubclass", "hasattr", "getattr",
    "setattr", "delattr", "callable", "iter", "next", "enumerate", "zip",
    "map", "filter", "sorted", "reversed", "min", "max", "sum", "abs",
    "round", "hash", "id", "repr", "format", "chr", "ord", "hex", "bin",
    "oct", "open", "input", "exit", "quit", "help", "dir", "vars", "globals",
    "locals", "exec", "eval", "compile", "importlib", "__import__",
    "staticmethod", "classmethod", "property", "any", "all", "divmod",
    "pow", "breakpoint", "memoryview", "slice", "complex",
    # Standard kwargs for built-ins
    "key", "reverse", "file", "flush", "end", "sep",
    # Sık kullanılan istisnalar
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "OSError", "IOError", "FileNotFoundError",
    "PermissionError", "TimeoutError", "ConnectionError", "ImportError",
    "StopIteration", "GeneratorExit", "SystemExit", "KeyboardInterrupt",
    "NotImplementedError", "OverflowError", "ZeroDivisionError",
    "MemoryError", "RecursionError", "UnicodeError", "UnicodeDecodeError",
    "UnicodeEncodeError", "BufferError",
    # Dunder metotlar ve özel adlar
    "__init__", "__new__", "__del__", "__repr__", "__str__", "__bytes__",
    "__format__", "__lt__", "__le__", "__eq__", "__ne__", "__gt__", "__ge__",
    "__hash__", "__bool__", "__getattr__", "__setattr__", "__delattr__",
    "__dir__", "__get__", "__set__", "__delete__", "__call__", "__len__",
    "__getitem__", "__setitem__", "__delitem__", "__iter__", "__next__",
    "__contains__", "__enter__", "__exit__", "__await__", "__aiter__",
    "__anext__", "__aenter__", "__aexit__", "__name__", "__file__",
    "__doc__", "__module__", "__class__", "__dict__", "__slots__",
    "__all__", "__version__", "__author__", "__builtins__", "__spec__",
    "__loader__", "__package__", "__cached__", "__annotations__",
    "__abstractmethods__", "__bases__", "__mro__", "__subclasses__",
    # Modül isimleri (sık import edilenler)
    "os", "sys", "re", "io", "time", "json", "ssl", "socket", "struct",
    "threading", "subprocess", "hashlib", "base64", "hmac", "ctypes",
    "platform", "select", "signal", "random", "string", "types", "ast",
    "inspect", "traceback", "logging", "pathlib", "collections", "itertools",
    "functools", "contextlib", "abc", "copy", "gc", "weakref", "textwrap",
    "shutil", "tempfile", "glob", "fnmatch", "errno", "stat",
    # Sık kullanılan metodlar / nitelikler
    "append", "extend", "insert", "remove", "pop", "clear", "copy", "update",
    "keys", "values", "items", "get", "setdefault", "read", "write", "close",
    "flush", "seek", "tell", "readline", "readlines", "split", "join",
    "strip", "lstrip", "rstrip", "replace", "find", "index", "count",
    "startswith", "endswith", "upper", "lower", "encode", "decode",
    "format", "send", "recv", "connect", "bind", "listen", "accept",
    "settimeout", "setblocking", "shutdown", "setsockopt", "getsockopt",
    "fileno", "makefile", "do_handshake", "wrap_socket", "start", "run",
    "join", "is_alive", "daemon", "target", "args", "kwargs",
    # Yaygın değişken isimleri (agent'a özgü, korunmalı)
    "self", "cls", "args", "kwargs",
})

# Junk kod şablonları (birbirinden bağımsız, yan etkisiz Python ifadeleri)
_JUNK_TEMPLATES = [
    # Matematik hesaplamalar
    "_{var} = (0x{h1} ^ 0x{h2}) + {n}",
    "_{var} = [{n} for _x in range({n2})]",
    "_{var} = abs({n} * {n2} - {n3})",
    "_{var} = '{s}'[::-1]",
    "_{var} = hash('{s}') & 0xFFFF",
    "_{var} = sum(range({n}))",
    "_{var} = len('{s}') * {n}",
    "_{var} = (lambda _f: _f(_f))((lambda _f: {n}))",
    "_{var} = '{s}'.encode().hex()",
    "_{var} = (True or False) and {n}",
    "_{var} = {n} if len('{s}') > {n2} else {n3}",
    "_{var} = round({n} / {n2}, {n3})",
]


# ============================================================
# Yardımcı Fonksiyonlar
# ============================================================

def _rand_name(prefix: str = "_", length: int = 12) -> str:
    """Rastgele, geçerli bir Python tanımlayıcısı üretir."""
    chars = string.ascii_letters + string.digits
    body = "".join(random.choices(chars, k=length))
    # İlk karakter rakam olamaz
    first = random.choice(string.ascii_letters)
    return prefix + first + body


def _rand_hex(n: int = 2) -> str:
    """n baytlık rastgele hex string döner (0x prefix yok)."""
    return "".join(random.choices("0123456789abcdef", k=n * 2))


def _xor_key() -> int:
    """1-254 arası rastgele XOR anahtarı döner."""
    return random.randint(1, 254)


def _xor_encrypt(text: str, key: int) -> list:
    """UTF-8 string'i XOR ile şifreler; byte listesi döner."""
    encoded = text.encode("utf-8")
    return [b ^ key for b in encoded]


def _make_junk_line() -> str:
    """Bir junk kod satırı üretir."""
    template = random.choice(_JUNK_TEMPLATES)
    var = _rand_name("", 6)
    n = random.randint(2, 999)
    n2 = random.randint(2, 99)
    n3 = random.randint(1, 9)
    s = "".join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
    h1 = _rand_hex(1)
    h2 = _rand_hex(1)
    return template.format(var=var, n=n, n2=n2, n3=n3, s=s, h1=h1, h2=h2)


# ============================================================
# Aşama 1: AST Rename (Tanımlayıcı İsim Değiştirme)
# ============================================================

class _NameCollector(ast.NodeVisitor):
    """Kaynak koddan yeniden adlandırılabilecek tüm tanımlayıcıları toplar."""

    def __init__(self):
        self.defined: set = set()

    def visit_FunctionDef(self, node):
        if not getattr(self, "in_class", False):
            if node.name not in _PROTECTED_NAMES and not node.name.startswith("__"):
                self.defined.add(node.name)
        # Parametreler
        for arg in node.args.args + getattr(node.args, 'posonlyargs', []) + node.args.kwonlyargs:
            if arg.arg not in _PROTECTED_NAMES and arg.arg != "self" and arg.arg != "cls":
                self.defined.add(arg.arg)
        if getattr(node.args, 'vararg', None) and node.args.vararg.arg not in _PROTECTED_NAMES:
            self.defined.add(node.args.vararg.arg)
        if getattr(node.args, 'kwarg', None) and node.args.kwarg.arg not in _PROTECTED_NAMES:
            self.defined.add(node.args.kwarg.arg)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        if node.name not in _PROTECTED_NAMES and not node.name.startswith("__"):
            self.defined.add(node.name)
        
        in_class_prev = getattr(self, "in_class", False)
        self.in_class = True
        self.generic_visit(node)
        self.in_class = in_class_prev

    def visit_Name(self, node):
        if (isinstance(node.ctx, ast.Store) and
                node.id not in _PROTECTED_NAMES and
                not node.id.startswith("__")):
            self.defined.add(node.id)
        self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            if name not in _PROTECTED_NAMES:
                self.defined.add(name)
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        for name in node.names:
            if name not in _PROTECTED_NAMES:
                self.defined.add(name)
        self.generic_visit(node)


class _NameRenamer(ast.NodeTransformer):
    """Toplanan tanımlayıcıları verilen mapping ile yeniden adlandırır."""

    def __init__(self, mapping: dict):
        self.mapping = mapping

    def visit_FunctionDef(self, node):
        if not getattr(self, "in_class", False):
            if node.name in self.mapping:
                node.name = self.mapping[node.name]
        for arg in node.args.args + getattr(node.args, 'posonlyargs', []) + node.args.kwonlyargs:
            if arg.arg in self.mapping:
                arg.arg = self.mapping[arg.arg]
        if getattr(node.args, 'vararg', None) and node.args.vararg.arg in self.mapping:
            node.args.vararg.arg = self.mapping[node.args.vararg.arg]
        if getattr(node.args, 'kwarg', None) and node.args.kwarg.arg in self.mapping:
            node.args.kwarg.arg = self.mapping[node.args.kwarg.arg]
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]

        in_class_prev = getattr(self, "in_class", False)
        self.in_class = True
        self.generic_visit(node)
        self.in_class = in_class_prev
        return node

    def visit_Name(self, node):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node

    def visit_Global(self, node):
        node.names = [self.mapping.get(n, n) for n in node.names]
        return node

    def visit_Nonlocal(self, node):
        node.names = [self.mapping.get(n, n) for n in node.names]
        return node

    def visit_Attribute(self, node):
        # Attribute erişimlerinde (.attr) sadece değeri değiştirme
        self.generic_visit(node)
        return node

    def visit_keyword(self, node):
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        self.generic_visit(node)
        return node


def _ast_rename(source: str, seed: Optional[int] = None) -> tuple:
    """
    Kaynak kodu parse edip tanımlayıcıları yeniden adlandırır.

    Returns:
        (obfuscated_source: str, mapping: dict)
    """
    if seed is not None:
        random.seed(seed)

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"[!] Kaynak kod parse edilemedi: {e}")

    # Koleksiyon
    collector = _NameCollector()
    collector.visit(tree)

    # Mapping oluştur
    mapping = {name: _rand_name("_O", 8) for name in collector.defined}

    # Uygula
    renamer = _NameRenamer(mapping)
    new_tree = renamer.visit(tree)
    ast.fix_missing_locations(new_tree)

    return ast.unparse(new_tree), mapping


# ============================================================
# Aşama 2: String XOR Şifreleme
# ============================================================

class _StringEncryptor(ast.NodeTransformer):
    """
    Kaynak koddaki string sabitlerini XOR ile şifreleyip
    runtime'da decode eden lambda ifadesiyle değiştirir.

    Örnek dönüşüm:
        "hello"
        ->
        (lambda _k, _d: bytes([_b ^ _k for _b in _d]).decode())
            (KEY, [ENCRYPTED_BYTES])
    """

    # Obfuscate edilmeyecek string desenleri (import isimleri, format spec vb.)
    _SKIP_PATTERNS = frozenset({
        "utf-8", "utf8", "latin-1", "ascii", "rb", "wb", "r", "w", "a",
        "rt", "wt", "utf-16",
    })

    def __init__(self):
        self.key = _xor_key()
        self.count = 0

    def visit_JoinedStr(self, node):
        # JoinedStr (f-string) içindeki dogrudan string literallerini senkronize bırak
        # Aksi taktirde AST icinde Call() unparse hatasi olusur
        new_values = []
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                new_values.append(self.visit(v))
            else:
                new_values.append(v)
        node.values = new_values
        return node

    def visit_Constant(self, node):
        # Sadece non-trivial string sabitleri
        if not isinstance(node.value, str):
            return node
        val = node.value
        if not val or len(val) < 2:
            return node
        if val in self._SKIP_PATTERNS:
            return node
        # Çok uzun string'leri atla (performans)
        if len(val) > 512:
            return node

        try:
            encrypted = _xor_encrypt(val, self.key)
        except Exception:
            return node

        self.count += 1
        # (lambda _k, _d: bytes([_b ^ _k for _b in _d]).decode('utf-8'))(KEY, [BYTES])
        key_node = ast.Constant(value=self.key)
        bytes_list = ast.List(
            elts=[ast.Constant(value=b) for b in encrypted],
            ctx=ast.Load()
        )

        lambda_node = ast.Lambda(
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="_k"), ast.arg(arg="_d")],
                vararg=None, kwonlyargs=[], kw_defaults=[],
                kwarg=None, defaults=[]
            ),
            body=ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Name(id="bytes", ctx=ast.Load()),
                        args=[ast.ListComp(
                            elt=ast.BinOp(
                                left=ast.Name(id="_b", ctx=ast.Load()),
                                op=ast.BitXor(),
                                right=ast.Name(id="_k", ctx=ast.Load())
                            ),
                            generators=[ast.comprehension(
                                target=ast.Name(id="_b", ctx=ast.Store()),
                                iter=ast.Name(id="_d", ctx=ast.Load()),
                                ifs=[], is_async=0
                            )]
                        )],
                        keywords=[]
                    ),
                    attr="decode",
                    ctx=ast.Load()
                ),
                args=[ast.Constant(value="utf-8")],
                keywords=[]
            )
        )

        call_node = ast.Call(
            func=lambda_node,
            args=[key_node, bytes_list],
            keywords=[]
        )
        return ast.copy_location(call_node, node)


def _encrypt_strings(source: str) -> tuple:
    """
    Kaynak koddaki string sabitlerini XOR ile şifreler.

    Returns:
        (obfuscated_source: str, count: int)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"[!] String şifreleme için parse hatası: {e}")

    encryptor = _StringEncryptor()
    new_tree = encryptor.visit(tree)
    ast.fix_missing_locations(new_tree)

    return ast.unparse(new_tree), encryptor.count


# ============================================================
# Aşama 3: Junk Code Enjeksiyonu
# ============================================================

def _inject_junk(source: str, density: float = 0.3) -> tuple:
    """
    Kaynak kodun satırlarına rastgele junk kod satırları ekler.
    Eklenen kodun syntax hatası oluşturmaması için doğrulamalı çoklu deneme yapar.

    Args:
        source:  Obfuscate edilecek Python kaynak kodu.
        density: Her N satırda bir junk satır ekleme olasılığı (0.0-1.0).

    Returns:
        (obfuscated_source: str, injected_count: int)
    """
    lines = source.split("\n")
    
    # Olası Syntax/Indentation hatalarına karşı 3 kez tekrar deneyebiliriz
    for attempt in range(3):
        result = []
        injected = 0
        in_multiline_string = False
        
        for line in lines:
            result.append(line)
            stripped = line.strip()
            
            # Basit çoklu satır string (docstring) takibi
            if stripped.count('"""') % 2 != 0 or stripped.count("'''") % 2 != 0:
                in_multiline_string = not in_multiline_string
                
            if in_multiline_string:
                continue

            # Bu karakterlerle biten veya başlayan satırların hemen altına kod eklemek risklidir
            is_unsafe = (
                stripped.endswith(":") or
                stripped.endswith("\\") or
                stripped.endswith(",") or
                stripped.endswith("(") or
                stripped.endswith("[") or
                stripped.endswith("{") or
                stripped.startswith("@") or
                stripped.startswith("elif ") or
                stripped.startswith("else:") or
                stripped.startswith("except ") or
                stripped.startswith("finally:") or
                '"""' in stripped or
                "'''" in stripped
            )

            if (stripped and
                    not stripped.startswith("#") and
                    not is_unsafe and
                    random.random() < density):
                    
                # Mevcut satırın girintisini al
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                junk = _make_junk_line()
                result.append(f"{indent_str}{junk}")
                injected += 1

        new_source = "\n".join(result)
        
        # Enjekte edilen kod parse edilebilir boyutta ve doğru mu kontrol et
        try:
            ast.parse(new_source)
            return new_source, injected
        except SyntaxError:
            # Hata varsa yoğunluğu düşür ve tekrar dene
            density /= 2

    # Tüm denemeler çalışmazsa, Junk eklenmeden doğrudan kendisini döndür
    return source, 0


# ============================================================
# Aşama 4: Control Flow Flattening (Kontrol Akışı Düzleştirme)
# ============================================================

class _ControlFlowFlattener(ast.NodeTransformer):
    """Fonksiyon gövdelerini state-machine benzeri while-switch yapısına dönüştürür.

    Basit (tek seviye, dallanmasız) fonksiyonlar için çalışır.
    Karmaşık kontrol akışları atlanır (try/except, nested if vb.).
    """

    def __init__(self):
        self.flattened_count = 0

    def _is_flattenable(self, body: list) -> bool:
        """Gövdenin düzleştirilebilir olup olmadığını kontrol eder."""
        if len(body) < 3:
            return False
        for node in body:
            if isinstance(node, (ast.Try, ast.With, ast.AsyncWith,
                                 ast.For, ast.AsyncFor, ast.While)):
                return False
        return True

    def visit_FunctionDef(self, node):
        self.generic_visit(node)

        if not self._is_flattenable(node.body):
            return node

        stmts = node.body
        if len(stmts) < 3:
            return node

        # State numaraları oluştur ve karıştır
        num_states = len(stmts)
        state_ids = list(range(num_states))
        random.shuffle(state_ids)

        # State -> statement mapping
        state_map = {}
        for i, stmt in enumerate(stmts):
            state_map[state_ids[i]] = stmt

        state_var = _rand_name("_s", 6)
        end_state = max(state_ids) + 1

        # Her state için: if state_var == X: <stmt>; state_var = next_state
        cases = []
        for idx in range(num_states):
            current_state = state_ids[idx]
            next_state = state_ids[idx + 1] if idx + 1 < num_states else end_state

            stmt = state_map[current_state]
            body_stmts = [stmt]

            if not isinstance(stmt, ast.Return):
                assign = ast.Assign(
                    targets=[ast.Name(id=state_var, ctx=ast.Store())],
                    value=ast.Constant(value=next_state),
                    lineno=0
                )
                body_stmts.append(assign)

            if_node = ast.If(
                test=ast.Compare(
                    left=ast.Name(id=state_var, ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=current_state)]
                ),
                body=body_stmts,
                orelse=[]
            )
            cases.append(if_node)

        # Sırayı karıştır
        random.shuffle(cases)

        # state_var = ilk_state
        init_assign = ast.Assign(
            targets=[ast.Name(id=state_var, ctx=ast.Store())],
            value=ast.Constant(value=state_ids[0]),
            lineno=0
        )

        # while state_var != end_state:
        while_node = ast.While(
            test=ast.Compare(
                left=ast.Name(id=state_var, ctx=ast.Load()),
                ops=[ast.NotEq()],
                comparators=[ast.Constant(value=end_state)]
            ),
            body=cases,
            orelse=[]
        )

        node.body = [init_assign, while_node]
        ast.fix_missing_locations(node)
        self.flattened_count += 1
        return node

    visit_AsyncFunctionDef = visit_FunctionDef


def _control_flow_flatten(source: str) -> tuple:
    """Fonksiyon gövdelerini state-machine yapısına dönüştürür.

    Returns:
        (obfuscated_source: str, flattened_count: int)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"[!] Control flow flatten parse hatası: {e}")

    flattener = _ControlFlowFlattener()
    new_tree = flattener.visit(tree)
    ast.fix_missing_locations(new_tree)

    return ast.unparse(new_tree), flattener.flattened_count


# ============================================================
# Aşama 5: Opaque Predicates (Opak Yüklemler)
# ============================================================

# Her zaman True olan matematiksel ifadeler
_OPAQUE_TRUE_TEMPLATES = [
    # (x * x) >= 0 her zaman True
    lambda var: ast.Compare(
        left=ast.BinOp(
            left=ast.Name(id=var, ctx=ast.Load()),
            op=ast.Mult(),
            right=ast.Name(id=var, ctx=ast.Load())
        ),
        ops=[ast.GtE()],
        comparators=[ast.Constant(value=0)]
    ),
    # (x | 1) != 0 her zaman True
    lambda var: ast.Compare(
        left=ast.BinOp(
            left=ast.Name(id=var, ctx=ast.Load()),
            op=ast.BitOr(),
            right=ast.Constant(value=1)
        ),
        ops=[ast.NotEq()],
        comparators=[ast.Constant(value=0)]
    ),
    # (x + 1) != x her zaman True
    lambda var: ast.Compare(
        left=ast.BinOp(
            left=ast.Name(id=var, ctx=ast.Load()),
            op=ast.Add(),
            right=ast.Constant(value=1)
        ),
        ops=[ast.NotEq()],
        comparators=[ast.Name(id=var, ctx=ast.Load())]
    ),
]


class _OpaquePredicateInjector(ast.NodeTransformer):
    """Opak yüklemler ekleyerek statik analizi zorlaştırır."""

    def __init__(self, density: float = 0.15):
        self.density = density
        self.injected_count = 0

    def _make_opaque_if(self, stmt):
        """Bir statement'ı opak yüklem ile sarar."""
        pred_var = _rand_name("_p", 6)
        pred_val = random.randint(2, 9999)

        assign = ast.Assign(
            targets=[ast.Name(id=pred_var, ctx=ast.Store())],
            value=ast.Constant(value=pred_val),
            lineno=0
        )

        template = random.choice(_OPAQUE_TRUE_TEMPLATES)
        test = template(pred_var)

        junk_var = _rand_name("_j", 6)
        fake_body = [ast.Assign(
            targets=[ast.Name(id=junk_var, ctx=ast.Store())],
            value=ast.Constant(value=random.randint(0, 9999)),
            lineno=0
        )]

        if_node = ast.If(
            test=test,
            body=[stmt],
            orelse=fake_body
        )

        self.injected_count += 1
        return [assign, if_node]

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        new_body = []
        for stmt in node.body:
            if (isinstance(stmt, (ast.Assign, ast.Expr, ast.AugAssign)) and
                    random.random() < self.density):
                new_body.extend(self._make_opaque_if(stmt))
            else:
                new_body.append(stmt)
        node.body = new_body
        return node

    visit_AsyncFunctionDef = visit_FunctionDef


def _inject_opaque_predicates(source: str, density: float = 0.15) -> tuple:
    """Opak yüklemler ekler.

    Returns:
        (obfuscated_source: str, injected_count: int)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"[!] Opaque predicate parse hatası: {e}")

    injector = _OpaquePredicateInjector(density=density)
    new_tree = injector.visit(tree)
    ast.fix_missing_locations(new_tree)

    try:
        result = ast.unparse(new_tree)
        ast.parse(result)
        return result, injector.injected_count
    except SyntaxError:
        return source, 0


# ============================================================
# Aşama 6: Dead Code Insertion (Ölü Kod Enjeksiyonu)
# ============================================================

_DEAD_FUNC_TEMPLATES = [
    'def {name}({p1}, {p2}):\n    {v1} = {p1} + {p2}\n    {v2} = [{p1}] * {n1}\n    for {v3} in range({n2}):\n        {v1} += {v3}\n    return {v1}',

    'def {name}({p1}):\n    {v1} = str({p1})\n    {v2} = {v1}[::-1]\n    return len({v2}) * {n1}',

    'def {name}({p1}, {p2}={n1}):\n    if {p1} > {p2}:\n        return {p1} - {p2}\n    return {p2} - {p1}',

    'class {name}:\n    def __init__(self):\n        self.{v1} = {n1}\n        self.{v2} = \"{s1}\"\n    def {v3}(self):\n        return self.{v1} * {n2}',
]


def _generate_dead_code_block() -> str:
    """Rastgele bir ölü kod bloğu üretir."""
    template = random.choice(_DEAD_FUNC_TEMPLATES)
    return template.format(
        name=_rand_name("_D", 8),
        p1=_rand_name("_a", 4),
        p2=_rand_name("_b", 4),
        v1=_rand_name("_v", 4),
        v2=_rand_name("_w", 4),
        v3=_rand_name("_x", 4),
        n1=random.randint(2, 999),
        n2=random.randint(2, 99),
        s1="".join(random.choices(string.ascii_lowercase, k=random.randint(5, 12))),
    )


def _inject_dead_code(source: str, count: int = 5) -> tuple:
    """Kaynak koda ölü (erişilmeyen) fonksiyon ve sınıf tanımları ekler.

    Args:
        source: Python kaynak kodu.
        count:  Eklenecek ölü blok sayısı.

    Returns:
        (obfuscated_source: str, injected_count: int)
    """
    dead_blocks = []
    for _ in range(count):
        block = _generate_dead_code_block()
        try:
            ast.parse(block)
            dead_blocks.append(block)
        except SyntaxError:
            continue

    if not dead_blocks:
        return source, 0

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0

    new_body = list(tree.body)
    inserted = 0
    for block_src in dead_blocks:
        try:
            block_tree = ast.parse(block_src)
            min_pos = 0
            for i, node in enumerate(new_body):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    min_pos = i + 1
            pos = random.randint(min_pos, len(new_body))
            for stmt in reversed(block_tree.body):
                new_body.insert(pos, stmt)
            inserted += 1
        except Exception:
            continue

    tree.body = new_body
    ast.fix_missing_locations(tree)

    try:
        result = ast.unparse(tree)
        ast.parse(result)
        return result, inserted
    except SyntaxError:
        return source, 0


# ============================================================
# Ana Pipeline
# ============================================================

def obfuscate(
    source: str,
    rename: bool = True,
    encrypt_strings: bool = True,
    inject_junk: bool = True,
    junk_density: float = 0.25,
    control_flow_flatten: bool = False,
    opaque_predicates: bool = False,
    dead_code: bool = False,
    dead_code_count: int = 5,
    seed: Optional[int] = None,
) -> dict:
    """
    Chimera agent kaynak koduna çok katmanlı obfuscation uygular.

    Args:
        source:                Ham Python kaynak kodu.
        rename:                AST rename aşamasını çalıştır.
        encrypt_strings:       String XOR şifreleme aşamasını çalıştır.
        inject_junk:           Junk code enjeksiyonunu çalıştır.
        junk_density:          Junk satır ekleme yoğunluğu (0.0-1.0).
        control_flow_flatten:  Kontrol akışı düzleştirmeyi çalıştır.
        opaque_predicates:     Opak yüklem enjeksiyonunu çalıştır.
        dead_code:             Ölü kod enjeksiyonunu çalıştır.
        dead_code_count:       Eklenecek ölü kod bloğu sayısı.
        seed:                  Tekrarlanabilir sonuçlar için RNG seed.

    Returns:
        dict:
            - success (bool)          : İşlem başarılı mı?
            - code (str)              : Obfuscate edilmiş kod.
            - error (str|None)        : Hata mesajı (varsa).
            - stats (dict)            : Ayrıntılı istatistikler.
    """
    if seed is not None:
        random.seed(seed)

    stats = {
        "original_lines": source.count("\n") + 1,
        "original_size": len(source.encode("utf-8")),
        "renamed_identifiers": 0,
        "encrypted_strings": 0,
        "injected_junk_lines": 0,
        "flattened_functions": 0,
        "opaque_predicates": 0,
        "dead_code_blocks": 0,
        "final_lines": 0,
        "final_size": 0,
    }

    result = {
        "success": False,
        "code": source,
        "error": None,
        "stats": stats,
    }

    current = source

    # --- Aşama 1: AST Rename ---
    if rename:
        try:
            current, mapping = _ast_rename(current, seed=seed)
            stats["renamed_identifiers"] = len(mapping)
        except Exception as e:
            result["error"] = f"[!] AST rename hatası: {e}"
            return result

    # --- Aşama 2: String Şifreleme ---
    if encrypt_strings:
        try:
            current, enc_count = _encrypt_strings(current)
            stats["encrypted_strings"] = enc_count
        except Exception as e:
            result["error"] = f"[!] String şifreleme hatası: {e}"
            return result

    # --- Aşama 3: Junk Code Enjeksiyonu ---
    if inject_junk:
        current, junk_count = _inject_junk(current, density=junk_density)
        stats["injected_junk_lines"] = junk_count

    # --- Aşama 4: Control Flow Flattening ---
    if control_flow_flatten:
        try:
            current, flat_count = _control_flow_flatten(current)
            stats["flattened_functions"] = flat_count
        except Exception as e:
            result["error"] = f"[!] Control flow flatten hatası: {e}"
            return result

    # --- Aşama 5: Opaque Predicates ---
    if opaque_predicates:
        try:
            current, opaque_count = _inject_opaque_predicates(current)
            stats["opaque_predicates"] = opaque_count
        except Exception as e:
            result["error"] = f"[!] Opaque predicate hatası: {e}"
            return result

    # --- Aşama 6: Dead Code Insertion ---
    if dead_code:
        try:
            current, dc_count = _inject_dead_code(current, count=dead_code_count)
            stats["dead_code_blocks"] = dc_count
        except Exception as e:
            result["error"] = f"[!] Dead code insertion hatası: {e}"
            return result

    stats["final_lines"] = current.count("\n") + 1
    stats["final_size"] = len(current.encode("utf-8"))

    result["success"] = True
    result["code"] = current
    return result


# ============================================================
# Obfuscation Raporu
# ============================================================

def print_obfuscation_report(result: dict):
    """Obfuscation sonuç raporunu ekrana basar."""
    if not result["success"]:
        print(f"\n  {result['error']}\n")
        return

    s = result["stats"]
    border = "═" * 58

    size_reduction = s["original_size"] - s["final_size"]
    size_pct = (size_reduction / s["original_size"] * 100) if s["original_size"] > 0 else 0
    line_growth = s["final_lines"] - s["original_lines"]

    print(f"\n  ╔{border}╗")
    print(f"  ║  🔀  CHIMERA OBFUSCATOR - Obfuscation Raporu          ║")
    print(f"  ╠{border}╣")
    print(f"  ║  Durum           : ✅ Başarılı                        ║")
    print(f"  ╠{border}╣")
    print(f"  ║  📊 İstatistikler                                     ║")
    print(f"  ║  ├─ Rename edilen tanımlayıcı : {str(s['renamed_identifiers']):<25}║")
    print(f"  ║  ├─ Şifrelenen string         : {str(s['encrypted_strings']):<25}║")
    print(f"  ║  ├─ Eklenen junk satır        : {str(s['injected_junk_lines']):<25}║")
    print(f"  ║  ├─ Düzleştirilen fonksiyon   : {str(s.get('flattened_functions', 0)):<25}║")
    print(f"  ║  ├─ Opak yüklem               : {str(s.get('opaque_predicates', 0)):<25}║")
    print(f"  ║  ├─ Ölü kod bloğu             : {str(s.get('dead_code_blocks', 0)):<25}║")
    print(f"  ╠{border}╣")
    print(f"  ║  📦 Boyut Bilgisi                                     ║")
    orig_str = f"{s['original_size']:,} B / {s['original_lines']} satır"
    print(f"  ║  ├─ Orijinal  : {orig_str:<41}║")
    final_str = f"{s['final_size']:,} B / {s['final_lines']} satır"
    print(f"  ║  ├─ Sonuç     : {final_str:<41}║")
    growth_str = f"+{line_growth} satır"
    print(f"  ║  └─ Büyüme    : {growth_str:<41}║")
    print(f"  ╚{border}╝\n")
