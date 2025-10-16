"""
Match record entity for tracking individual match performance.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..base import Entity, BusinessRuleViolationError


@dataclass
class MatchRecord(Entity):
    """
    Match record entity representing a player's performance in a single match.

    This entity tracks detailed statistics and performance metrics
    for a player in a specific match.
    """

    record_id: str = ""
    match_id: str = ""
    player_profile_id: str = ""
    match_date: datetime = field(default_factory=datetime.utcnow)
    result: str = ""  # "win", "loss", "remake"

    # Performance statistics
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    cs: int = 0  # Creep score
    gold_earned: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    vision_score: int = 0

    # Champion and position
    champion_name: str = ""
    position_played: str = ""

    # Rating changes
    rating_before: float = 0.0
    rating_after: float = 0.0
    rating_change: float = 0.0

    # Six dimensions performance
    six_dimensions_before: Dict[str, float] = None
    six_dimensions_after: Dict[str, float] = None

    # Additional match metadata
    game_duration: int = 0  # seconds
    game_mode: str = "CLASSIC"

    def __post_init__(self) -> None:
        """Post initialization validation."""

        # Set default empty dicts if None
        if self.six_dimensions_before is None:
            object.__setattr__(self, "six_dimensions_before", {})
        if self.six_dimensions_after is None:
            object.__setattr__(self, "six_dimensions_after", {})

        # Validate result
        valid_results = {"win", "loss", "remake"}
        if self.result not in valid_results:
            raise BusinessRuleViolationError(
                f"Invalid match result: {self.result}. Valid results: {valid_results}"
            )

        # Validate statistics (non-negative)
        stats_fields = [
            "kills",
            "deaths",
            "assists",
            "cs",
            "gold_earned",
            "damage_dealt",
            "damage_taken",
            "vision_score",
            "game_duration",
        ]
        for field in stats_fields:
            value = getattr(self, field)
            if value < 0:
                raise BusinessRuleViolationError(
                    f"{field} cannot be negative, got {value}"
                )

        # Validate KDA reasonableness
        if self.kills > 50 or self.deaths > 50 or self.assists > 100:
            raise BusinessRuleViolationError(
                f"Unreasonable KDA values: {self.kills}/{self.deaths}/{self.assists}"
            )

        # Validate game duration
        if self.game_duration > 0 and self.game_duration < 300:  # 5 minutes minimum
            raise BusinessRuleViolationError(
                f"Game duration too short: {self.game_duration} seconds"
            )

        # Validate champion name
        if not self.champion_name.strip():
            raise BusinessRuleViolationError("Champion name is required")

    @classmethod
    def create(
        cls,
        match_id: str,
        player_profile_id: str,
        match_date: datetime,
        result: str,
        kills: int,
        deaths: int,
        assists: int,
        cs: int,
        gold_earned: int,
        damage_dealt: int,
        damage_taken: int,
        vision_score: int,
        champion_name: str,
        position_played: str,
        rating_before: float,
        rating_after: float,
        game_duration: int = 0,
        game_mode: str = "CLASSIC",
        six_dimensions_before: Optional[Dict[str, float]] = None,
        six_dimensions_after: Optional[Dict[str, float]] = None,
    ) -> "MatchRecord":
        """
        Create a new match record.

        Args:
            match_id: Unique match identifier
            player_profile_id: Player profile ID
            match_date: When the match was played
            result: Match result ("win", "loss", "remake")
            kills: Number of kills
            deaths: Number of deaths
            assists: Number of assists
            cs: Creep score (minion kills)
            gold_earned: Total gold earned
            damage_dealt: Total damage dealt to champions
            damage_taken: Total damage taken
            vision_score: Vision control score
            champion_name: Champion played
            position_played: Position played in match
            rating_before: Rating before the match
            rating_after: Rating after the match
            game_duration: Game duration in seconds
            game_mode: Game mode
            six_dimensions_before: Six dimensions scores before match
            six_dimensions_after: Six dimensions scores after match

        Returns:
            New MatchRecord entity
        """
        record_id = f"rec_{uuid.uuid4().hex[:12]}"
        rating_change = rating_after - rating_before

        return cls(
            record_id=record_id,
            match_id=match_id,
            player_profile_id=player_profile_id,
            match_date=match_date,
            result=result,
            kills=kills,
            deaths=deaths,
            assists=assists,
            cs=cs,
            gold_earned=gold_earned,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            vision_score=vision_score,
            champion_name=champion_name,
            position_played=position_played,
            rating_before=rating_before,
            rating_after=rating_after,
            rating_change=rating_change,
            game_duration=game_duration,
            game_mode=game_mode,
            six_dimensions_before=six_dimensions_before or {},
            six_dimensions_after=six_dimensions_after or {},
        )

    @property
    def kda_ratio(self) -> float:
        """Calculate KDA ratio."""
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths

    @property
    def kill_participation(self) -> float:
        """Calculate kill participation (for team-wide statistics)."""
        total_team_kills_assists = self.kills + self.assists
        return (
            total_team_kills_assists  # This would need team data for proper calculation
        )

    @property
    def cs_per_minute(self) -> float:
        """Calculate CS per minute."""
        if self.game_duration <= 0:
            return 0.0
        return (self.cs * 60.0) / self.game_duration

    @property
    def gold_per_minute(self) -> float:
        """Calculate gold per minute."""
        if self.game_duration <= 0:
            return 0.0
        return (self.gold_earned * 60.0) / self.game_duration

    @property
    def damage_per_minute(self) -> float:
        """Calculate damage per minute."""
        if self.game_duration <= 0:
            return 0.0
        return (self.damage_dealt * 60.0) / self.game_duration

    @property
    def was_victory(self) -> bool:
        """Check if this was a victory."""
        return self.result == "win"

    @property
    def was_defeat(self) -> bool:
        """Check if this was a defeat."""
        return self.result == "loss"

    @property
    def was_remake(self) -> bool:
        """Check if this was a remake."""
        return self.result == "remake"

    @property
    def performance_summary(self) -> Dict[str, Any]:
        """Get a summary of match performance."""
        return {
            "kda": f"{self.kills}/{self.deaths}/{self.assists}",
            "kda_ratio": round(self.kda_ratio, 2),
            "cs": self.cs,
            "cs_per_min": round(self.cs_per_minute, 1),
            "gold_earned": self.gold_earned,
            "gold_per_min": round(self.gold_per_minute, 1),
            "damage_dealt": self.damage_dealt,
            "damage_per_min": round(self.damage_per_minute, 1),
            "vision_score": self.vision_score,
            "rating_change": round(self.rating_change, 2),
            "result": self.result,
            "champion": self.champion_name,
            "position": self.position_played,
        }

    def get_dimension_change(self, dimension: str) -> float:
        """
        Get the change in a specific six-dimension score.

        Args:
            dimension: Dimension name

        Returns:
            Change in dimension score
        """
        before = self.six_dimensions_before.get(dimension, 0.0)
        after = self.six_dimensions_after.get(dimension, 0.0)
        return after - before

    def __str__(self) -> str:
        """String representation of the match record."""
        return (
            f"MatchRecord({self.champion_name}, "
            f"{self.kills}/{self.deaths}/{self.assists}, "
            f"{self.result}, rating_change={self.rating_change:+.1f})"
        )

    def __hash__(self) -> int:
        """Hash based on record ID."""
        return hash(self.record_id)
