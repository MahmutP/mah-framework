import unittest
from unittest.mock import MagicMock
from core.plugin import BasePlugin
from core.plugin_manager import PluginManager
from core.hooks import HookType
from core.shared_state import shared_state

class TestPluginSystem(unittest.TestCase):
    def setUp(self):
        # Her test öncesi temiz PluginManager
        self.plugin_manager = PluginManager()
        # Mock plugin klasörü/yükleme işlemi için setup gerekebilir
        # Ancak burada manuel olarak plugin ekleyeceğiz
        
    def test_hook_types(self):
        """HookType enumlarının doğruluğunu test et."""
        self.assertTrue(hasattr(HookType, 'ON_STARTUP'))
        self.assertTrue(hasattr(HookType, 'ON_SHUTDOWN'))
        self.assertTrue(hasattr(HookType, 'PRE_COMMAND'))
        self.assertTrue(hasattr(HookType, 'POST_COMMAND'))

    def test_plugin_registration(self):
        """Plugin manuel kaydını test et."""
        # Mock Plugin
        class MockPlugin(BasePlugin):
            Name = "TestPlugin"
            Version = "1.0"
            Enabled = True
            def get_hooks(self):
                return {}

        plugin = MockPlugin()
        self.plugin_manager.plugins["TestPlugin"] = plugin
        
        self.assertIn("TestPlugin", self.plugin_manager.get_all_plugins())
        self.assertEqual(self.plugin_manager.get_plugin("TestPlugin"), plugin)

    def test_enable_disable(self):
        """Plugin enable/disable fonksiyonlarını test et."""
        class MockPlugin(BasePlugin):
            Name = "TestPlugin"
            Enabled = True
            def get_hooks(self):
                return {}

        plugin = MockPlugin()
        self.plugin_manager.plugins["TestPlugin"] = plugin
        
        # Disable
        self.plugin_manager.disable_plugin("TestPlugin")
        self.assertFalse(plugin.Enabled)
        self.assertFalse("TestPlugin" in self.plugin_manager.get_enabled_plugins())
        
        # Enable
        self.plugin_manager.enable_plugin("TestPlugin")
        self.assertTrue(plugin.Enabled)
        self.assertTrue("TestPlugin" in self.plugin_manager.get_enabled_plugins())

    def test_hook_trigger(self):
        """Hook tetiklenmesini test et."""
        mock_handler = MagicMock()
        
        class MockPlugin(BasePlugin):
            Name = "HookTester"
            Enabled = True
            def get_hooks(self):
                return {
                    HookType.PRE_COMMAND: mock_handler
                }
        
        plugin = MockPlugin()
        self.plugin_manager.plugins["HookTester"] = plugin
        # Hook'ları manuel kaydet (normalde load_plugins veya enable_plugin yapar)
        self.plugin_manager._register_hooks(plugin)
        
        # Hook tetikle
        self.plugin_manager.trigger_hook(HookType.PRE_COMMAND, command="help")
        
        # Handler çağrıldı mı?
        mock_handler.assert_called_once()
        args, kwargs = mock_handler.call_args
        self.assertEqual(kwargs['command'], "help")

    def test_shared_state_integration(self):
        """SharedState entegrasyonunu kontrol et."""
        shared_state.plugin_manager = self.plugin_manager
        self.assertIsNotNone(shared_state.plugin_manager)
        self.assertEqual(shared_state.plugin_manager, self.plugin_manager)

if __name__ == '__main__':
    unittest.main()
