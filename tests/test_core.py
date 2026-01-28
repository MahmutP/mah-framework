import pytest
from pathlib import Path
from core.module_manager import ModuleManager
from core.command_manager import CommandManager

def test_module_manager_initialization():
    """Test ModuleManager initialization."""
    mm = ModuleManager()
    assert mm.modules == {}
    # Default directory should be "modules"
    assert mm.modules_dir == Path("modules")

def test_command_manager_initialization():
    """Test CommandManager initialization."""
    cm = CommandManager()
    assert cm.commands == {}
    assert cm.aliases == {}
    # Default directory should be "commands"
    assert cm.commands_dir == Path("commands")
