"""AST-based model introspector for SQLAlchemy 2.0 models.

Reads Python model files and extracts field definitions, relationships,
and metadata into EntityDefinition objects — the same format as the
YAML parser produces, so the rest of the pipeline treats both sources
identically.

Only supports patterns that FastStack generates. Does NOT attempt to
handle arbitrary SQLAlchemy code.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cli.yaml_parser import EntityDefinition, FieldDefinition, RelationshipDefinition

# ── Reverse type mapping: Python annotation → YAML type ─────────────

ANNOTATION_TO_YAML_TYPE: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "float",
    "bool": "boolean",
    "datetime": "datetime",
    "date": "date",
    "UUID": "uuid",
    "uuid.UUID": "uuid",
    "Decimal": "decimal",
    "dict": "json",
}


# ── Public API ───────────────────────────────────────────────────────


def introspect_model(path: Path) -> EntityDefinition:
    """Parse a SQLAlchemy model file and return an EntityDefinition.

    Extracts:
    - Class name and base class from class definition
    - ``__tablename__`` from class body
    - ``Mapped[type]`` fields from annotated assignments
    - ``mapped_column()`` arguments (unique, nullable, default, ForeignKey)
    - ``relationship()`` calls (back_populates, target entity)
    - Enum classes defined above the model (``str, enum.Enum`` subclasses)
    """
    source = path.read_text()
    tree = ast.parse(source)

    # First pass: collect enum classes defined in the file.
    enum_classes = _collect_enum_classes(tree)

    # Second pass: find the model class (first non-enum class).
    model_node = _find_model_class(tree, enum_classes)
    if model_node is None:
        raise ValueError(f"No model class found in {path}")

    name = model_node.name
    base = _extract_base_name(model_node)
    table_name = _extract_tablename(model_node)

    fields: list[FieldDefinition] = []
    explicit_relationships: list[RelationshipDefinition] = []
    # FK-derived relationships are added only when no explicit relationship()
    # targets the same entity, so we collect them separately.
    fk_relationships: list[RelationshipDefinition] = []

    for node in model_node.body:
        # Skip non-annotated assignments and plain assignments (like __tablename__).
        if not isinstance(node, ast.AnnAssign):
            continue
        if node.target is None or not isinstance(node.target, ast.Name):
            continue

        field_name = node.target.id
        annotation = node.annotation

        # ── relationship() ────────────────────────────────────
        if _is_relationship_call(node.value):
            assert isinstance(node.value, ast.Call)  # narrowing for mypy
            rel = _parse_relationship(field_name, annotation, node.value, name)
            if rel is not None:
                explicit_relationships.append(rel)
            continue

        # ── mapped_column() or bare annotation ────────────────
        mapped_type = _resolve_annotation_type(annotation, enum_classes)
        nullable = _annotation_is_nullable(annotation)

        # Defaults from mapped_column() args
        unique = False
        default = None
        foreign_key: str | None = None
        enum_values: list[str] | None = None

        if mapped_type == "enum":
            enum_name = _extract_enum_class_name(annotation)
            if enum_name and enum_name in enum_classes:
                enum_values = enum_classes[enum_name]

        if node.value is not None and _is_mapped_column_call(node.value):
            assert isinstance(node.value, ast.Call)  # narrowing for mypy
            col_info = _parse_mapped_column(node.value)
            unique = col_info.get("unique", False)
            if col_info.get("default") is not None:
                default = col_info["default"]
            if col_info.get("foreign_key") is not None:
                foreign_key = col_info["foreign_key"]

        # Record FK-derived relationship (may be superseded by an explicit one).
        if foreign_key is not None:
            ref_entity = _fk_to_entity_name(foreign_key, name, table_name)
            rel_type = "self_referential" if ref_entity == name else "many_to_one"
            fk_relationships.append(
                RelationshipDefinition(
                    field_name=field_name,
                    type=rel_type,
                    target_entity=ref_entity,
                    back_populates=None,
                )
            )

        field = FieldDefinition(
            name=field_name,
            type=mapped_type,
            required=not nullable,
            unique=unique,
            default=default,
            references=_fk_to_entity_name(foreign_key, name, table_name) if foreign_key else None,
            enum_values=enum_values if enum_values else [],
        )
        fields.append(field)

    # Merge relationships: explicit relationship() calls take precedence over
    # FK-derived ones.  Only add a FK-derived relationship when no explicit
    # relationship() targets the same entity with a compatible type.
    relationships = list(explicit_relationships)
    for fk_rel in fk_relationships:
        has_explicit = any(
            r.target_entity == fk_rel.target_entity
            and r.type in ("many_to_one", "self_referential")
            for r in explicit_relationships
        )
        if not has_explicit:
            relationships.append(fk_rel)

    return EntityDefinition(
        name=name,
        base=base,
        table_name=table_name,
        fields=fields,
        relationships=relationships,
    )


# ── Enum collection ──────────────────────────────────────────────────


def _collect_enum_classes(tree: ast.Module) -> dict[str, list[str]]:
    """Return ``{ClassName: [value1, value2, ...]}`` for ``str, enum.Enum`` classes."""
    enums: dict[str, list[str]] = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _is_enum_class(node):
            continue
        values: list[str] = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        val = _extract_constant(item.value)
                        if val is not None:
                            values.append(val)
        enums[node.name] = values
    return enums


def _is_enum_class(node: ast.ClassDef) -> bool:
    """Return True if the class inherits from ``(str, enum.Enum)`` or ``(str, Enum)``."""
    base_names = [_base_name_str(b) for b in node.bases]
    return "str" in base_names and any(n in ("enum.Enum", "Enum") for n in base_names)


# ── Model-class detection ────────────────────────────────────────────


def _find_model_class(tree: ast.Module, enum_classes: dict[str, list[str]]) -> ast.ClassDef | None:
    """Return the first non-enum ClassDef in the module (the model)."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name not in enum_classes:
            return node
    return None


