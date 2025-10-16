"""
Six dimension performance analyzer for FlyEsports rating system.

Analyzes player performance across six key dimensions:
1. KDA - Kill/Death/Assist performance
2. Damage - Damage output and efficiency
3. Economy - Gold earning and farming efficiency
4. Vision - Vision control and map awareness
5. Objective - Objective control and impact
6. Teamfight - Team fighting contribution and positioning
"""

import math
from typing import Dict, Any, Optional
from ..base import DomainService
from ..value_objects.match_performance import MatchPerformance


class SixDimensionAnalyzer(DomainService):
    """
    Six-dimensional performance analyzer.

    Converts raw match performance data into standardized dimension scores (0-100 scale).
    Each dimension uses position-specific benchmarks and calculations.
    """

    def __init__(self):
        """Initialize analyzer with position-specific benchmarks."""

        # Position-specific performance benchmarks (per 30-minute match)
        self.benchmarks = {
            'TOP': {
                'kda': 2.0, 'dpm': 600, 'gpm': 400,
                'vision_score': 20, 'cspm': 6.5,
                'objective_damage': 5000, 'teamfight_participation': 0.70,
                'damage_efficiency': 1.2  # damage_dealt / damage_taken
            },
            'JUNGLE': {
                'kda': 2.2, 'dpm': 500, 'gpm': 350,
                'vision_score': 35, 'cspm': 4.0,
                'objective_damage': 8000, 'teamfight_participation': 0.75,
                'damage_efficiency': 1.5
            },
            'MIDDLE': {
                'kda': 2.1, 'dpm': 700, 'gpm': 450,
                'vision_score': 25, 'cspm': 7.0,
                'objective_damage': 4000, 'teamfight_participation': 0.80,
                'damage_efficiency': 1.8
            },
            'BOTTOM': {
                'kda': 1.8, 'dpm': 800, 'gpm': 500,
                'vision_score': 15, 'cspm': 8.0,
                'objective_damage': 3000, 'teamfight_participation': 0.75,
                'damage_efficiency': 2.5
            },
            'UTILITY': {
                'kda': 1.5, 'dpm': 200, 'gpm': 250,
                'vision_score': 50, 'cspm': 1.0,
                'objective_damage': 2000, 'teamfight_participation': 0.85,
                'damage_efficiency': 0.8
            }
        }

    async def analyze_performance(
        self,
        performance: MatchPerformance,
        player_profile_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Analyze performance across all six dimensions.

        Args:
            performance: Match performance data
            player_profile_id: Optional player profile ID for historical comparison

        Returns:
            Dictionary with dimension scores (0-100 scale)
        """
        position = performance.position
        benchmarks = self.benchmarks.get(position, self.benchmarks['MIDDLE'])

        dimensions = {
            'kda': await self._calculate_kda_score(performance, benchmarks),
            'damage': await self._calculate_damage_score(performance, benchmarks, position),
            'economy': await self._calculate_economy_score(performance, benchmarks, position),
            'vision': await self._calculate_vision_score(performance, benchmarks, position),
            'objective': await self._calculate_objective_score(performance, benchmarks, position),
            'teamfight': await self._calculate_teamfight_score(performance, benchmarks, position)
        }

        return dimensions

    async def _calculate_kda_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float]
    ) -> float:
        """
        Calculate KDA dimension score.

        Considers:
        - KDA ratio with zero-death bonus
        - Kill participation relative to team
        - Consistency of performance
        """
        kda = performance.kda
        kills = performance.kills
        deaths = performance.deaths
        assists = performance.assists

        # Base KDA score using non-linear mapping
        if kda >= 4.0:
            base_score = 95 + min((kda - 4.0) * 1.25, 5.0)  # Cap at 100
        elif kda >= 3.0:
            base_score = 85 + (kda - 3.0) * 10
        elif kda >= 2.0:
            base_score = 65 + (kda - 2.0) * 20
        elif kda >= 1.0:
            base_score = 35 + (kda - 1.0) * 30
        else:
            base_score = kda * 35

        # Zero death bonus
        if deaths == 0 and (kills + assists) > 0:
            base_score = min(100, base_score * 1.15)

        # Perfect game bonus (kills + assists >= 10 and deaths == 0)
        if deaths == 0 and (kills + assists) >= 10:
            base_score = min(100, base_score * 1.25)

        # Penalty for excessive deaths
        if deaths >= 8:
            death_penalty = min(0.3, (deaths - 7) * 0.05)
            base_score *= (1 - death_penalty)

        return max(0, min(100, base_score))

    async def _calculate_damage_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate damage dimension score.

        Considers:
        - Damage per minute relative to position benchmark
        - Damage efficiency (dealt vs taken ratio)
        - Damage share relative to team expectations
        """
        dpm = performance.dpm or 0.0
        benchmark_dpm = benchmarks['dpm']

        # DPM score (0-70 points)
        dpm_ratio = dpm / benchmark_dpm if benchmark_dpm > 0 else 0
        if dpm_ratio >= 2.0:
            dpm_score = 70
        elif dpm_ratio >= 1.5:
            dpm_score = 55 + (dpm_ratio - 1.5) * 30  # 55-70 range
        elif dpm_ratio >= 1.0:
            dpm_score = 35 + (dpm_ratio - 1.0) * 40  # 35-55 range
        else:
            dpm_score = dpm_ratio * 35

        # Damage efficiency score (0-20 points)
        damage_efficiency = performance.calculate_damage_efficiency()
        expected_efficiency = benchmarks['damage_efficiency']

        if math.isinf(damage_efficiency):
            efficiency_score = 20  # Perfect efficiency
        else:
            efficiency_ratio = damage_efficiency / expected_efficiency
            if efficiency_ratio >= 1.5:
                efficiency_score = 20
            elif efficiency_ratio >= 1.0:
                efficiency_score = 15 + (efficiency_ratio - 1.0) * 10
            else:
                efficiency_score = efficiency_ratio * 15

        # Consistency bonus (0-10 points)
        consistency_score = 10  # Default full points, would need historical data for real calculation

        total_score = dpm_score + efficiency_score + consistency_score
        return max(0, min(100, total_score))

    async def _calculate_economy_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate economy dimension score.

        Considers:
        - Gold per minute relative to position
        - CS per minute for farming positions
        - Gold efficiency per CS
        """
        gpm = performance.gpm or 0.0
        cspm = performance.calculate_cspm()

        benchmark_gpm = benchmarks['gpm']
        benchmark_cspm = benchmarks['cspm']

        # GPM score (0-50 points)
        gpm_ratio = gpm / benchmark_gpm if benchmark_gpm > 0 else 0
        gpm_score = min(50, gpm_ratio * 40)

        # CSPM score (0-40 points) - reduced weight for non-farming positions
        if position in ['JUNGLE', 'UTILITY']:
            # Jungle and Support have lower CS expectations
            cspm_weight = 0.3
        else:
            cspm_weight = 1.0

        cspm_ratio = cspm / benchmark_cspm if benchmark_cspm > 0 else 0
        cspm_score = min(40 * cspm_weight, cspm_ratio * 35 * cspm_weight)

        # Gold efficiency score (0-10 points)
        gold_per_cs = performance.calculate_gold_per_cs()
        expected_gold_per_cs = 20  # Base expectation

        if gold_per_cs > 0:
            efficiency_ratio = gold_per_cs / expected_gold_per_cs
            if efficiency_ratio >= 1.2:
                efficiency_score = 10
            elif efficiency_ratio >= 1.0:
                efficiency_score = 8 + (efficiency_ratio - 1.0) * 10
            else:
                efficiency_score = efficiency_ratio * 8
        else:
            efficiency_score = 0

        total_score = gpm_score + cspm_score + efficiency_score
        return max(0, min(100, total_score))

    async def _calculate_vision_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate vision dimension score.

        Considers:
        - Vision score per minute relative to position
        - Wards placed and cleared efficiency
        - Vision control impact
        """
        vision_per_minute = performance.calculate_vision_per_minute()
        wards_per_minute = performance.calculate_wards_placed_per_minute()

        benchmark_vision_per_minute = benchmarks['vision_score'] / 30.0  # 30-min baseline

        # Vision score (0-60 points)
        vision_ratio = vision_per_minute / benchmark_vision_per_minute if benchmark_vision_per_minute > 0 else 0
        vision_score = min(60, vision_ratio * 50)

        # Ward placement efficiency (0-25 points)
        expected_wards_per_minute = {
            'UTILITY': 2.0, 'JUNGLE': 1.5, 'MIDDLE': 1.0,
            'TOP': 0.8, 'BOTTOM': 0.6
        }.get(position, 1.0)

        ward_ratio = wards_per_minute / expected_wards_per_minute if expected_wards_per_minute > 0 else 0
        ward_score = min(25, ward_ratio * 20)

        # Ward clearing efficiency (0-15 points)
        wards_cleared_per_minute = performance.wards_cleared / (performance.match_duration / 60.0)
        expected_clears_per_minute = {
            'UTILITY': 1.2, 'JUNGLE': 1.0, 'MIDDLE': 0.8,
            'TOP': 0.6, 'BOTTOM': 0.4
        }.get(position, 0.8)

        clear_ratio = wards_cleared_per_minute / expected_clears_per_minute if expected_clears_per_minute > 0 else 0
        clear_score = min(15, clear_ratio * 12)

        total_score = vision_score + ward_score + clear_score
        return max(0, min(100, total_score))

    async def _calculate_objective_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate objective dimension score.

        Considers:
        - Dragon and Baron kills
        - Tower takedowns
        - Objective damage contribution
        """
        # Epic monster score (0-40 points)
        dragon_score = min(25, performance.dragon_kills * 5)    # 5 points per dragon
        baron_score = min(15, performance.baron_kills * 15)     # 15 points per baron
        epic_score = dragon_score + baron_score

        # Tower score (0-30 points)
        tower_score = min(30, performance.tower_kills * 6)      # 6 points per tower

        # Objective damage score (0-30 points)
        benchmark_obj_damage = benchmarks['objective_damage']
        if performance.objective_damage > 0 and benchmark_obj_damage > 0:
            damage_ratio = performance.objective_damage / benchmark_obj_damage
            damage_score = min(30, damage_ratio * 25)
        else:
            damage_score = 0

        # Position-specific weight adjustments
        position_weights = {
            'JUNGLE': 1.2,     # Junglers should excel at objectives
            'TOP': 1.1,        # Top laners often help with objectives
            'UTILITY': 1.0,    # Supports enable objective control
            'MIDDLE': 0.9,     # Mid laners help but not primary role
            'BOTTOM': 0.8      # ADCs focus more on teamfights
        }

        weight = position_weights.get(position, 1.0)
        total_score = (epic_score + tower_score + damage_score) * weight

        return max(0, min(100, total_score))

    async def _calculate_teamfight_score(
        self,
        performance: MatchPerformance,
        benchmarks: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate teamfight dimension score.

        Considers:
        - Teamfight participation rate
        - Damage share in teamfights
        - KD ratio in teamfights
        - Positioning and survival
        """
        # Participation score (0-40 points)
        participation = performance.teamfight_participation
        benchmark_participation = benchmarks['teamfight_participation']

        participation_ratio = participation / benchmark_participation if benchmark_participation > 0 else 0
        participation_score = min(40, participation_ratio * 35)

        # Damage share score (0-30 points)
        damage_share = performance.teamfight_damage_share
        expected_share = {
            'BOTTOM': 0.30, 'MIDDLE': 0.25, 'TOP': 0.20,
            'JUNGLE': 0.15, 'UTILITY': 0.10
        }.get(position, 0.20)

        if damage_share > 0:
            share_ratio = damage_share / expected_share
            share_score = min(30, share_ratio * 25)
        else:
            share_score = 0

        # Teamfight KD score (0-30 points)
        tf_kd = performance.get_teamfight_kd_ratio()
        if tf_kd >= 3.0:
            kd_score = 30
        elif tf_kd >= 2.0:
            kd_score = 25 + (tf_kd - 2.0) * 5
        elif tf_kd >= 1.0:
            kd_score = 15 + (tf_kd - 1.0) * 10
        else:
            kd_score = tf_kd * 15

        # Perfect teamfight bonus
        if performance.teamfight_deaths == 0 and performance.teamfight_kills > 0:
            kd_score = min(30, kd_score * 1.2)

        total_score = participation_score + share_score + kd_score
        return max(0, min(100, total_score))

    def calculate_overall_performance_score(
        self,
        dimensions: Dict[str, float],
        position: str,
        match_result: float
    ) -> float:
        """
        Calculate overall performance score from six dimensions.

        Args:
            dimensions: Six dimension scores
            position: Player position
            match_result: Match result (1.0=win, 0.0=loss)

        Returns:
            Overall performance score (0-100)
        """
        # Position-specific dimension weights
        position_weights = {
            'TOP': {
                'kda': 0.20, 'damage': 0.20, 'economy': 0.15,
                'vision': 0.10, 'objective': 0.25, 'teamfight': 0.10
            },
            'JUNGLE': {
                'kda': 0.15, 'damage': 0.15, 'economy': 0.15,
                'vision': 0.25, 'objective': 0.30, 'teamfight': 0.00
            },
            'MIDDLE': {
                'kda': 0.20, 'damage': 0.25, 'economy': 0.15,
                'vision': 0.10, 'objective': 0.15, 'teamfight': 0.15
            },
            'BOTTOM': {
                'kda': 0.15, 'damage': 0.30, 'economy': 0.20,
                'vision': 0.05, 'objective': 0.15, 'teamfight': 0.15
            },
            'UTILITY': {
                'kda': 0.10, 'damage': 0.05, 'economy': 0.10,
                'vision': 0.30, 'objective': 0.20, 'teamfight': 0.25
            }
        }

        weights = position_weights.get(position, position_weights['MIDDLE'])

        # Calculate weighted average
        weighted_score = sum(
            dimensions.get(dim, 50.0) * weight
            for dim, weight in weights.items()
        )

        # Apply match result bonus/penalty
        if match_result == 1.0:  # Win
            weighted_score *= 1.05  # Small bonus for winning
        elif match_result == 0.0:  # Loss
            weighted_score *= 0.95  # Small penalty for losing

        return max(0, min(100, weighted_score))