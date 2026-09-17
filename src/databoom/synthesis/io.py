"""Small file, hashing, and path-safety helpers for synthesis artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_digest(*parts: str) -> str:
    """Hash length-prefixed text parts so namespace boundaries stay unambiguous."""

    digest = hashlib.sha256()
    for part in parts:
        encoded = part.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def stable_int_seed(*parts: str) -> int:
    """Return a provider-compatible deterministic 32-bit seed."""

    return int(stable_digest(*parts)[:8], 16)


def canonical_row(columns: Sequence[str], row: Mapping[str, Any]) -> str:
    """Serialize a row in declared column order for fingerprints and comparisons."""

    values = ["" if row.get(column) is None else str(row.get(column)) for column in columns]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def write_model_json(path: Path, model: BaseModel) -> None:
    """Write a Pydantic artifact through a same-directory temporary file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, payload: Any) -> None:
    """Write a JSON-compatible payload atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def resolve_within(root: Path, relative_path: str) -> Path:
    """Resolve a relative artifact path and reject directory traversal."""

    if Path(relative_path).is_absolute():
        raise ValueError("artifact path must be relative to the experiment root")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("artifact path escapes the experiment root")
    return resolved


def relative_to_root(root: Path, path: Path) -> str:
    """Return a portable relative artifact name after containment validation."""

    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("artifact path escapes the experiment root")
    return resolved.relative_to(resolved_root).as_posix()
