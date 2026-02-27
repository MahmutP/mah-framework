import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.module import BaseModule
from core.module_manager import ModuleManager
from core.shared_state import shared_state
import sys

# Test için geçici modüller
class ValidModule(BaseModule):
    Name = "Test Valid"
    Description = "A valid test module"
    Category = "test"
    Version = "1.0"
    Requirements = {"python": ["unittest"], "system": []}
    
    def run(self, options):
        return True

class MissingDepModule(BaseModule):
    Name = "Test Missing"
    Description = "Module with missing dependencies"
    Category = "test"
    Version = "1.0"
    Requirements = {"python": ["nonexistent_package_12345"], "system": ["nonexistent_command_12345"]}
    
    def run(self, options):
        return True

class TestModuleManager(unittest.TestCase):
    def setUp(self):
        self.manager = ModuleManager(modules_dir="tests/mock_modules")
        shared_state.module_manager = self.manager
        
        # Test modüllerini manuel olarak hafızaya ekle (Diskten okumamak için)
        self.valid_mod = ValidModule()
        self.valid_mod.Path = "test/valid"
        
        self.missing_mod = MissingDepModule()
        self.missing_mod.Path = "test/missing"
        
        self.manager.modules = {
            "test/valid": self.valid_mod,
            "test/missing": self.missing_mod
        }

    def test_dependency_check_success(self):
        """Bağımlılıkları tam olan modülün başarıyla çalışabilmesini (check_dependencies = True) doğrula."""
        self.assertTrue(self.valid_mod.check_dependencies())

    @patch('builtins.print')
    def test_dependency_check_fail(self, mock_print):
        """Eksik paket/komut olduğunda check_dependencies()'in False döndüğünü ve uyarı yazdırdığını doğrula."""
        self.assertFalse(self.missing_mod.check_dependencies())
        mock_print.assert_any_call("[Test Missing] Eksik Python paketleri: nonexistent_package_12345 (pip ile kurun)")
        mock_print.assert_any_call("[Test Missing] Eksik sistem araçları: nonexistent_command_12345 (apt/brew ile kurun)")

    @patch('core.module.BaseModule.check_dependencies')
    def test_run_module_dependency_block(self, mock_check_deps):
        """run_module metodunun bağımlılık eksikken çalışmayı reddettiğini doğrula."""
        mock_check_deps.return_value = False
        
        # modülü çalıştırdığımızda False dönmeli (dependency hatası)
        result = self.manager.run_module("test/missing")
        self.assertFalse(result)
        mock_check_deps.assert_called_once()
        
    @patch('core.module.BaseModule.check_dependencies')
    @patch('core.module.BaseModule.check_required_options')
    def test_run_module_dependency_pass(self, mock_check_options, mock_check_deps):
        """Bağımlılıklar ve seçenekler tamken run_module metodunun başarılı olduğunu doğrula."""
        mock_check_options.return_value = True
        mock_check_deps.return_value = True
        
        # Orijinal metodu mocklamak yerine dönüş değerinden true geldiğini kontrol edeceğiz.
        # Bizim sahte "ValidModule.run" metodumuz zaten True dönüyor.
        
        result = self.manager.run_module("test/valid")
        
        self.assertTrue(result)
        mock_check_deps.assert_called_once()
        mock_check_options.assert_called_once()

if __name__ == '__main__':
    unittest.main()
