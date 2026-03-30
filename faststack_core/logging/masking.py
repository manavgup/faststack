from typing import Any

DEFAULT_SENSITIVE_PATTERNS = [
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "credit_card",
]
MASK_VALUE = "***MASKED***"


def mask_sensitive_data(
    data: Any,
    sensitive_patterns: list[str] | None = None,
    max_depth: int = 5,
) -> Any:
    """Recursively mask values for keys matching sensitive patterns.

    - Works on dicts, lists, and nested combinations
    - Depth-limited to prevent performance issues on large payloads
    - Does NOT mutate the input — returns a masked copy
    - Key matching is case-insensitive substring match
    """
    if max_depth <= 0:
        return data

    patterns = sensitive_patterns if sensitive_patterns is not None else DEFAULT_SENSITIVE_PATTERNS

    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            key_lower = key.lower() if isinstance(key, str) else str(key).lower()
            if any(pattern.lower() in key_lower for pattern in patterns):
                masked[key] = MASK_VALUE
            else:
                masked[key] = mask_sensitive_data(value, patterns, max_depth - 1)
        return masked

    if isinstance(data, list):
        return [mask_sensitive_data(item, patterns, max_depth - 1) for item in data]

    return data
