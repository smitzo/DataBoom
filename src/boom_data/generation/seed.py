"""Deterministic seed derivation for generation runs."""

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
