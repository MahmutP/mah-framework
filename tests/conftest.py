import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.shared_state import reset_shared_state as _reset_shared_state
from core.service_container import reset_container as _reset_container


@pytest.fixture(autouse=True)
def auto_reset_test_state():
    """Reset shared state and container before each test."""
    _reset_shared_state()
    _reset_container()
    yield