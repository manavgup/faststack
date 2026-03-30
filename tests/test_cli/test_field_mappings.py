"""Tests for cli.field_mappings — type mapping from YAML to SQLAlchemy / Pydantic / Python."""

from __future__ import annotations

import pytest

from cli.field_mappings import (
    ALL_YAML_TYPES,
    PYDANTIC_TYPE_MAP,
    PYTHON_TYPE_MAP,
    SQLALCHEMY_TYPE_MAP,
    get_pydantic_type,
    get_python_type,
    get_sqlalchemy_imports,
    get_sqlalchemy_type,
)

# ---------------------------------------------------------------------------
# All 13 supported YAML types
# ---------------------------------------------------------------------------
ALL_13_TYPES = [
    "string",
    "text",
    "integer",
    "float",
    "boolean",
    "datetime",
    "date",
    "uuid",
    "decimal",
    "json",
    "enum",
    "array",
    "jsonb",
]


class TestTypeMapsCompleteness:
    """Verify every type map covers all 13 types."""

    def test_all_yaml_types_constant(self):
        assert len(ALL_YAML_TYPES) == 13
        assert set(ALL_13_TYPES) == ALL_YAML_TYPES

    def test_sqlalchemy_map_covers_all_types(self):
        for t in ALL_13_TYPES:
            assert t in SQLALCHEMY_TYPE_MAP, f"Missing SQLAlchemy mapping for {t}"

    def test_pydantic_map_covers_all_types(self):
        for t in ALL_13_TYPES:
            assert t in PYDANTIC_TYPE_MAP, f"Missing Pydantic mapping for {t}"

    def test_python_map_covers_all_types(self):
        for t in ALL_13_TYPES:
            assert t in PYTHON_TYPE_MAP, f"Missing Python mapping for {t}"


# ---------------------------------------------------------------------------
# SQLAlchemy type map values
# ---------------------------------------------------------------------------


