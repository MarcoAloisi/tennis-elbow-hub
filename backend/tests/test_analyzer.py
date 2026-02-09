"""Tests for the analyzer service."""

import pytest

from app.services.analyzer import (
    analyze_match_log,
    extract_header_info,
    extract_stats_from_table,
    parse_ratio,
    parse_speed,
)


class TestParseRatio:
    """Tests for ratio string parsing."""

    def test_parse_full_format(self) -> None:
        """Test parsing '2 / 5 = 40%' format."""
        result = parse_ratio("2 / 5 = 40%")

        assert result == (2, 5, 40.0)

    def test_parse_simple_ratio(self) -> None:
        """Test parsing '2 / 5' format."""
        result = parse_ratio("2 / 5")

        assert result[0] == 2
        assert result[1] == 5
        assert result[2] == 40.0

    def test_parse_single_number(self) -> None:
        """Test parsing just a number."""
        result = parse_ratio("5")

        assert result[0] == 5
        assert result[1] == 0

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        result = parse_ratio("")

        assert result == (0, 0, 0.0)


class TestParseSpeed:
    """Tests for speed string parsing."""

    def test_parse_with_unit(self) -> None:
        """Test parsing '195 Km/h' format."""
        result = parse_speed("195 Km/h")

        assert result == 195.0

    def test_parse_without_unit(self) -> None:
        """Test parsing number without unit."""
        result = parse_speed("175")

        assert result == 175.0

    def test_parse_decimal(self) -> None:
        """Test parsing decimal speed."""
        result = parse_speed("175.5 Km/h")

        assert result == 175.5

    def test_parse_zero(self) -> None:
        """Test parsing zero."""
        result = parse_speed("0 Km/h")

        assert result == 0.0


class TestAnalyzeMatchLog:
    """Tests for complete match log analysis."""

    def test_analyze_valid_html(self, sample_match_html: str) -> None:
        """Test analyzing valid HTML content."""
        result = analyze_match_log(sample_match_html)

        assert result is not None
        assert result.info.player1_name is not None
        assert result.info.player2_name is not None

    def test_analyze_extracts_header(self, sample_match_html: str) -> None:
        """Test that header info is extracted."""
        result = analyze_match_log(sample_match_html)

        assert result is not None
        assert "Federer" in result.info.player1_name
        assert "Nadal" in result.info.player2_name

    def test_analyze_empty_html(self) -> None:
        """Test analyzing empty HTML."""
        result = analyze_match_log("")

        # Should return default values, not crash
        assert result is not None

    def test_analyze_malformed_html(self) -> None:
        """Test analyzing malformed HTML."""
        html = "<html><body><p>Not a match log</p></body></html>"
        result = analyze_match_log(html)

        # Should handle gracefully
        assert result is not None


class TestSpanishMatchLog:
    """Tests for Spanish match log analysis using 'vs' separator."""

    def test_analyze_spanish_html(self, sample_spanish_match_html: str) -> None:
        """Test analyzing Spanish HTML content."""
        result = analyze_match_log(sample_spanish_match_html)

        assert result is not None
        assert result.info.player1_name == "alnicozu"
        assert result.info.player2_name == "Franky Franchicha"

    def test_spanish_elo_extraction(self, sample_spanish_match_html: str) -> None:
        """Test that ELO is extracted correctly from Spanish format with Crc."""
        result = analyze_match_log(sample_spanish_match_html)

        assert result is not None
        assert result.info.player1_elo == 1606
        assert result.info.player1_elo_diff == 19
        assert result.info.player2_elo == 1772
        assert result.info.player2_elo_diff == -19

    def test_spanish_score_and_tournament(self, sample_spanish_match_html: str) -> None:
        """Test score and tournament extraction from Spanish header."""
        result = analyze_match_log(sample_spanish_match_html)

        assert result is not None
        assert result.info.score == "6/3"
        assert result.info.tournament == "AO Rod Laver Day"

    def test_spanish_stats_extraction(self, sample_spanish_match_html: str) -> None:
        """Test that positional stats are extracted from Spanish log."""
        result = analyze_match_log(sample_spanish_match_html)

        assert result is not None
        # P1 aces = 4 (Row 1 Left)
        assert result.player1.serve.aces == 4
        # P1 winners = 9 (Row 6 Left)
        assert result.player1.points.winners == 9
        # P1 total points = 30 (Row 11 Left)
        assert result.player1.points.total_points_won == 30
        # P2 total points = 21
        assert result.player2.points.total_points_won == 21


class TestPolishMatchLog:
    """Tests for Polish match log analysis using 'Przegrana' separator."""

    def test_analyze_polish_html(self, sample_polish_match_html: str) -> None:
        """Test analyzing Polish HTML content."""
        result = analyze_match_log(sample_polish_match_html)

        assert result is not None
        # Verify doubled player names are captured
        assert "POLAND" in result.info.player1_name
        assert "Lleyton Hewitt" in result.info.player1_name
        assert "Marcolino" in result.info.player2_name
        assert "Bob Bryan" in result.info.player2_name

    def test_polish_elo_extraction(self, sample_polish_match_html: str) -> None:
        """Test ELO extraction from Polish header (should be None as it uses Crc)."""
        result = analyze_match_log(sample_polish_match_html)

        assert result is not None
        # No ELO in this fixture
        assert result.info.player1_elo is None
        assert result.info.player2_elo is None

    def test_polish_score_and_tournament(self, sample_polish_match_html: str) -> None:
        """Test score and tournament from Polish header."""
        result = analyze_match_log(sample_polish_match_html)

        assert result is not None
        assert result.info.score == "6/3 6/7(4) 6/3"
        assert result.info.tournament == "AO Rod Laver Night"

    def test_polish_stats_extraction(self, sample_polish_match_html: str) -> None:
        """Test positional stats extraction from Polish log."""
        result = analyze_match_log(sample_polish_match_html)

        assert result is not None
        # P1 aces = 5
        assert result.player1.serve.aces == 5
        # P1 winners = 54 (Row 9 Left)
        assert result.player1.points.winners == 54
        # P1 total points = 108 (Row 11 Left)
        assert result.player1.points.total_points_won == 108
        # P2 total points = 88
        assert result.player2.points.total_points_won == 88
