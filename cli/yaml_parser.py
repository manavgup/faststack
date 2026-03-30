"""Parse ``entities.yaml`` files into structured :class:`EntityDefinition` objects.

Handles relationship resolution, table-name pluralization, and validation
of cross-entity references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import inflect
import yaml

# Shared inflect engine
_inflect_engine = inflect.engine()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FieldDefinition:
    """A single field within an entity."""

    name: str
    type: str  # YAML type (string, uuid, enum, etc.)
    required: bool = False
    unique: bool = False
    default: str | None = None
    references: str | None = None  # FK target entity name, or "self"
    on_delete: str = "SET NULL"  # CASCADE, SET NULL, RESTRICT
    enum_values: list[str] = field(default_factory=list)  # for enum type
    items: str | None = None  # for array type -- inner type name


@dataclass
class RelationshipDefinition:
    """A resolved relationship between entities."""

    field_name: str  # e.g. "user_id" or "tags"
    type: str  # "many_to_one", "many_to_many", "self_referential"
    target_entity: str  # e.g. "User" or "self"
    back_populates: str | None = None  # e.g. "posts"


@dataclass
class EntityDefinition:
    """Fully parsed entity definition from YAML."""

    name: str
    base: str = "FullAuditedEntity"
    fields: list[FieldDefinition] = field(default_factory=list)
    relationships: list[RelationshipDefinition] = field(default_factory=list)
    searchable: list[str] = field(default_factory=list)
    table_name: str = ""  # auto-generated pluralized name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pluralize(name: str) -> str:
    """Return a lowercase, pluralized table name for *name*.

    Uses *inflect* for proper English pluralization.
    """
    # Convert CamelCase to snake_case first
    snake = _camel_to_snake(name)
    plural = _inflect_engine.plural_noun(snake)
    # inflect returns False if the word is already plural
    return plural if plural else snake


def _camel_to_snake(name: str) -> str:
    """Convert ``CamelCase`` to ``snake_case``."""
    import re

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _resolve_back_populates(
    source_entity: str,
    rel_type: str,
) -> str:
    """Generate the ``back_populates`` name for the *other* side of a relationship.

    For a many_to_one from Post -> User, the User side gets ``back_populates="posts"``.
    For self-referential, returns ``"children"``.
    """
    if rel_type == "self_referential":
        return "children"
    # Pluralize the source entity name for the reverse side
    return _pluralize(source_entity)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_entities_yaml(path: Path) -> list[EntityDefinition]:
    """Parse an ``entities.yaml`` file into :class:`EntityDefinition` objects.

    Resolves relationships:
    - uuid field with ``references: EntityName`` -> many_to_one relationship
    - many_to_many field with ``references: EntityName`` -> many_to_many relationship
    - uuid field with ``references: self`` -> self_referential relationship

    Generates ``back_populates`` names using *inflect* for pluralization.
    Validates that referenced entities exist in the YAML.

    Parameters
    ----------
    path:
        Path to the YAML file.

    Returns
    -------
    list[EntityDefinition]
        Parsed entity definitions with resolved relationships.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the YAML is structurally invalid or references unknown entities.
    """
    if not path.exists():
        raise FileNotFoundError(f"entities.yaml not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or "entities" not in raw:
        raise ValueError("YAML must contain a top-level 'entities' key")

    raw_entities: dict[str, dict] = raw["entities"]
    entity_names = set(raw_entities.keys())

    # First pass: build EntityDefinition objects with fields
    entities: list[EntityDefinition] = []
    for entity_name, entity_data in raw_entities.items():
        entity_data = entity_data or {}
        entity = EntityDefinition(
            name=entity_name,
            base=entity_data.get("base", "FullAuditedEntity"),
            table_name=_pluralize(entity_name),
            searchable=list(entity_data.get("searchable", [])),
        )

        raw_fields: dict[str, dict] = entity_data.get("fields", {})
        for field_name, field_data in raw_fields.items():
            field_data = field_data or {}
            fd = FieldDefinition(
                name=field_name,
                type=field_data.get("type", "string"),
                required=bool(field_data.get("required", False)),
                unique=bool(field_data.get("unique", False)),
                default=field_data.get("default"),
                references=field_data.get("references"),
                on_delete=field_data.get("on_delete", "SET NULL"),
                enum_values=list(field_data.get("values", [])),
                items=field_data.get("items"),
            )
            entity.fields.append(fd)

        entities.append(entity)

    # Second pass: resolve relationships and validate references
    for entity in entities:
        for fd in entity.fields:
            if fd.references is None:
                continue

            # Validate reference target
            if fd.references != "self" and fd.references not in entity_names:
                raise ValueError(
                    f"Entity '{entity.name}' field '{fd.name}' references "
                    f"unknown entity '{fd.references}'. "
                    f"Known entities: {', '.join(sorted(entity_names))}"
                )

            # Determine relationship type
            if fd.references == "self":
                rel = RelationshipDefinition(
                    field_name=fd.name,
                    type="self_referential",
                    target_entity=entity.name,
                    back_populates=_resolve_back_populates(entity.name, "self_referential"),
                )
            elif fd.type == "uuid":
                rel = RelationshipDefinition(
                    field_name=fd.name,
                    type="many_to_one",
                    target_entity=fd.references,
                    back_populates=_resolve_back_populates(entity.name, "many_to_one"),
                )
            else:
                # Treat other typed references as many_to_many
                rel = RelationshipDefinition(
                    field_name=fd.name,
                    type="many_to_many",
                    target_entity=fd.references,
                    back_populates=_resolve_back_populates(entity.name, "many_to_many"),
                )

            entity.relationships.append(rel)

    return entities
