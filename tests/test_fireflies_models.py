"""Tests for Fireflies Pydantic models."""

from claude_dump.fireflies_models import (
    FirefliesTranscript,
    FirefliesTranscriptSummaryItem,
    Sentence,
    TranscriptSummary,
)


class TestFirefliesTranscript:
    def test_full_response(self):
        """Parse a complete transcript response with all nested fields."""
        data = {
            "id": "tx-001",
            "title": "Weekly Standup",
            "date": "2026-05-10T09:00:00Z",
            "duration": 1800.0,
            "transcript_url": "https://app.fireflies.ai/view/tx-001",
            "audio_url": "https://storage.fireflies.ai/tx-001.mp3",
            "video_url": "",
            "speakers": [
                {"id": "s1", "name": "Alice"},
                {"id": "s2", "name": "Bob"},
            ],
            "meeting_attendees": [
                {"displayName": "Alice Smith", "email": "alice@example.com"},
                {"displayName": "Bob Jones", "email": "bob@example.com"},
            ],
            "sentences": [
                {
                    "speaker_name": "Alice",
                    "text": "Good morning everyone.",
                    "raw_text": "Good morning everyone.",
                    "start_time": 0.5,
                    "end_time": 2.1,
                },
                {
                    "speaker_name": "Bob",
                    "text": "Morning!",
                    "raw_text": "Morning!",
                    "start_time": 2.5,
                    "end_time": 3.0,
                },
            ],
            "summary": {
                "keywords": ["standup", "sprint"],
                "action_items": ["Review PR #42"],
                "overview": "Weekly standup covering sprint progress.",
                "shorthand_bullet": "- Sprint on track\n- PR review needed",
                "outline": "1. Status updates\n2. Blockers",
            },
        }

        result = FirefliesTranscript.model_validate(data)

        assert result.id == "tx-001"
        assert result.title == "Weekly Standup"
        assert result.duration == 1800.0
        assert len(result.speakers) == 2
        assert result.speakers[0].name == "Alice"
        assert len(result.meeting_attendees) == 2
        assert result.meeting_attendees[1].email == "bob@example.com"
        assert len(result.sentences) == 2
        assert result.sentences[0].text == "Good morning everyone."
        assert result.summary is not None
        assert result.summary.keywords == ["standup", "sprint"]
        assert result.summary.action_items == ["Review PR #42"]

    def test_extra_fields_ignored(self):
        """Unknown API fields should not cause validation errors."""
        data = {
            "id": "tx-002",
            "title": "Test",
            "unknown_field": "should be ignored",
            "another_extra": 42,
            "speakers": [{"id": "s1", "name": "Alice", "extra_speaker_field": True}],
            "sentences": [
                {
                    "speaker_name": "Alice",
                    "text": "Hello",
                    "confidence": 0.95,  # extra field
                }
            ],
            "summary": {
                "overview": "Short",
                "new_summary_field": "ignored",
            },
        }

        result = FirefliesTranscript.model_validate(data)

        assert result.id == "tx-002"
        assert result.speakers[0].name == "Alice"
        assert result.sentences[0].text == "Hello"


class TestFirefliesTranscriptSummaryItem:
    def test_list_query_shape(self):
        """Parse the lighter shape returned by the transcripts list query."""
        data = {
            "id": "tx-003",
            "title": "Design Review",
            "date": "2026-05-09T14:00:00Z",
            "duration": 3600.0,
            "transcript_url": "https://app.fireflies.ai/view/tx-003",
            "participants": ["Alice", "Bob", "Charlie"],
        }

        result = FirefliesTranscriptSummaryItem.model_validate(data)

        assert result.id == "tx-003"
        assert result.title == "Design Review"
        assert result.duration == 3600.0
        assert len(result.participants) == 3
        assert "Charlie" in result.participants

    def test_empty_participants(self):
        """Participants defaults to empty list when not provided."""
        data = {"id": "tx-004", "title": "Solo"}

        result = FirefliesTranscriptSummaryItem.model_validate(data)

        assert result.participants == []


class TestSentenceDefaults:
    def test_missing_times_default_to_zero(self):
        """start_time and end_time default to 0.0 when absent."""
        data = {"speaker_name": "Alice", "text": "Hello"}

        result = Sentence.model_validate(data)

        assert result.start_time == 0.0
        assert result.end_time == 0.0
        assert result.raw_text == ""


class TestTranscriptSummaryPartial:
    def test_partial_summary(self):
        """Summary with only overview, no action_items or keywords."""
        data = {"overview": "A brief meeting about nothing."}

        result = TranscriptSummary.model_validate(data)

        assert result.overview == "A brief meeting about nothing."
        assert result.keywords == []
        assert result.action_items == []
        assert result.shorthand_bullet == ""
        assert result.outline == ""
