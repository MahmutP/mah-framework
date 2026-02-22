"""
Chimera In-Memory Module Loading Tests
Agent'ın modül yükleme ve çalıştırma yeteneklerini test eder.
"""
import unittest
import base64
import sys
import os
import types
from unittest.mock import MagicMock, patch

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def _load_chimera_agent_class():
    """chimera agent sınıfını yükle"""
    from modules.payloads.python.chimera.generate import Payload
    gen = Payload()
    gen.set_option_value("LHOST", "127.0.0.1")
    gen.set_option_value("LPORT", 9999)
    code = gen.generate()["code"]
    
    module = types.ModuleType("chimera_agent_test")
    exec(compile(code, "<chimera_agent>", "exec"), module.__dict__)
    return module.ChimeraAgent

ChimeraAgent = _load_chimera_agent_class()


@unittest.skip("Bu özellik (In-Memory Module Loading) henüz implement edilmedi.")
class TestModuleLoading(unittest.TestCase):
    """In-Memory Module Loading testleri"""
    
    def setUp(self):
        self.agent = ChimeraAgent("127.0.0.1", 9999)
    
    def test_loadmodule_basic(self):
        """Basit bir modül yükleme testi"""
        # Test modülü
        test_code = """
def hello():
    return "Hello from module!"

def add(a, b):
    return a + b
"""
        encoded = base64.b64encode(test_code.encode()).decode()
        cmd = f"loadmodule testmod {encoded}"
        
        result = self.agent.execute_command(cmd)
        
        self.assertIn("başarıyla yüklendi", result)
        self.assertIn("testmod", self.agent.loaded_modules)
    
    def test_loadmodule_invalid_base64(self):
        """Geçersiz base64 ile hata kontrolü"""
        cmd = "loadmodule badmod invalid_base64!!!"
        result = self.agent.execute_command(cmd)
        
        self.assertIn("Base64 decode hatası", result)
    
    def test_loadmodule_syntax_error(self):
        """Syntax hatası olan modül yükleme"""
        bad_code = "def broken(\n    return 'oops'"
        encoded = base64.b64encode(bad_code.encode()).decode()
        cmd = f"loadmodule broken {encoded}"
        
        result = self.agent.execute_command(cmd)
        
        self.assertIn("Modül yükleme hatası", result)
    
    def test_runmodule_success(self):
        """Yüklenmiş modülün fonksiyonunu çalıştırma"""
        # Önce modülü yükle
        test_code = """
def greet(name):
    return f"Merhaba, {name}!"
"""
        encoded = base64.b64encode(test_code.encode()).decode()
        self.agent.execute_command(f"loadmodule greeter {encoded}")
        
        # Fonksiyonu çalıştır
        result = self.agent.execute_command("runmodule greeter greet Chimera")
        
        self.assertIn("Sonuç:", result)
        self.assertIn("Merhaba, Chimera!", result)
    
    def test_runmodule_module_not_loaded(self):
        """Yüklenmemiş modül çalıştırma hatası"""
        result = self.agent.execute_command("runmodule nonexistent func")
        
        self.assertIn("yüklü değil", result)
    
    def test_runmodule_function_not_found(self):
        """Modülde olmayan fonksiyon çağırma"""
        test_code = "def foo(): return 'bar'"
        encoded = base64.b64encode(test_code.encode()).decode()
        self.agent.execute_command(f"loadmodule testmod {encoded}")
        
        result = self.agent.execute_command("runmodule testmod nonexistent")
        
        self.assertIn("fonksiyonu bulunamadı", result)
    
    def test_listmodules_empty(self):
        """Hiç modül yüklenmemişken listele"""
        result = self.agent.execute_command("listmodules")
        
        self.assertIn("Yüklenmiş modül yok", result)
    
    def test_listmodules_with_modules(self):
        """Modüller yüklendiğinde listele"""
        # İki modül yükle
        code1 = "def func1(): pass\ndef func2(): pass"
        code2 = "def helper(): pass"
        
        enc1 = base64.b64encode(code1.encode()).decode()
        enc2 = base64.b64encode(code2.encode()).decode()
        
        self.agent.execute_command(f"loadmodule mod1 {enc1}")
        self.agent.execute_command(f"loadmodule mod2 {enc2}")
        
        result = self.agent.execute_command("listmodules")
        
        self.assertIn("Yüklenmiş modüller:", result)
        self.assertIn("mod1", result)
        self.assertIn("mod2", result)
        self.assertIn("func1", result)
        self.assertIn("func2", result)
        self.assertIn("helper", result)
    
    def test_module_isolation(self):
        """Modüller birbirinden izole olmalı"""
        code1 = "x = 10\ndef get_x(): return x"
        code2 = "x = 20\ndef get_x(): return x"
        
        enc1 = base64.b64encode(code1.encode()).decode()
        enc2 = base64.b64encode(code2.encode()).decode()
        
        self.agent.execute_command(f"loadmodule mod1 {enc1}")
        self.agent.execute_command(f"loadmodule mod2 {enc2}")
        
        result1 = self.agent.execute_command("runmodule mod1 get_x")
        result2 = self.agent.execute_command("runmodule mod2 get_x")
        
        self.assertIn("10", result1)
        self.assertIn("20", result2)
    
    def test_module_can_import_stdlib(self):
        """Modül içinden stdlib import edilebilmeli"""
        code = """
import os
import platform

def get_info():
    return f"{platform.system()} - PID: {os.getpid()}"
"""
        encoded = base64.b64encode(code.encode()).decode()
        self.agent.execute_command(f"loadmodule sysinfo {encoded}")
        
        result = self.agent.execute_command("runmodule sysinfo get_info")
        
        self.assertIn("Sonuç:", result)
        self.assertIn("PID:", result)


if __name__ == "__main__":
    unittest.main()
