"""Type mappings from YAML field types to SQLAlchemy, Pydantic, and Python types.

Supports all 13 field types defined in the FastStack design plan:
string, text, integer, float, boolean, datetime, date, uuid, decimal, json, enum, array, jsonb.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# YAML type -> SQLAlchemy column type string (used in template rendering)
# ---------------------------------------------------------------------------
SQLALCHEMY_TYPE_MAP: dict[str, str] = {
    "string": "String(255)",
    "text": "Text",
    "integer": "Integer",
    "float": "Float",
    "boolean": "Boolean",
    "datetime": "DateTime",
    "date": "Date",
    "uuid": "UUID(as_uuid=True)",
    "decimal": "Numeric(10, 2)",
    "json": "JSON",
    "enum": "Enum",  # special handling -- needs the enum class name
    "array": "ARRAY",  # special handling -- needs inner type, PostgreSQL only
    "jsonb": "JSONB",
}

# ---------------------------------------------------------------------------
# YAML type -> Pydantic field type string
# ---------------------------------------------------------------------------
PYDANTIC_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "text": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
    "datetime": "datetime",
    "date": "date",
    "uuid": "UUID",
    "decimal": "Decimal",
    "json": "dict",
    "enum": "str",  # will be Literal[...] in schema, str in general
    "array": "list",  # will be list[inner] in schema
    "jsonb": "dict",
}

# ---------------------------------------------------------------------------
# YAML type -> Python native type string
# ---------------------------------------------------------------------------
PYTHON_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "text": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
    "datetime": "datetime",
    "date": "date",
    "uuid": "uuid.UUID",
    "decimal": "Decimal",
    "json": "dict",
    "enum": "str",
    "array": "list",
    "jsonb": "dict",
}

# ---------------------------------------------------------------------------
# SQLAlchemy import map -- which imports are needed for each YAML type
# ---------------------------------------------------------------------------
_SQLALCHEMY_IMPORT_MAP: dict[str, list[str]] = {
    "string": ["String"],
    "text": ["Text"],
    "integer": ["Integer"],
    "float": ["Float"],
    "boolean": ["Boolean"],
    "datetime": ["DateTime"],
    "date": ["Date"],
    "uuid": ["UUID"],
    "decimal": ["Numeric"],
    "json": ["JSON"],
    "enum": ["Enum"],
    "array": ["ARRAY"],
    "jsonb": ["JSONB"],
}

ALL_YAML_TYPES = frozenset(SQLALCHEMY_TYPE_MAP.keys())


def _validate_type(yaml_type: str) -> None:
    """Raise ValueError if *yaml_type* is not a recognised YAML field type."""
    if yaml_type not in ALL_YAML_TYPES:
        raise ValueError(
            f"Unknown YAML field type: {yaml_type!r}. "
            f"Supported types: {', '.join(sorted(ALL_YAML_TYPES))}"
        )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_sqlalchemy_type(yaml_type: str, **kwargs: str) -> str:
    """Return the full SQLAlchemy column-type expression for *yaml_type*.

    Special keyword arguments:
    - ``enum_class`` (str): Required when *yaml_type* is ``"enum"``.
      Produces e.g. ``Enum(StatusEnum)``.
    - ``items`` (str): Required when *yaml_type* is ``"array"``.
      Produces e.g. ``ARRAY(String)``.
    """
    _validate_type(yaml_type)

    if yaml_type == "enum":
        enum_class = kwargs.get("enum_class")
        if not enum_class:
            raise ValueError("enum type requires 'enum_class' kwarg for SQLAlchemy mapping")
        return f"Enum({enum_class})"

    if yaml_type == "array":
        items = kwargs.get("items")
        if not items:
            raise ValueError("array type requires 'items' kwarg for SQLAlchemy mapping")
        # Map the inner YAML type to its SQLAlchemy type name (without params)
        inner_sa = SQLALCHEMY_TYPE_MAP.get(items)
        if inner_sa is None:
            raise ValueError(f"Unknown inner type for array: {items!r}")
        # Strip any parenthesised params for the inner type -- ARRAY(String) not ARRAY(String(255))
        inner_name = inner_sa.split("(")[0]
        return f"ARRAY({inner_name})"

    return SQLALCHEMY_TYPE_MAP[yaml_type]


def get_pydantic_type(yaml_type: str, **kwargs: str | list[str]) -> str:
    """Return the Pydantic type annotation string for *yaml_type*.

    Special keyword arguments:
    - ``values`` (list[str]): For ``"enum"`` type, returns ``Literal["a", "b", "c"]``.
    - ``items`` (str): For ``"array"`` type, returns e.g. ``list[str]``.
    """
    _validate_type(yaml_type)

    if yaml_type == "enum":
        values = kwargs.get("values")
        if values and isinstance(values, list):
            quoted = ", ".join(f'"{v}"' for v in values)
            return f"Literal[{quoted}]"
        return PYDANTIC_TYPE_MAP[yaml_type]

    if yaml_type == "array":
        items = kwargs.get("items")
        if items and isinstance(items, str):
            inner_py = PYDANTIC_TYPE_MAP.get(items)
            if inner_py is None:
                raise ValueError(f"Unknown inner type for array: {items!r}")
            return f"list[{inner_py}]"
        return PYDANTIC_TYPE_MAP[yaml_type]

    return PYDANTIC_TYPE_MAP[yaml_type]


def get_python_type(yaml_type: str, **kwargs: str | list[str]) -> str:
    """Return the Python native type string for *yaml_type*."""
    _validate_type(yaml_type)
    return PYTHON_TYPE_MAP[yaml_type]


def get_sqlalchemy_imports(yaml_type: str) -> list[str]:
    """Return the list of SQLAlchemy imports needed for *yaml_type*."""
    _validate_type(yaml_type)
    return list(_SQLALCHEMY_IMPORT_MAP[yaml_type])
