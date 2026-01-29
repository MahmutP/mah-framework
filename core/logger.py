"""Logging modülü - Uygulama olaylarını kaydetmek için basit logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
config/logs/ dizinine kaydeder.
"""
"""Logging modülü - Uygulama olaylarını kaydetmek için basit logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
config/logs/ dizinine kaydeder.
"""
from pathlib import Path
from loguru import logger
import sys

# Log dizini ve dosya yolu
LOG_DIR = Path(__file__).parent.parent / "config" / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Logger instance (Loguru already provides a singleton, but we maintain the variable for compatibility if needed)
_logger = logger

def setup_logger():
    """Logger'ı yapılandır ve başlat.
    
    Returns:
        loguru.logger: Yapılandırılmış logger instance.
    """
    global _logger
    
    # Log dizinini oluştur
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Mevcut handler'ları temizle (Loguru default handler'ı da dahil)
    _logger.remove()
    
    # Konsol çıktısı (Sadece hata ve kritik durumlar, minimal format)
    _logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level="ERROR"
    )
    
    # Dosya çıktısı (Rotation ve Retention ile)
    _logger.add(
        LOG_FILE,
        rotation="500 MB",
        retention="10 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    return _logger


def get_logger():
    """Mevcut logger instance'ını al.
    
    Returns:
        loguru.logger: Logger instance.
    """
    # Loguru singleton olduğu için ve setup_logger idempotent tasarlandığı için
    # her seferinde setup çağrısı yapmak yerine, sadece configure edilip edilmediğini kontrol edebiliriz
    # Basitlik için burada setup_logger'ı çağırıyoruz, loguru.add duplicate handler eklemez (sink ID kontrolü gerekir ama burada remove() çağırıyoruz setup'ta).
    # Ancak performans için sadece logger'ı döndürelim, configuration main.py başında yapılmalı normalde.
    # Mevcut yapıya uyum sağlamak için setup_logger'ı burada çağırabiliriz ama duplicate handler sorunu olmasın diye
    # setup_logger içinde remove() var. Bu yüzden her get_logger çağrısında handler'lar silinip tekrar eklenir.
    # Bu verimsiz. O yüzden basit bir flag kullanabiliriz veya sadece logger döndürürüz.
    # En doğrusu: setup_logger uygulamanın başında bir kere çağrılmalı. 
    # Ama mevcut kod yapısını bozmamak için burada lazy initialization yapalım.
    
    # Not: Loguru zaten yapılandırılmışsa tekrar yapılandırmamak lazım.
    # Ancak loguru'nun "handlers" listesine doğrudan erişim yok (internal).
    # Basit bir çözüm olarak module level bir flag kullanabiliriz.
    
    return _logger

# Module level flag to track initialization
_initialized = False

def initialize_logging_if_needed():
    global _initialized
    if not _initialized:
        setup_logger()
        _initialized = True

# Kolaylık fonksiyonları - Loguru metodlarını wrap ediyoruz
def debug(message):
    """Debug seviyesinde log yaz."""
    initialize_logging_if_needed()
    _logger.debug(message)


def info(message):
    """Info seviyesinde log yaz."""
    initialize_logging_if_needed()
    _logger.info(message)


def warning(message):
    """Warning seviyesinde log yaz."""
    initialize_logging_if_needed()
    _logger.warning(message)


def error(message):
    """Error seviyesinde log yaz."""
    initialize_logging_if_needed()
    _logger.error(message)


def critical(message):
    """Critical seviyesinde log yaz."""
    initialize_logging_if_needed()
    _logger.critical(message)


def exception(message):
    """Exception log yaz."""
    initialize_logging_if_needed()
    _logger.exception(message)

