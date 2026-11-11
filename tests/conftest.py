from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo() -> Path:
    return Path(__file__).resolve().parent.parent
