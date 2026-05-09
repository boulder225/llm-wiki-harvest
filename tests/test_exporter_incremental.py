"""Tests for incremental export (manifest-based delta logic)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from claude_dump.exporter import export_project, ExportResult
from claude_dump.manifest import ExportManifest, MANIFEST_FILENAME
from claude_dump.models import Conversation, ChatMessage, ContentBlock


def _make_conv(uuid: str, updated_at: str, name: str = "Test") -> Conversation:
    """Helper to create a Conversation with minimal fields."""
    return Conversation(
        uuid=uuid,
        name=name,
        created_at="2026-01-01T00:00:00Z",
        updated_at=updated_at,
        chat_messages=[
            ChatMessage(
                uuid="msg-1",
                sender="human",
                content=[ContentBlock(type="text", text="Hello")],
            )
        ],
    )


def _mock_client(conversations: list[Conversation]):
    """Create a mock ClaudeAPIClient."""
    client = MagicMock()
    # list_conversations returns metadata (no messages)
    meta = [
        Conversation(uuid=c.uuid, name=c.name, created_at=c.created_at, updated_at=c.updated_at)
        for c in conversations
    ]
    client.list_conversations.return_value = meta
    # get_conversation returns full conversation by uuid
    conv_map = {c.uuid: c for c in conversations}
    client.get_conversation.side_effect = lambda uuid: conv_map[uuid]
    client.list_knowledge_docs.return_value = []
    return client


class TestIncrementalExport:
    def test_first_run_exports_all_and_creates_manifest(self, tmp_path: Path):
        convs = [_make_conv("aaa", "2026-01-01T10:00:00Z")]
        client = _mock_client(convs)

        result = export_project(client, "proj-1", "Test", tmp_path)

        assert result.conversations_exported == 1
        assert result.conversations_skipped == 0
        manifest_path = tmp_path / MANIFEST_FILENAME
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert "aaa" in data["conversations"]

    def test_second_run_skips_unchanged(self, tmp_path: Path):
        convs = [_make_conv("aaa", "2026-01-01T10:00:00Z")]
        client = _mock_client(convs)

        # First run
        export_project(client, "proj-1", "Test", tmp_path)
        # Second run -- same updated_at
        client.get_conversation.reset_mock()
        result = export_project(client, "proj-1", "Test", tmp_path)

        assert result.conversations_exported == 0
        assert result.conversations_skipped == 1
        client.get_conversation.assert_not_called()

    def test_updated_conversation_is_re_exported(self, tmp_path: Path):
        client = _mock_client([_make_conv("aaa", "2026-01-01T10:00:00Z")])
        export_project(client, "proj-1", "Test", tmp_path)

        # Second run with updated timestamp
        updated_convs = [_make_conv("aaa", "2026-01-02T10:00:00Z")]
        client2 = _mock_client(updated_convs)
        result = export_project(client2, "proj-1", "Test", tmp_path)

        assert result.conversations_exported == 1
        assert result.conversations_skipped == 0

    def test_new_conversation_is_exported(self, tmp_path: Path):
        client = _mock_client([_make_conv("aaa", "2026-01-01T10:00:00Z")])
        export_project(client, "proj-1", "Test", tmp_path)

        # Second run with additional conversation
        new_convs = [
            _make_conv("aaa", "2026-01-01T10:00:00Z"),
            _make_conv("bbb", "2026-01-02T10:00:00Z", name="New"),
        ]
        client2 = _mock_client(new_convs)
        result = export_project(client2, "proj-1", "Test", tmp_path)

        assert result.conversations_exported == 1
        assert result.conversations_skipped == 1

    def test_full_flag_ignores_manifest(self, tmp_path: Path):
        convs = [_make_conv("aaa", "2026-01-01T10:00:00Z")]
        client = _mock_client(convs)

        export_project(client, "proj-1", "Test", tmp_path)
        # Second run with --full
        result = export_project(client, "proj-1", "Test", tmp_path, full=True)

        assert result.conversations_exported == 1
        assert result.conversations_skipped == 0
