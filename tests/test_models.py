"""Tests for Pydantic models: ContentBlock, Attachment, FileRef, ChatMessage, Conversation."""

import pytest
from claude_dump.models import (
    Attachment,
    ChatMessage,
    ContentBlock,
    Conversation,
    FileRef,
)


# ---------------------------------------------------------------------------
# ContentBlock
# ---------------------------------------------------------------------------


class TestContentBlock:
    def test_text_block(self):
        block = ContentBlock.model_validate({"type": "text", "text": "Hello world"})
        assert block.type == "text"
        assert block.text == "Hello world"

    def test_thinking_block(self):
        block = ContentBlock.model_validate(
            {"type": "thinking", "thinking": "Let me reason about this..."}
        )
        assert block.type == "thinking"
        assert block.thinking == "Let me reason about this..."

    def test_tool_use_block(self):
        block = ContentBlock.model_validate(
            {
                "type": "tool_use",
                "name": "calculator",
                "input": {"expression": "2+2"},
            }
        )
        assert block.type == "tool_use"
        assert block.name == "calculator"
        assert block.input == {"expression": "2+2"}

    def test_tool_result_block(self):
        block = ContentBlock.model_validate(
            {
                "type": "tool_result",
                "content": [{"type": "text", "text": "4"}],
            }
        )
        assert block.type == "tool_result"
        assert block.content == [{"type": "text", "text": "4"}]

    def test_unknown_type_does_not_raise(self):
        """Unknown block types should not raise validation errors (extra='ignore')."""
        block = ContentBlock.model_validate(
            {"type": "some_future_type", "some_field": "value"}
        )
        assert block.type == "some_future_type"

    def test_defaults_for_optional_fields(self):
        block = ContentBlock.model_validate({"type": "text"})
        assert block.text == ""
        assert block.thinking == ""
        assert block.name == ""
        assert block.input == {}
        assert block.content == []

    def test_extra_fields_ignored(self):
        block = ContentBlock.model_validate(
            {"type": "text", "text": "hi", "unknown_field": 42}
        )
        assert block.type == "text"
        assert not hasattr(block, "unknown_field")


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------


class TestAttachment:
    def test_basic(self):
        att = Attachment.model_validate(
            {
                "file_name": "report.pdf",
                "file_type": "application/pdf",
                "extracted_content": "Some extracted text",
            }
        )
        assert att.file_name == "report.pdf"
        assert att.file_type == "application/pdf"
        assert att.extracted_content == "Some extracted text"

    def test_defaults(self):
        att = Attachment.model_validate({})
        assert att.file_name == ""
        assert att.file_type == ""
        assert att.extracted_content == ""

    def test_extra_fields_ignored(self):
        att = Attachment.model_validate({"file_name": "a.pdf", "extra": True})
        assert att.file_name == "a.pdf"
        assert not hasattr(att, "extra")


# ---------------------------------------------------------------------------
# FileRef
# ---------------------------------------------------------------------------


class TestFileRef:
    def test_basic(self):
        ref = FileRef.model_validate(
            {
                "file_uuid": "abc-123",
                "file_name": "image.png",
                "file_kind": "image",
            }
        )
        assert ref.file_uuid == "abc-123"
        assert ref.file_name == "image.png"
        assert ref.file_kind == "image"

    def test_defaults(self):
        ref = FileRef.model_validate({})
        assert ref.file_uuid == ""
        assert ref.file_name == ""
        assert ref.file_kind == ""

    def test_extra_fields_ignored(self):
        ref = FileRef.model_validate({"file_uuid": "x", "size": 1024})
        assert ref.file_uuid == "x"
        assert not hasattr(ref, "size")


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------


class TestChatMessage:
    def test_basic_human_message(self):
        msg = ChatMessage.model_validate(
            {
                "sender": "human",
                "content": [{"type": "text", "text": "Hello"}],
            }
        )
        assert msg.sender == "human"
        assert len(msg.content) == 1
        assert isinstance(msg.content[0], ContentBlock)
        assert msg.content[0].text == "Hello"

    def test_assistant_message_with_mixed_blocks(self):
        msg = ChatMessage.model_validate(
            {
                "sender": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "reasoning..."},
                    {"type": "text", "text": "Here is the answer"},
                    {"type": "tool_use", "name": "search", "input": {"q": "test"}},
                ],
            }
        )
        assert msg.sender == "assistant"
        assert len(msg.content) == 3
        assert msg.content[0].type == "thinking"
        assert msg.content[1].type == "text"
        assert msg.content[2].type == "tool_use"

    def test_defaults(self):
        msg = ChatMessage.model_validate({"sender": "human"})
        assert msg.uuid == ""
        assert msg.created_at == ""
        assert msg.content == []
        assert msg.attachments == []
        assert msg.files_v2 == []

    def test_with_attachments_and_files(self):
        msg = ChatMessage.model_validate(
            {
                "sender": "human",
                "attachments": [
                    {"file_name": "doc.pdf", "extracted_content": "text from pdf"}
                ],
                "files_v2": [
                    {"file_uuid": "uuid-1", "file_name": "img.png", "file_kind": "image"}
                ],
            }
        )
        assert len(msg.attachments) == 1
        assert isinstance(msg.attachments[0], Attachment)
        assert msg.attachments[0].extracted_content == "text from pdf"
        assert len(msg.files_v2) == 1
        assert isinstance(msg.files_v2[0], FileRef)
        assert msg.files_v2[0].file_uuid == "uuid-1"

    def test_extra_fields_ignored(self):
        msg = ChatMessage.model_validate(
            {"sender": "human", "unknown_api_field": "ignored"}
        )
        assert msg.sender == "human"
        assert not hasattr(msg, "unknown_api_field")


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class TestConversation:
    def test_metadata_only(self):
        """Conversation from list endpoint has metadata but no messages."""
        conv = Conversation.model_validate(
            {
                "uuid": "conv-123",
                "name": "Test Conversation",
                "model": "claude-3-opus-20240229",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }
        )
        assert conv.uuid == "conv-123"
        assert conv.name == "Test Conversation"
        assert conv.model == "claude-3-opus-20240229"
        assert conv.chat_messages == []

    def test_with_chat_messages(self):
        """Conversation from single-fetch has messages."""
        conv = Conversation.model_validate(
            {
                "uuid": "conv-456",
                "name": "Full Conversation",
                "chat_messages": [
                    {
                        "sender": "human",
                        "content": [{"type": "text", "text": "Hi"}],
                    },
                    {
                        "sender": "assistant",
                        "content": [{"type": "text", "text": "Hello!"}],
                    },
                ],
            }
        )
        assert len(conv.chat_messages) == 2
        assert isinstance(conv.chat_messages[0], ChatMessage)
        assert conv.chat_messages[0].sender == "human"
        assert conv.chat_messages[1].sender == "assistant"

    def test_defaults(self):
        conv = Conversation.model_validate({"uuid": "abc"})
        assert conv.name == ""
        assert conv.model == ""
        assert conv.created_at == ""
        assert conv.updated_at == ""
        assert conv.summary == ""
        assert conv.chat_messages == []

    def test_extra_fields_ignored(self):
        conv = Conversation.model_validate(
            {"uuid": "abc", "some_new_api_field": "whatever"}
        )
        assert conv.uuid == "abc"
        assert not hasattr(conv, "some_new_api_field")