def _extract_base_name(node: ast.ClassDef) -> str:
    """Return the first base class name as a string."""
    if node.bases:
        return _base_name_str(node.bases[0])
    return ""


def _base_name_str(node: ast.expr) -> str:
    """Convert a base-class AST node to a dotted string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_base_name_str(node.value)}.{node.attr}"
    return ""


def _extract_tablename(node: ast.ClassDef) -> str:
    """Extract the ``__tablename__`` string from the class body."""
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    val = _extract_constant(item.value)
                    if val is not None:
                        return val
    return ""


# ── Annotation helpers ───────────────────────────────────────────────


def _resolve_annotation_type(annotation: ast.expr, enum_classes: dict[str, list[str]]) -> str:
    """Map a ``Mapped[X]`` annotation to a YAML type string."""
    inner = _unwrap_mapped(annotation)
    if inner is None:
        return "string"  # fallback

    # Strip Optional / nullable union (X | None).
    inner = _strip_none_union(inner)

    # list[...] → "array"
    if isinstance(inner, ast.Subscript) and _name_of(inner.value) == "list":
        return "array"

    type_str = _name_of(inner)

    # Check if the annotation refers to a known enum class.
    if type_str in enum_classes:
        return "enum"

    return ANNOTATION_TO_YAML_TYPE.get(type_str, "string")


def _annotation_is_nullable(annotation: ast.expr) -> bool:
    """Return True if the annotation contains ``| None`` or ``Optional[...]``."""
    inner = _unwrap_mapped(annotation)
    if inner is None:
        return False
    return _is_none_union(inner)


def _unwrap_mapped(annotation: ast.expr) -> ast.expr | None:
    """If ``Mapped[X]``, return ``X``. Otherwise return ``None``."""
    if isinstance(annotation, ast.Subscript) and _name_of(annotation.value) == "Mapped":
        return annotation.slice
    return None


def _strip_none_union(node: ast.expr) -> ast.expr:
    """Given ``X | None``, return ``X``. Otherwise return node unchanged."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        if _is_none(node.right):
            return node.left
        if _is_none(node.left):
            return node.right
    return node


def _is_none_union(node: ast.expr) -> bool:
    """Return True if the node is a union containing None (``X | None``)."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_none(node.right) or _is_none(node.left)
    return False


def _is_none(node: ast.expr) -> bool:
    """Return True if the node represents ``None``."""
    return isinstance(node, ast.Constant) and node.value is None


def _extract_enum_class_name(annotation: ast.expr) -> str | None:
    """Extract the enum class name from ``Mapped[EnumName]``."""
    inner = _unwrap_mapped(annotation)
    if inner is None:
        return None
    inner = _strip_none_union(inner)
    name = _name_of(inner)
    return name if name else None


def _name_of(node: ast.expr) -> str:
    """Return a simple or dotted name from a Name or Attribute node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name_of(node.value)}.{node.attr}"
    return ""


# ── mapped_column() parsing ──────────────────────────────────────────


def _is_mapped_column_call(node: ast.expr | None) -> bool:
    """Return True if the node is a ``mapped_column(...)`` call."""
    return isinstance(node, ast.Call) and _name_of(node.func) == "mapped_column"


