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
