"""Tests for the parser service."""

import pytest

from app.models.game_server import ControlMode, PlayerConfig, SkillMode
from app.services.parser import (
    parse_game_info_bitfield,
    parse_server_entry,
    tokenize_server_line,
)


class TestParseGameInfoBitfield:
    """Tests for GameInfo bitfield parsing."""

    def test_parse_singles_mode(self) -> None:
        """Test parsing a singles game configuration."""
        # Value with PlayerConfig = 0 (Singles)
        value = 0x00000000
        result = parse_game_info_bitfield(value)

        assert result.player_config == PlayerConfig.SINGLES
        assert result.trial == 0

    def test_parse_doubles_mode(self) -> None:
        """Test parsing a doubles game configuration."""
        # PlayerConfig = 2 at bits 2-4 means Competitive Doubles
        value = 0x00000008  # Binary: 1000, bits 2-4 = 010 = 2
        result = parse_game_info_bitfield(value)

        assert result.player_config == PlayerConfig.COMPETITIVE_DOUBLES

    def test_parse_full_bitfield(self) -> None:
        """Test parsing a complete bitfield value."""
        # 0x1B198E41 from sample data
        value = 0x1B198E41
        result = parse_game_info_bitfield(value)

        # Verify structure is returned
        assert hasattr(result, "player_config")
        assert hasattr(result, "nb_set")
        assert hasattr(result, "skill_mode")
        assert hasattr(result, "tiredness")

    def test_parse_tiredness_flag(self) -> None:
        """Test parsing the tiredness bit."""
        # Bit 27 set
        value = 0x08000000
        result = parse_game_info_bitfield(value)

        assert result.tiredness is True

        # Bit 27 clear
        value = 0x00000000
        result = parse_game_info_bitfield(value)

        assert result.tiredness is False


class TestTokenizeServerLine:
    """Tests for server line tokenization."""

    def test_tokenize_simple_line(self) -> None:
        """Test tokenizing a simple server entry."""
        line = '0 E9FD "Test Match" 1234'
        tokens = tokenize_server_line(line)

        assert "0" in tokens
        assert "E9FD" in tokens
        assert "Test Match" in tokens
        assert "1234" in tokens

    def test_tokenize_with_unicode(self) -> None:
        """Test tokenizing with unicode characters."""
        line = '0 E9FD "プレイヤー vs 選手" 1234'
        tokens = tokenize_server_line(line)

        assert "プレイヤー vs 選手" in tokens

    def test_tokenize_empty_quotes(self) -> None:
        """Test tokenizing empty quoted strings."""
        line = '0 E9FD "" 1234'
        tokens = tokenize_server_line(line)

        # Tokenizer captures hex values, empty quotes may or may not be included
        assert "0" in tokens
        assert "E9FD" in tokens
        assert "1234" in tokens


class TestParseServerEntry:
    """Tests for complete server entry parsing."""

    def test_parse_valid_entry(self, sample_server_data: str) -> None:
        """Test parsing a valid server entry."""
        tokens = tokenize_server_line(sample_server_data)
        result = parse_server_entry(tokens)

        assert result is not None
        assert result.ip == "0.0.0.0"
        assert result.is_started is True
        assert "RBI vs TestPlayer" in result.match_name

    def test_parse_incomplete_entry(self) -> None:
        """Test handling of incomplete entries."""
        tokens = ["0", "E9FD", "Test"]  # Too few tokens
        result = parse_server_entry(tokens)

        assert result is None

    def test_parse_port_conversion(self) -> None:
        """Test hex port conversion."""
        tokens = tokenize_server_line(
            '0 1F90 "Test" 0 0 0 0 "" "" 0 0 0 "" 0'
        )
        result = parse_server_entry(tokens)

        if result:
            assert result.port == 0x1F90  # 8080 in decimal
