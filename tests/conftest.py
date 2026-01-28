import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.shared_state import shared_state

@pytest.fixture(autouse=True)
def reset_shared_state():
    """Reset shared state before each test."""
    # Reset singleton instance state
    shared_state._initialize()
    yield
