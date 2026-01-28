import pytest
from commands.help import Help
from commands.set import Set
from core.shared_state import shared_state

def test_help_command_structure():
    """Test Help command metadata."""
    cmd = Help()
    assert cmd.Name == "help"
    assert cmd.Category == "core"

def test_set_command_execution():
    """Test Set command functionality."""
    cmd = Set()
    
    # Mock a selected module (would be handled by shared_state in integration)
    # But for unit test, 'set' interacts with shared_state.selected_module
    
    # If no module selected, it should print info (return True usually, or handled)
    # This is a basic test to ensure class instantiation works
    assert cmd.Name == "set"
