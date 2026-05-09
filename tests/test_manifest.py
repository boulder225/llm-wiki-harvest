"""Tests for ExportManifest load/save/delta computation."""

import json

import pytest

from claude_dump.manifest import DeltaResult, ExportManifest, MANIFEST_FILENAME
from claude_dump.models import Conversation


# ---------------------------------------------------------------------------
# load / save
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_missing_file_returns_empty(self, tmp_path):
        """Loading from a dir without manifest returns empty manifest."""
        manifest = ExportManifest.load(tmp_path)
        assert manifest.conversations == {}
        assert manifest.exported_at == ""

    def test_load_roundtrip(self, tmp_path):
        """Save then load produces equivalent manifest."""
        manifest = ExportManifest.load(tmp_path)
        manifest.conversations = {"conv-1": "2026-01-01T00:00:00Z", "conv-2": "2026-01-02T00:00:00Z"}
        manifest.save()

        loaded = ExportManifest.load(tmp_path)
        assert loaded.conversations == manifest.conversations
        assert loaded.exported_at != ""


class TestSave:
    def test_save_writes_json(self, tmp_path):
        """Save writes a valid JSON file with conversations and exported_at."""
        manifest = ExportManifest.load(tmp_path)
        manifest.conversations = {"conv-1": "2026-01-01T00:00:00Z"}
        manifest.save()

        path = tmp_path / MANIFEST_FILENAME
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "conversations" in data
        assert "exported_at" in data
        assert data["conversations"] == {"conv-1": "2026-01-01T00:00:00Z"}


# ---------------------------------------------------------------------------
# compute_delta
# ---------------------------------------------------------------------------


def _make_conv(uuid: str, updated_at: str = "2026-01-01T00:00:00Z") -> Conversation:
    return Conversation(uuid=uuid, updated_at=updated_at)


class TestComputeDelta:
    def test_delta_all_new(self):
        """Empty manifest means all conversations are new."""
        manifest = ExportManifest()
        convs = [_make_conv("c1"), _make_conv("c2")]
        delta = manifest.compute_delta(convs)
        assert len(delta.new) == 2
        assert len(delta.updated) == 0
        assert len(delta.unchanged) == 0
        assert len(delta.deleted_uuids) == 0

    def test_delta_unchanged(self):
        """Conversations with matching updated_at are unchanged."""
        manifest = ExportManifest(conversations={"c1": "2026-01-01T00:00:00Z"})
        convs = [_make_conv("c1", "2026-01-01T00:00:00Z")]
        delta = manifest.compute_delta(convs)
        assert len(delta.unchanged) == 1
        assert len(delta.new) == 0
        assert len(delta.updated) == 0

    def test_delta_updated(self):
        """Conversations with different updated_at are updated."""
        manifest = ExportManifest(conversations={"c1": "2026-01-01T00:00:00Z"})
        convs = [_make_conv("c1", "2026-02-01T00:00:00Z")]
        delta = manifest.compute_delta(convs)
        assert len(delta.updated) == 1
        assert len(delta.new) == 0
        assert len(delta.unchanged) == 0

    def test_delta_deleted(self):
        """Conversations in manifest but not in API list are deleted."""
        manifest = ExportManifest(conversations={"c1": "2026-01-01T00:00:00Z", "c2": "2026-01-01T00:00:00Z"})
        convs = [_make_conv("c1", "2026-01-01T00:00:00Z")]
        delta = manifest.compute_delta(convs)
        assert delta.deleted_uuids == ["c2"]
        assert len(delta.unchanged) == 1


# ---------------------------------------------------------------------------
# record
# ---------------------------------------------------------------------------


class TestRecord:
    def test_record_adds_conversation(self):
        """record() adds/updates a conversation entry."""
        manifest = ExportManifest()
        conv = _make_conv("c1", "2026-03-01T00:00:00Z")
        manifest.record(conv)
        assert manifest.conversations["c1"] == "2026-03-01T00:00:00Z"

    def test_record_updates_existing(self):
        """record() overwrites updated_at for existing conversation."""
        manifest = ExportManifest(conversations={"c1": "2026-01-01T00:00:00Z"})
        conv = _make_conv("c1", "2026-04-01T00:00:00Z")
        manifest.record(conv)
        assert manifest.conversations["c1"] == "2026-04-01T00:00:00Z"
