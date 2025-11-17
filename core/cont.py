# core/cont.py

# ==============================================================================
# LOGLAMA SABİTLERİ
# Uygulamanın loglama sistemi için temel ayarları tanımlar.
# ==============================================================================
# Henüz logging yapısı kodlanmadı.
LOG_LEVELS = {
    # Hata ayıklama seviyesi: Geliştirme sırasında detaylı bilgileri loglamak için kullanılır.
    "DEBUG": 10,
    # Bilgi seviyesi: Uygulamanın normal çalışması sırasındaki önemli olayları loglar.
    "INFO": 20,
    # Uyarı seviyesi: Potansiyel sorunlara işaret eden ancak uygulamayı durdurmayan olayları loglar.
    "WARNING": 30,
    # Hata seviyesi: Bir işlevin düzgün çalışmasını engelleyen hataları loglar.
    "ERROR": 40,
    # Kritik seviye: Uygulamanın tamamen durmasına neden olabilecek çok ciddi hataları loglar.
    "CRITICAL": 50
}

# Varsayılan loglama seviyesi. Bu seviyedeki ve bu seviyeden daha yüksek
# seviyelerdeki (sayısal olarak daha büyük) log mesajları işlenecektir.
DEFAULT_LOG_LEVEL = "INFO"

# Log dosyalarının saklanacağı dizin yolu.
# Bu dizin, logları kalıcı olarak diske kaydetmek için kullanılır.
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

# Terminal genişliği belirlenemediğinde kullanılacak varsayılan sütun sayısı.
# Çıktıların taşmasını önlemek için bir yedek değerdir.
DEFAULT_TERMINAL_WIDTH = 120

# Tablo ve liste çıktılarının başlangıcındaki sol kenar boşluğu (boşluk sayısı).
LEFT_PADDING = 4

# Tablo sütunları arasındaki minimum boşluk (boşluk sayısı).
COL_SPACING = 4

# Otomatik tamamlama için kullanılan 'Tab' karakterinin genişliği (şu an kullanılmıyor olabilir
# ancak genel terminal çıktıları için bir standart tanımlar).
TAB_SPING = 8

# ==============================================================================
# KOMUT VE MODÜL YÖNETİMİ SABİTLERİ
# Komut ve modül kategorilerini tanımlar.
# ==============================================================================

# Komutların kategorilerini ve bunların kullanıcıya gösterilecek başlıklarını
# tanımlayan sözlük. Bu, 'help' komutunun çıktısını düzenler.
COMMAND_CATEGORIES = {
    "core": "Core Commands",      # Uygulamanın temel komutları (help, exit, vb.)
    "module": "Module Commands",  # Modüllerle etkileşim komutları (use, set, run, vb.)
    "system": "System Commands"   # Sistemle ilgili komutlar (alias, clear, shell, vb.)
}

# Modül seçenekleri için varsayılan regex deseni.
# Bir seçenek için özel bir regex tanımlanmadığında, bu desen (herhangi bir karakter)
# kullanılır, bu da her türlü değere izin verildiği anlamına gelir.
DEFAULT_REGEX = r".*"

# ==============================================================================
# UYGULAMA METADATA SABİTLERİ (İsteğe Bağlı Eklemeler)
# ==============================================================================

# Uygulamanın gösterim adı (prompt veya banner için kullanılabilir).
APP_NAME = "Mah Framework"

# Uygulamanın versiyon numarası.
APP_VERSION = "1.0.0"

# Geliştiricinin iletişim bilgisi veya ekip adı.
APP_AUTHOR = "MahmutP."
