# Plugin ve olay yönetim sisteminin temel yapı taşlarından biri olan 'Hook' türlerini tanımlayan modül.
# Hook'lar (kancalar), framework'ün çalışması sırasında belirli noktalara (olaylara) eklentilerin müdahale etmesini sağlar.
# Bu sayede çekirdek kodu değiştirmeden yeni özellikler eklenebilir.

from enum import Enum


class HookType(Enum):
    """
    Plugin (Eklenti) Hook Türleri.
    
    Bu enum sınıfı, eklentilerin hangi olayları dinleyebileceğini tanımlar.
    Her bir eleman, framework içinde gerçekleşen belirli bir ana veya olaya karşılık gelir.
    """
    
    # ==============================================================================
    # Framework Yaşam Döngüsü (Lifecycle) Hook'ları
    # ==============================================================================
    
    ON_STARTUP = "on_startup"
    """
    Framework tamamen başlatıldığında, ancak kullanıcı etkileşimine girmeden hemen önce tetiklenir.
    Kullanım Alanları:
    - Başlangıç mesajlarını göstermek.
    - Otomatik bağlantı kontrolleri yapmak.
    - Arka plan servislerini başlatmak.
    """
    
    ON_SHUTDOWN = "on_shutdown"
    """
    Framework kapatılma sürecine girdiğinde tetiklenir.
    Kullanım Alanları:
    - Açık bağlantıları temizlemek.
    - Geçici dosyaları silmek.
    - Oturum raporlarını kaydetmek.
    """
    
    # ==============================================================================
    # Komut Çalıştırma (Command Execution) Hook'ları
    # ==============================================================================
    
    PRE_COMMAND = "pre_command"
    """
    Kullanıcının girdiği herhangi bir komut çalıştırılmadan HEMEN ÖNCE tetiklenir.
    Kullanım Alanları:
    - Komut loglaması yapmak (Audit logs).
    - Komut yetkilendirmesi veya kısıtlaması uygulamak.
    - Komut parametrelerini manipüle etmek (gelişmiş senaryolar).
    """
    
    POST_COMMAND = "post_command"
    """
    Komut çalıştırılıp işi bittikten SONRA (başarılı veya başarısız) tetiklenir.
    Kullanım Alanları:
    - Komut sonucunu bildirmek.
    - Başarısız komutlarda hata analizi veya öneri sunmak.
    """
    
    # ==============================================================================
    # Modül Çalıştırma (Module Execution) Hook'ları
    # ==============================================================================
    
    PRE_MODULE_RUN = "pre_module_run"
    """
    Seçili bir modül 'run' veya 'exploit' komutuyla çalıştırılmadan önce tetiklenir.
    Kullanım Alanları:
    - Gerekli seçeneklerin (options) doluluğunu son kez kontrol etmek.
    - Hedef sistemin erişilebilirliğini doğrulamak.
    """
    
    POST_MODULE_RUN = "post_module_run"
    """
    Modül çalışmasını tamamladıktan sonra tetiklenir.
    Kullanım Alanları:
    - Elde edilen sonuçları (başarı/başarısızlık) raporlamak.
    - Modül çıktısını ayrıştırıp veritabanına kaydetmek.
    """
    
    ON_MODULE_SELECT = "on_module_select"
    """
    Kullanıcı 'use' komutuyla yeni bir modül seçtiğinde tetiklenir.
    Kullanım Alanları:
    - Modüle özgü yardım metnini otomatik göstermek.
    - Modül için varsayılan ayarları yüklemek.
    """
    
    # ==============================================================================
    # Seçenek Yönetimi (Option Management) Hook'ları
    # ==============================================================================
    
    ON_OPTION_SET = "on_option_set"
    """
    Kullanıcı 'set' komutuyla bir modül seçeneğini değiştirdiğinde tetiklenir.
    Kullanım Alanları:
    - Girilen değerin formatını doğrulamak (örn: IP adresi kontrolü).
    - Bir seçenek değiştiğinde diğerini otomatik güncellemek (bağımlı seçenekler).
    """
