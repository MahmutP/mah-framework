from unittest.mock import MagicMock, patch

from commands.alias import Alias
from commands.back import Back
from commands.banner import BannerCommand
from commands.clear import Clear
from commands.exit import Exit
from commands.help import Help
from commands.history import History
from commands.info import Info
from commands.record import Record
from commands.reload import ReloadCommand
from commands.resource import Resource
from commands.run import Run
from commands.search import Search
from commands.sessions import SessionsCommand
from commands.set import Set
from commands.show import Show
from commands.unset import Unset
from commands.use import Use
from core.shared_state import reset_shared_state


def test_alias_command():
    cmd = Alias()
    assert cmd.Name == "alias"
    assert cmd.Category == "system"
    assert isinstance(cmd.Aliases, list)


def test_back_command():
    cmd = Back()
    assert cmd.Name == "back"
    assert cmd.Category == "module"


def test_banner_command():
    cmd = BannerCommand()
    assert cmd.Name == "banner"
    assert cmd.Category == "system"


def test_clear_command():
    cmd = Clear()
    assert cmd.Name == "clear"
    assert cmd.Category == "system"


def test_exit_command():
    cmd = Exit()
    assert cmd.Name == "exit"
    assert cmd.Category == "core"


def test_help_command():
    cmd = Help()
    assert cmd.Name == "help"
    assert cmd.Category == "core"
    assert len(cmd.Usage) > 0


def test_history_command():
    cmd = History()
    assert cmd.Name == "history"
    assert cmd.Category == "system"


def test_info_command():
    cmd = Info()
    assert cmd.Name == "info"
    assert cmd.Category == "module"


def test_record_command():
    cmd = Record()
    assert cmd.Name == "record"
    assert cmd.Category == "system"


def test_reload_command():
    cmd = ReloadCommand()
    assert cmd.Name == "reload"
    assert cmd.Category == "core"


def test_resource_command():
    cmd = Resource()
    assert cmd.Name == "resource"
    assert cmd.Category == "core"


def test_run_command():
    cmd = Run()
    assert cmd.Name == "run"
    assert cmd.Category == "module"


def test_search_command():
    cmd = Search()
    assert cmd.Name == "search"
    assert cmd.Category == "core"


def test_sessions_command():
    cmd = SessionsCommand()
    assert cmd.Name == "sessions"
    assert cmd.Category == "core"


def test_set_command():
    cmd = Set()
    assert cmd.Name == "set"
    assert cmd.Category == "module"


def test_show_command():
    cmd = Show()
    assert cmd.Name == "show"
    assert cmd.Category == "core"


def test_unset_command():
    cmd = Unset()
    assert cmd.Name == "unset"
    assert cmd.Category == "module"


def test_use_command():
    cmd = Use()
    assert cmd.Name == "use"
    assert cmd.Category == "module"


def test_alias_execute_without_args():
    """Alias komutu argümansız çağrılınca False döndürür."""
    cmd = Alias()
    result = cmd.execute()
    assert result is False


def test_alias_add_and_list():
    """Alias ekleme ve listeleme çalışmalı."""
    reset_shared_state()
    cmd = Alias()

    from core.shared_state import shared_state
    mock_cmd_mgr = MagicMock()
    mock_cmd_mgr.add_alias.return_value = True
    mock_cmd_mgr.get_aliases.return_value = {"ll": "list files"}
    shared_state.command_manager = mock_cmd_mgr

    result = cmd.execute("add", "ll", "list", "files")
    assert result is True

    result_list = cmd.execute("list")
    assert result_list is True


def test_help_execute():
    """Help komutu argümansız çalıştırılabilmeli."""
    cmd = Help()
    from core.shared_state import shared_state
    mock_cmd_mgr = MagicMock()
    mock_cmd_mgr.get_categorized_commands.return_value = {
        "Core": {"help": cmd}
    }
    shared_state.command_manager = mock_cmd_mgr
    result = cmd.execute()
    assert result is True


def test_info_no_module_selected():
    """Modül seçili değilken info komutu False döndürmeli."""
    reset_shared_state()
    cmd = Info()
    result = cmd.execute()
    assert result is False


def test_back_no_module_selected():
    """Modül seçili değilken back komutu False döndürmeli."""
    reset_shared_state()
    cmd = Back()
    result = cmd.execute()
    assert result is False


def test_show_no_module():
    """Modül seçili değilken show komutu False döndürmeli."""
    reset_shared_state()
    cmd = Show()
    result = cmd.execute()
    assert result is False


def test_search_without_query():
    """Search komutu argümansız çağrılınca False döndürmeli."""
    cmd = Search()
    from core.shared_state import shared_state
    mock_mgr = MagicMock()
    mock_mgr.get_all_modules.return_value = {}
    shared_state.module_manager = mock_mgr
    result = cmd.execute()
    assert result is False


