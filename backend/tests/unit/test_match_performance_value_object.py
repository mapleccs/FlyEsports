"""
Unit tests for match performance value object.
"""

import pytest
from datetime import datetime

from src.domain.value_objects.match_performance import MatchPerformance


class TestMatchPerformance:
    """Test suite for match performance value object."""

    def create_sample_performance(self, **overrides):
        """Create sample match performance with optional overrides."""
        defaults = {
            "player_profile_id": "player-123",
            "match_id": "match-456",
            "position": "MIDDLE",
            "match_duration": 1800,
            "kills": 8,
            "deaths": 3,
            "assists": 12,
            "damage_dealt": 25000,
            "damage_taken": 15000,
            "gold_earned": 12000,
            "cs_score": 180,
            "vision_score": 25,
            "wards_placed": 8,
            "wards_cleared": 5,
            "dragon_kills": 2,
            "baron_kills": 1,
            "tower_kills": 3,
            "objective_damage": 8000,
            "teamfight_participation": 0.8,
            "teamfight_damage_share": 0.25,
            "teamfight_kills": 4,
            "teamfight_deaths": 1,
            "match_result": "win",
            "played_at": datetime.utcnow()
        }
        defaults.update(overrides)
        return MatchPerformance(**defaults)

    def test_create_valid_performance(self):
        """Test creation of valid match performance."""
        perf = self.create_sample_performance()

        assert perf.player_profile_id == "player-123"
        assert perf.match_id == "match-456"
        assert perf.position == "MIDDLE"
        assert perf.kills == 8
        assert perf.deaths == 3
        assert perf.assists == 12

    def test_kda_calculation_normal(self):
        """Test KDA calculation for normal case."""
        perf = self.create_sample_performance(kills=10, deaths=5, assists=15)

        # KDA = (kills + assists) / deaths = (10 + 15) / 5 = 5.0
        assert perf.kda == 5.0

    def test_kda_calculation_zero_deaths(self):
        """Test KDA calculation with zero deaths."""
        perf = self.create_sample_performance(kills=8, deaths=0, assists=12)

        # KDA with zero deaths should use special calculation
        # Usually (kills + assists) + 1 or similar
        assert perf.kda >= 20.0  # Perfect KDA should be high

    def test_kda_calculation_zero_kills_assists(self):
        """Test KDA calculation with zero kills and assists."""
        perf = self.create_sample_performance(kills=0, deaths=5, assists=0)

        # KDA = (0 + 0) / 5 = 0.0
        assert perf.kda == 0.0

    def test_dpm_calculation(self):
        """Test damage per minute calculation."""
        perf = self.create_sample_performance(
            damage_dealt=30000,
            match_duration=1500  # 25 minutes
        )

        # DPM = 30000 / (1500/60) = 30000 / 25 = 1200.0
        assert perf.dpm == 1200.0

    def test_gpm_calculation(self):
        """Test gold per minute calculation."""
        perf = self.create_sample_performance(
            gold_earned=15000,
            match_duration=1800  # 30 minutes
        )

        # GPM = 15000 / (1800/60) = 15000 / 30 = 500.0
        assert perf.gpm == 500.0

    def test_cspm_calculation(self):
        """Test CS per minute calculation."""
        perf = self.create_sample_performance(
            cs_score=240,
            match_duration=1800  # 30 minutes
        )

        # CSPM = 240 / (1800/60) = 240 / 30 = 8.0
        assert perf.cspm == 8.0

    def test_kill_participation(self):
        """Test kill participation calculation."""
        perf = self.create_sample_performance(kills=5, assists=10)

        # With 5 kills and 10 assists = 15 total kill participation
        assert perf.kill_participation == 15

    def test_zero_duration_handling(self):
        """Test handling of zero match duration."""
        with pytest.raises(ValueError, match="Match duration must be positive"):
            self.create_sample_performance(match_duration=0)

    def test_negative_duration_handling(self):
        """Test handling of negative match duration."""
        with pytest.raises(ValueError, match="Match duration must be positive"):
            self.create_sample_performance(match_duration=-100)

    def test_negative_kills_validation(self):
        """Test validation of negative kills."""
        with pytest.raises(ValueError, match="Kills cannot be negative"):
            self.create_sample_performance(kills=-1)

    def test_negative_deaths_validation(self):
        """Test validation of negative deaths."""
        with pytest.raises(ValueError, match="Deaths cannot be negative"):
            self.create_sample_performance(deaths=-1)

    def test_negative_assists_validation(self):
        """Test validation of negative assists."""
        with pytest.raises(ValueError, match="Assists cannot be negative"):
            self.create_sample_performance(assists=-1)

    def test_negative_damage_validation(self):
        """Test validation of negative damage."""
        with pytest.raises(ValueError, match="Damage dealt cannot be negative"):
            self.create_sample_performance(damage_dealt=-1)

    def test_negative_gold_validation(self):
        """Test validation of negative gold."""
        with pytest.raises(ValueError, match="Gold earned cannot be negative"):
            self.create_sample_performance(gold_earned=-1)

    def test_negative_cs_validation(self):
        """Test validation of negative CS."""
        with pytest.raises(ValueError, match="CS score cannot be negative"):
            self.create_sample_performance(cs_score=-1)

    def test_invalid_position_validation(self):
        """Test validation of invalid position."""
        valid_positions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

        with pytest.raises(ValueError, match="Invalid position"):
            self.create_sample_performance(position="INVALID")

    def test_valid_positions(self):
        """Test all valid positions are accepted."""
        valid_positions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

        for position in valid_positions:
            perf = self.create_sample_performance(position=position)
            assert perf.position == position

    def test_invalid_match_result_validation(self):
        """Test validation of invalid match result."""
        valid_results = ["win", "loss", "draw"]

        with pytest.raises(ValueError, match="Invalid match result"):
            self.create_sample_performance(match_result="invalid")

    def test_valid_match_results(self):
        """Test all valid match results are accepted."""
        valid_results = ["win", "loss", "draw"]

        for result in valid_results:
            perf = self.create_sample_performance(match_result=result)
            assert perf.match_result == result

    def test_teamfight_participation_bounds(self):
        """Test teamfight participation bounds validation."""
        # Valid range 0.0 - 1.0
        perf = self.create_sample_performance(teamfight_participation=0.5)
        assert perf.teamfight_participation == 0.5

        perf = self.create_sample_performance(teamfight_participation=0.0)
        assert perf.teamfight_participation == 0.0

        perf = self.create_sample_performance(teamfight_participation=1.0)
        assert perf.teamfight_participation == 1.0

        # Invalid values
        with pytest.raises(ValueError, match="Teamfight participation must be between 0.0 and 1.0"):
            self.create_sample_performance(teamfight_participation=-0.1)

        with pytest.raises(ValueError, match="Teamfight participation must be between 0.0 and 1.0"):
            self.create_sample_performance(teamfight_participation=1.1)

    def test_teamfight_damage_share_bounds(self):
        """Test teamfight damage share bounds validation."""
        # Valid range 0.0 - 1.0
        perf = self.create_sample_performance(teamfight_damage_share=0.3)
        assert perf.teamfight_damage_share == 0.3

        # Invalid values
        with pytest.raises(ValueError, match="Teamfight damage share must be between 0.0 and 1.0"):
            self.create_sample_performance(teamfight_damage_share=-0.1)

        with pytest.raises(ValueError, match="Teamfight damage share must be between 0.0 and 1.0"):
            self.create_sample_performance(teamfight_damage_share=1.5)

    def test_immutability(self):
        """Test that match performance is immutable."""
        perf = self.create_sample_performance()

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            perf.kills = 10

        with pytest.raises(AttributeError):
            perf.match_id = "new-match"

    def test_equality(self):
        """Test equality comparison."""
        perf1 = self.create_sample_performance()
        perf2 = self.create_sample_performance()

        assert perf1 == perf2

        # Different values should not be equal
        perf3 = self.create_sample_performance(kills=10)
        assert perf1 != perf3

    def test_hash_consistency(self):
        """Test hash consistency for same values."""
        perf1 = self.create_sample_performance()
        perf2 = self.create_sample_performance()

        # Same values should have same hash
        assert hash(perf1) == hash(perf2)

        # Different values should have different hash (usually)
        perf3 = self.create_sample_performance(kills=10)
        assert hash(perf1) != hash(perf3)

    def test_string_representation(self):
        """Test string representation."""
        perf = self.create_sample_performance()

        str_repr = str(perf)
        assert "MatchPerformance" in str_repr
        assert perf.player_profile_id in str_repr
        assert perf.match_id in str_repr

    def test_extreme_values_handling(self):
        """Test handling of extreme but valid values."""
        # Very long match
        long_match = self.create_sample_performance(
            match_duration=7200,  # 2 hours
            kills=30,
            assists=40,
            damage_dealt=100000,
            gold_earned=30000,
            cs_score=500
        )

        assert long_match.dpm == 100000 / (7200 / 60)  # 833.33
        assert long_match.gpm == 30000 / (7200 / 60)   # 250.0

        # Very short match
        short_match = self.create_sample_performance(
            match_duration=300,  # 5 minutes
            kills=2,
            assists=3,
            damage_dealt=5000,
            gold_earned=3000,
            cs_score=25
        )

        assert short_match.dpm == 5000 / (300 / 60)  # 1000.0
        assert short_match.gpm == 3000 / (300 / 60)  # 600.0

    def test_perfect_game_stats(self):
        """Test perfect game statistics."""
        perfect_game = self.create_sample_performance(
            kills=15,
            deaths=0,
            assists=20,
            teamfight_participation=1.0,
            teamfight_damage_share=0.4
        )

        assert perfect_game.deaths == 0
        assert perfect_game.kda >= 35.0  # Should be very high for perfect game
        assert perfect_game.teamfight_participation == 1.0

    def test_support_typical_stats(self):
        """Test typical support statistics."""
        support_game = self.create_sample_performance(
            position="UTILITY",
            kills=2,
            deaths=3,
            assists=25,
            damage_dealt=8000,
            gold_earned=8000,
            cs_score=35,  # Low CS for support
            vision_score=60,
            wards_placed=25,
            wards_cleared=15
        )

        assert support_game.position == "UTILITY"
        assert support_game.assists > support_game.kills  # Typical for support
        assert support_game.vision_score > 50  # High vision for support