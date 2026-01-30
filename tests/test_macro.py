import os
import pytest
from commands.record import Record
from core.shared_state import shared_state

@pytest.fixture
def clean_state():
    """Reset shared state before each test."""
    shared_state.is_recording = False
    shared_state.recorded_commands = []
    yield
    shared_state.is_recording = False
    shared_state.recorded_commands = []

def test_record_start(clean_state):
    """Test start recording."""
    cmd = Record()
    assert cmd.execute("start") is True
    assert shared_state.is_recording is True
    assert shared_state.recorded_commands == []

def test_record_status(clean_state, capsys):
    """Test recording status."""
    cmd = Record()
    
    # Not recording
    assert cmd.execute("status") is True
    captured = capsys.readouterr()
    assert "Kaydedilen komut yok" in captured.out
    
    # Start recording
    cmd.execute("start")
    shared_state.recorded_commands.append("show options")
    
    assert cmd.execute("status") is True
    captured = capsys.readouterr()
    assert "Kayıt DEVAM EDİYOR" in captured.out
    assert "kaydedilen komut sayısı: 1" in captured.out

def test_record_stop_no_file(clean_state, capsys):
    """Test stopping without saving (just display)."""
    cmd = Record()
    cmd.execute("start")
    shared_state.recorded_commands.append("use exploit/test")
    
    assert cmd.execute("stop") is True
    captured = capsys.readouterr()
    
    assert shared_state.is_recording is False
    assert shared_state.recorded_commands == [] # Should be cleared
    assert "Kaydedilen Komutlar (1)" in captured.out
    assert "use exploit/test" in captured.out

def test_record_stop_with_file(clean_state, tmp_path):
    """Test stopping and saving to file."""
    cmd = Record()
    cmd.execute("start")
    shared_state.recorded_commands.append("help")
    shared_state.recorded_commands.append("exit")
    
    # Create a temporary file path
    output_file = tmp_path / "test_macro.rc"
    file_path_str = str(output_file)
    
    assert cmd.execute("stop", file_path_str) is True
    
    assert shared_state.is_recording is False
    assert shared_state.recorded_commands == []
    
    # Check file content
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    expected = "help\nexit\n"
    assert content == expected

def test_record_stop_auto_extension(clean_state, tmp_path):
    """Test automatic .rc extension."""
    cmd = Record()
    cmd.execute("start")
    shared_state.recorded_commands.append("banner")
    
    # Provide filename without extension
    base_name = "my_macro"
    output_path = tmp_path / f"{base_name}.rc"
    full_path_str = str(tmp_path / base_name) # Passing without extension
    
    assert cmd.execute("stop", full_path_str) is True
    
    # Check if file exists with .rc extension
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content == "banner\n"
