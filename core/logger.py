"""Logging modülü - Uygulama olaylarını kaydetmek için basit ve güçlü logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
'config/logs/' dizinine kaydeder.
Loglama için 'loguru' kütüphanesi kullanılır, bu da standart logging modülüne göre 
daha kolay yapılandırma ve daha iyi performans sağlar.
"""

from pathlib import Path
from loguru import logger
import sys

# Log dosyalarının saklanacağı ana dizin ve dosya yolu belirleniyor.
# __file__ ile bu dosyanın bulunduğu konumu alıp, iki üst dizine (framework köküne) çıkarız.
LOG_DIR = Path(__file__).parent.parent / "config" / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Logger instance'ı (örneği). 
# Loguru aslında tekil (singleton) bir logger sağlar ama uyumluluk ve kolay erişim için değişkene atıyoruz.
_logger = logger

def setup_logger():
    """
    Logger'ı yapılandırır ve başlatır.
    Bu fonksiyon uygulamanın en başında çalıştırılmalıdır.
    
    Yapılandırma detayları:
    1. Log dizini yoksa oluşturur.
    2. Konsola (stderr) sadece ERROR seviyesindeki kritik mesajları basar.
    3. Dosyaya (app.log) tüm detayları (DEBUG seviyesi dahil) yazar.
    4. Dosya boyutuna göre otomatik döndürme (rotation) ve eski dosyaları silme (retention) yapar.
    
    Returns:
        loguru.logger: Yapılandırılmış logger nesnesi.
    """
    global _logger
    
    # Log dizinini oluştur (parents=True: aradaki eksik klasörleri de oluşturur)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Mevcut tüm handler'ları (işleyicileri) temizle.
    # Loguru varsayılan olarak stderr'e her şeyi basar, bunu istemiyoruz.
    _logger.remove()
    
    # ==============================================================================
    # 1. Konsol Çıktısı (Handler)
    # ==============================================================================
    # Konsola sadece hataları basacağız, böylece kullanıcının ekranı debug mesajlarıyla dolmaz.
    _logger.add(
        sys.stderr, # Çıktı hedefi (Standard Error Stream)
        format="<level>{level: <8}</level> | <level>{message}</level>", # Basit format
        level="ERROR" # Sadece ERROR ve üzeri (CRITICAL) mesajları göster
    )
    
    # ==============================================================================
    # 2. Dosya Çıktısı (Handler)
    # ==============================================================================
    # Dosyaya her şeyi (DEBUG dahil) detaylı bir şekilde yazacağız.
    _logger.add(
        LOG_FILE, # Hedef dosya yolu
        rotation="500 MB", # Dosya 500 MB olunca yeni dosyaya geç (app.log.1, app.log.2...)
        retention="10 days", # 10 günden eski log dosyalarını otomatik sil
        encoding="utf-8", # Türkçe karakter sorunu olmaması için UTF-8
        # Detaylı format: Tarih | Seviye | Dosya:Fonksiyon:Satır - Mesaj
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG" # En düşük seviye, yani her şeyi kaydet
    )
    
    return _logger

def get_logger():
    """
    Mevcut ve yapılandırılmış logger nesnesini döndürür.
    Eğer logger henüz yapılandırılmamışsa, lazy initialization (talep anında başlatma) yapar.
    
    Returns:
        loguru.logger: Kullanıma hazır logger nesnesi.
    """
    # Aşağıdaki yardımcı fonksiyon sayesinde, logger yapılandırılmamışsa bile otomatik yapılandırılır.
    return _logger

# Logger'ın başlatılıp başlatılmadığını takip eden bayrak (flag).
# Modül seviyesinde global bir değişkendir.
_initialized = False

def initialize_logging_if_needed():
    """
    Logger'ın daha önce yapılandırılıp yapılandırılmadığını kontrol eder.
    Eğer yapılandırılmamışsa setup_logger() fonksiyonunu çağırır.
    Bu, geliştiricinin manuel olarak setup çağırmayı unuttuğu durumlar için bir güvenlik önlemidir.
    """
    global _initialized
    if not _initialized:
        setup_logger()
        _initialized = True

# ==============================================================================
# Kolaylık Fonksiyonları (Wrapper Functions)
# ==============================================================================
# Geliştiricilerin direkt `core.logger.debug("mesaj")` şeklinde kullanabilmesi için
# Loguru metodlarını sarmalıyoruz (wrap). Ayrıca her çağrıda başlatma kontrolü yapıyoruz.

def debug(message):
    """
    Debug seviyesinde (en detaylı) log kaydı oluşturur.
    Geliştirme aşamasında değişken değerlerini izlemek için kullanılır.
    """
    initialize_logging_if_needed()
    _logger.debug(message)


def info(message):
    """
    Info seviyesinde (bilgilendirme) log kaydı oluşturur.
    Uygulamanın normal akışını takip etmek için kullanılır (örn: Modül yüklendi).
    """
    initialize_logging_if_needed()
    _logger.info(message)


def warning(message):
    """
    Warning seviyesinde (uyarı) log kaydı oluşturur.
    Hata olmayan ama dikkat edilmesi gereken durumlar için (örn: Konfigürasyon eksik).
    """
    initialize_logging_if_needed()
    _logger.warning(message)


def error(message):
    """
    Error seviyesinde (hata) log kaydı oluşturur.
    İşlemin başarısız olduğu durumlarda kullanılır.
    """
    initialize_logging_if_needed()
    _logger.error(message)


def critical(message):
    """
    Critical seviyesinde (kritik hata) log kaydı oluşturur.
    Uygulamanın çökmesine neden olabilecek ciddi sorunlar için.
    """
    initialize_logging_if_needed()
    _logger.critical(message)


def exception(message):
    """
    Bir Exception (Hata) yakalandığında kullanılır.
    Hata mesajıyla birlikte tam yığın izini (traceback) de loglar.
    Bu sayede hatanın kodun neresinde oluştuğu tam olarak görülebilir.
    """
    initialize_logging_if_needed()
    _logger.exception(message)
