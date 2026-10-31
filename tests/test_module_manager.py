import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.module import BaseModule
from core.module_manager import ModuleManager
from core.shared_state import shared_state


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
    Requirements = {
        "python": ["nonexistent_package_12345"],
        "system": ["nonexistent_command_12345"],
    }

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
            "test/missing": self.missing_mod,
        }

    def test_dependency_check_success(self):
        """Bağımlılıkları tam olan modülün başarıyla çalışabilmesini (check_dependencies = True) doğrula."""
        self.assertTrue(self.valid_mod.check_dependencies())

    @patch("builtins.print")
    def test_dependency_check_fail(self, mock_print):
        """Eksik paket/komut olduğunda check_dependencies()'in False döndüğünü ve uyarı yazdırdığını doğrula."""
        self.assertFalse(self.missing_mod.check_dependencies())
        mock_print.assert_any_call(
            "[Test Missing] Eksik Python paketleri: nonexistent_package_12345 (pip ile kurun)"
        )
        mock_print.assert_any_call(
            "[Test Missing] Eksik sistem araçları: nonexistent_command_12345 (apt/brew ile kurun)"
        )

    @patch("core.module.BaseModule.check_dependencies")
    def test_run_module_dependency_block(self, mock_check_deps):
        """run_module metodunun bağımlılık eksikken çalışmayı reddettiğini doğrula."""
        mock_check_deps.return_value = False

        # modülü çalıştırdığımızda False dönmeli (dependency hatası)
        result = self.manager.run_module("test/missing")
        self.assertFalse(result)
        mock_check_deps.assert_called_once()

    @patch("core.module.BaseModule.check_dependencies")
    @patch("core.module.BaseModule.check_required_options")
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


MODULE_TEMPLATE = '''from core.module import BaseModule


class Payload(BaseModule):
    Name = "{name}"
    Description = "{description}"
    Category = "payloads"

    def run(self, options):
        return True
'''

BROKEN_MODULE = '''from core.module import BaseModule

raise RuntimeError("import sırasında patlıyor")


class Payload(BaseModule):
    Name = "broken"
    Description = "Bozuk modül"
    Category = "payloads"

    def run(self, options):
        return True
'''


class TestModuleCatalogRefresh(unittest.TestCase):
    """Katalog tam listelenmeli: yeni modüller tespit edilmeli, yüklenemeyen
    modüller listeden düşmemeli."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.manager = ModuleManager(
            modules_dir=str(self.root),
            manifest_path=self.root / "manifest.json",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _write_module(self, relative: str, name: str, description: str) -> Path:
        file_path = self.root / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            MODULE_TEMPLATE.format(name=name, description=description),
            encoding="utf-8",
        )
        return file_path

    def test_refresh_detects_new_module(self):
        """Çalışma sırasında eklenen modül refresh_modules ile listeye girmeli."""
        self._write_module("payloads/python/chimera/generate.py", "chimera", "Chimera")
        self.manager.load_modules()
        self.assertIn("payloads/python/chimera/generate", self.manager.modules)

        self._write_module("payloads/python/yeni/generate.py", "yeni", "Yeni payload")
        changes = self.manager.refresh_modules()

        self.assertIn("payloads/python/yeni/generate", changes["added"])
        self.assertIn("payloads/python/yeni/generate", self.manager.modules)
        # Kategori listesinde ve completer cache'inde de görünmeli
        payloads = self.manager.get_modules_by_category()["Payloads"]
        self.assertIn("payloads/python/yeni/generate", payloads)
        self.assertIn("payloads/python/yeni/generate", self.manager.get_module_paths())

    def test_refresh_detects_removed_module(self):
        """Silinen modül katalogdan çıkarılmalı."""
        module_file = self._write_module(
            "payloads/python/chimera/generate.py", "chimera", "Chimera"
        )
        self.manager.load_modules()
        module_file.unlink()

        changes = self.manager.refresh_modules()

        self.assertIn("payloads/python/chimera/generate", changes["removed"])
        self.assertNotIn("payloads/python/chimera/generate", self.manager.modules)

    @patch("builtins.print")
    def test_failed_load_keeps_module_listed(self, mock_print):
        """Yüklenemeyen modül 'show modules' listesinden kaybolmamalı."""
        file_path = self.root / "payloads/python/boom/generate.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(BROKEN_MODULE, encoding="utf-8")
        self.manager.load_modules()

        self.assertIsNone(self.manager.ensure_loaded("payloads/python/boom/generate"))

        self.assertIn("payloads/python/boom/generate", self.manager.modules)
        self.assertTrue(self.manager.is_load_failed("payloads/python/boom/generate"))
        self.assertIn(
            "payloads/python/boom/generate",
            self.manager.get_modules_by_category()["Payloads"],
        )

    def test_get_module_finds_module_added_later(self):
        """Oturum sırasında eklenen modül use/get_module ile bulunabilmeli."""
        self._write_module("payloads/python/chimera/generate.py", "chimera", "Chimera")
        self.manager.load_modules()

        self._write_module("payloads/python/yeni/generate.py", "yeni", "Yeni payload")
        module = self.manager.get_module("payloads/python/yeni/generate")

        self.assertIsNotNone(module)
        self.assertEqual(module.Name, "yeni")


if __name__ == "__main__":
    unittest.main()

