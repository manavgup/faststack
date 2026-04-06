"""Auto-mark all tests in test_templates/ as unit tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "/test_templates/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
