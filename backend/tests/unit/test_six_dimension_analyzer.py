"""
Unit tests for six dimension analyzer service.
"""

import pytest
from datetime import datetime

from src.domain.services.six_dimension_analyzer import SixDimensionAnalyzer
from src.domain.value_objects.match_performance import MatchPerformance


class TestSixDimensionAnalyzer:
    """Test suite for six dimension analyzer."""

    def setup_method(self):
        """Setup test instance."""
        self.analyzer = SixDimensionAnalyzer()

    def create_sample_performance(
        self,
        position: str = "MIDDLE",
        kills: int = 8,
        deaths: int = 3,
        assists: int = 12,
        damage_dealt: int = 25000,
        gold_earned: int = 12000,
        cs_score: int = 180,
        vision_score: int = 25,
        wards_placed: int = 8,
        wards_cleared: int = 5,
        match_duration: int = 1800,  # 30 minutes
        **kwargs
    ) -> MatchPerformance:
        """Create sample match performance for testing."""
        defaults = {
            "player_profile_id": "test-player-123",
            "match_id": "test-match-456",
            "position": position,
            "match_duration": match_duration,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "damage_dealt": damage_dealt,
            "damage_taken": 15000,
            "gold_earned": gold_earned,
            "cs_score": cs_score,
            "vision_score": vision_score,
            "wards_placed": wards_placed,
            "wards_cleared": wards_cleared,
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
        defaults.update(kwargs)
        return MatchPerformance(**defaults)

    @pytest.mark.asyncio
    async def test_kda_dimension_calculation(self):
        """Test KDA dimension calculation."""
        # High KDA performance
        high_kda_perf = self.create_sample_performance(
            kills=15, deaths=2, assists=20
        )

        analysis = await self.analyzer.analyze_performance(high_kda_perf)

        assert "kda" in analysis
        # High KDA should result in high score (>70)
        assert analysis["kda"] > 70.0

        # Low KDA performance
        low_kda_perf = self.create_sample_performance(
            kills=2, deaths=8, assists=3
        )

        analysis = await self.analyzer.analyze_performance(low_kda_perf)

        # Low KDA should result in low score (<40)
        assert analysis["kda"] < 40.0

    @pytest.mark.asyncio
    async def test_damage_dimension_calculation(self):
        """Test damage dimension calculation."""
        # High damage performance
        high_damage_perf = self.create_sample_performance(
            damage_dealt=40000,
            match_duration=1800,
            position="MIDDLE"
        )

        analysis = await self.analyzer.analyze_performance(high_damage_perf)

        assert "damage" in analysis
        # High DPM should result in high score
        assert analysis["damage"] > 60.0

        # Low damage performance
        low_damage_perf = self.create_sample_performance(
            damage_dealt=8000,
            match_duration=1800,
            position="MIDDLE"
        )

        analysis = await self.analyzer.analyze_performance(low_damage_perf)

        # Low DPM should result in low score
        assert analysis["damage"] < 40.0

    @pytest.mark.asyncio
    async def test_economy_dimension_calculation(self):
        """Test economy dimension calculation."""
        # High economy performance
        high_economy_perf = self.create_sample_performance(
            gold_earned=16000,
            cs_score=250,
            match_duration=1800
        )

        analysis = await self.analyzer.analyze_performance(high_economy_perf)

        assert "economy" in analysis
        # High GPM and CS should result in high score
        assert analysis["economy"] > 65.0

        # Low economy performance
        low_economy_perf = self.create_sample_performance(
            gold_earned=8000,
            cs_score=120,
            match_duration=1800
        )

        analysis = await self.analyzer.analyze_performance(low_economy_perf)

        # Low GPM and CS should result in low score
        assert analysis["economy"] < 45.0

    @pytest.mark.asyncio
    async def test_vision_dimension_calculation(self):
        """Test vision dimension calculation."""
        # High vision performance
        high_vision_perf = self.create_sample_performance(
            vision_score=45,
            wards_placed=15,
            wards_cleared=12,
            match_duration=1800
        )

        analysis = await self.analyzer.analyze_performance(high_vision_perf)

        assert "vision" in analysis
        # High vision metrics should result in high score
        assert analysis["vision"] > 70.0

        # Low vision performance
        low_vision_perf = self.create_sample_performance(
            vision_score=10,
            wards_placed=3,
            wards_cleared=1,
            match_duration=1800
        )

        analysis = await self.analyzer.analyze_performance(low_vision_perf)

        # Low vision metrics should result in low score
        assert analysis["vision"] < 40.0

    @pytest.mark.asyncio
    async def test_objective_dimension_calculation(self):
        """Test objective dimension calculation."""
        # High objective performance
        high_objective_perf = self.create_sample_performance(
            dragon_kills=4,
            baron_kills=2,
            tower_kills=6,
            objective_damage=15000
        )

        analysis = await self.analyzer.analyze_performance(high_objective_perf)

        assert "objective" in analysis
        # High objective participation should result in high score
        assert analysis["objective"] > 65.0

        # Low objective performance
        low_objective_perf = self.create_sample_performance(
            dragon_kills=0,
            baron_kills=0,
            tower_kills=1,
            objective_damage=2000
        )

        analysis = await self.analyzer.analyze_performance(low_objective_perf)

        # Low objective participation should result in low score
        assert analysis["objective"] < 45.0

    @pytest.mark.asyncio
    async def test_teamfight_dimension_calculation(self):
        """Test teamfight dimension calculation."""
        # High teamfight performance
        high_teamfight_perf = self.create_sample_performance(
            teamfight_participation=0.95,
            teamfight_damage_share=0.35,
            teamfight_kills=8,
            teamfight_deaths=1
        )

        analysis = await self.analyzer.analyze_performance(high_teamfight_perf)

        assert "teamfight" in analysis
        # High teamfight metrics should result in high score
        assert analysis["teamfight"] > 70.0

        # Low teamfight performance
        low_teamfight_perf = self.create_sample_performance(
            teamfight_participation=0.4,
            teamfight_damage_share=0.1,
            teamfight_kills=1,
            teamfight_deaths=4
        )

        analysis = await self.analyzer.analyze_performance(low_teamfight_perf)

        # Low teamfight metrics should result in low score
        assert analysis["teamfight"] < 40.0

    @pytest.mark.asyncio
    async def test_position_specific_weights(self):
        """Test that different positions have different dimension weights."""
        # Same performance but different positions
        performance_data = {
            "kills": 8,
            "deaths": 3,
            "assists": 12,
            "damage_dealt": 20000,
            "gold_earned": 12000,
            "cs_score": 160,
            "vision_score": 20,
            "wards_placed": 6,
            "wards_cleared": 4
        }

        # Test ADC position (should emphasize damage and economy)
        adc_perf = self.create_sample_performance(position="BOTTOM", **performance_data)
        adc_analysis = await self.analyzer.analyze_performance(adc_perf)

        # Test Support position (should emphasize vision and teamfight)
        support_perf = self.create_sample_performance(position="UTILITY", **performance_data)
        support_analysis = await self.analyzer.analyze_performance(support_perf)

        # Test Jungle position (should emphasize objective control)
        jungle_perf = self.create_sample_performance(position="JUNGLE", **performance_data)
        jungle_analysis = await self.analyzer.analyze_performance(jungle_perf)

        # Different positions should produce different dimension scores
        # even with same raw stats due to different weights
        assert adc_analysis != support_analysis
        assert adc_analysis != jungle_analysis
        assert support_analysis != jungle_analysis

    @pytest.mark.asyncio
    async def test_support_position_weighting(self):
        """Test specific weighting for support position."""
        # Performance with high vision but low damage (typical support)
        support_perf = self.create_sample_performance(
            position="UTILITY",
            kills=2,
            deaths=2,
            assists=20,
            damage_dealt=8000,
            gold_earned=8000,
            cs_score=30,  # Low CS for support
            vision_score=50,
            wards_placed=20,
            wards_cleared=15
        )

        analysis = await self.analyzer.analyze_performance(support_perf)

        # Support should get high scores despite low damage/economy
        # due to high vision and assist numbers
        assert analysis["vision"] > 70.0
        assert analysis["kda"] > 60.0  # High assists boost KDA

    @pytest.mark.asyncio
    async def test_jungle_position_weighting(self):
        """Test specific weighting for jungle position."""
        # Performance with high objective control (typical jungle)
        jungle_perf = self.create_sample_performance(
            position="JUNGLE",
            kills=6,
            deaths=4,
            assists=15,
            damage_dealt=18000,
            dragon_kills=3,
            baron_kills=2,
            tower_kills=4,
            objective_damage=12000
        )

        analysis = await self.analyzer.analyze_performance(jungle_perf)

        # Jungle should get high objective score due to high objective participation
        assert analysis["objective"] > 70.0

    @pytest.mark.asyncio
    async def test_score_boundaries(self):
        """Test that dimension scores stay within 0-100 bounds."""
        # Extreme high performance
        extreme_high_perf = self.create_sample_performance(
            kills=25,
            deaths=0,
            assists=30,
            damage_dealt=80000,
            gold_earned=25000,
            cs_score=400,
            vision_score=100,
            wards_placed=30,
            wards_cleared=25,
            dragon_kills=6,
            baron_kills=3,
            tower_kills=10,
            objective_damage=25000,
            teamfight_participation=1.0,
            teamfight_damage_share=0.6,
            teamfight_kills=15,
            teamfight_deaths=0
        )

        analysis = await self.analyzer.analyze_performance(extreme_high_perf)

        # All scores should be within bounds
        for dimension, score in analysis.items():
            assert 0.0 <= score <= 100.0

        # Extreme low performance
        extreme_low_perf = self.create_sample_performance(
            kills=0,
            deaths=15,
            assists=1,
            damage_dealt=2000,
            gold_earned=5000,
            cs_score=50,
            vision_score=5,
            wards_placed=1,
            wards_cleared=0,
            dragon_kills=0,
            baron_kills=0,
            tower_kills=0,
            objective_damage=500,
            teamfight_participation=0.2,
            teamfight_damage_share=0.05,
            teamfight_kills=0,
            teamfight_deaths=8
        )

        analysis = await self.analyzer.analyze_performance(extreme_low_perf)

        # All scores should be within bounds
        for dimension, score in analysis.items():
            assert 0.0 <= score <= 100.0

    @pytest.mark.asyncio
    async def test_zero_deaths_handling(self):
        """Test handling of zero deaths for KDA calculation."""
        # Perfect game (0 deaths)
        perfect_perf = self.create_sample_performance(
            kills=10,
            deaths=0,
            assists=15
        )

        analysis = await self.analyzer.analyze_performance(perfect_perf)

        # Should handle zero deaths gracefully and give high KDA score
        assert "kda" in analysis
        assert analysis["kda"] > 85.0

    @pytest.mark.asyncio
    async def test_short_match_handling(self):
        """Test handling of very short matches."""
        # 10-minute match
        short_match_perf = self.create_sample_performance(
            match_duration=600,
            kills=5,
            deaths=2,
            assists=8,
            damage_dealt=12000,
            gold_earned=7000,
            cs_score=80
        )

        analysis = await self.analyzer.analyze_performance(short_match_perf)

        # Should calculate rates properly for short matches
        for dimension, score in analysis.items():
            assert 0.0 <= score <= 100.0

    @pytest.mark.asyncio
    async def test_dimension_consistency(self):
        """Test that dimension analysis is consistent across multiple calls."""
        perf = self.create_sample_performance()

        # Analyze same performance multiple times
        analysis1 = await self.analyzer.analyze_performance(perf)
        analysis2 = await self.analyzer.analyze_performance(perf)
        analysis3 = await self.analyzer.analyze_performance(perf)

        # Results should be identical
        assert analysis1 == analysis2 == analysis3

    @pytest.mark.asyncio
    async def test_all_dimensions_present(self):
        """Test that all six dimensions are always present in analysis."""
        perf = self.create_sample_performance()
        analysis = await self.analyzer.analyze_performance(perf)

        expected_dimensions = {"kda", "damage", "economy", "vision", "objective", "teamfight"}
        assert set(analysis.keys()) == expected_dimensions

    @pytest.mark.asyncio
    async def test_invalid_position_handling(self):
        """Test handling of invalid position."""
        # Invalid position should use default weights
        invalid_position_perf = self.create_sample_performance(position="INVALID")

        analysis = await self.analyzer.analyze_performance(invalid_position_perf)

        # Should still produce valid analysis with default weights
        assert len(analysis) == 6
        for score in analysis.values():
            assert 0.0 <= score <= 100.0