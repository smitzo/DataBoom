"""Versioned prompt-pack loading and non-sensitive cache identifiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from databoom.planning.models import PlanResourceInput, ProductKind


@dataclass(frozen=True)
class PromptPack:
    """Stable prompt prefix and strict output schema shipped with the package."""

    version: str
    system: str
    developer: str
    examples: str
    output_schema: dict[str, Any]

    @property
    def stable_prefix(self) -> str:
        """Return stable content in cache-friendly order."""

        return "\n\n".join((self.system, self.developer, self.examples))


def load_prompt_pack(version: str = "v1") -> PromptPack:
    """Load a prompt pack from package resources so wheels and containers agree."""

    root = files("databoom.planning.prompt_packs").joinpath(version)
    return PromptPack(
        version=root.joinpath("version.txt").read_text(encoding="utf-8").strip(),
        system=root.joinpath("system.md").read_text(encoding="utf-8").strip(),
        developer=root.joinpath("developer.md").read_text(encoding="utf-8").strip(),
        examples=root.joinpath("examples.md").read_text(encoding="utf-8").strip(),
        output_schema=json.loads(root.joinpath("output-schema.json").read_text(encoding="utf-8")),
    )


def schema_fingerprint(resources: tuple[PlanResourceInput, ...]) -> str:
    """Hash normalized metadata without including source values or user identity."""

    normalized = [
        resource.model_dump(mode="json")
        for resource in sorted(resources, key=lambda item: (item.kind.value, item.name))
    ]
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_prompt_cache_key(
    *,
    product_kind: ProductKind,
    planner_version: str,
    schema_hash: str,
    prompt_pack_version: str,
) -> str:
    """Build a stable key that contains no secrets or raw customer values."""

    key = (
        f"databoom:{product_kind.value}:{planner_version}:{schema_hash[:24]}:{prompt_pack_version}"
    )
    return key[:64]
