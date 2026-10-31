"""Logging modülü - Uygulama olaylarını kaydetmek için basit ve güçlü logger.

Bu modül, uygulamanın tüm olaylarını, komut yürütmelerini ve hataları
'config/logs/' dizinine kaydeder.
Loglama için 'loguru' kütüphanesi kullanılır; dosya sink'i enqueue ile
asenkron yazılır (komut sıcak yolunu bloklamaz).

Disk kullanımı sınırlıdır:
- Tek dosya 10 MB'ta döner (rotation), eski dosyalar sıkıştırılır.
- 7 günden eski loglar silinir.
- Toplam log boyutu LOG_MAX_TOTAL_BYTES'ı geçemez (başlangıçta temizlenir).
- `diagnose`/`backtrace` kapalıdır; hata kayıtları dev traceback'lerle şişmez.
"""

import atexit
import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

# Log dosyalarının saklanacağı ana dizin ve dosya yolu belirleniyor.
LOG_DIR = Path(__file__).parent.parent / "config" / "logs"
LOG_FILE = LOG_DIR / "app.log"

# ── Disk kullanım limitleri ───────────────────────────────────────────────────
# Tek bir log dosyası bu boyuta ulaşınca döndürülür.
LOG_ROTATION = "10 MB"
# Döndürülmüş/eski logların saklanma süresi.
LOG_RETENTION_DAYS = 7
LOG_RETENTION = f"{LOG_RETENTION_DAYS} days"
# config/logs altındaki app*.log dosyalarının toplam üst sınırı.
LOG_MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB

_logger = logger
_initialized = False


def _unlink(path: Path) -> int:
    """Dosyayı siler; başarılıysa 1, değilse 0 döndürür."""
    try:
        path.unlink()
        return 1
    except OSError:
        return 0


def cleanup_logs(
    max_total_bytes: int = LOG_MAX_TOTAL_BYTES,
    retention_days: int = LOG_RETENTION_DAYS,
) -> int:
    """Eski/şişmiş log dosyalarını temizler; silinen dosya sayısını döndürür.

    Loguru'nun `retention` ayarı yalnızca rotation anında çalıştığı için,
    daha önce oluşmuş dev dosyalar aksi halde diskte kalır. Bu fonksiyon
    başlangıçta çalışarak:
      1. `retention_days`'ten eski döndürülmüş logları siler,
      2. toplam boyut `max_total_bytes`'ı aşıyorsa en eskiden başlayarak siler,
      3. aktif `app.log` tek başına limiti aşıyorsa onu sıfırlar.
    """
    if not LOG_DIR.exists():
        return 0

    removed = 0
    cutoff = time.time() - retention_days * 86400

    log_files: list[tuple[Path, os.stat_result]] = []
    for path in LOG_DIR.glob("app*.log*"):
        try:
            log_files.append((path, path.stat()))
        except OSError:
            continue

    # En yeni dosya önce sayılsın ki aktif log korunsun.
    log_files.sort(key=lambda item: item[1].st_mtime, reverse=True)

    total = 0
    for path, stat in log_files:
        if path == LOG_FILE:
            # Aktif dosya her zaman korunur; boyutu limiti aşarsa sıfırlanır.
            total += stat.st_size
            continue

        if stat.st_mtime < cutoff or total + stat.st_size > max_total_bytes:
            removed += _unlink(path)
            continue

        total += stat.st_size

    try:
        if LOG_FILE.stat().st_size > max_total_bytes:
            LOG_FILE.write_text("", encoding="utf-8")
            removed += 1
    except OSError:
        pass

    return removed


def setup_logger() -> Any:
    """
    Logger'ı yapılandırır ve başlatır.

    Dosya sink'i `enqueue=True` ile ayrı thread'de yazılır; konsol ERROR
    senkron kalır.
    """
    global _logger, _initialized

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_logs()

    _logger.remove()

    _logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level="ERROR",
    )

    _logger.add(
        LOG_FILE,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        enqueue=True,
        catch=True,
        # diagnose=True her hata kaydına tüm yerel değişkenleri döker; log
        # dosyaları saniyeler içinde yüzlerce MB'a çıkabiliyordu.
        diagnose=False,
        backtrace=False,
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
