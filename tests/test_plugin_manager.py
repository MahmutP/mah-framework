
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call
from core.plugin_manager import PluginManager
from core.hooks import HookType
from core.plugin import BasePlugin

# Fixture'lar
@pytest.fixture
def plugin_manager(tmp_path):
    # Geçici bir plugin klasörü ile manager oluştur
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return PluginManager(plugins_dir=str(plugins_dir))

@pytest.fixture
def mock_plugin():
    class MockPlugin(BasePlugin):
        Name = "MockPlugin"
        Version = "1.0"
        Enabled = True
        Priority = 100
        
        def get_hooks(self):
            return {}
            
    return MockPlugin()

# Testler
def test_plugin_manager_init(plugin_manager):
    """PluginManager oluşturulabilir mi ve varsayılan değerler doğru mu?"""
    assert isinstance(plugin_manager, PluginManager)
    assert plugin_manager.plugins == {}
    
    # hooks dict tüm HookType'ları içeriyor mu
    assert len(plugin_manager.hooks) == len(HookType)
    for hook_type in HookType:
        assert hook_type in plugin_manager.hooks
        assert plugin_manager.hooks[hook_type] == []

def test_load_plugins_empty_dir(plugin_manager):
    """Boş klasörde hata vermeden çalışır mı?"""
    try:
        plugin_manager.load_plugins()
    except Exception as e:
        pytest.fail(f"Boş klasörde load_plugins hata verdi: {e}")
    
    assert len(plugin_manager.plugins) == 0

def test_trigger_hook_no_handlers(plugin_manager):
    """Handler olmadan hook tetiklenebilir mi?"""
    try:
        plugin_manager.trigger_hook(HookType.ON_STARTUP)
    except Exception as e:
        pytest.fail(f"Handler olmadan trigger_hook hata verdi: {e}")

def test_enable_disable_plugin(plugin_manager, mock_plugin):
    """Plugin enable/disable çalışıyor mu?"""
    # Plugin'i manuel yükle
    plugin_manager.plugins["MockPlugin"] = mock_plugin
    
    # Başlangıçta enable (mock_plugin enabled=True)
    assert mock_plugin.Enabled is True
    
    # Disable et
    result = plugin_manager.disable_plugin("MockPlugin")
    assert result is True
    assert mock_plugin.Enabled is False
    # Hooklardan silinmiş olmalı (bu örnekte hook yok ama mantık olarak)
    
    # Enable et
    result = plugin_manager.enable_plugin("MockPlugin")
    assert result is True
    assert mock_plugin.Enabled is True

def test_hook_priority(plugin_manager):
    """Düşük priority'li handler önce mi çalışıyor?"""
    call_order = []
    
    handler_high_prio = MagicMock(side_effect=lambda **kw: call_order.append("high"))  # Priority 10
    handler_low_prio = MagicMock(side_effect=lambda **kw: call_order.append("low"))    # Priority 100
    
    class HighPrioPlugin(BasePlugin):
        Name = "High"
        Priority = 10
        def get_hooks(self):
            return {HookType.PRE_COMMAND: handler_high_prio}
            
    class LowPrioPlugin(BasePlugin):
        Name = "Low"
        Priority = 100
        def get_hooks(self):
            return {HookType.PRE_COMMAND: handler_low_prio}
            
    # Pluginleri kaydet
    p1 = HighPrioPlugin()
    p2 = LowPrioPlugin()
    
    plugin_manager.plugins["High"] = p1
    plugin_manager.plugins["Low"] = p2
    
    # Enable fonksiyonunu kullanarak hook'ları kaydettir (register_hooks çağrılır)
    # Ancak enable_plugin zaten Enabled ise işlem yapmayabilir, o yüzden önce False yapıp sonra True yapabiliriz
    # Veya direkt internal _register_hooks çağırabiliriz
    plugin_manager._register_hooks(p1)
    plugin_manager._register_hooks(p2)
    
    plugin_manager.trigger_hook(HookType.PRE_COMMAND, command="test")
    
    assert call_order == ["high", "low"]
    
def test_hook_error_handling(plugin_manager):
    """Handler hata verse bile diğerleri çalışır mı?"""
    
    handler_error = MagicMock(side_effect=Exception("Boom!"))
    handler_success = MagicMock()
    
    class ErrorPlugin(BasePlugin):
        Name = "Error"
        Priority = 10
        def get_hooks(self):
            return {HookType.ON_STARTUP: handler_error}
            
    class SuccessPlugin(BasePlugin):
        Name = "Success"
        Priority = 20
        def get_hooks(self):
            return {HookType.ON_STARTUP: handler_success}
            
    plugin_manager.plugins["Error"] = ErrorPlugin()
    plugin_manager.plugins["Success"] = SuccessPlugin()
    
    plugin_manager._register_hooks(plugin_manager.plugins["Error"])
    plugin_manager._register_hooks(plugin_manager.plugins["Success"])
    
    # Trigger hook - exception fırlatmamalı
    try:
        plugin_manager.trigger_hook(HookType.ON_STARTUP)
    except Exception:
        pytest.fail("trigger_hook exception fırlattı (hata yakalanamadı)")
        
    handler_error.assert_called_once()
    handler_success.assert_called_once()
