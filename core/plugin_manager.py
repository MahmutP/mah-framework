# Plugin (Eklenti) yaşam döngüsünü ve olay tabanlı hook sistemini yöneten sınıf.
# Framework'ün genişletilebilirliğini sağlayan ana bileşendir.

from pathlib import Path
import importlib.util # Dosyalardan dinamik sınıf yüklemek için.
from typing import Dict, List, Callable, Optional, Any, Tuple

from core.plugin import BasePlugin # Plugin'lerin temel sınıfı.
from core.hooks import HookType # Olay türleri (Enum).
from core import logger


class PluginManager:
    """
    Eklenti Yönetim Sınıfı (PluginManager).
    
    Bu sınıfın sorumlulukları:
    1. 'plugins/' dizinindeki eklentileri bulmak ve yüklemek.
    2. Eklentileri etkinleştirmek (enable) veya devre dışı bırakmak (disable).
    3. Framework içindeki olaylar tetiklendiğinde (trigger_hook), ilgili eklenti fonksiyonlarını çağırmak.
    """
    
    def __init__(self, plugins_dir: str = "plugins") -> None:
        """
        Args:
            plugins_dir (str): Eklenti dosyalarının aranacağı dizin. Varsayılan: "plugins".
        """
        self.plugins_dir: Path = Path(plugins_dir)
        
        # Yüklü plugin nesnelerini tutan sözlük (Plugin Adı -> Plugin Instance).
        self.plugins: Dict[str, BasePlugin] = {}
        
        # Hook kayıtlarını tutan yapı.
        # Key: HookType (Örn: PRE_COMMAND)
        # Value: (Öncelik, Fonksiyon) demetlerinin listesi.
        self.hooks: Dict[HookType, List[Tuple[int, Callable[..., Any]]]] = {
            hook: [] for hook in HookType
        }
    
    def load_plugins(self) -> None:
        """
        Belirtilen dizindeki tüm eklentileri tarar, belleğe yükler ve başlatır.
        Her plugin için 'on_load' metodunu çağırır ve hook'larını kaydeder.
        """
        # Yeniden yükleme ihtimaline karşı mevcut listeleri temizle.
        self.plugins.clear()
        for hook in self.hooks:
            self.hooks[hook].clear()
        
        # Plugin dizini yoksa uyarı ver ve çık.
        if not self.plugins_dir.exists():
            logger.warning(f"Plugin klasörü bulunamadı: {self.plugins_dir}")
            return
        
        # .py dosyalarını gez
        for file_path in self.plugins_dir.glob("*.py"):
            # Paket dosyalarını atla.
            if file_path.name == "__init__.py":
                continue
            
            plugin_name = file_path.stem
            
            try:
                # 1. Modül spesifikasyonu oluştur.
                spec = importlib.util.spec_from_file_location(plugin_name, str(file_path))
                if spec is None or spec.loader is None:
                    logger.warning(f"Plugin spesifikasyonu alınamadı: {file_path}")
                    continue
                
                # 2. Modülü yükle.
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 3. BasePlugin'den türetilmiş sınıfları bul.
                for name, obj in module.__dict__.items():
                    if (isinstance(obj, type) and 
                        issubclass(obj, BasePlugin) and 
                        obj is not BasePlugin):
                        
                        # Sınıftan örnek (instance) oluştur.
                        plugin_instance = obj()
                        self.plugins[plugin_name] = plugin_instance
                        
                        # Eklentinin başlangıç kodunu (on_load) çalıştır.
                        try:
                            plugin_instance.on_load()
                        except Exception as e:
                            # Bir plugin'in yüklenirken hata vermesi diğerlerini etkilememeli.
                            logger.exception(f"Plugin on_load hatası '{plugin_name}'")
                        
                        # Eğer plugin varsayılan olarak aktifse, hook'larını sisteme kaydet.
                        if plugin_instance.Enabled:
                            self._register_hooks(plugin_instance)
                        
                        logger.info(f"Plugin yüklendi: {plugin_name} v{plugin_instance.Version}")
                        break # Bir dosyada tek plugin sınıfı varsayıyoruz.
                        
            except SyntaxError as e:
                logger.exception(f"Plugin sözdizimi hatası '{file_path}'")
            except ImportError as e:
                logger.exception(f"Plugin import hatası '{file_path}'")
            except Exception as e:
                logger.exception(f"Plugin yüklenirken beklenmeyen hata '{file_path}'")
        
        logger.info(f"{len(self.plugins)} plugin yüklendi")
    
    def _register_hooks(self, plugin: BasePlugin) -> None:
        """
        Bir eklentinin dinlemek istediği olayları (hook'ları) sisteme kaydeder.
        
        Args:
            plugin: Kaydedilecek eklenti nesnesi.
        """
        # Eklentiden dinleyeceği hook'ları al.
        plugin_hooks = plugin.get_hooks()
        
        for hook_type, handler in plugin_hooks.items():
            # (Öncelik, İşleyici Fonksiyon) şeklinde listeye ekle.
            self.hooks[hook_type].append((plugin.Priority, handler))
            
            # Öncelik değerine (Priority) göre listeyi sırala.
            # Düşük sayı (örn: 10) = Yüksek Öncelik (Listenin başında yer alır).
            self.hooks[hook_type].sort(key=lambda x: x[0])
    
    def _unregister_hooks(self, plugin: BasePlugin) -> None:
        """
        Bir eklentinin hook kayıtlarını sistemden siler.
        Plugin devre dışı bırakıldığında veya kaldırıldığında kullanılır.
        """
        plugin_hooks = plugin.get_hooks()
        for hook_type, handler in plugin_hooks.items():
            # İlgili hook listesinden, bu plugin'in handler'ını filtreleyerek yeni liste oluştur.
            self.hooks[hook_type] = [
                (p, h) for p, h in self.hooks[hook_type] if h != handler
            ]
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Belirtilen eklentiyi tamamen sistemden kaldırır.
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin bulunamadı: {plugin_name}")
            return False
        
        # Eklentinin temizlik kodunu (on_unload) çalıştır.
        try:
            plugin.on_unload()
        except Exception as e:
            logger.exception(f"Plugin on_unload hatası '{plugin_name}'")
        
        # Hook'ları sil.
        self._unregister_hooks(plugin)
        
        # Nesneyi sözlükten sil.
        del self.plugins[plugin_name]
        
        logger.info(f"Plugin kaldırıldı: {plugin_name}")
        return True
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Pasif durumdaki bir eklentiyi aktifleştirir. Hook'larını kaydeder.
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
        """
        Aktif bir eklentiyi pasifleştirir. Hook'larını siler ama bellekte tutar.
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
        """
        BELİRLİ BİR OLAY GERÇEKLEŞTİĞİNDE ÇAĞRILIR.
        Kayıtlı tüm eklentilerin ilgili fonksiyonlarını sırayla çalıştırır.
        
        Args:
            hook_type: Tetiklenen olayın türü (örn: HookType.PRE_COMMAND).
            **kwargs: İşleyicilere (handler) gönderilecek parametreler (örn: command_line="help").
        """
        handlers = self.hooks.get(hook_type, [])
        
        for priority, handler in handlers:
            try:
                # İşleyici fonksiyonu çağır.
                handler(**kwargs)
            except Exception as e:
                # Bir eklentinin çökmesi, framework'ü veya diğer eklentileri durdurmamalı.
                logger.exception(f"Plugin hook hatası ({hook_type.value})")
                continue
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Yüklü tüm plugin'leri döndürür."""
        return self.plugins
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Belirtilen plugin'i döndürür."""
        return self.plugins.get(plugin_name)
    
    def get_enabled_plugins(self) -> Dict[str, BasePlugin]:
        """Sadece aktif (enable edilmiş) plugin'leri filtreleyip döndürür."""
        return {
            name: plugin 
            for name, plugin in self.plugins.items() 
            if plugin.Enabled
        }
