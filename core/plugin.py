# Framework'ün eklenti (plugin) mimarisinin temel yapı taşı.
# Modüllerden farklı olarak, eklentiler framework'ün olaylarını (event) dinler ve tepki verir.

from typing import Dict, Callable, Any
from core.hooks import HookType


class BasePlugin:
    """
    Eklentilerin (Plugin) Ana Sınıfı.
    
    Yeni bir eklenti geliştirmek için bu sınıftan miras alınmalı ve ilgili metodlar doldurulmalıdır.
    Eklentiler, framework başlatıldığında, bir modül seçildiğinde veya komut çalıştırıldığında
    devreye girebilen kod parçacıklarıdır.
    """
    
    # ==============================================================================
    # Eklenti Metadata (Kimlik) Bilgileri
    # ==============================================================================
    
    Name: str = "Default Plugin"
    """Plugin'in kullanıcıya görünen adı. 'plugins list' komutunda çıkar."""
    
    Description: str = "Plugin description"
    """Plugin'in ne yaptığını anlatan kısa açıklama."""
    
    Author: str = "Unknown"
    """Plugin'i kodlayan kişinin adı."""
    
    Version: str = "1.0.0"
    """Plugin sürüm numarası. (Major.Minor.Patch formatı önerilir)"""
    
    Enabled: bool = True
    """
    Plugin'in varsayılan olarak aktif olup olmadığını belirler.
    Kullanıcı 'config' dosyasından veya çalışma zamanında bunu değiştirebilir.
    False ise hook'lar tetiklenmez.
    """
    
    Priority: int = 100
    """
    Plugin'in çalışma önceliği.
    Aynı olayı dinleyen birden fazla plugin varsa, PERFORMANS ve SIRALAMA için kullanılır.
    Düşük sayı = Yüksek öncelik (Daha önce çalışır).
    """
    
    DefaultConfig: dict = {}
    """
    Plugin'in varsayılan yapılandırma ayarları.
    get_config() çağrıldığında dosya yoksa bu değer ile oluşturulur.
    """
    
    def __init__(self) -> None:
        """
        Plugin örneği oluşturulduğunda çalışan yapıcı metod.
        Genellikle değişken tanımları için kullanılır. Ağırlıklı işler on_load'da yapılmalıdır.
        """
        pass
    
    def on_load(self) -> None:
        """
        Plugin framework'e yüklendiğinde VEYA aktifleştirildiğinde (enabled) çağrılır.
        
        Kullanım:
        - Veritabanı bağlantısını başlatmak.
        - Gerekli dosyaları kontrol etmek.
        - Kullanıcıya "Plugin yüklendi" mesajı göstermek.
        """
        pass
    
    def on_unload(self) -> None:
        """
        Plugin framework'den kaldırıldığında VEYA devre dışı bırakıldığında (disabled) çağrılır.
        
        Kullanım:
        - Açık bağlantıları kapatmak.
        - Geçici dosyaları temizlemek.
        - Kaynakları serbest bırakmak.
        """
        pass
    
    def get_hooks(self) -> Dict[HookType, Callable[..., Any]]:
        """
        Plugin'in HANGİ olayları dinlediğini ve bu olaylar olduğunda HANGİ fonksiyonu çağıracağını belirler.
        
        Returns:
            Dict: HookType (Olay Türü) -> Fonksiyon (Handler) eşleşmesi.
            
        Örnek:
            return {
                HookType.PRE_COMMAND: self.komut_oncesi_calis,
                HookType.POST_MODULE_RUN: self.modul_sonrasi_calis
            }
        """
        return {}

    def _get_config_path(self) -> str:
        """Plugin config dosyasının konumu."""
        from pathlib import Path
        config_dir = Path("config") / "plugins"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / f"{self.Name.lower().replace(' ', '_')}.json")

    def get_config(self) -> dict:
        """
        Plugin'in yapılandırma dosyasını okur.
        Dosya yoksa DefaultConfig kullanılarak oluşturulur.
        """
        import json
        config_file = self._get_config_path()
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.save_config(self.DefaultConfig)
            return self.DefaultConfig
        except json.JSONDecodeError:
            from core import logger
            logger.error(f"Plugin config okunamadı (JSON hatası): {config_file}")
            return self.DefaultConfig

    def save_config(self, config_data: dict) -> bool:
        """
        Plugin'in yapılandırma ayarlarını JSON dosyasına kaydeder.
        """
        import json
        config_file = self._get_config_path()
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            from core import logger
            logger.error(f"Plugin config kaydedilemedi: {e}")
            return False
