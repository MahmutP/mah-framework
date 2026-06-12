# Uygulama bağlamı (Application Context) - Çalışma zamanı durumunu ve servis referanslarını tutar.
# SharedState'in işlevlerini taşır ancak singleton DEĞILDIR, DI ile enjekte edilir.

from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from core.hooks import HookType


@dataclass
class AppContext:
    """
    Uygulama Bağlamı (Application Context).

    Framework'ün çalışma zamanındaki durumunu ve servis referanslarını tutar.
    Her test veya çalışma örneği için ayrı bir context oluşturulabilir.
    Thread-safe değildir, tek thread'de kullanım için tasarlanmıştır.
    """

    # --- Modül Durumu ---
    selected_module: Any = None

    # --- Servis Referansları ---
    command_manager: Any = None
    module_manager: Any = None
    console_instance: Any = None
    plugin_manager: Any = None
    session_manager: Any = None
    repo_manager: Any = None
    module_downloader: Any = None
    plugin_downloader: Any = None

    # --- Makro ve Kayıt Özellikleri ---
    is_recording: bool = False
    recorded_commands: list = field(default_factory=list)

    # --- Hook/Event Sistemı ---
    _hook_handlers: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Hook handler sözlüğünü başlat."""
        for hook in HookType:
            self._hook_handlers[hook] = []

    # --- Modül Seçimi ---
    def get_selected_module(self) -> Any:
        """O anki seçili modülü döndürür."""
        return self.selected_module

    def set_selected_module(self, module_obj: Any) -> None:
        """Seçili modülü günceller."""
        self.selected_module = module_obj

    # --- Hook Yönetimi ---
    def register_hook(self, hook_type: HookType, priority: int, handler: Callable[..., Any]) -> None:
        """Hook handler kaydeder."""
        self._hook_handlers[hook_type].append((priority, handler))
        self._hook_handlers[hook_type].sort(key=lambda x: x[0])

    def unregister_hook(self, hook_type: HookType, handler: Callable[..., Any]) -> None:
        """Hook handler siler."""
        self._hook_handlers[hook_type] = [
            (p, h) for p, h in self._hook_handlers[hook_type] if h != handler
        ]

    def trigger_hook(self, hook_type: HookType, **kwargs: Any) -> None:
        """Hook tetikler."""
        handlers: list = self._hook_handlers.get(hook_type, [])
        for _, handler in handlers:
            if callable(handler):
                try:
                    handler(**kwargs)
                except Exception:
                    pass


# Geriye uyumluluk için global context (kademeli geçiş için)
# Yeni kod AppContext'i DI ile almalı, eski kod shared_state'i kullanabilir.
_global_context: AppContext | None = None


def get_global_context() -> AppContext:
    """Global context'i döndürür, yoksa oluşturur."""
    global _global_context
    if _global_context is None:
        _global_context = AppContext()
    return _global_context


def set_global_context(ctx: AppContext) -> None:
    """Global context'i değiştirir (testler için)."""
    global _global_context
    _global_context = ctx


def reset_global_context() -> None:
    """Global context'i sıfırlar (testler için)."""
    global _global_context
    _global_context = AppContext()