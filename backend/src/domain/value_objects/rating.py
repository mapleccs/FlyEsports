"""
Rating value object for player performance evaluation.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from ..base import ValueObject, BusinessRuleViolationError


@dataclass(frozen=True)
class Rating(ValueObject):
    """
    Rating value object representing a player's skill level.
    
    This includes the current score, locked score (if signed to a team),
    confidence level, match count, and six-dimensional analysis.
    """
    
    current_score: float
    locked_score: Optional[float]
    confidence_level: float
    total_matches: int
    six_dimensions: Dict[str, float]
    
    # Rating constraints
    MIN_RATING = 0.0
    MAX_RATING = 100.0
    MIN_CONFIDENCE = 0.5
    MAX_CONFIDENCE = 0.95
    
    # Six dimensions keys
    DIMENSION_KEYS = {
        'kda', 'damage', 'economy', 'vision', 'objective', 'teamfight'
    }
    
    def __post_init__(self):
        """Validate rating values after initialization."""
        # Validate current score
        if not (self.MIN_RATING <= self.current_score <= self.MAX_RATING):
            raise BusinessRuleViolationError(
                f"Current score must be between {self.MIN_RATING} and {self.MAX_RATING}, "
                f"got {self.current_score}"
            )
        
        # Validate locked score if present
        if self.locked_score is not None:
            if not (self.MIN_RATING <= self.locked_score <= self.MAX_RATING):
                raise BusinessRuleViolationError(
                    f"Locked score must be between {self.MIN_RATING} and {self.MAX_RATING}, "
                    f"got {self.locked_score}"
                )
        
        # Validate confidence level
        if not (self.MIN_CONFIDENCE <= self.confidence_level <= self.MAX_CONFIDENCE):
            raise BusinessRuleViolationError(
                f"Confidence level must be between {self.MIN_CONFIDENCE} and {self.MAX_CONFIDENCE}, "
                f"got {self.confidence_level}"
            )
        
        # Validate total matches
        if self.total_matches < 0:
            raise BusinessRuleViolationError(
                f"Total matches cannot be negative, got {self.total_matches}"
            )
        
        # Validate six dimensions
        if not isinstance(self.six_dimensions, dict):
            raise BusinessRuleViolationError("Six dimensions must be a dictionary")
        
        # Check required dimension keys
        missing_keys = self.DIMENSION_KEYS - set(self.six_dimensions.keys())
        if missing_keys:
            raise BusinessRuleViolationError(
                f"Missing required dimension keys: {missing_keys}"
            )
        
        # Validate dimension values
        for key, value in self.six_dimensions.items():
            if not isinstance(value, (int, float)):
                raise BusinessRuleViolationError(
                    f"Dimension {key} must be numeric, got {type(value)}"
                )
            if not (self.MIN_RATING <= value <= self.MAX_RATING):
                raise BusinessRuleViolationError(
                    f"Dimension {key} must be between {self.MIN_RATING} and {self.MAX_RATING}, "
                    f"got {value}"
                )
    
    @classmethod
    def create_initial(
        cls,
        initial_score: float,
        initial_dimensions: Optional[Dict[str, float]] = None
    ) -> 'Rating':
        """
        Create initial rating for a new player.
        
        Args:
            initial_score: Initial rating score
            initial_dimensions: Initial six dimensions (optional)
            
        Returns:
            Rating value object
        """
        if initial_dimensions is None:
            initial_dimensions = {
                key: initial_score for key in cls.DIMENSION_KEYS
            }
        
        return cls(
            current_score=initial_score,
            locked_score=None,
            confidence_level=cls.MIN_CONFIDENCE,
            total_matches=0,
            six_dimensions=initial_dimensions
        )
    
    def with_new_score(self, new_score: float) -> 'Rating':
        """
        Create a new Rating with updated score and incremented match count.
        
        Args:
            new_score: New rating score
            
        Returns:
            New Rating instance with updated score
        """
        # Increase confidence level slightly with each match (up to maximum)
        new_confidence = min(
            self.MAX_CONFIDENCE,
            self.confidence_level + 0.01
        )
        
        return Rating(
            current_score=new_score,
            locked_score=self.locked_score,
            confidence_level=new_confidence,
            total_matches=self.total_matches + 1,
            six_dimensions=self.six_dimensions
        )
    
    def with_locked_score(self, locked_value: float) -> 'Rating':
        """
        Create a new Rating with locked score (when signing to a team).
        
        Args:
            locked_value: Score to lock at
            
        Returns:
            New Rating instance with locked score
        """
        return Rating(
            current_score=self.current_score,
            locked_score=locked_value,
            confidence_level=self.confidence_level,
            total_matches=self.total_matches,
            six_dimensions=self.six_dimensions
        )
    
    def with_unlocked_score(self) -> 'Rating':
        """
        Create a new Rating with unlocked score (when leaving a team).
        
        Returns:
            New Rating instance without locked score
        """
        return Rating(
            current_score=self.current_score,
            locked_score=None,
            confidence_level=self.confidence_level,
            total_matches=self.total_matches,
            six_dimensions=self.six_dimensions
        )
    
    def with_updated_dimensions(self, dimensions: Dict[str, float]) -> 'Rating':
        """
        Create a new Rating with updated six dimensions.
        
        Args:
            dimensions: New dimension values
            
        Returns:
            New Rating instance with updated dimensions
        """
        return Rating(
            current_score=self.current_score,
            locked_score=self.locked_score,
            confidence_level=self.confidence_level,
            total_matches=self.total_matches,
            six_dimensions=dimensions
        )
    
    def with_updated_confidence(self, new_confidence: float) -> 'Rating':
        """
        Create a new Rating with updated confidence level.
        
        Args:
            new_confidence: New confidence level
            
        Returns:
            New Rating instance with updated confidence
        """
        return Rating(
            current_score=self.current_score,
            locked_score=self.locked_score,
            confidence_level=new_confidence,
            total_matches=self.total_matches,
            six_dimensions=self.six_dimensions
        )
    
    @property
    def effective_score(self) -> float:
        """
        Get the effective rating score.
        
        Returns locked score if player is locked, otherwise current score.
        """
        return self.locked_score if self.locked_score is not None else self.current_score
    
    @property
    def is_locked(self) -> bool:
        """Check if the rating is locked."""
        return self.locked_score is not None
    
    @property
    def is_experienced(self) -> bool:
        """Check if the player has enough matches to be considered experienced."""
        return self.total_matches >= 10
    
    @property
    def is_confident(self) -> bool:
        """Check if the rating has high confidence."""
        return self.confidence_level >= 0.8
    
    @property
    def average_dimension_score(self) -> float:
        """Get the average score across all six dimensions."""
        if not self.six_dimensions:
            return self.current_score
        return sum(self.six_dimensions.values()) / len(self.six_dimensions)
    
    def get_dimension_score(self, dimension: str) -> float:
        """
        Get the score for a specific dimension.
        
        Args:
            dimension: Dimension name
            
        Returns:
            Dimension score
            
        Raises:
            KeyError: If dimension doesn't exist
        """
        if dimension not in self.DIMENSION_KEYS:
            raise KeyError(f"Unknown dimension: {dimension}")
        return self.six_dimensions[dimension]
    
    def __str__(self) -> str:
        """String representation of the rating."""
        lock_status = " (LOCKED)" if self.is_locked else ""
        return f"Rating({self.effective_score:.1f}, conf={self.confidence_level:.2f}, matches={self.total_matches}){lock_status}"
    
    def __hash__(self) -> int:
        """Hash based on all rating components."""
        return hash((
            self.current_score,
            self.locked_score,
            self.confidence_level,
            self.total_matches,
            tuple(sorted(self.six_dimensions.items()))
        ))