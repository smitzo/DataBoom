"""Document generation model contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentFieldSpec:
    """Declarative field shape for a generated document."""

    name: str
    kind: str
    fields: tuple[DocumentFieldSpec, ...] = ()
    item_fields: tuple[DocumentFieldSpec, ...] = ()
    target_collection: str | None = None


@dataclass(frozen=True)
class DocumentCollectionSpec:
    """Declarative collection shape for Docu-Boom generation."""

    name: str
    default_count: int
    fields: tuple[DocumentFieldSpec, ...]
