"""Logging modülü - Uygulama olaylarını kaydetmek için basit ve güçlü logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
'config/logs/' dizinine kaydeder.
Loglama için 'loguru' kütüphanesi kullanılır; dosya sink'i enqueue ile
asenkron yazılır (komut sıcak yolunu bloklamaz).
"""

import atexit
import contextlib
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Log dosyalarının saklanacağı ana dizin ve dosya yolu belirleniyor.
LOG_DIR = Path(__file__).parent.parent / "config" / "logs"
LOG_FILE = LOG_DIR / "app.log"

_logger = logger
_initialized = False


def setup_logger() -> Any:
    """
    Logger'ı yapılandırır ve başlatır.

    Dosya sink'i `enqueue=True` ile ayrı thread'de yazılır; konsol ERROR
    senkron kalır.
    """
    global _logger, _initialized

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    _logger.remove()

    _logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level="ERROR",
    )

    _logger.add(
        LOG_FILE,
        rotation="500 MB",
        retention="10 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        enqueue=True,
        catch=True,
    )

    _initialized = True
    return _logger


def get_logger() -> Any:
    """Mevcut ve yapılandırılmış logger nesnesini döndürür."""
    initialize_logging_if_needed()
    return _logger


def initialize_logging_if_needed() -> None:
    """Logger yapılandırılmamışsa setup_logger() çağırır."""
    global _initialized
    if not _initialized:
        setup_logger()


def shutdown_logger() -> None:
    """Enqueue edilmiş logların flush edilmesini sağlar."""
    global _initialized
    if _initialized:
        with contextlib.suppress(Exception):
            _logger.remove()
        _initialized = False


atexit.register(shutdown_logger)


def debug(message: str) -> None:
    initialize_logging_if_needed()
    _logger.debug(message)


def info(message: str) -> None:
    initialize_logging_if_needed()
    _logger.info(message)


def warning(message: str) -> None:
    initialize_logging_if_needed()
    _logger.warning(message)


def error(message: str) -> None:
    initialize_logging_if_needed()
    _logger.error(message)
    try:
        from core.hooks import HookType
        from core.shared_state import shared_state

        if hasattr(shared_state, "plugin_manager") and shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(
                HookType.ON_ERROR, message=message, level="error"
            )
    except Exception:
        pass


def critical(message: str) -> None:
    initialize_logging_if_needed()
    _logger.critical(message)


def exception(message: str) -> None:
    initialize_logging_if_needed()
    _logger.exception(message)
    try:
        from core.hooks import HookType
        from core.shared_state import shared_state

        if hasattr(shared_state, "plugin_manager") and shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(
                HookType.ON_ERROR, message=message, level="exception"
            )
    except Exception:
        pass