def _parse_mapped_column(call: ast.Call) -> dict:
    """Extract structured info from a ``mapped_column(...)`` call.

    Returns a dict with optional keys: unique, default, foreign_key.
    """
    info: dict = {}

    # Scan positional args for ForeignKey("table.col").
    for arg in call.args:
        fk = _extract_foreign_key(arg)
        if fk is not None:
            info["foreign_key"] = fk

    # Scan keyword args.
    for kw in call.keywords:
        if kw.arg == "unique" and isinstance(kw.value, ast.Constant):
            info["unique"] = kw.value.value
        elif kw.arg == "default":
            info["default"] = _extract_default(kw.value)
        elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
            # We already infer nullable from annotation; this is a backup.
            pass

    return info


def _extract_foreign_key(node: ast.expr) -> str | None:
    """If the node is ``ForeignKey("table.col")``, return the string arg."""
    if isinstance(node, ast.Call) and _name_of(node.func) == "ForeignKey":
        if node.args and isinstance(node.args[0], ast.Constant):
            return str(node.args[0].value)
    return None


def _extract_default(node: ast.expr) -> str | None:
    """Best-effort extraction of a default value as a string."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    # Handle Enum member access like PostStatus.DRAFT.
    if isinstance(node, ast.Attribute):
        return f"{_name_of(node.value)}.{node.attr}"
    # Handle simple names like True, False.
    if isinstance(node, ast.Name):
        return node.id
    return None


# ── relationship() parsing ───────────────────────────────────────────


def _is_relationship_call(node: ast.expr | None) -> bool:
    """Return True if the node is a ``relationship(...)`` call."""
    return isinstance(node, ast.Call) and _name_of(node.func) == "relationship"


def _parse_relationship(
    field_name: str,
    annotation: ast.expr,
    call: ast.Call,
    model_name: str,
) -> RelationshipDefinition | None:
    """Parse a ``relationship()`` call into a RelationshipDefinition."""
    target = _resolve_relationship_target(annotation)
    if target is None:
        return None

    back_populates: str | None = None
    for kw in call.keywords:
        if kw.arg == "back_populates" and isinstance(kw.value, ast.Constant):
            back_populates = str(kw.value.value)

    # Determine relationship kind from annotation shape.
    rel_type = _infer_relationship_type(annotation, target, model_name)

    return RelationshipDefinition(
        field_name=field_name,
        type=rel_type,
        target_entity=target,
        back_populates=back_populates,
    )


def _resolve_relationship_target(annotation: ast.expr) -> str | None:
    """Extract the target entity name from a relationship annotation.

    Handles:
    - ``Mapped["User"]`` → ``"User"``
    - ``Mapped[list["Post"]]`` → ``"Post"``
    """
    inner = _unwrap_mapped(annotation)
    if inner is None:
        return None

    # Mapped["User"] — string constant (forward ref).
    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
        return inner.value

    # Mapped[list["Post"]] — subscript with list.
    if isinstance(inner, ast.Subscript) and _name_of(inner.value) == "list":
        item = inner.slice
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            return item.value

    # Mapped[User] — bare name (non-forward-ref).
    name = _name_of(inner)
    if name:
        return name

    return None


def _infer_relationship_type(annotation: ast.expr, target: str, model_name: str) -> str:
    """Infer the relationship type from the annotation shape.

    - ``Mapped["X"]`` → ``"many_to_one"``
    - ``Mapped[list["X"]]`` → ``"one_to_many"``
    - self-referential → ``"self_referential"``
    """
    inner = _unwrap_mapped(annotation)
    if inner is not None and isinstance(inner, ast.Subscript) and _name_of(inner.value) == "list":
        return "one_to_many"
    if target == model_name:
        return "self_referential"
    return "many_to_one"


# ── FK → entity name resolution ─────────────────────────────────────


def _fk_to_entity_name(fk_string: str | None, model_name: str, table_name: str) -> str:
    """Convert ``"users.id"`` → ``"User"`` (singular, capitalised).

    For self-referential FKs (table matches own table), returns the model name.
    """
    if fk_string is None:
        return ""
    table, _, _col = fk_string.partition(".")
    if table == table_name:
        return model_name
    # Naive singularisation: strip trailing "s" and title-case.
    # This matches FastStack's generated table names (lower-case plural).
    singular = table.rstrip("s") if table.endswith("s") else table
    return singular.title()


def _extract_constant(node: ast.expr) -> str | None:
    """Return the string value of a Constant node, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None
