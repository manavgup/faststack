"""Auto-mark all tests in test_e2e/ as e2e tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "/test_e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
