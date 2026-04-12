"""Markdown rendering for Claude.ai conversation export.

Pure transformation layer: converts Conversation/ChatMessage/ContentBlock
model objects into well-formatted Markdown strings.  No I/O, no HTTP calls.
"""

import json

from claude_dump.models import ChatMessage, ContentBlock, Conversation


def render_block(block: ContentBlock) -> str:
    """Render a single content block to Markdown.

    Handles: text, thinking, tool_use, tool_result.
    Unknown types return empty string (graceful degradation).
    """
    if block.type == "text":
        return block.text

    if block.type == "thinking":
        return (
            "<details>\n"
            "<summary>Thinking</summary>\n"
            "\n"
            f"{block.thinking}\n"
            "\n"
            "</details>"
        )

    if block.type == "tool_use":
        # Artifact detection: name starts with "artifact" or input.type
        # contains "artifact".
        is_artifact = block.name.startswith("artifact") or "artifact" in str(
            block.input.get("type", "")
        )
        if is_artifact:
            return (
                "> [Artifact: content not available"
                " - Claude strips artifact source code server-side]"
            )
        return (
            f"```tool_use: {block.name}\n"
            f"{json.dumps(block.input, indent=2)}\n"
            "```"
        )

    if block.type == "tool_result":
        texts = [
            item.get("text", "")
            for item in block.content
            if isinstance(item, dict)
        ]
        joined = "\n".join(texts)
        return f"```tool_result\n{joined}\n```"

    # Unknown type -- graceful skip
    return ""


def render_message(msg: ChatMessage) -> str:
    """Render a single chat message to Markdown.

    Includes sender heading, timestamp, content blocks, and any attachment
    extracted content.
    """
    sender_label = msg.sender.capitalize()
    parts: list[str] = [
        f"### {sender_label}",
        f"*{msg.created_at}*",
        "",
    ]

    # Content blocks
    block_texts = [render_block(b) for b in msg.content]
    block_texts = [t for t in block_texts if t]  # drop empty
    parts.append("\n\n".join(block_texts))

    # Attachments with extracted content
    for att in msg.attachments:
        if att.extracted_content:
            parts.append("")
            parts.append(f"> **Attached: {att.file_name}**")
            # Prefix each line of extracted content with >
            for line in att.extracted_content.splitlines():
                parts.append(f"> {line}" if line else ">")

    return "\n".join(parts)


def render_conversation(conv: Conversation) -> str:
    """Render a full conversation to a Markdown document.

    Produces YAML front matter, optional summary blockquote, document
    heading, and all messages separated by horizontal rules.
    """
    lines: list[str] = [
        "---",
        f"title: {conv.name}",
        f"model: {conv.model}",
        f"created: {conv.created_at}",
        f"updated: {conv.updated_at}",
        f"uuid: {conv.uuid}",
        "---",
    ]

    if conv.summary:
        lines.append(f"> {conv.summary}")
        lines.append("")

    lines.append("")
    lines.append(f"# {conv.name}")
    lines.append("")

    messages = [render_message(m) for m in conv.chat_messages]
    lines.append("\n\n---\n\n".join(messages))

    return "\n".join(lines)
