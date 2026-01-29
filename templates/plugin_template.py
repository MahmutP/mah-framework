"""Mah Framework için Örnek Plugin Şablonu.

Bu dosya, geliştiricilerin Mah Framework için kendi plugin'lerini (eklentilerini)
oluştururken kullanabilecekleri bir başlangıç şablonudur.

Kullanım:
1. Bu dosyayı kopyalayın ve `plugins/` klasörüne yapıştırın (örn: `plugins/benim_pluginim.py`).
2. `ExamplePlugin` sınıf adını kendi plugin adınızla değiştirin.
3. Meta verileri (Name, Description vb.) güncelleyin.
4. `get_hooks` metodunda dinlemek istediğiniz olayları belirtin.
5. İlgili olaylar için metodlarınızı yazın.

Plugin Sistemi:
Pluginler, framework'ün belirli noktalarında (hook) devreye giren ve
akışı değiştirebilen veya izleyebilen yapılardır.
"""

from typing import Dict, Any, Callable
from rich import print
from core.plugin import BasePlugin
from core.hooks import HookType


class ExamplePlugin(BasePlugin):
    """Örnek Plugin Sınıfı.
    
    Tüm pluginler BasePlugin sınıfından türetilmelidir.
    """
    
    # --------------------------------------------------------------------------
    # Plugin Meta Verileri (Zorunlu Alanlar)
    # --------------------------------------------------------------------------
    
    # Plugin'in görünen adı
    Name: str = "Örnek Plugin"
    
    # Kısa açıklama (plugins list komutunda görünür)
    Description: str = "Geliştiriciler için örnek plugin şablonu."
    
    # Plugin yazarı
    Author: str = "Geliştirici Adı"
    
    # Versiyon numarası
    Version: str = "1.0.0"
    
    # Varsayılan olarak aktif mi? (True/False)
    Enabled: bool = True
    
    # Çalışma önceliği (Düşük sayı = Yüksek öncelik)
    # Örn: 10 olan plugin, 100 olan pluginden önce çalışır.
    Priority: int = 100
    
    # --------------------------------------------------------------------------
    # Yaşam Döngüsü Metodları
    # --------------------------------------------------------------------------
    
    def on_load(self) -> None:
        """Plugin yüklendiğinde (framework başladığında) çalışır."""
        # Buraya başlatma kodlarını yazın (örn: veritabanı bağlantısı, dosya açma)
        # print(f"[bilgi] {self.Name} yüklendi.")
        pass
        
    def on_unload(self) -> None:
        """Plugin kaldırıldığında veya framework kapanırken çalışır."""
        # Buraya temizlik kodlarını yazın (örn: bağlantıları kapatma)
        # print(f"[bilgi] {self.Name} kapatıldı.")
        pass
        
    # --------------------------------------------------------------------------
    # Hook (Kanca) Tanımları
    # --------------------------------------------------------------------------
    
    def get_hooks(self) -> Dict[HookType, Callable[..., Any]]:
        """Plugin'in dinleyeceği olayları (hook) ve işleyicilerini döndürür.
        
        Returns:
            Dict: {HookTipi: Metod} formatında sözlük.
        """
        return {
            # Komut çalışmadan ÖNCE tetiklenir
            HookType.PRE_COMMAND: self.on_command,
            
            # Modül çalıştıktan SONRA tetiklenir
            HookType.POST_MODULE_RUN: self.on_module_run
            
            # Diğer Hooklar:
            # HookType.ON_STARTUP      : Başlangıçta
            # HookType.ON_SHUTDOWN     : Kapanışta
            # HookType.POST_COMMAND    : Komut sonrası
            # HookType.PRE_MODULE_RUN  : Modül öncesi
            # HookType.ON_MODULE_SELECT: Modül seçilince
            # HookType.ON_OPTION_SET   : Option değişince
        }
    
    # --------------------------------------------------------------------------
    # Hook İşleyicileri (Handler'lar)
    # --------------------------------------------------------------------------
    
    def on_command(self, command_line: str, **kwargs: Any) -> None:
        """PRE_COMMAND hook işleyicisi örneği.
        
        Args:
            command_line (str): Girilen komut satırı.
            **kwargs: Ek parametreler.
        """
        # Örnek: 'gizli' komutu girilirse engelle veya logla
        if command_line.strip() == "gizli":
            print("[uyarı] Gizli komut tespit edildi!")
            
    def on_module_run(self, module_path: str, success: bool, **kwargs: Any) -> None:
        """POST_MODULE_RUN hook işleyicisi örneği.
        
        Args:
            module_path (str): Çalışan modülün yolu.
            success (bool): Başarılı oldu mu?
            **kwargs: Modül objesi (module) vb.
        """
        durum = "başarılı" if success else "başarısız"
        # print(f"[bilgi] Modül {module_path} {durum} şekilde tamamlandı.")
