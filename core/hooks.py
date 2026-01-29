# Plugin sisteminin hook türlerini tanımlayan modül
# Hook'lar, framework'ün belirli olaylarında plugin'lerin tetiklenmesini sağlar

from enum import Enum


class HookType(Enum):
    """Plugin hook türleri.
    
    Bu enum, plugin sisteminde kullanılan tüm hook türlerini tanımlar.
    Her hook belirli bir framework olayına karşılık gelir ve o olay
    gerçekleştiğinde kayıtlı plugin handler'ları tetiklenir.
    
    Attributes:
        ON_STARTUP: Framework başladığında tetiklenir.
        ON_SHUTDOWN: Framework kapanırken tetiklenir.
        PRE_COMMAND: Her komut çalıştırılmadan önce tetiklenir.
        POST_COMMAND: Her komut çalıştırıldıktan sonra tetiklenir.
        PRE_MODULE_RUN: Modül çalıştırılmadan önce tetiklenir.
        POST_MODULE_RUN: Modül çalıştırıldıktan sonra tetiklenir.
        ON_MODULE_SELECT: Bir modül seçildiğinde tetiklenir.
        ON_OPTION_SET: Bir option değeri değiştirildiğinde tetiklenir.
    """
    
    # Framework yaşam döngüsü hook'ları
    ON_STARTUP = "on_startup"
    """Framework başladığında tetiklenir. Başlangıç kontrolleri ve bağlantı testleri için kullanılır."""
    
    ON_SHUTDOWN = "on_shutdown"
    """Framework kapanırken tetiklenir. Temizlik ve log kaydetme işlemleri için kullanılır."""
    
    # Komut hook'ları
    PRE_COMMAND = "pre_command"
    """Her komut çalıştırılmadan önce tetiklenir. Komut loglama ve izin kontrolü için kullanılır."""
    
    POST_COMMAND = "post_command"
    """Her komut çalıştırıldıktan sonra tetiklenir. Sonuç bildirimi için kullanılır."""
    
    # Modül hook'ları
    PRE_MODULE_RUN = "pre_module_run"
    """Modül çalıştırılmadan önce tetiklenir. Seçenek doğrulama için kullanılır."""
    
    POST_MODULE_RUN = "post_module_run"
    """Modül çalıştırıldıktan sonra tetiklenir. Sonuç bildirimi ve raporlama için kullanılır."""
    
    ON_MODULE_SELECT = "on_module_select"
    """Bir modül seçildiğinde (use komutu) tetiklenir. Otomasyon ve logging için kullanılır."""
    
    # Option hook'ları
    ON_OPTION_SET = "on_option_set"
    """Bir option değeri değiştirildiğinde (set komutu) tetiklenir. Doğrulama ve bağımlılık kontrolü için kullanılır."""
