# Geriye uyumluluk katmanı - SharedState singleton artık AppContext wrapper'ıdır.
# Yeni kod DI (Dependency Injection) ile AppContext/ServiceContainer kullanmalıdır.

from typing import Any

from core.context import AppContext, get_global_context


class SharedState:
    """
    Paylaşılan Durum (Shared State) - Geriye Uyumluluk Wrapper.

    Bu sınıf artık singleton DEĞİLDIR. Global AppContext'e delegate eder.
    Yeni kod: `container.resolve(AppContext)` veya constructor injection kullanmalı.
    Eski kod: `from core.shared_state import shared_state` çalışmaya devam eder.
    """

    def __init__(self) -> None:
        pass

    @property
    def _ctx(self) -> AppContext:
        return get_global_context()

    # --- Modül Durumu ---
    @property
    def selected_module(self) -> Any:
        return self._ctx.selected_module

    @selected_module.setter
    def selected_module(self, value: Any) -> None:
        self._ctx.selected_module = value

    # --- Servis Referansları ---
    @property
    def command_manager(self) -> Any:
        return self._ctx.command_manager

    @command_manager.setter
    def command_manager(self, value: Any) -> None:
        self._ctx.command_manager = value

    @property
    def module_manager(self) -> Any:
        return self._ctx.module_manager

    @module_manager.setter
    def module_manager(self, value: Any) -> None:
        self._ctx.module_manager = value

    @property
    def console_instance(self) -> Any:
        return self._ctx.console_instance

    @console_instance.setter
    def console_instance(self, value: Any) -> None:
        self._ctx.console_instance = value

    @property
    def plugin_manager(self) -> Any:
        return self._ctx.plugin_manager

    @plugin_manager.setter
    def plugin_manager(self, value: Any) -> None:
        self._ctx.plugin_manager = value

    @property
    def session_manager(self) -> Any:
        return self._ctx.session_manager

    @session_manager.setter
    def session_manager(self, value: Any) -> None:
        self._ctx.session_manager = value

    @property
    def repo_manager(self) -> Any:
        return self._ctx.repo_manager

    @repo_manager.setter
    def repo_manager(self, value: Any) -> None:
        self._ctx.repo_manager = value

    @property
    def module_downloader(self) -> Any:
        return self._ctx.module_downloader

    @module_downloader.setter
    def module_downloader(self, value: Any) -> None:
        self._ctx.module_downloader = value

    @property
    def plugin_downloader(self) -> Any:
        return self._ctx.plugin_downloader

    @plugin_downloader.setter
    def plugin_downloader(self, value: Any) -> None:
        self._ctx.plugin_downloader = value

    # --- Makro ve Kayıt Özellikleri ---
    @property
    def is_recording(self) -> bool:
        return self._ctx.is_recording

    @is_recording.setter
    def is_recording(self, value: bool) -> None:
        self._ctx.is_recording = value

    @property
    def recorded_commands(self) -> list:
        return self._ctx.recorded_commands

    @recorded_commands.setter
    def recorded_commands(self, value: list) -> None:
        self._ctx.recorded_commands = value

    def get_selected_module(self) -> Any:
        return self._ctx.get_selected_module()

    def set_selected_module(self, module_obj: Any) -> None:
        self._ctx.set_selected_module(module_obj)


# Geriye uyumluluk için global instance (eski kod bu import ediyor)
shared_state = SharedState()


# Testler için yardımcı fonksiyonlar
def reset_shared_state() -> None:
    """Testler arası shared state'i sıfırlar."""
    from core.context import reset_global_context

    reset_global_context()