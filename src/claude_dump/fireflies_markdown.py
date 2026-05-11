"""Markdown rendering for Fireflies.ai transcript export.

Pure transformation layer: converts FirefliesTranscript model objects into
well-formatted Markdown strings with speaker-attributed lines.  No I/O, no
HTTP calls.
"""

from __future__ import annotations

from claude_dump.fireflies_models import FirefliesTranscript
from claude_dump.markdown import sanitize_title


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format.

    If seconds >= 3600, format as ``HH:MM:SS``.
    Otherwise, format as ``MM:SS``.
    Returns ``"00:00"`` for 0.0.
    """
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def render_transcript(transcript: FirefliesTranscript) -> str:
    """Render a full Fireflies transcript to a Markdown document.

    Produces YAML frontmatter, attendees, summary, action items, keywords,
    and speaker-grouped transcript body with timestamps.
    """
    lines: list[str] = [
        "---",
        f"title: {transcript.title}",
        f"date: {transcript.date}",
        f"duration: {format_timestamp(transcript.duration)}",
        f"transcript_url: {transcript.transcript_url}",
        "source: fireflies",
        "---",
        "",
        f"# {transcript.title}",
        "",
    ]

    # Attendees section
    if transcript.meeting_attendees:
        lines.append("## Attendees")
        lines.append("")
        for attendee in transcript.meeting_attendees:
            if attendee.email:
                lines.append(f"- {attendee.displayName} ({attendee.email})")
            else:
                lines.append(f"- {attendee.displayName}")
        lines.append("")

    # Summary section
    if transcript.summary and transcript.summary.overview:
        lines.append("## Summary")
        lines.append("")
        lines.append(transcript.summary.overview)
        lines.append("")

    # Action items section
    if transcript.summary and transcript.summary.action_items:
        lines.append("## Action Items")
        lines.append("")
        for item in transcript.summary.action_items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    # Keywords
    if transcript.summary and transcript.summary.keywords:
        lines.append(f"**Keywords:** {', '.join(transcript.summary.keywords)}")
        lines.append("")

    # Transcript section
    lines.append("## Transcript")
    lines.append("")

    if not transcript.sentences:
        lines.append("*No transcript content available.*")
        lines.append("")
        return "\n".join(lines)

    # Group consecutive sentences by same speaker
    groups: list[list] = []
    current_speaker: str | None = None
    for sentence in transcript.sentences:
        if sentence.speaker_name != current_speaker:
            groups.append([sentence])
            current_speaker = sentence.speaker_name
        else:
            groups[-1].append(sentence)

    for i, group in enumerate(groups):
        speaker = group[0].speaker_name
        timestamp = format_timestamp(group[0].start_time)
        lines.append(f"**{speaker}** [{timestamp}]")
        for sentence in group:
            lines.append(sentence.text)
        if i < len(groups) - 1:
            lines.append("")

    lines.append("")
    return "\n".join(lines)


def make_transcript_filename(transcript: FirefliesTranscript) -> str:
    """Generate a sort-friendly, collision-resistant Markdown filename.

    Format: ``YYYY-MM-DD_sanitized-title_id8.md``
    """
    date = transcript.date[:10] if transcript.date else "0000-00-00"
    sanitized = sanitize_title(transcript.title)
    short_id = transcript.id[:8]
    return f"{date}_{sanitized}_{short_id}.md"
