# core/cont.py
# Bu dosya, tüm framework genelinde kullanılan sabit (değişmeyen) değerleri içerir.
# Ayarlar, varsayılan değerler ve yapılandırma parametreleri buradan yönetilir.

# ==============================================================================
# LOGLAMA SABİTLERİ
# Uygulamanın loglama sistemi için temel ayarları tanımlar.
# ==============================================================================
LOG_LEVELS = {
    # Hata ayıklama seviyesi: Geliştirme sırasında detaylı bilgileri loglamak için kullanılır.
    # Değişken değerleri, fonksiyon giriş-çıkışları gibi detaylar buradadır.
    "DEBUG": 10,
    
    # Bilgi seviyesi: Uygulamanın normal çalışması sırasındaki önemli olayları loglar.
    # Örn: "Sunucu başlatıldı", "Bağlantı kabul edildi".
    "INFO": 20,
    
    # Uyarı seviyesi: Potansiyel sorunlara işaret eden ancak uygulamayı durdurmayan olayları loglar.
    # Örn: "Disk alanı azalıyor", "Bilinmeyen yapılandırma parametresi".
    "WARNING": 30,
    
    # Hata seviyesi: Bir işlevin düzgün çalışmasını engelleyen hataları loglar.
    # Örn: "Dosya bulunamadı", "Bağlantı koptu".
    "ERROR": 40,
    
    # Kritik seviye: Uygulamanın tamamen durmasına neden olabilecek çok ciddi hataları loglar.
    # Örn: "Bellek doldu", "Çekirdek modül yüklenemedi".
    "CRITICAL": 50
}

# Varsayılan loglama seviyesi. Bu seviyedeki ve bu seviyeden daha yüksek
# seviyelerdeki (sayısal olarak daha büyük) log mesajları işlenecektir.
DEFAULT_LOG_LEVEL = "INFO"

# Log dosyalarının saklanacağı dizin yolu.
# Bu dizin, logları kalıcı olarak diske kaydetmek için oluşturulur.
LOG_DIR = "config/logs"

# ==============================================================================
# YAPILANDIRMA VE KALICILIK SABİTLERİ
# Uygulama durumunu ve kullanıcı ayarlarını saklayan dosyaları tanımlar.
# ==============================================================================

# Komut takma adlarının (aliases) kalıcı olarak saklandığı JSON dosyasının yolu.
# Bu dosya, CommandManager tarafından okunur ve yazılır.
ALIASES_FILE = "config/aliases.json"

# ==============================================================================
# KONSOL VE ÇIKTI BİÇİMLENDİRME SABİTLERİ
# Terminal çıktılarının düzenlenmesi ve hizalanması için kullanılır.
# ==============================================================================

# Terminal genişliği belirlenemediğinde (örn: pipe kullanımında) kullanılacak varsayılan sütun sayısı.
# Çıktıların taşmasını veya bozuk görünmesini önlemek için bir yedek değerdir.
DEFAULT_TERMINAL_WIDTH = 120

# Tablo ve liste çıktılarının başlangıcındaki sol kenar boşluğu (indentation).
LEFT_PADDING = 4

# Tablo sütunları arasındaki minimum boşluk (whitespace).
COL_SPACING = 4

# Otomatik tamamlama veya hizalama için kullanılan 'Tab' karakterinin genişliği.
TAB_SPING = 8

# ==============================================================================
# KOMUT VE MODÜL YÖNETİMİ SABİTLERİ
# Komut ve modül kategorilerini ve varsayılan davranışları tanımlar.
# ==============================================================================

# Komutların kategorilerini ve bunların kullanıcıya gösterilecek başlıklarını
# tanımlayan sözlük. Bu, 'help' komutunun çıktısını düzenler ve gruplar.
COMMAND_CATEGORIES = {
    "core": "Core Commands",      # Uygulamanın temel komutları (help, exit, vb.)
    "module": "Module Commands",  # Modüllerle etkileşim komutları (use, set, run, vb.)
    "system": "System Commands"   # Sistemle ilgili komutlar (alias, clear, shell, vb.)
}

# Modül seçenekleri (Option) için varsayılan regex deseni.
# Bir seçenek için özel bir doğrulama kuralı (regex) tanımlanmadığında, 
# bu desen (herhangi bir karakter dizisi) kullanılır.
DEFAULT_REGEX = r".*"

# ==============================================================================
# UYGULAMA METADATA SABİTLERİ (Bilgi Amaçlı)
# ==============================================================================

# Uygulamanın gösterim adı (prompt veya banner için kullanılabilir).
APP_NAME = "Mah Framework"

# Uygulamanın versiyon numarası. Güncellemelerle birlikte artırılır.
APP_VERSION = "1.0.0"

# Geliştiricinin iletişim bilgisi veya ekip adı.
APP_AUTHOR = "MahmutP."
