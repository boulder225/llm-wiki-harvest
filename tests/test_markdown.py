"""Tests for the Markdown rendering module."""

from claude_dump.markdown import render_block, render_conversation, render_message
from claude_dump.models import Attachment, ChatMessage, ContentBlock, Conversation


# ---------------------------------------------------------------------------
# render_block tests
# ---------------------------------------------------------------------------


class TestRenderBlockText:
    def test_returns_text_as_is(self):
        block = ContentBlock(type="text", text="Hello world")
        assert render_block(block) == "Hello world"

    def test_preserves_line_breaks(self):
        block = ContentBlock(type="text", text="line1\nline2\nline3")
        assert render_block(block) == "line1\nline2\nline3"


class TestRenderBlockThinking:
    def test_renders_details_section(self):
        block = ContentBlock(type="thinking", thinking="I need to think...")
        result = render_block(block)
        assert "<details>" in result
        assert "<summary>Thinking</summary>" in result
        assert "I need to think..." in result
        assert "</details>" in result

    def test_preserves_truncation_note(self):
        block = ContentBlock(
            type="thinking",
            thinking="Some thinking...\n\n(5000 characters truncated)",
        )
        result = render_block(block)
        assert "(5000 characters truncated)" in result


class TestRenderBlockToolUse:
    def test_renders_code_fence_with_name(self):
        block = ContentBlock(
            type="tool_use",
            name="search",
            input={"query": "hello"},
        )
        result = render_block(block)
        assert "```tool_use: search" in result
        assert '"query": "hello"' in result
        assert result.strip().endswith("```")

    def test_artifact_returns_placeholder(self):
        block = ContentBlock(
            type="tool_use",
            name="artifact",
            input={"type": "text/html", "content": "<h1>Hi</h1>"},
        )
        result = render_block(block)
        assert "Artifact: content not available" in result
        assert "```" not in result

    def test_artifact_detected_by_input_type(self):
        block = ContentBlock(
            type="tool_use",
            name="some_tool",
            input={"type": "application/vnd.ant.artifact"},
        )
        result = render_block(block)
        assert "Artifact: content not available" in result


class TestRenderBlockToolResult:
    def test_renders_tool_result_fence(self):
        block = ContentBlock(
            type="tool_result",
            content=[{"type": "text", "text": "Result line 1"}, {"type": "text", "text": "Result line 2"}],
        )
        result = render_block(block)
        assert "```tool_result" in result
        assert "Result line 1" in result
        assert "Result line 2" in result
        assert result.strip().endswith("```")


class TestRenderBlockUnknown:
    def test_unknown_type_returns_empty(self):
        block = ContentBlock(type="some_future_type", text="whatever")
        assert render_block(block) == ""


# ---------------------------------------------------------------------------
# render_message tests
# ---------------------------------------------------------------------------


class TestRenderMessage:
    def test_human_sender_label(self):
        msg = ChatMessage(
            sender="human",
            created_at="2026-01-15T14:30:00Z",
            content=[ContentBlock(type="text", text="Hello")],
        )
        result = render_message(msg)
        assert "### Human" in result
        assert "*2026-01-15T14:30:00Z*" in result
        assert "Hello" in result

    def test_assistant_sender_label(self):
        msg = ChatMessage(
            sender="assistant",
            created_at="2026-01-15T14:31:00Z",
            content=[ContentBlock(type="text", text="Hi there")],
        )
        result = render_message(msg)
        assert "### Assistant" in result

    def test_includes_attachment_extracted_content(self):
        msg = ChatMessage(
            sender="human",
            created_at="2026-01-15T14:30:00Z",
            content=[ContentBlock(type="text", text="See attached")],
            attachments=[
                Attachment(
                    file_name="report.pdf",
                    file_type="application/pdf",
                    extracted_content="This is the extracted text from the PDF.",
                )
            ],
        )
        result = render_message(msg)
        assert "> **Attached: report.pdf**" in result
        assert "This is the extracted text from the PDF." in result


# ---------------------------------------------------------------------------
# render_conversation tests
# ---------------------------------------------------------------------------


class TestRenderConversation:
    def _make_conversation(self, **kwargs):
        defaults = {
            "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "name": "Test Conversation",
            "model": "claude-3-opus-20240229",
            "created_at": "2026-01-15T14:30:00Z",
            "updated_at": "2026-01-15T15:00:00Z",
            "summary": "",
            "chat_messages": [],
        }
        defaults.update(kwargs)
        return Conversation(**defaults)

    def test_yaml_header_present(self):
        conv = self._make_conversation()
        result = render_conversation(conv)
        assert result.startswith("---\n")
        assert "title: Test Conversation" in result
        assert "model: claude-3-opus-20240229" in result
        assert "created: 2026-01-15T14:30:00Z" in result
        assert "updated: 2026-01-15T15:00:00Z" in result
        assert "uuid: a1b2c3d4-e5f6-7890-abcd-ef1234567890" in result

    def test_summary_included_when_present(self):
        conv = self._make_conversation(summary="A chat about testing")
        result = render_conversation(conv)
        assert "> A chat about testing" in result

    def test_summary_omitted_when_empty(self):
        conv = self._make_conversation(summary="")
        result = render_conversation(conv)
        # Should not have a bare ">" blockquote line
        lines = result.split("\n")
        # After the closing --- of YAML, there should be no "> " line
        yaml_end_idx = None
        for i, line in enumerate(lines):
            if i > 0 and line == "---":
                yaml_end_idx = i
                break
        assert yaml_end_idx is not None
        # Check lines immediately after YAML closing
        after_yaml = lines[yaml_end_idx + 1 : yaml_end_idx + 4]
        assert not any(line.startswith("> ") for line in after_yaml)

    def test_multiple_messages_separated_by_hr(self):
        conv = self._make_conversation(
            chat_messages=[
                ChatMessage(
                    sender="human",
                    created_at="2026-01-15T14:30:00Z",
                    content=[ContentBlock(type="text", text="Hello")],
                ),
                ChatMessage(
                    sender="assistant",
                    created_at="2026-01-15T14:31:00Z",
                    content=[ContentBlock(type="text", text="Hi!")],
                ),
            ]
        )
        result = render_conversation(conv)
        assert "\n\n---\n\n" in result
        assert "### Human" in result
        assert "### Assistant" in result

    def test_document_heading(self):
        conv = self._make_conversation(name="My Great Chat")
        result = render_conversation(conv)
        assert "# My Great Chat" in result
