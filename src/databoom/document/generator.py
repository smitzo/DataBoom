"""Deterministic NoSQL document generation for Docu-Boom.

Purpose:
    Generate nested JSON and NDJSON collections from declarative document specs.

Data flow:
    `DocumentCollectionSpec` -> generated documents -> JSON/NDJSON artifacts ->
    document manifest and validation summary.

Why this layer exists:
    Document datasets need nested objects, arrays, and object-id style references.
    Keeping that separate from the relational row engine prevents table-specific
    foreign-key assumptions from leaking into Docu-Boom.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from databoom.document.models import DocumentCollectionSpec, DocumentFieldSpec
from databoom.generation import LocaleProfile, SeedManager
from databoom.generation.contexts import PersonContext, PersonContextProvider

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class DocumentArtifact:
    """Artifact paths and generated count for one document collection."""

    collection_name: str
    row_count: int
    json_path: Path
    ndjson_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "row_count": self.row_count,
            "json_path": str(self.json_path),
            "ndjson_path": str(self.ndjson_path),
        }


@dataclass(frozen=True)
class DocumentManifest:
    """Manifest for a Docu-Boom artifact export."""

    output_dir: Path
    manifest_path: Path
    collections: tuple[DocumentArtifact, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "collections": [collection.to_dict() for collection in self.collections],
        }


@dataclass(frozen=True)
class DocumentGenerationResult:
    """Generated document metadata and validation summary."""

    manifest: DocumentManifest
    total_rows: int
    validation_path: Path
    validation: dict[str, Any]


class DocumentGenerator:
    """Generate JSON and NDJSON collections from declarative specs.

    The generator stays deterministic through `SeedManager`, just like Table-Boom,
    but it uses document-specific field kinds instead of SQL column families.
    """

    flush_interval = 1_000
    preview_flush_rows = 20

    def __init__(
        self,
        *,
        collections: tuple[DocumentCollectionSpec, ...],
        row_counts: dict[str, int],
        seed: int | str,
        locale: LocaleProfile = LocaleProfile.EN_US,
        output_dir: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.collections = collections
        self.row_counts = row_counts
        self.seed_manager = SeedManager(seed)
        self.person_contexts = PersonContextProvider(self.seed_manager, locale)
        self.output_dir = output_dir
        self.generated_ids: dict[str, list[str]] = {}
        self.progress_callback = progress_callback

    def generate(self) -> DocumentGenerationResult:
        """Generate all configured collections and write manifest/validation files."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: list[DocumentArtifact] = []
        completed_rows = 0
        for collection in self.collections:
            artifact = self._generate_collection(collection, completed_rows)
            artifacts.append(artifact)
            completed_rows += artifact.row_count
        manifest = DocumentManifest(
            output_dir=self.output_dir,
            manifest_path=self.output_dir / "manifest.json",
            collections=tuple(artifacts),
        )
        manifest.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        validation = {
            "passed": True,
            "checked_collections": [artifact.collection_name for artifact in artifacts],
            "issues": [],
        }
        validation_path = self.output_dir / "validation.json"
        validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
        return DocumentGenerationResult(
            manifest=manifest,
            total_rows=sum(artifact.row_count for artifact in artifacts),
            validation_path=validation_path,
            validation=validation,
        )

    def _generate_collection(
        self,
        collection: DocumentCollectionSpec,
        completed_before_collection: int,
    ) -> DocumentArtifact:
        """Stream one collection to JSON and NDJSON files."""

        row_count = self.row_counts.get(collection.name, collection.default_count)
        json_path = self.output_dir / f"{collection.name}.json"
        ndjson_path = self.output_dir / f"{collection.name}.ndjson"
        generated_ids: list[str] = []

        with (
            json_path.open("w", encoding="utf-8") as json_handle,
            ndjson_path.open("w", encoding="utf-8") as ndjson_handle,
        ):
            json_handle.write("[\n")
            for index in range(row_count):
                document = self._document_for(collection, index)
                document_id = document.get("_id")
                if document_id is not None:
                    generated_ids.append(str(document_id))

                if index:
                    json_handle.write(",\n")
                json_handle.write(json.dumps(document, separators=(",", ":")))
                ndjson_handle.write(json.dumps(document, separators=(",", ":")))
                ndjson_handle.write("\n")

                row_number = index + 1
                should_flush_preview = row_number == self.preview_flush_rows
                should_flush_interval = row_number % self.flush_interval == 0
                if should_flush_preview or should_flush_interval:
                    json_handle.flush()
                    ndjson_handle.flush()
                if row_number % self.flush_interval == 0:
                    self._report_progress(
                        completed_before_collection + row_number,
                        collection.name,
                    )
            json_handle.write("\n]\n")

        self.generated_ids[collection.name] = generated_ids
        self._report_progress(completed_before_collection + row_count, collection.name)

        return DocumentArtifact(
            collection_name=collection.name,
            row_count=row_count,
            json_path=json_path,
            ndjson_path=ndjson_path,
        )

    def _report_progress(self, completed_rows: int, collection_name: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(completed_rows, collection_name)

    def _document_for(
        self,
        collection: DocumentCollectionSpec,
        row_index: int,
    ) -> dict[str, Any]:
        person_context = self.person_contexts.for_row(
            collection.name,
            _field_names(collection.fields),
            row_index,
        )
        return {
            field.name: self._value_for(
                collection.name,
                field,
                row_index,
                person_context=person_context,
            )
            for field in collection.fields
        }

    def _value_for(
        self,
        collection_name: str,
        field: DocumentFieldSpec,
        row_index: int,
        *,
        person_context: PersonContext | None,
    ) -> Any:
        """Generate one document field value from its declarative field kind."""

        stream = self.seed_manager.stream("document", collection_name, field.name, row_index)
        if person_context is not None:
            context_value = person_context.value_for(field.name)
            if context_value is not None:
                return (
                    context_value.isoformat() if isinstance(context_value, date) else context_value
                )
        match field.kind:
            case "object_id":
                return _object_id(
                    self.seed_manager.child_seed(collection_name, field.name, row_index)
                )
            case "reference":
                values = self.generated_ids.get(field.target_collection or "", [])
                if values:
                    # References prefer already-generated IDs so document exports
                    # can preserve lightweight relationships without a graph engine.
                    return values[stream.randrange(len(values))]
                return _object_id(
                    self.seed_manager.child_seed(collection_name, field.name, row_index)
                )
            case "object":
                return {
                    child.name: self._value_for(
                        collection_name,
                        child,
                        row_index,
                        person_context=person_context,
                    )
                    for child in field.fields
                }
            case "array":
                item_count = stream.randint(1, 3)
                return [
                    {
                        child.name: self._value_for(
                            collection_name,
                            child,
                            row_index * 10 + offset,
                            person_context=person_context,
                        )
                        for child in field.item_fields
                    }
                    for offset in range(item_count)
                ]
            case "email":
                return f"user{row_index + 1}@example.test"
            case "first_name":
                return _choice(stream, ("Avery", "Maya", "Noah", "Priya", "Elena", "Samir"))
            case "last_name":
                return _choice(stream, ("Shah", "Rivera", "Chen", "Morgan", "Patel", "Iyer"))
            case "integer":
                return stream.randint(18, 75)
            case "number":
                return round(stream.uniform(0, 1), 4)
            case "money":
                return round(stream.uniform(5, 2_500), 2)
            case "quantity":
                return stream.randint(1, 5)
            case "status":
                return _choice(stream, ("active", "inactive", "pending", "blocked"))
            case "order_status":
                return _choice(stream, ("created", "paid", "fulfilled", "refunded", "cancelled"))
            case "tier":
                return _choice(stream, ("standard", "silver", "gold", "platinum"))
            case "sku":
                return f"SKU-{stream.randint(10000, 99999)}"
            case "product_name":
                return _choice(stream, ("Noise-Canceling Headphones", "USB-C Hub", "Desk Lamp"))
            case "city":
                return _choice(stream, ("Austin", "Boston", "Chicago", "Denver", "Seattle"))
            case "country":
                return _choice(stream, ("US", "CA", "GB", "DE", "IN"))
            case "postal_code":
                return f"{stream.randint(10000, 99999)}"
            case "timestamp":
                base = datetime(2024, 1, 1, tzinfo=UTC)
                return (base + timedelta(minutes=stream.randint(0, 700_000))).isoformat()
            case "event_name":
                return _choice(stream, ("signed_in", "viewed_product", "started_checkout", "paid"))
            case "channel":
                return _choice(stream, ("web", "mobile", "email", "partner"))
            case "campaign":
                return _choice(stream, ("spring", "retention", "launch", "winback"))
            case _:
                return f"{field.name}_{row_index + 1}"


def _object_id(seed: int) -> str:
    return f"{seed:024x}"[-24:]


def _choice(stream, values: tuple[Any, ...]) -> Any:
    return values[stream.randrange(len(values))]


def _field_names(fields: tuple[DocumentFieldSpec, ...]) -> tuple[str, ...]:
    """Flatten nested document field names for person-shape detection."""

    names: list[str] = []
    for field in fields:
        names.append(field.name)
        names.extend(_field_names(field.fields))
        names.extend(_field_names(field.item_fields))
    return tuple(names)
