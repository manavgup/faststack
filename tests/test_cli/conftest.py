"""Auto-mark all tests in test_cli/ as integration tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "/test_cli/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