def test_search_empty_result():
    """Search komutu eşleşmeyen sorguda boş sonuç döndürmeli."""
    cmd = Search()
    from core.shared_state import shared_state
    mock_mgr = MagicMock()
    mock_mgr.get_all_modules.return_value = {}
    shared_state.module_manager = mock_mgr
    result = cmd.execute("nonexistent_module_xyz")
    assert result is True


def test_run_no_module_selected():
    """Modül seçili değilken run False döndürmeli."""
    reset_shared_state()
    cmd = Run()
    from core.shared_state import shared_state
    mock_mgr = MagicMock()
    shared_state.module_manager = mock_mgr
    result = cmd.execute()
    assert result is False


def test_unset_without_module():
    """Modül seçili değilken unset False döndürmeli."""
    reset_shared_state()
    cmd = Unset()
    result = cmd.execute("RHOST")
    assert result is False


def test_use_invalid_module():
    """Geçersiz modül yolu use komutunda False döndürmeli."""
    cmd = Use()
    result = cmd.execute("nonexistent/path")
    assert result is False


def test_sessions_list_empty():
    """Sessions komutu boş listeyi gösterebilmeli."""
    reset_shared_state()
    cmd = SessionsCommand()
    from core.shared_state import shared_state
    mock_sm = MagicMock()
    mock_sm.get_all_sessions.return_value = {}
    shared_state.session_manager = mock_sm
    result = cmd.execute()
    assert result is True


def test_record_start():
    """Record komutu kayıt başlatabilmeli."""
    reset_shared_state()
    cmd = Record()
    result = cmd.execute("start")
    assert result is True


def test_resource_nonexistent():
    """Var olmayan resource dosyası False döndürmeli."""
    cmd = Resource()
    result = cmd.execute("/nonexistent/file.rc")
    assert result is False


def test_execute_default_return():
    """Exit komutu çalışmalı."""
    cmd = Exit()
    from core.shared_state import shared_state
    mock_console = MagicMock()
    mock_console.running = True
    shared_state.console_instance = mock_console
    result = cmd.execute()
    assert result is True


def test_command_has_category():
    """Her komutun geçerli bir kategorisi olmalı."""
    commands = [
        Alias(), Back(), BannerCommand(), Clear(), Exit(), Help(), History(),
        Info(), Record(), ReloadCommand(), Resource(), Run(), Search(),
        SessionsCommand(), Set(), Show(), Unset(), Use(),
    ]
    valid_categories = {"core", "module", "system"}
    for cmd in commands:
        assert cmd.Category in valid_categories, f"{cmd.Name} invalid category: {cmd.Category}"


def test_command_has_description():
    """Her komutun açıklaması olmalı."""
    commands = [
        Alias(), Back(), BannerCommand(), Clear(), Exit(), Help(), History(),
        Info(), Record(), ReloadCommand(), Resource(), Run(), Search(),
        SessionsCommand(), Set(), Show(), Unset(), Use(),
    ]
    for cmd in commands:
        assert cmd.Description, f"{cmd.Name} empty description"
        assert cmd.Description != "Description for command", f"{cmd.Name} default description"


def test_banner_execute():
    """Banner komutu çalıştırılabilmeli."""
    cmd = BannerCommand()
    result = cmd.execute()
    assert result is True


def test_history_execute():
    """History komutu çalıştırılabilmeli."""
    cmd = History()
    from core.shared_state import shared_state
    mock_console = MagicMock()
    mock_console.history = MagicMock()
    mock_console.history.get_string.return_value = "test\nhelp\n"
    shared_state.console_instance = mock_console
    result = cmd.execute()
    assert result is True


def test_reload_execute():
    """Reload komutu çalıştırılabilmeli."""
    cmd = ReloadCommand()
    from core.shared_state import shared_state
    mock_mgr = MagicMock()
    mock_mgr.load_modules.return_value = None
    shared_state.module_manager = mock_mgr
    result = cmd.execute("all")
    assert result is True


def test_set_empty_args():
    """Set komutu argümansız çağrılır, modül varsa False döndürmeli."""
    reset_shared_state()
    cmd = Set()
    from core.shared_state import shared_state
    mock_module = MagicMock()
    mock_module.get_options.return_value = {}
    shared_state.selected_module = mock_module
    result = cmd.execute()
    assert result is False


def test_session_command_attributes():
    """Sessions komutunun alias ve usage bilgileri olmalı."""
    cmd = SessionsCommand()
    assert cmd.Name == "sessions"
    assert cmd.Category == "core"