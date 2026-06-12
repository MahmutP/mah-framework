"""Entegrasyon testleri - Modül yükleme, çalıştırma ve sistem akışı."""

import tempfile
from pathlib import Path

from core.command_manager import CommandManager
from core.context import get_global_context, reset_global_context
from core.hooks import HookType
from core.module import BaseModule
from core.option import Option


def test_base_module_instantiation():
    """BaseModule temel özellikleri doğru olmalı."""
    module = BaseModule()
    assert module.Name == "Default Module Name"
    assert module.Description == "description for module"
    assert module.Author == "Unknown"
    assert module.Category == "uncategorized"
    assert module.Version == "1.0"
    assert module.Path == ""
    assert module.Options == {}
    assert module.Requirements == {}


def test_base_module_run_default():
    """BaseModule varsayılan run() metodu çalışmalı."""
    module = BaseModule()
    result = module.run({})
    assert "tamamlandı" in str(result)


def test_base_module_get_options():
    """BaseModule.get_options() boş sözlük döndürmeli."""
    module = BaseModule()
    assert module.get_options() == {}


def test_base_module_set_get_option():
    """BaseModule seçenek atama ve okuma çalışmalı."""
    class TestModule(BaseModule):
        Options = {
            "RHOST": Option("RHOST", "127.0.0.1", True, "Hedef IP"),
            "RPORT": Option("RPORT", 8080, True, "Hedef port"),
        }

    module = TestModule()
    assert module.get_option_value("RHOST") == "127.0.0.1"
    assert module.get_option_value("RPORT") == 8080

    module.set_option_value("RHOST", "192.168.1.1")
    assert module.get_option_value("RHOST") == "192.168.1.1"


def test_base_module_check_required():
    """check_required_options zorunlu seçenekleri doğru kontrol etmeli."""
    class TestModule(BaseModule):
        Options = {
            "RHOST": Option("RHOST", "", True, "Hedef IP"),
        }

    module = TestModule()
    assert not module.check_required_options()

    module.set_option_value("RHOST", "192.168.1.1")
    assert module.check_required_options()


def test_base_module_check_dependencies_empty():
    """check_dependencies boş bağımlılıklarla True döndürmeli."""
    module = BaseModule()
    assert module.check_dependencies()


def test_option_validation():
    """Option regex validasyonu çalışmalı."""
    opt = Option("test", "test", False, "Test option", regex_check=True, regex=r"^\d+$")
    assert opt.value == "test"

    # Geçersiz değer atanmamalı
    opt.value = "abc"
    assert opt.value == "test"

    # Geçerli değer atanmalı
    opt.value = "123"
    assert opt.value == "123"


def test_option_default_values():
    """Option varsayılan değerleri doğru olmalı."""
    opt = Option("opt1", "default", False, "A test option")
    assert opt.value == "default"
    assert opt.required is False
    assert opt.description == "A test option"


def test_command_manager_load_empty_dir():
    """CommandManager boş dizini yüklemeyi dene - hata vermemeli."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CommandManager(commands_dir=tmpdir)
        cm.load_commands()
        assert len(cm.get_all_commands()) == 0


def test_command_manager_alias_management():
    """CommandManager alias ekleme/silme/listeleme çalışmalı."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from core.cont import ALIASES_FILE
        original = ALIASES_FILE

        # Geçici alias dosyası kullan
        import core.cont as cont
        test_aliases = str(Path(tmpdir) / "aliases.json")
        original_file = ALIASES_FILE
        cont.ALIASES_FILE = test_aliases

        try:
            cm = CommandManager(commands_dir=tmpdir)
            result = cm.add_alias("ll", "list files")
            assert result is True

            result = cm.add_alias("ll", "list files")
            assert result is False

            aliases = cm.get_aliases()
            assert "ll" in aliases
            assert aliases["ll"] == "list files"

            result = cm.remove_alias("ll")
            assert result is True
            assert "ll" not in cm.get_aliases()
        finally:
            cont.ALIASES_FILE = original_file


def test_command_manager_resolve():
    """resolve_command alias ve direkt komut çözümlemesi çalışmalı."""
    cm = CommandManager()

    # Alias yoksa, bilinmeyen komut None dönmeli
    name, is_alias = cm.resolve_command("unknown_cmd_12345")
    assert name is None
    assert is_alias is False


def test_hook_type_values():
    """HookType enum değerleri benzersiz ve anlamlı olmalı."""
    values = [ht.value for ht in HookType]
    assert len(values) == len(set(values))
    assert "on_startup" in values
    assert "on_shutdown" in values
    assert "pre_command" in values
    assert "post_command" in values
    assert "pre_module_load" in values
    assert "pre_module_run" in values
    assert "post_module_run" in values
    assert "post_module_load" in values
    assert "pre_plugin_load" in values
    assert "post_plugin_load" in values


def test_hook_count():
    """HookType toplam hook sayısı doğru olmalı (beklenen: 15)."""
    assert len(HookType) == 15


def test_app_context_reset():
    """AppContext sıfırlama tüm alanları temizlemeli."""
    ctx = get_global_context()
    ctx.selected_module = object()
    ctx.is_recording = True
    ctx.recorded_commands = ["test"]

    reset_global_context()

    ctx2 = get_global_context()
    assert ctx2.selected_module is None
    assert ctx2.is_recording is False
    assert ctx2.recorded_commands == []


def test_service_registration():
    """Servis kaydı ve çözümleme çalışmalı."""
    from core.service_container import ServiceContainer

    container = ServiceContainer()

    class MockService:
        def work(self) -> str:
            return "done"

    svc = MockService()
    container.register(MockService, svc)
    resolved = container.resolve(MockService)
    assert resolved is svc
    assert resolved.work() == "done"


def test_service_not_registered():
    """Kayıtlı olmayan servis KeyError fırlatmalı."""
    from core.service_container import ServiceContainer

    container = ServiceContainer()
    try:
        container.resolve(int)
        assert False
    except KeyError:
        assert True


def test_code_scanner_scan_result():
    """ScanResult özellikleri doğru çalışmalı."""
    from core.code_scanner import ScanResult
    result = ScanResult("/tmp/test.py")
    assert result.file_path == "/tmp/test.py"
    assert result.is_safe
    assert result.dangerous == []
    assert result.errors == []

    result.dangerous.append(("eval", "execution", "test", 1))
    assert not result.is_safe


def test_shared_state_backward_compat():
    """SharedState geriye uyumluluk wrapper'ı çalışmalı."""
    from core.shared_state import shared_state, reset_shared_state
    from core.context import get_global_context

    reset_shared_state()
    ctx = get_global_context()

    ctx.is_recording = True
    assert shared_state.is_recording is True

    ctx.is_recording = False
    assert shared_state.is_recording is False

    shared_state.is_recording = True
    assert ctx.is_recording is True