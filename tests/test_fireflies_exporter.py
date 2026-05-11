"""Tests for Fireflies export pipeline."""

from unittest.mock import MagicMock

from claude_dump.fireflies_exporter import export_fireflies_transcripts
from claude_dump.fireflies_models import (
    FirefliesTranscript,
    FirefliesTranscriptSummaryItem,
    Sentence,
    TranscriptSummary,
)


def _make_summary(id: str, title: str) -> FirefliesTranscriptSummaryItem:
    return FirefliesTranscriptSummaryItem(
        id=id,
        title=title,
        date="2026-05-10T10:00:00Z",
        duration=600.0,
        participants=["Alice", "Bob"],
    )


def _make_transcript(id: str, title: str) -> FirefliesTranscript:
    return FirefliesTranscript(
        id=id,
        title=title,
        date="2026-05-10T10:00:00Z",
        duration=600.0,
        sentences=[
            Sentence(speaker_name="Alice", text="Hello there.", start_time=0.0, end_time=2.0),
            Sentence(speaker_name="Bob", text="Hi Alice.", start_time=2.0, end_time=4.0),
        ],
        summary=TranscriptSummary(overview="A quick sync."),
    )


class TestExportFirefliesTranscripts:
    def test_exports_two_transcripts(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_all_transcripts.return_value = [
            _make_summary("id-aaa11111", "Meeting One"),
            _make_summary("id-bbb22222", "Meeting Two"),
        ]
        mock_client.get_transcript.side_effect = [
            _make_transcript("id-aaa11111", "Meeting One"),
            _make_transcript("id-bbb22222", "Meeting Two"),
        ]

        result = export_fireflies_transcripts(mock_client, tmp_path)

        assert result.transcripts_exported == 2
        assert result.transcripts_failed == 0
        assert len(result.exported_files) == 2

        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) == 2

        # Verify content
        for f in md_files:
            content = f.read_text(encoding="utf-8")
            assert "## Transcript" in content
            assert "Alice" in content
            assert "Bob" in content

    def test_empty_transcript_list(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_all_transcripts.return_value = []

        result = export_fireflies_transcripts(mock_client, tmp_path)

        assert result.transcripts_exported == 0
        assert result.transcripts_failed == 0
        assert len(list(tmp_path.glob("*.md"))) == 0

    def test_one_failing_transcript(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_all_transcripts.return_value = [
            _make_summary("id-ccc33333", "Good Meeting"),
            _make_summary("id-ddd44444", "Bad Meeting"),
        ]
        mock_client.get_transcript.side_effect = [
            _make_transcript("id-ccc33333", "Good Meeting"),
            RuntimeError("API timeout"),
        ]

        result = export_fireflies_transcripts(mock_client, tmp_path)

        assert result.transcripts_exported == 1
        assert result.transcripts_failed == 1
        assert len(result.exported_files) == 1

    def test_creates_output_directory(self, tmp_path):
        nested = tmp_path / "sub" / "dir"
        mock_client = MagicMock()
        mock_client.list_all_transcripts.return_value = []

        export_fireflies_transcripts(mock_client, nested)

        assert nested.is_dir()
