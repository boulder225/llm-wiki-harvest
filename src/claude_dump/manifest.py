"""Export manifest for tracking incremental conversation exports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_dump.models import Conversation

MANIFEST_FILENAME = ".export-state.json"


@dataclass
class DeltaResult:
    """Result of comparing manifest against current conversation list."""

    new: list[Conversation] = field(default_factory=list)
    updated: list[Conversation] = field(default_factory=list)
    unchanged: list[Conversation] = field(default_factory=list)
    deleted_uuids: list[str] = field(default_factory=list)


@dataclass
class ExportManifest:
    """Tracks exported conversations by UUID -> updated_at mapping."""

    conversations: dict[str, str] = field(default_factory=dict)  # uuid -> updated_at
    exported_at: str = ""
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, output_dir: Path) -> ExportManifest:
        """Load manifest from output_dir/.export-state.json. Returns empty if missing."""
        path = output_dir / MANIFEST_FILENAME
        if not path.exists():
            return cls(_path=path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            conversations=data.get("conversations", {}),
            exported_at=data.get("exported_at", ""),
            _path=path,
        )

    def save(self) -> None:
        """Persist manifest to disk."""
        if self._path is None:
            raise ValueError("Manifest path not set")
        self.exported_at = datetime.now(timezone.utc).isoformat()
        data = {
            "conversations": self.conversations,
            "exported_at": self.exported_at,
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def compute_delta(self, current: list[Conversation]) -> DeltaResult:
        """Compare current conversation list against manifest state."""
        result = DeltaResult()
        seen_uuids: set[str] = set()

        for conv in current:
            seen_uuids.add(conv.uuid)
            stored_updated_at = self.conversations.get(conv.uuid)
            if stored_updated_at is None:
                result.new.append(conv)
            elif stored_updated_at != conv.updated_at:
                result.updated.append(conv)
            else:
                result.unchanged.append(conv)

        for uuid in self.conversations:
            if uuid not in seen_uuids:
                result.deleted_uuids.append(uuid)

        return result

    def record(self, conv: Conversation) -> None:
        """Record a conversation as exported with its current updated_at."""
        self.conversations[conv.uuid] = conv.updated_at
