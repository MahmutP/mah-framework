# Plugin'lerin miras alacağı temel sınıf
# Tüm plugin'ler bu sınıftan türetilmelidir

from typing import Dict, Callable, Any
from core.hooks import HookType


class BasePlugin:
    """Tüm plugin'lerin miras alacağı temel sınıf.
    
    Bu sınıf, plugin geliştirmek için gerekli temel yapıyı sağlar.
    Yeni bir plugin oluştururken bu sınıftan miras alınmalı ve
    gerekli özellikler ile metodlar override edilmelidir.
    
    Attributes:
        Name: Plugin'in adı.
        Description: Plugin'in açıklaması.
        Author: Plugin'i geliştiren kişi.
        Version: Plugin versiyonu.
        Enabled: Plugin'in aktif olup olmadığı.
        Priority: Plugin önceliği (düşük değer = önce çalışır).
    
    Example:
        >>> class MyPlugin(BasePlugin):
        ...     Name = "My Plugin"
        ...     Description = "Örnek bir plugin"
        ...     Author = "Mahmut"
        ...     Version = "1.0.0"
        ...     
        ...     def get_hooks(self):
        ...         return {
        ...             HookType.POST_COMMAND: self.on_command_complete
        ...         }
        ...     
        ...     def on_command_complete(self, command_line: str, success: bool, **kwargs):
        ...         print(f"Komut çalıştırıldı: {command_line}")
    """
    
    # Plugin temel özellikleri
    Name: str = "Default Plugin"
    """Plugin'in görünen adı."""
    
    Description: str = "Plugin description"
    """Plugin'in ne yaptığını açıklayan kısa metin."""
    
    Author: str = "Unknown"
    """Plugin'i geliştiren kişinin adı."""
    
    Version: str = "1.0.0"
    """Plugin'in sürüm numarası (semantic versioning önerilir)."""
    
    Enabled: bool = True
    """Plugin'in aktif olup olmadığını belirtir. False ise hook'lar tetiklenmez."""
    
    Priority: int = 100
    """Plugin önceliği. Düşük değerli plugin'ler önce çalışır (0-1000 arası önerilir)."""
    
    def __init__(self) -> None:
        """Plugin init fonksiyonu.
        
        Alt sınıflar bu metodu override edebilir ancak super().__init__()
        çağrılması önerilir.
        """
        pass
    
    def on_load(self) -> None:
        """Plugin yüklendiğinde çağrılır.
        
        Bu metod, plugin ilk kez yüklendiğinde veya enable edildiğinde
        çalıştırılır. Başlangıç yapılandırmaları burada yapılabilir.
        
        Override edilebilir.
        """
        pass
    
    def on_unload(self) -> None:
        """Plugin kaldırıldığında çağrılır.
        
        Bu metod, plugin disable edildiğinde veya framework kapanırken
        çalıştırılır. Temizlik işlemleri burada yapılabilir.
        
        Override edilebilir.
        """
        pass
    
    def get_hooks(self) -> Dict[HookType, Callable[..., Any]]:
        """Plugin'in dinlediği hook'ları döndürür.
        
        Bu metod, plugin'in hangi event'leri dinlediğini ve her event için
        hangi handler fonksiyonunun çağrılacağını tanımlar.
        
        Returns:
            Dict[HookType, Callable]: Hook türü -> handler fonksiyonu eşleştirmesi.
            
        Example:
            >>> def get_hooks(self):
            ...     return {
            ...         HookType.PRE_COMMAND: self.before_command,
            ...         HookType.POST_MODULE_RUN: self.after_module
            ...     }
        
        Hook Handler Parametreleri:
            - ON_STARTUP: Parametre yok
            - ON_SHUTDOWN: Parametre yok
            - PRE_COMMAND: command_line (str)
            - POST_COMMAND: command_line (str), success (bool)
            - PRE_MODULE_RUN: module_path (str), module (BaseModule)
            - POST_MODULE_RUN: module_path (str), module (BaseModule), success (bool)
            - ON_MODULE_SELECT: module_path (str), module (BaseModule)
            - ON_OPTION_SET: option_name (str), value (Any), module (BaseModule)
        """
        return {}
