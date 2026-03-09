"""
Chimera Evasion Techniques - Unit Tests
Obfuscator pipeline iyileştirmeleri, polimorfik engine,
sleep obfuscation ve sandbox tespit güncellemelerini test eder.
"""
import unittest
import ast
import sys
import os
import time
import random
import types
from unittest.mock import MagicMock, patch

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# Obfuscator Pipeline Testleri (Yeni aşamalar)
# ============================================================

class TestControlFlowFlattening(unittest.TestCase):
    """Control flow flattening testleri."""

    def setUp(self):
        from build.chimera_obfuscator import obfuscate
        self.obfuscate = obfuscate

    def test_flattening_produces_valid_python(self):
        """Düzleştirilen kod geçerli Python çıktısı verir."""
        code = '''
def compute(a, b):
    x = a + b
    y = x * 2
    z = y - a
    return z
'''
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            control_flow_flatten=True, seed=42
        )
        self.assertTrue(result["success"])
        # Geçerli Python olmalı
        compile(result["code"], "<test>", "exec")

    def test_flattening_preserves_functionality(self):
        """Düzleştirilen kod orijinalle aynı sonucu verir."""
        code = '''
def add(a, b):
    result = a + b
    doubled = result * 2
    final = doubled + 1
    return final
'''
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            control_flow_flatten=True, seed=42
        )
        self.assertTrue(result["success"])

        # Orijinal sonuç
        ns_orig = {}
        exec(code, ns_orig)
        orig_val = ns_orig["add"](3, 4)

        # Obfuscate sonuç
        ns_obf = {}
        exec(result["code"], ns_obf)
        obf_val = ns_obf["add"](3, 4)

        self.assertEqual(orig_val, obf_val)

    def test_flattening_count_in_stats(self):
        """İstatistiklerde düzleştirilen fonksiyon sayısı görünür."""
        code = '''
def f1(x):
    a = x + 1
    b = a + 2
    c = b + 3
    return c

def f2(y):
    d = y * 2
    e = d * 3
    f = e * 4
    return f
'''
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            control_flow_flatten=True, seed=42
        )
        self.assertTrue(result["success"])
        self.assertGreater(result["stats"]["flattened_functions"], 0)


class TestOpaquePredicates(unittest.TestCase):
    """Opaque predicate testleri."""

    def setUp(self):
        from build.chimera_obfuscator import obfuscate
        self.obfuscate = obfuscate

    def test_opaque_predicates_produce_valid_python(self):
        """Opak yüklemler eklenen kod geçerli Python çıktısı verir."""
        code = '''
def process(data):
    result = data + 10
    extra = result * 2
    return extra
'''
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            opaque_predicates=True, seed=42
        )
        self.assertTrue(result["success"])
        compile(result["code"], "<test>", "exec")

    def test_opaque_predicates_preserve_functionality(self):
        """Opak yüklemler fonksiyon davranışını değiştirmez."""
        code = '''
def calc(x):
    a = x * 3
    b = a + 5
    return b
'''
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            opaque_predicates=True, seed=42
        )
        self.assertTrue(result["success"])

        ns_orig = {}
        exec(code, ns_orig)

        ns_obf = {}
        exec(result["code"], ns_obf)

        for val in [0, 1, 5, 10, -3]:
            self.assertEqual(ns_orig["calc"](val), ns_obf["calc"](val))


class TestDeadCodeInsertion(unittest.TestCase):
    """Dead code insertion testleri."""

    def setUp(self):
        from build.chimera_obfuscator import obfuscate
        self.obfuscate = obfuscate

    def test_dead_code_increases_size(self):
        """Ölü kod eklenmesi toplam boyutu artırır."""
        code = 'x = 1\ny = 2\nz = x + y\n'
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            dead_code=True, dead_code_count=3, seed=42
        )
        self.assertTrue(result["success"])
        self.assertGreater(result["stats"]["dead_code_blocks"], 0)
        self.assertGreater(result["stats"]["final_size"], result["stats"]["original_size"])

    def test_dead_code_valid_python(self):
        """Ölü kod eklenmiş çıktı geçerli Python."""
        code = 'print("hello")\n'
        result = self.obfuscate(
            code, rename=False, encrypt_strings=False, inject_junk=False,
            dead_code=True, dead_code_count=5, seed=42
        )
        self.assertTrue(result["success"])
        compile(result["code"], "<test>", "exec")