class TestSQLAlchemyTypeMap:
    @pytest.mark.parametrize(
        "yaml_type, expected",
        [
            ("string", "String(255)"),
            ("text", "Text"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Boolean"),
            ("datetime", "DateTime"),
            ("date", "Date"),
            ("uuid", "UUID(as_uuid=True)"),
            ("decimal", "Numeric(10, 2)"),
            ("json", "JSON"),
            ("enum", "Enum"),
            ("array", "ARRAY"),
            ("jsonb", "JSONB"),
        ],
    )
    def test_sqlalchemy_map_values(self, yaml_type, expected):
        assert SQLALCHEMY_TYPE_MAP[yaml_type] == expected


# ---------------------------------------------------------------------------
# Pydantic type map values
# ---------------------------------------------------------------------------


class TestPydanticTypeMap:
    @pytest.mark.parametrize(
        "yaml_type, expected",
        [
            ("string", "str"),
            ("text", "str"),
            ("integer", "int"),
            ("float", "float"),
            ("boolean", "bool"),
            ("datetime", "datetime"),
            ("date", "date"),
            ("uuid", "UUID"),
            ("decimal", "Decimal"),
            ("json", "dict"),
            ("enum", "str"),
            ("array", "list"),
            ("jsonb", "dict"),
        ],
    )
    def test_pydantic_map_values(self, yaml_type, expected):
        assert PYDANTIC_TYPE_MAP[yaml_type] == expected


# ---------------------------------------------------------------------------
# Python type map values
# ---------------------------------------------------------------------------


class TestPythonTypeMap:
    @pytest.mark.parametrize(
        "yaml_type, expected",
        [
            ("string", "str"),
            ("text", "str"),
            ("integer", "int"),
            ("float", "float"),
            ("boolean", "bool"),
            ("datetime", "datetime"),
            ("date", "date"),
            ("uuid", "uuid.UUID"),
            ("decimal", "Decimal"),
            ("json", "dict"),
            ("enum", "str"),
            ("array", "list"),
            ("jsonb", "dict"),
        ],
    )
    def test_python_map_values(self, yaml_type, expected):
        assert PYTHON_TYPE_MAP[yaml_type] == expected


# ---------------------------------------------------------------------------
# get_sqlalchemy_type helper
# ---------------------------------------------------------------------------


class TestGetSQLAlchemyType:
    def test_simple_types(self):
        assert get_sqlalchemy_type("string") == "String(255)"
        assert get_sqlalchemy_type("integer") == "Integer"
        assert get_sqlalchemy_type("uuid") == "UUID(as_uuid=True)"
        assert get_sqlalchemy_type("jsonb") == "JSONB"

    def test_enum_with_class(self):
        result = get_sqlalchemy_type("enum", enum_class="StatusEnum")
        assert result == "Enum(StatusEnum)"

    def test_enum_without_class_raises(self):
        with pytest.raises(ValueError, match="enum_class"):
            get_sqlalchemy_type("enum")

    def test_array_with_items(self):
        result = get_sqlalchemy_type("array", items="string")
        assert result == "ARRAY(String)"

    def test_array_with_integer_items(self):
        result = get_sqlalchemy_type("array", items="integer")
        assert result == "ARRAY(Integer)"

    def test_array_without_items_raises(self):
        with pytest.raises(ValueError, match="items"):
            get_sqlalchemy_type("array")

    def test_array_with_unknown_inner_type_raises(self):
        with pytest.raises(ValueError, match="Unknown inner type"):
            get_sqlalchemy_type("array", items="foobar")

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown YAML field type"):
            get_sqlalchemy_type("nonexistent")


# ---------------------------------------------------------------------------
# get_pydantic_type helper
# ---------------------------------------------------------------------------


class TestGetPydanticType:
    def test_simple_types(self):
        assert get_pydantic_type("string") == "str"
        assert get_pydantic_type("integer") == "int"
        assert get_pydantic_type("uuid") == "UUID"
        assert get_pydantic_type("decimal") == "Decimal"

    def test_enum_with_values(self):
        result = get_pydantic_type("enum", values=["admin", "editor", "viewer"])
        assert result == 'Literal["admin", "editor", "viewer"]'

    def test_enum_without_values_returns_str(self):
        result = get_pydantic_type("enum")
        assert result == "str"

    def test_array_with_items(self):
        result = get_pydantic_type("array", items="string")
        assert result == "list[str]"

    def test_array_with_integer_items(self):
        result = get_pydantic_type("array", items="integer")
        assert result == "list[int]"

    def test_array_without_items_returns_list(self):
        result = get_pydantic_type("array")
        assert result == "list"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown YAML field type"):
            get_pydantic_type("nonexistent")


# ---------------------------------------------------------------------------
# get_python_type helper
# ---------------------------------------------------------------------------


class TestGetPythonType:
    def test_simple_types(self):
        assert get_python_type("string") == "str"
        assert get_python_type("uuid") == "uuid.UUID"
        assert get_python_type("decimal") == "Decimal"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown YAML field type"):
            get_python_type("nonexistent")


# ---------------------------------------------------------------------------
# get_sqlalchemy_imports helper
# ---------------------------------------------------------------------------


class TestGetSQLAlchemyImports:
    @pytest.mark.parametrize(
        "yaml_type, expected_imports",
        [
            ("string", ["String"]),
            ("text", ["Text"]),
            ("integer", ["Integer"]),
            ("float", ["Float"]),
            ("boolean", ["Boolean"]),
            ("datetime", ["DateTime"]),
            ("date", ["Date"]),
            ("uuid", ["UUID"]),
            ("decimal", ["Numeric"]),
            ("json", ["JSON"]),
            ("enum", ["Enum"]),
            ("array", ["ARRAY"]),
            ("jsonb", ["JSONB"]),
        ],
    )
    def test_imports_for_each_type(self, yaml_type, expected_imports):
        result = get_sqlalchemy_imports(yaml_type)
        assert result == expected_imports

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown YAML field type"):
            get_sqlalchemy_imports("nonexistent")

    def test_returns_new_list_each_call(self):
        """Ensure we get a copy, not the internal list."""
        a = get_sqlalchemy_imports("string")
        b = get_sqlalchemy_imports("string")
        assert a == b
        assert a is not b
