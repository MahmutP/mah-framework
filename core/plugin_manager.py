# Plugin yönetimi için ana sınıf
# Plugin'lerin yüklenmesi, etkinleştirilmesi ve hook tetiklemelerini yönetir

from pathlib import Path
import importlib.util
from typing import Dict, List, Callable, Optional, Any, Tuple

from core.plugin import BasePlugin
from core.hooks import HookType
from core import logger


class PluginManager:
    """Plugin yönetim sınıfı.
    
    Bu sınıf, plugin'lerin yüklenmesi, etkinleştirilmesi, devre dışı bırakılması
    ve hook tetiklemelerini yönetir.
    
    Attributes:
        plugins_dir: Plugin dosyalarının bulunduğu klasör.
        plugins: Yüklü plugin'lerin isim -> obje eşleştirmesi.
        hooks: Hook türü -> handler listesi eşleştirmesi.
    
    Example:
        >>> pm = PluginManager()
        >>> pm.load_plugins()
        >>> pm.trigger_hook(HookType.ON_STARTUP)
    """
    
    def __init__(self, plugins_dir: str = "plugins") -> None:
        """PluginManager init fonksiyonu.
        
        Args:
            plugins_dir: Plugin dosyalarının bulunduğu klasör. Varsayılan: "plugins"
        """
        self.plugins_dir: Path = Path(plugins_dir)
        self.plugins: Dict[str, BasePlugin] = {}
        self.hooks: Dict[HookType, List[Tuple[int, Callable[..., Any]]]] = {
            hook: [] for hook in HookType
        }
    
    def load_plugins(self) -> None:
        """Tüm plugin'leri yükler.
        
        plugins/ klasöründeki tüm .py dosyalarını tarar, BasePlugin'den
        türeyen sınıfları bulur ve yükler. Her plugin için on_load() çağrılır
        ve hook'lar kaydedilir.
        """
        self.plugins.clear()
        for hook in self.hooks:
            self.hooks[hook].clear()
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugin klasörü bulunamadı: {self.plugins_dir}")
            return
        
        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            
            plugin_name = file_path.stem
            
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, str(file_path))
                if spec is None or spec.loader is None:
                    logger.warning(f"Plugin spesifikasyonu alınamadı: {file_path}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # BasePlugin'den türeyen sınıfları bul
                for name, obj in module.__dict__.items():
                    if (isinstance(obj, type) and 
                        issubclass(obj, BasePlugin) and 
                        obj is not BasePlugin):
                        
                        plugin_instance = obj()
                        self.plugins[plugin_name] = plugin_instance
                        
                        # on_load() çağır
                        try:
                            plugin_instance.on_load()
                        except Exception as e:
                            logger.exception(f"Plugin on_load hatası '{plugin_name}'")
                        
                        # Hook'ları kaydet
                        if plugin_instance.Enabled:
                            self._register_hooks(plugin_instance)
                        
                        logger.info(f"Plugin yüklendi: {plugin_name} v{plugin_instance.Version}")
                        break
                        
            except SyntaxError as e:
                logger.exception(f"Plugin sözdizimi hatası '{file_path}'")
            except ImportError as e:
                logger.exception(f"Plugin import hatası '{file_path}'")
            except Exception as e:
                logger.exception(f"Plugin yüklenirken beklenmeyen hata '{file_path}'")
        
        logger.info(f"{len(self.plugins)} plugin yüklendi")
    
    def _register_hooks(self, plugin: BasePlugin) -> None:
        """Plugin'in hook'larını kaydeder.
        
        Args:
            plugin: Hook'ları kaydedilecek plugin.
        """
        plugin_hooks = plugin.get_hooks()
        for hook_type, handler in plugin_hooks.items():
            # (priority, handler) tuple olarak ekle
            self.hooks[hook_type].append((plugin.Priority, handler))
            # Priority'ye göre sırala (düşük önce)
            self.hooks[hook_type].sort(key=lambda x: x[0])
    
    def _unregister_hooks(self, plugin: BasePlugin) -> None:
        """Plugin'in hook'larını kaldırır.
        
        Args:
            plugin: Hook'ları kaldırılacak plugin.
        """
        plugin_hooks = plugin.get_hooks()
        for hook_type, handler in plugin_hooks.items():
            self.hooks[hook_type] = [
                (p, h) for p, h in self.hooks[hook_type] if h != handler
            ]
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Plugin'i kaldırır.
        
        Args:
            plugin_name: Kaldırılacak plugin'in adı.
            
        Returns:
            bool: Başarılı olup olmadığı.
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin bulunamadı: {plugin_name}")
            return False
        
        try:
            plugin.on_unload()
        except Exception as e:
            logger.exception(f"Plugin on_unload hatası '{plugin_name}'")
        
        self._unregister_hooks(plugin)
        del self.plugins[plugin_name]
        
        logger.info(f"Plugin kaldırıldı: {plugin_name}")
        return True
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Plugin'i etkinleştirir.
        
        Args:
            plugin_name: Etkinleştirilecek plugin'in adı.
            
        Returns:
            bool: Başarılı olup olmadığı.
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin bulunamadı: {plugin_name}")
            return False
        
        if plugin.Enabled:
            logger.info(f"Plugin zaten aktif: {plugin_name}")
            return True
        
        plugin.Enabled = True
        self._register_hooks(plugin)
        
        logger.info(f"Plugin etkinleştirildi: {plugin_name}")
        return True
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Plugin'i devre dışı bırakır.
        
        Args:
            plugin_name: Devre dışı bırakılacak plugin'in adı.
            
        Returns:
            bool: Başarılı olup olmadığı.
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin bulunamadı: {plugin_name}")
            return False
        
        if not plugin.Enabled:
            logger.info(f"Plugin zaten devre dışı: {plugin_name}")
            return True
        
        plugin.Enabled = False
        self._unregister_hooks(plugin)
        
        logger.info(f"Plugin devre dışı bırakıldı: {plugin_name}")
        return True
    
    def trigger_hook(self, hook_type: HookType, **kwargs: Any) -> None:
        """Belirtilen hook'u tetikler.
        
        Kayıtlı tüm handler'ları priority sırasına göre çağırır.
        Her handler try-except ile sarılır, bir handler'ın hatası
        diğer handler'ların çalışmasını engellemez.
        
        Args:
            hook_type: Tetiklenecek hook türü.
            **kwargs: Handler'lara geçirilecek parametreler.
        """
        handlers = self.hooks.get(hook_type, [])
        
        for priority, handler in handlers:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.exception(f"Plugin hook hatası ({hook_type.value})")
                # Hata olsa bile diğer handler'lara devam et
                continue
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Tüm plugin'leri döndürür.
        
        Returns:
            Dict[str, BasePlugin]: Plugin adı -> obje eşleştirmesi.
        """
        return self.plugins
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Belirtilen plugin'i döndürür.
        
        Args:
            plugin_name: Plugin adı.
            
        Returns:
            Optional[BasePlugin]: Plugin objesi veya None.
        """
        return self.plugins.get(plugin_name)
    
    def get_enabled_plugins(self) -> Dict[str, BasePlugin]:
        """Sadece aktif plugin'leri döndürür.
        
        Returns:
            Dict[str, BasePlugin]: Aktif plugin'lerin adı -> obje eşleştirmesi.
        """
        return {
            name: plugin 
            for name, plugin in self.plugins.items() 
            if plugin.Enabled
        }
