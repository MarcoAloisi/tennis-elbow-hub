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
