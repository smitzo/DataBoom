"""Deterministic seed derivation for generation runs.

Purpose:
    Create repeatable, isolated random streams from one run seed.

Data flow:
    root seed + namespace parts -> SHA-256 digest -> integer child seed ->
    `random.Random` stream.

Why this layer exists:
    DataBoom needs controlled randomness. Namespaced streams make output
    repeatable while avoiding one column's random calls from shifting another
    column's values.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SeedManager:
    """Derive stable random streams from one root seed."""

    root_seed: int | str

    def child_seed(self, *parts: Any) -> int:
        """Return a deterministic integer seed for a namespace."""

        # JSON with sorted keys gives a stable seed payload across Python runs.
        payload = json.dumps(
            {
                "root_seed": self.root_seed,
                "parts": parts,
            },
            default=str,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=False)

    def stream(self, *parts: Any) -> random.Random:
        """Return an isolated deterministic random stream for a namespace."""

        return random.Random(self.child_seed(*parts))
