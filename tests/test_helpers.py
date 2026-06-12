"""Test helper'ları - Mock servis sağlayıcıları ve test verisi oluşturma araçları."""

from typing import Any
from unittest.mock import MagicMock

from core.context import AppContext
from core.service_container import ServiceContainer


def make_mock_command_manager() -> MagicMock:
    """Mock CommandManager oluşturur."""
    mgr = MagicMock()
    mgr.get_all_commands.return_value = {}
    mgr.get_categorized_commands.return_value = {}
    mgr.resolve_command.return_value = (None, False)
    mgr.execute_command.return_value = True
    mgr.get_aliases.return_value = {}
    return mgr


def make_mock_module_manager() -> MagicMock:
    """Mock ModuleManager oluşturur."""
    mgr = MagicMock()
    mgr.get_all_modules.return_value = {}
    mgr.get_modules_by_category.return_value = {}
    mgr.get_module.return_value = None
    mgr.load_modules.return_value = None
    return mgr


def make_mock_plugin_manager() -> MagicMock:
    """Mock PluginManager oluşturur."""
    mgr = MagicMock()
    mgr.get_all_plugins.return_value = {}
    mgr.get_plugin.return_value = None
    mgr.get_enabled_plugins.return_value = {}
    mgr.trigger_hook.return_value = None
    mgr.load_plugins.return_value = None
    return mgr


def make_mock_session_manager() -> MagicMock:
    """Mock SessionManager oluşturur."""
    mgr = MagicMock()
    mgr.get_all_sessions.return_value = {}
    mgr.get_session.return_value = None
    mgr.add_session.return_value = "session_1"
    mgr.remove_session.return_value = True
    mgr.shutdown_all.return_value = None
    return mgr


def make_mock_repo_manager() -> MagicMock:
    """Mock RepoManager oluşturur."""
    mgr = MagicMock()
    mgr.list_repos.return_value = {}
    return mgr


def make_test_context() -> AppContext:
    """Testler için dolu bir AppContext oluşturur."""
    ctx = AppContext()
    ctx.command_manager = make_mock_command_manager()
    ctx.module_manager = make_mock_module_manager()
    ctx.plugin_manager = make_mock_plugin_manager()
    ctx.session_manager = make_mock_session_manager()
    ctx.repo_manager = make_mock_repo_manager()
    return ctx


def make_test_container(ctx: AppContext | None = None) -> ServiceContainer:
    """Testler için dolu bir ServiceContainer oluşturur."""
    container = ServiceContainer()
    if ctx is None:
        ctx = make_test_context()
    container.register(AppContext, ctx)
    container.register(type(ctx.command_manager), ctx.command_manager)
    container.register(type(ctx.module_manager), ctx.module_manager)
    container.register(type(ctx.plugin_manager), ctx.plugin_manager)
    container.register(type(ctx.session_manager), ctx.session_manager)
    container.register(type(ctx.repo_manager), ctx.repo_manager)
    return container


def create_test_module_class(
    name: str = "TestModule",
    description: str = "Test module",
    author: str = "tester",
    category: str = "test",
    version: str = "1.0",
    options: dict | None = None,
) -> type:
    """Test modül sınıfı oluşturur (factory pattern)."""
    opts = options or {}

    class _TestModule:
        Name = name
        Description = description
        Author = author
        Category = category
        Version = version
        Path = f"test/{name.lower()}"
        Options = opts
        Requirements: dict[str, list[str]] = {}

        def __init__(self) -> None:
            for opt_name, opt_value in self.Options.items():
                setattr(self, opt_name, opt_value.value if hasattr(opt_value, 'value') else opt_value)

        def run(self, options: dict[str, Any]) -> str:
            return f"[{self.Name}] ok"

        def get_options(self) -> dict:
            return self.Options

        def get_option_value(self, name: str) -> Any:
            opt = self.Options.get(name)
            if opt:
                return opt.value if hasattr(opt, 'value') else opt
            return None

        def set_option_value(self, name: str, value: Any) -> bool:
            self.Options[name] = value
            return True

        def check_required_options(self) -> bool:
            return True

        def check_dependencies(self) -> bool:
            return True

    return _TestModule


def create_mock_option(
    name: str = "RHOST",
    default: str = "",
    required: bool = True,
    description: str = "Test option",
) -> MagicMock:
    """Mock Option nesnesi oluşturur."""
    opt = MagicMock()
    opt.name = name
    opt.value = default
    opt.required = required
    opt.description = description
    return opt