"""Tests for ClaudeAPIClient conversation methods using pytest-httpx."""

import json

import pytest
from pytest_httpx import HTTPXMock

from claude_dump.client import ClaudeAPIClient
from claude_dump.models import Conversation


@pytest.fixture
def client() -> ClaudeAPIClient:
    """Create a client with org_id pre-set."""
    c = ClaudeAPIClient(cookie="sk-ant-test-cookie", org_id="org-123")
    yield c
    c.close()


@pytest.fixture
def client_no_org() -> ClaudeAPIClient:
    """Create a client without org_id."""
    c = ClaudeAPIClient(cookie="sk-ant-test-cookie")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# list_conversations
# ---------------------------------------------------------------------------


class TestListConversations:
    def test_single_page(self, client: ClaudeAPIClient, httpx_mock: HTTPXMock):
        """When fewer than 100 items returned, no further pages fetched."""
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/projects/proj-1/conversations_v2?limit=100&offset=0",
            json=[
                {"uuid": "conv-1", "name": "First"},
                {"uuid": "conv-2", "name": "Second"},
            ],
        )

        result = client.list_conversations("proj-1")

        assert len(result) == 2
        assert all(isinstance(c, Conversation) for c in result)
        assert result[0].uuid == "conv-1"
        assert result[1].uuid == "conv-2"

    def test_pagination_two_pages(self, client: ClaudeAPIClient, httpx_mock: HTTPXMock):
        """When first page has exactly 100 items, fetch next page."""
        # First page: 100 items
        page1 = [{"uuid": f"conv-{i}", "name": f"Conv {i}"} for i in range(100)]
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/projects/proj-1/conversations_v2?limit=100&offset=0",
            json=page1,
        )
        # Second page: 30 items (less than 100 => stop)
        page2 = [{"uuid": f"conv-{100+i}", "name": f"Conv {100+i}"} for i in range(30)]
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/projects/proj-1/conversations_v2?limit=100&offset=100",
            json=page2,
        )

        result = client.list_conversations("proj-1")

        assert len(result) == 130

    def test_handles_data_wrapper(self, client: ClaudeAPIClient, httpx_mock: HTTPXMock):
        """API may return {"data": [...]} wrapper."""
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/projects/proj-1/conversations_v2?limit=100&offset=0",
            json={"data": [{"uuid": "conv-1", "name": "Wrapped"}]},
        )

        result = client.list_conversations("proj-1")

        assert len(result) == 1
        assert result[0].name == "Wrapped"

    def test_empty_project(self, client: ClaudeAPIClient, httpx_mock: HTTPXMock):
        """Empty project returns empty list."""
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/projects/proj-1/conversations_v2?limit=100&offset=0",
            json=[],
        )

        result = client.list_conversations("proj-1")

        assert result == []

    def test_requires_org_id(self, client_no_org: ClaudeAPIClient):
        """Should raise ValueError if org_id not set."""
        with pytest.raises(ValueError, match="org_id is required"):
            client_no_org.list_conversations("proj-1")


# ---------------------------------------------------------------------------
# get_conversation
# ---------------------------------------------------------------------------


class TestGetConversation:
    def test_returns_conversation_with_messages(
        self, client: ClaudeAPIClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/chat_conversations/conv-1?tree=True&rendering_mode=messages&render_all_tools=true",
            json={
                "uuid": "conv-1",
                "name": "Test Conv",
                "model": "claude-3-opus-20240229",
                "chat_messages": [
                    {
                        "sender": "human",
                        "content": [{"type": "text", "text": "Hello"}],
                    },
                    {
                        "sender": "assistant",
                        "content": [{"type": "text", "text": "Hi there!"}],
                    },
                ],
            },
        )

        result = client.get_conversation("conv-1")

        assert isinstance(result, Conversation)
        assert result.uuid == "conv-1"
        assert result.name == "Test Conv"
        assert len(result.chat_messages) == 2
        assert result.chat_messages[0].sender == "human"
        assert result.chat_messages[1].content[0].text == "Hi there!"

    def test_requires_org_id(self, client_no_org: ClaudeAPIClient):
        """Should raise ValueError if org_id not set."""
        with pytest.raises(ValueError, match="org_id is required"):
            client_no_org.get_conversation("conv-1")

    def test_conversation_with_all_block_types(
        self, client: ClaudeAPIClient, httpx_mock: HTTPXMock
    ):
        """Verify full round-trip parsing of all content block types."""
        httpx_mock.add_response(
            url="https://claude.ai/api/organizations/org-123/chat_conversations/conv-2?tree=True&rendering_mode=messages&render_all_tools=true",
            json={
                "uuid": "conv-2",
                "name": "Complex Conv",
                "chat_messages": [
                    {
                        "sender": "assistant",
                        "content": [
                            {"type": "thinking", "thinking": "Let me think..."},
                            {"type": "text", "text": "Answer"},
                            {
                                "type": "tool_use",
                                "name": "search",
                                "input": {"query": "test"},
                            },
                            {
                                "type": "tool_result",
                                "content": [{"type": "text", "text": "result"}],
                            },
                        ],
                    }
                ],
            },
        )

        result = client.get_conversation("conv-2")

        blocks = result.chat_messages[0].content
        assert len(blocks) == 4
        assert blocks[0].type == "thinking"
        assert blocks[1].type == "text"
        assert blocks[2].type == "tool_use"
        assert blocks[2].name == "search"
        assert blocks[3].type == "tool_result"