class TestFullPipeline(unittest.TestCase):
    """Tüm pipeline'ın birlikte çalışmasını test eder."""

    def setUp(self):
        from build.chimera_obfuscator import obfuscate
        self.obfuscate = obfuscate

    def test_all_stages_combined(self):
        """Tüm 6 aşama birlikte çalışır ve geçerli Python üretir."""
        code = '''
def greet(name):
    msg = "Hello " + name
    marker = "test_marker"
    value = len(msg) * 2
    return msg

result = greet("world")
'''
        result = self.obfuscate(
            code,
            rename=True,
            encrypt_strings=True,
            inject_junk=True,
            control_flow_flatten=True,
            opaque_predicates=True,
            dead_code=True,
            seed=42
        )
        self.assertTrue(result["success"], f"Hata: {result.get('error')}")
        compile(result["code"], "<test>", "exec")

    def test_backward_compatibility(self):
        """Eski parametrelerle (sadece 3 aşama) çalışmaya devam eder."""
        code = 'x = "test"\nprint(x)\n'
        result = self.obfuscate(code, seed=42)  # Varsayılan: rename+strings+junk
        self.assertTrue(result["success"])
        compile(result["code"], "<test>", "exec")


# ============================================================
# Polimorfik Engine Testleri
# ============================================================

class TestPolymorphicEngine(unittest.TestCase):
    """Polimorfik payload engine testleri."""

    def setUp(self):
        from build.chimera_polymorphic import polymorphic_wrap
        self.polymorphic_wrap = polymorphic_wrap

    def test_different_seeds_different_output(self):
        """Farklı seed'lerle farklı çıktı üretilir."""
        code = 'import os\nimport sys\nprint("test")\n'
        r1 = self.polymorphic_wrap(code, seed=1)
        r2 = self.polymorphic_wrap(code, seed=2)
        self.assertTrue(r1["success"])
        self.assertTrue(r2["success"])
        self.assertNotEqual(r1["code"], r2["code"])

    def test_output_valid_python(self):
        """Polimorfik çıktı geçerli Python kodu."""
        code = 'x = 42\nprint(x)\n'
        result = self.polymorphic_wrap(code, seed=42)
        self.assertTrue(result["success"])
        compile(result["code"], "<test>", "exec")

    def test_output_executes_correctly(self):
        """Polimorfik çıktı doğru çalışır."""
        code = 'POLY_RESULT = 42\n'
        result = self.polymorphic_wrap(code, seed=42)
        self.assertTrue(result["success"])
        # Exec ile çalıştır - hata fırlatmamalı
        exec(result["code"])

    def test_mutations_list_populated(self):
        """Uygulanan mutasyonlar listelenir."""
        code = 'import os\nimport sys\nprint("test")\n'
        result = self.polymorphic_wrap(code, seed=42)
        self.assertTrue(result["success"])
        self.assertGreater(len(result["mutations"]), 0)

    def test_no_mutations_when_disabled(self):
        """Tüm mutasyonlar kapalıyken mutasyon uygulanmaz."""
        code = 'x = 1\n'
        result = self.polymorphic_wrap(
            code, seed=42,
            shuffle_imports=False,
            shuffle_defs=False,
            encoding_wrapper=False,
            decoy_metadata=False,
            entry_stub=False
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["mutations"]), 0)
        self.assertEqual(result["code"], code)

    def test_import_shuffle(self):
        """Import sırasını karıştırma çalışır."""
        code = 'import os\nimport sys\nimport time\nimport json\nprint("ok")\n'
        # Birden fazla kez çalıştırıp farklı sıra olup olmadığını kontrol et
        results = set()
        for seed in range(5):
            r = self.polymorphic_wrap(
                code, seed=seed,
                shuffle_imports=True,
                shuffle_defs=False,
                encoding_wrapper=False,
                decoy_metadata=False
            )
            if r["success"]:
                results.add(r["code"])
        # En az 2 farklı çıktı olmalı
        self.assertGreater(len(results), 1)


# ============================================================
# Sleep Obfuscation Testleri
# ============================================================

