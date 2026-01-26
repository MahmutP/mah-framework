"""Logging modülü - Uygulama olaylarını kaydetmek için basit logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
config/logs/ dizinine kaydeder.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

# Log dizini ve dosya yolu
LOG_DIR = Path(__file__).parent.parent / "config" / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Logger instance
_logger = None


def setup_logger():
    """Logger'ı yapılandır ve başlat.
    
    Returns:
        logging.Logger: Yapılandırılmış logger instance.
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # Log dizinini oluştur
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Logger oluştur
    _logger = logging.getLogger("mah_framework")
    _logger.setLevel(logging.DEBUG)
    
    # Eğer handler zaten eklenmişse tekrar ekleme
    if _logger.handlers:
        return _logger
    
    # File handler - dosyaya yazma
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Log formatı: [TIMESTAMP] [LEVEL] - MESSAGE
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Handler'ı logger'a ekle
    _logger.addHandler(file_handler)
    
    return _logger


def get_logger():
    """Mevcut logger instance'ını al.
    
    Returns:
        logging.Logger: Logger instance.
    """
    if _logger is None:
        return setup_logger()
    return _logger


# Kolaylık fonksiyonları
def debug(message):
    """Debug seviyesinde log yaz."""
    get_logger().debug(message)


def info(message):
    """Info seviyesinde log yaz."""
    get_logger().info(message)


def warning(message):
    """Warning seviyesinde log yaz."""
    get_logger().warning(message)


def error(message):
    """Error seviyesinde log yaz."""
    get_logger().error(message)


def critical(message):
    """Critical seviyesinde log yaz."""
    get_logger().critical(message)
