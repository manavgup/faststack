"""Auto-mark all tests in test_core/ as unit tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "/test_core/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
