"""Tests for Fireflies Markdown renderer."""

from claude_dump.fireflies_markdown import (
    format_timestamp,
    make_transcript_filename,
    render_transcript,
)
from claude_dump.fireflies_models import (
    FirefliesTranscript,
    MeetingAttendee,
    Sentence,
    TranscriptSummary,
)


# ---------------------------------------------------------------------------
# format_timestamp
# ---------------------------------------------------------------------------


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0.0) == "00:00"

    def test_seconds_only(self):
        assert format_timestamp(65.0) == "01:05"

    def test_hour_boundary(self):
        assert format_timestamp(3661.0) == "01:01:01"

    def test_fractional_seconds(self):
        # 125.5 -> 2 min 5 sec (fractional truncated)
        assert format_timestamp(125.5) == "02:05"

    def test_exact_hour(self):
        assert format_timestamp(3600.0) == "01:00:00"


# ---------------------------------------------------------------------------
# render_transcript
# ---------------------------------------------------------------------------


class TestRenderTranscript:
    def test_full_transcript(self):
        transcript = FirefliesTranscript(
            id="abc12345-def6",
            title="Weekly Standup",
            date="2026-05-10T10:00:00Z",
            duration=1825.0,
            transcript_url="https://app.fireflies.ai/view/abc",
            meeting_attendees=[
                MeetingAttendee(displayName="Alice", email="alice@example.com"),
                MeetingAttendee(displayName="Bob", email="bob@example.com"),
            ],
            sentences=[
                Sentence(speaker_name="Alice", text="Good morning everyone.", start_time=0.0, end_time=3.0),
                Sentence(speaker_name="Alice", text="Let's start the standup.", start_time=3.0, end_time=6.0),
                Sentence(speaker_name="Bob", text="Sure, I'll go first.", start_time=6.0, end_time=9.0),
            ],
            summary=TranscriptSummary(
                overview="Weekly standup meeting covering sprint progress.",
                action_items=["Review PR #42", "Update documentation"],
                keywords=["standup", "sprint", "review"],
            ),
        )

        result = render_transcript(transcript)

        # Frontmatter
        assert "---" in result
        assert "title: Weekly Standup" in result
        assert "date: 2026-05-10T10:00:00Z" in result
        assert "duration: 30:25" in result
        assert "source: fireflies" in result

        # Attendees
        assert "## Attendees" in result
        assert "- Alice (alice@example.com)" in result
        assert "- Bob (bob@example.com)" in result

        # Summary
        assert "## Summary" in result
        assert "Weekly standup meeting covering sprint progress." in result

        # Action items
        assert "## Action Items" in result
        assert "- [ ] Review PR #42" in result
        assert "- [ ] Update documentation" in result

        # Keywords
        assert "**Keywords:** standup, sprint, review" in result

        # Transcript body with speaker grouping
        assert "## Transcript" in result
        assert "**Alice** [00:00]" in result
        assert "Good morning everyone." in result
        assert "Let's start the standup." in result
        assert "**Bob** [00:06]" in result
        assert "Sure, I'll go first." in result

    def test_empty_sentences(self):
        transcript = FirefliesTranscript(
            id="empty123",
            title="Empty Meeting",
            date="2026-05-10",
            sentences=[],
        )

        result = render_transcript(transcript)
        assert "*No transcript content available.*" in result

    def test_no_summary(self):
        transcript = FirefliesTranscript(
            id="nosummary1",
            title="No Summary Meeting",
            date="2026-05-10",
            sentences=[
                Sentence(speaker_name="Alice", text="Hello.", start_time=0.0, end_time=1.0),
            ],
        )

        result = render_transcript(transcript)
        assert "## Summary" not in result
        assert "## Action Items" not in result
        assert "**Keywords:**" not in result

    def test_speaker_grouping(self):
        """Consecutive sentences by same speaker produce one header."""
        transcript = FirefliesTranscript(
            id="group1234",
            title="Group Test",
            date="2026-05-10",
            sentences=[
                Sentence(speaker_name="Alice", text="First.", start_time=0.0, end_time=1.0),
                Sentence(speaker_name="Alice", text="Second.", start_time=1.0, end_time=2.0),
                Sentence(speaker_name="Bob", text="Third.", start_time=2.0, end_time=3.0),
                Sentence(speaker_name="Alice", text="Fourth.", start_time=3.0, end_time=4.0),
            ],
        )

        result = render_transcript(transcript)

        # Alice appears twice (two separate groups), Bob once
        alice_headers = result.count("**Alice**")
        bob_headers = result.count("**Bob**")
        assert alice_headers == 2, f"Expected 2 Alice headers, got {alice_headers}"
        assert bob_headers == 1, f"Expected 1 Bob header, got {bob_headers}"

    def test_attendee_no_email(self):
        """Attendee without email skips parenthetical."""
        transcript = FirefliesTranscript(
            id="noemail12",
            title="No Email",
            date="2026-05-10",
            meeting_attendees=[
                MeetingAttendee(displayName="Charlie", email=""),
            ],
            sentences=[],
        )

        result = render_transcript(transcript)
        assert "- Charlie" in result
        assert "- Charlie ()" not in result


# ---------------------------------------------------------------------------
# make_transcript_filename
# ---------------------------------------------------------------------------


class TestMakeTranscriptFilename:
    def test_normal_filename(self):
        transcript = FirefliesTranscript(
            id="abc12345-def6-7890",
            title="Weekly Standup",
            date="2026-05-10T10:00:00Z",
        )
        filename = make_transcript_filename(transcript)
        assert filename == "2026-05-10_weekly-standup_abc12345.md"

    def test_no_date(self):
        transcript = FirefliesTranscript(
            id="xyz98765-abcd",
            title="Untitled Meeting",
            date="",
        )
        filename = make_transcript_filename(transcript)
        assert filename == "0000-00-00_untitled-meeting_xyz98765.md"

    def test_special_characters_in_title(self):
        transcript = FirefliesTranscript(
            id="spec1234-5678",
            title="Q1 2026: Budget Review & Planning!",
            date="2026-03-15",
        )
        filename = make_transcript_filename(transcript)
        assert filename == "2026-03-15_q1-2026-budget-review-planning_spec1234.md"