class TestSleepObfuscation(unittest.TestCase):
    """Sleep obfuscation testleri (Agent sınıfı üzerinden)."""

    @classmethod
    def setUpClass(cls):
        """Agent sınıfını yükle."""
        from modules.payloads.python.chimera.generate import Payload
        gen = Payload()
        gen.set_option_value("LHOST", "127.0.0.1")
        gen.set_option_value("LPORT", 9999)
        code = gen.generate()["code"]
        module = types.ModuleType("chimera_evasion_test")
        exec(compile(code, "<chimera_agent>", "exec"), module.__dict__)
        cls.AgentClass = module.ChimeraAgent

    def setUp(self):
        self.agent = self.AgentClass("127.0.0.1", 9999)

    def test_xor_memory_encrypt_decrypt(self):
        """XOR şifreleme ve çözme geri dönüşümlü."""
        data = b"Hello, World! This is sensitive data."
        key = b"secret_key_12345"
        encrypted = self.agent._xor_memory(data, key)
        decrypted = self.agent._xor_memory(encrypted, key)
        self.assertEqual(data, decrypted)
        self.assertNotEqual(data, encrypted)

    def test_xor_memory_different_keys(self):
        """Farklı anahtarlar farklı şifreli çıktı verir."""
        data = b"test data"
        key1 = b"key_one"
        key2 = b"key_two"
        enc1 = self.agent._xor_memory(data, key1)
        enc2 = self.agent._xor_memory(data, key2)
        self.assertNotEqual(enc1, enc2)

    def test_generate_sleep_key_length(self):
        """Anahtar üretimi doğru uzunlukta."""
        key = self.agent._generate_sleep_key(16)
        self.assertEqual(len(key), 16)
        key32 = self.agent._generate_sleep_key(32)
        self.assertEqual(len(key32), 32)

    def test_generate_sleep_key_random(self):
        """Her anahtar farklı."""
        k1 = self.agent._generate_sleep_key()
        k2 = self.agent._generate_sleep_key()
        self.assertNotEqual(k1, k2)

    def test_encrypt_decrypt_sensitive_attrs(self):
        """Hassas öznitelikler şifrelendikten sonra geri çözülür."""
        original_host = self.agent.host
        original_port = self.agent.port
        
        key = self.agent._generate_sleep_key()
        backup = self.agent._encrypt_sensitive_attrs(key)
        
        # Şifreleme sonrası değişmeli
        self.assertNotEqual(self.agent.host, original_host)
        
        # Çözme
        self.agent._decrypt_sensitive_attrs(key, backup)
        self.assertEqual(self.agent.host, original_host)
        self.assertEqual(self.agent.port, original_port)

    def test_sleep_obfuscated_duration(self):
        """_sleep_obfuscated yaklaşık doğru süre uyur (jitter dahil)."""
        duration = 0.3
        t_start = time.time()
        self.agent._sleep_obfuscated(duration)
        elapsed = time.time() - t_start
        
        # Jitter ±15% + küçük overhead ile uyumlu olmalı
        self.assertGreater(elapsed, duration * 0.80)
        self.assertLess(elapsed, duration * 1.25)

    def test_sleep_obfuscated_preserves_attrs(self):
        """_sleep_obfuscated uyku sonrası öznitelikleri korur."""
        original_host = self.agent.host
        original_port = self.agent.port
        
        self.agent._sleep_obfuscated(0.1)
        
        self.assertEqual(self.agent.host, original_host)
        self.assertEqual(self.agent.port, original_port)


# ============================================================
# Sandbox Tespit Testleri
# ============================================================

class TestSandboxDetection(unittest.TestCase):
    """Geliştirilmiş sandbox tespit testleri."""

    @classmethod
    def setUpClass(cls):
        """Agent sınıfını yükle."""
        from modules.payloads.python.chimera.generate import Payload
        gen = Payload()
        gen.set_option_value("LHOST", "127.0.0.1")
        gen.set_option_value("LPORT", 9999)
        code = gen.generate()["code"]
        module = types.ModuleType("chimera_sandbox_test")
        exec(compile(code, "<chimera_agent>", "exec"), module.__dict__)
        cls.AgentClass = module.ChimeraAgent

    def setUp(self):
        self.agent = self.AgentClass("127.0.0.1", 9999)

    def test_detect_virtualization_returns_dict(self):
        """detect_virtualization dict döner."""
        result = self.agent.detect_virtualization()
        self.assertIsInstance(result, dict)
        self.assertIn("is_virtualized", result)
        self.assertIn("vm_indicators", result)
        self.assertIn("confidence", result)

    def test_detect_virtualization_confidence_values(self):
        """Confidence değeri geçerli bir string."""
        result = self.agent.detect_virtualization()
        self.assertIn(result["confidence"], ["low", "medium", "high"])

    def test_detect_environment_precheck_returns_bool(self):
        """detect_environment_precheck bool döner."""
        result = self.agent.detect_environment_precheck()
        self.assertIsInstance(result, bool)

    def test_detect_environment_returns_string(self):
        """detect_environment formatlanmış string döner."""
        result = self.agent.detect_environment()
        self.assertIsInstance(result, str)
        self.assertIn("ORTAM", result)
        self.assertIn("Risk", result)


# ============================================================
# Builder Entegrasyon Testleri
# ============================================================

class TestBuilderIntegration(unittest.TestCase):
    """Builder'ın yeni parametreleri doğru geçirip geçirmediğini test eder."""

    def test_builder_accepts_polymorphic_param(self):
        """build_payload polymorphic parametresini kabul eder."""
        from build.chimera_builder import build_payload
        # Sadece parametre kabul edildiğini kontrol et (LHOST yoksa hata verir ama
        # parametre hatasından farklı)
        result = build_payload(
            lhost="127.0.0.1",
            lport=4444,
            polymorphic=True,
            quiet=True
        )
        # Builder'ın polymorphic_mutations anahtarı içermesi
        self.assertIn("polymorphic_mutations", result)

    def test_generate_module_has_polymorphic_option(self):
        """Generate modülü POLYMORPHIC option'ına sahip."""
        from modules.payloads.python.chimera.generate import Payload
        gen = Payload()
        self.assertIn("POLYMORPHIC", gen.Options)


if __name__ == "__main__":
    unittest.main()
