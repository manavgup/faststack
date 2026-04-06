"""Tests for the logging module: masking, structured logger, and config."""

import logging

from faststack_core.logging.config import LogConfig
from faststack_core.logging.masking import MASK_VALUE, SensitiveDataFilter, mask_sensitive_data
from faststack_core.logging.structured_logger import (
    StructuredLogger,
    correlation_id_var,
    get_correlation_id,
)

# ---------------------------------------------------------------------------
# LogConfig
# ---------------------------------------------------------------------------


def test_log_config_defaults():
    config = LogConfig()
    assert config.level == "INFO"
    assert config.format == "json"
    assert "password" in config.sensitive_patterns


def test_log_config_custom():
    config = LogConfig(level="DEBUG", format="text", app_name="myapp")
    assert config.level == "DEBUG"
    assert config.app_name == "myapp"


# ---------------------------------------------------------------------------
# Sensitive data masking
# ---------------------------------------------------------------------------


def test_mask_simple_dict():
    data = {"username": "alice", "password": "secret123"}
    result = mask_sensitive_data(data)
    assert result["username"] == "alice"
    assert result["password"] == MASK_VALUE


def test_mask_does_not_mutate_input():
    data = {"password": "original"}
    mask_sensitive_data(data)
    assert data["password"] == "original"


def test_mask_nested_dict():
    data = {"user": {"name": "alice", "api_key": "abc123"}}
    result = mask_sensitive_data(data)
    assert result["user"]["name"] == "alice"
    assert result["user"]["api_key"] == MASK_VALUE


def test_mask_list_of_dicts():
    data = [{"token": "xyz"}, {"name": "bob"}]
    result = mask_sensitive_data(data)
    assert result[0]["token"] == MASK_VALUE
    assert result[1]["name"] == "bob"


def test_mask_case_insensitive():
    data = {"Password": "secret", "API_KEY": "abc"}
    result = mask_sensitive_data(data)
    assert result["Password"] == MASK_VALUE
    assert result["API_KEY"] == MASK_VALUE


def test_mask_respects_depth_limit():
    data = {"level1": {"level2": {"level3": {"secret": "deep"}}}}
    result = mask_sensitive_data(data, max_depth=2)
    # At depth 2, we stop recursing — level3's contents pass through unmasked
    assert result["level1"]["level2"]["level3"]["secret"] == "deep"


def test_mask_custom_patterns():
    data = {"ssn": "123-45-6789", "name": "alice"}
    result = mask_sensitive_data(data, sensitive_patterns=["ssn"])
    assert result["ssn"] == MASK_VALUE
    assert result["name"] == "alice"


def test_mask_non_dict_passthrough():
    assert mask_sensitive_data("just a string") == "just a string"
    assert mask_sensitive_data(42) == 42
    assert mask_sensitive_data(None) is None


def test_sensitive_data_filter_masks_extra_fields():
    filt = SensitiveDataFilter(["password"])
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    record.password = "secret123"
    record.username = "alice"
    filt.filter(record)
    assert record.password == MASK_VALUE
    assert record.username == "alice"


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def test_structured_logger_setup():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-app", log_level="DEBUG")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-app"
    assert logger.level == logging.DEBUG


def test_structured_logger_has_handler():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-handlers")
    assert len(logger.handlers) > 0


def test_structured_logger_json_format():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-json", log_format="json")
    handler = logger.handlers[0]
    from pythonjsonlogger import json as jsonlogger

    assert isinstance(handler.formatter, jsonlogger.JsonFormatter)


def test_structured_logger_text_format():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-text", log_format="text")
    handler = logger.handlers[0]
    assert isinstance(handler.formatter, logging.Formatter)
    assert "%(asctime)s" in handler.formatter._fmt


def test_structured_logger_masking_filter():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-masking", sensitive_fields=["password", "token"])
    handler = logger.handlers[0]
    filters = handler.filters
    assert len(filters) == 1
    assert filters[0].patterns == ["password", "token"]


def test_structured_logger_no_masking_by_default():
    sl = StructuredLogger()
    logger = sl.setup(app_name="test-no-masking")
    handler = logger.handlers[0]
    assert len(handler.filters) == 0


# ---------------------------------------------------------------------------
# Correlation ID contextvar
# ---------------------------------------------------------------------------


def test_correlation_id_default_empty():
    # Reset to default
    token = correlation_id_var.set("")
    try:
        assert get_correlation_id() == ""
    finally:
        correlation_id_var.reset(token)


def test_correlation_id_set_and_get():
    token = correlation_id_var.set("test-123")
    try:
        assert get_correlation_id() == "test-123"
    finally:
        correlation_id_var.reset(token)
