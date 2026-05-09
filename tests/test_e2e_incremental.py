"""End-to-end tests for incremental delta export across realistic multi-run scenarios.

These tests simulate full export lifecycles with multiple conversations, knowledge
files, file attachments, and verify the on-disk output structure end-to-end.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from claude_dump.exporter import export_project
from claude_dump.manifest import MANIFEST_FILENAME
from claude_dump.models import (
    ChatMessage,
    ContentBlock,
    Conversation,
    FileRef,
    KnowledgeDoc,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _conv(
    uuid: str,
    name: str,
    updated_at: str,
    created_at: str = "2026-01-15T09:00:00Z",
    messages: list[ChatMessage] | None = None,
) -> Conversation:
    if messages is None:
        messages = [
            ChatMessage(
                uuid=f"msg-{uuid}",
                sender="human",
                content=[ContentBlock(type="text", text=f"Hello from {name}")],
            ),
            ChatMessage(
                uuid=f"msg-{uuid}-reply",
                sender="assistant",
                content=[ContentBlock(type="text", text=f"Hi! This is {name}.")],
            ),
        ]
    return Conversation(
        uuid=uuid,
        name=name,
        created_at=created_at,
        updated_at=updated_at,
        chat_messages=messages,
    )


def _knowledge(uuid: str, file_name: str, content: str) -> KnowledgeDoc:
    return KnowledgeDoc(uuid=uuid, file_name=file_name, content=content)


def _build_client(
    conversations: list[Conversation],
    knowledge: list[KnowledgeDoc] | None = None,
) -> MagicMock:
    """Build a mock client that returns metadata on list and full conv on get."""
    client = MagicMock()

    # list_conversations returns metadata only (no chat_messages)
    meta = [
        Conversation(
            uuid=c.uuid,
            name=c.name,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]
    client.list_conversations.return_value = meta

    # get_conversation returns full conversation
    conv_map = {c.uuid: c for c in conversations}
    client.get_conversation.side_effect = lambda uuid: conv_map[uuid]

    # knowledge docs
    client.list_knowledge_docs.return_value = knowledge or []

    return client


# ---------------------------------------------------------------------------
# Scenario 1: Fresh project with multiple conversations — full lifecycle
# ---------------------------------------------------------------------------


class TestScenario1_FreshMultiConversationExport:
    """First export of a project with 3 conversations, knowledge, and index."""

    def test_first_export_creates_complete_output_structure(self, tmp_path: Path):
        convs = [
            _conv("c1", "Setup Guide", "2026-01-15T10:00:00Z", "2026-01-10T08:00:00Z"),
            _conv("c2", "Bug Report", "2026-01-16T14:30:00Z", "2026-01-12T09:00:00Z"),
            _conv("c3", "Feature Ideas", "2026-01-17T11:00:00Z", "2026-01-14T16:00:00Z"),
        ]
        knowledge = [
            _knowledge("k1", "architecture.md", "# Architecture\nMicroservices."),
            _knowledge("k2", "api-spec.md", "# API Spec\nREST endpoints."),
        ]
        client = _build_client(convs, knowledge)

        result = export_project(client, "proj-1", "My Project", tmp_path)

        # All conversations exported
        assert result.conversations_exported == 3
        assert result.conversations_skipped == 0
        assert result.conversations_failed == 0

        # Knowledge files downloaded
        assert result.knowledge_exported == 2

        # Conversation files exist on disk
        conv_files = list((tmp_path / "conversations").glob("*.md"))
        assert len(conv_files) == 3

        # Knowledge files exist
        assert (tmp_path / "knowledge" / "architecture.md").exists()
        assert (tmp_path / "knowledge" / "api-spec.md").exists()

        # Index generated
        index = (tmp_path / "index.md").read_text()
        assert "Setup Guide" in index
        assert "Bug Report" in index
        assert "Feature Ideas" in index
        assert "| Conversations | 3 |" in index

        # Manifest created with all 3 conversations
        manifest_data = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert len(manifest_data["conversations"]) == 3
        assert manifest_data["conversations"]["c1"] == "2026-01-15T10:00:00Z"
        assert manifest_data["conversations"]["c2"] == "2026-01-16T14:30:00Z"
        assert manifest_data["conversations"]["c3"] == "2026-01-17T11:00:00Z"
        assert "exported_at" in manifest_data


# ---------------------------------------------------------------------------
# Scenario 2: Incremental run — mix of new, updated, and unchanged
# ---------------------------------------------------------------------------


class TestScenario2_IncrementalMixedDelta:
    """Second export where 1 conv is unchanged, 1 is updated, 1 is new."""

    def test_mixed_delta_only_fetches_changed(self, tmp_path: Path):
        # --- Run 1: export 2 conversations ---
        original_convs = [
            _conv("c1", "Old Chat", "2026-01-10T10:00:00Z", "2026-01-05T08:00:00Z"),
            _conv("c2", "Stable Chat", "2026-01-11T10:00:00Z", "2026-01-06T08:00:00Z"),
        ]
        client1 = _build_client(original_convs)
        result1 = export_project(client1, "proj-1", "Test", tmp_path)
        assert result1.conversations_exported == 2

        # --- Run 2: c1 updated, c2 unchanged, c3 is new ---
        run2_convs = [
            _conv("c1", "Old Chat (edited)", "2026-01-20T10:00:00Z", "2026-01-05T08:00:00Z"),
            _conv("c2", "Stable Chat", "2026-01-11T10:00:00Z", "2026-01-06T08:00:00Z"),
            _conv("c3", "Brand New", "2026-01-19T14:00:00Z", "2026-01-19T14:00:00Z"),
        ]
        client2 = _build_client(run2_convs)
        result2 = export_project(client2, "proj-1", "Test", tmp_path)

        # Only c1 (updated) and c3 (new) should be exported
        assert result2.conversations_exported == 2
        assert result2.conversations_skipped == 1
        assert result2.conversations_failed == 0

        # get_conversation should only be called for c1 and c3
        fetched_uuids = [call.args[0] for call in client2.get_conversation.call_args_list]
        assert "c1" in fetched_uuids
        assert "c3" in fetched_uuids
        assert "c2" not in fetched_uuids

        # Manifest updated with new timestamps
        manifest_data = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert manifest_data["conversations"]["c1"] == "2026-01-20T10:00:00Z"
        assert manifest_data["conversations"]["c2"] == "2026-01-11T10:00:00Z"  # preserved
        assert manifest_data["conversations"]["c3"] == "2026-01-19T14:00:00Z"

        # Conversation files on disk: original c1 + updated c1 + c2 + c3
        # (renaming a conversation produces a new filename since title is in the name)
        conv_files = list((tmp_path / "conversations").glob("*.md"))
        assert len(conv_files) == 4  # old c1 + new c1 + c2 + c3


# ---------------------------------------------------------------------------
# Scenario 3: --full flag re-exports everything despite existing manifest
# ---------------------------------------------------------------------------


class TestScenario3_FullFlagOverride:
    """--full forces complete re-export even when manifest shows nothing changed."""

    def test_full_re_exports_all_conversations(self, tmp_path: Path):
        convs = [
            _conv("c1", "Chat A", "2026-02-01T10:00:00Z"),
            _conv("c2", "Chat B", "2026-02-02T10:00:00Z"),
            _conv("c3", "Chat C", "2026-02-03T10:00:00Z"),
        ]
        client = _build_client(convs)

        # Run 1: full export
        result1 = export_project(client, "proj-1", "Test", tmp_path)
        assert result1.conversations_exported == 3

        # Run 2: incremental (nothing changed) — should skip all
        client2 = _build_client(convs)
        result2 = export_project(client2, "proj-1", "Test", tmp_path)
        assert result2.conversations_exported == 0
        assert result2.conversations_skipped == 3

        # Run 3: --full flag — should re-export everything
        client3 = _build_client(convs)
        result3 = export_project(client3, "proj-1", "Test", tmp_path, full=True)
        assert result3.conversations_exported == 3
        assert result3.conversations_skipped == 0

        # All conversations were fetched
        assert client3.get_conversation.call_count == 3

        # Manifest still valid after --full
        manifest_data = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert len(manifest_data["conversations"]) == 3


# ---------------------------------------------------------------------------
# Scenario 4: Conversation deleted between runs — manifest handles gracefully
# ---------------------------------------------------------------------------


class TestScenario4_ConversationDeleted:
    """A conversation exported in run 1 no longer exists in run 2."""

    def test_deleted_conversation_file_preserved_on_disk(self, tmp_path: Path):
        # Run 1: export 3 conversations
        convs = [
            _conv("c1", "Will Stay", "2026-03-01T10:00:00Z"),
            _conv("c2", "Will Be Deleted", "2026-03-02T10:00:00Z"),
            _conv("c3", "Also Stays", "2026-03-03T10:00:00Z"),
        ]
        client1 = _build_client(convs)
        result1 = export_project(client1, "proj-1", "Test", tmp_path)
        assert result1.conversations_exported == 3

        # Verify c2 file exists
        conv_files_before = {f.name for f in (tmp_path / "conversations").glob("*.md")}
        assert len(conv_files_before) == 3

        # Run 2: c2 is gone from API (deleted by user)
        remaining_convs = [
            _conv("c1", "Will Stay", "2026-03-01T10:00:00Z"),
            _conv("c3", "Also Stays", "2026-03-03T10:00:00Z"),
        ]
        client2 = _build_client(remaining_convs)
        result2 = export_project(client2, "proj-1", "Test", tmp_path)

        # Nothing new to export, c1 and c3 unchanged
        assert result2.conversations_exported == 0
        assert result2.conversations_skipped == 2

        # The deleted conversation's file is STILL on disk (not cleaned up)
        conv_files_after = {f.name for f in (tmp_path / "conversations").glob("*.md")}
        assert len(conv_files_after) == 3  # file preserved

        # Manifest no longer records c2 as needing update but keeps c1/c3
        manifest_data = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        # c2 is still in manifest (we don't remove deleted entries, just track them)
        assert "c1" in manifest_data["conversations"]
        assert "c3" in manifest_data["conversations"]


# ---------------------------------------------------------------------------
# Scenario 5: Rapid successive exports — manifest consistency under churn
# ---------------------------------------------------------------------------


class TestScenario5_RapidSuccessiveExports:
    """Multiple rapid exports with conversations being added/updated each time."""

    def test_three_consecutive_runs_with_evolving_data(self, tmp_path: Path):
        # --- Run 1: single conversation ---
        run1 = [_conv("c1", "First Chat", "2026-04-01T10:00:00Z", "2026-04-01T09:00:00Z")]
        client1 = _build_client(run1)
        r1 = export_project(client1, "proj-1", "Test", tmp_path)
        assert r1.conversations_exported == 1
        assert r1.conversations_skipped == 0

        manifest1 = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert len(manifest1["conversations"]) == 1
        ts1 = manifest1["exported_at"]

        # --- Run 2: add second conversation, first unchanged ---
        run2 = [
            _conv("c1", "First Chat", "2026-04-01T10:00:00Z", "2026-04-01T09:00:00Z"),
            _conv("c2", "Second Chat", "2026-04-02T12:00:00Z", "2026-04-02T11:00:00Z"),
        ]
        client2 = _build_client(run2)
        r2 = export_project(client2, "proj-1", "Test", tmp_path)
        assert r2.conversations_exported == 1  # only c2
        assert r2.conversations_skipped == 1  # c1 skipped

        manifest2 = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert len(manifest2["conversations"]) == 2
        assert manifest2["exported_at"] > ts1  # timestamp advanced

        # --- Run 3: both conversations updated ---
        run3 = [
            _conv("c1", "First Chat (v2)", "2026-04-03T08:00:00Z", "2026-04-01T09:00:00Z"),
            _conv("c2", "Second Chat (v2)", "2026-04-03T09:00:00Z", "2026-04-02T11:00:00Z"),
        ]
        client3 = _build_client(run3)
        r3 = export_project(client3, "proj-1", "Test", tmp_path)
        assert r3.conversations_exported == 2  # both updated
        assert r3.conversations_skipped == 0

        manifest3 = json.loads((tmp_path / MANIFEST_FILENAME).read_text())
        assert manifest3["conversations"]["c1"] == "2026-04-03T08:00:00Z"
        assert manifest3["conversations"]["c2"] == "2026-04-03T09:00:00Z"
        assert manifest3["exported_at"] > manifest2["exported_at"]

        # Verify final disk state: old filenames remain + new filenames created
        # (title change = new filename since title is part of the filename)
        conv_files = list((tmp_path / "conversations").glob("*.md"))
        assert len(conv_files) == 4  # c1 + c1(v2) + c2 + c2(v2)

        # Verify the latest versions exist with "(v2)" content
        v2_files = [f for f in conv_files if "v2" in f.name]
        assert len(v2_files) == 2
        for f in v2_files:
            content = f.read_text()
            assert "v2" in content
