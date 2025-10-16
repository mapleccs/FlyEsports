"""
Update player rating use case for FlyEsports.

Handles rating updates after matches including ELO calculation,
dimension analysis, and confidence level updates.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import structlog

from ..base import UseCase, UseCaseError
from ...domain.repositories.player_profile import PlayerProfileRepository
from ...domain.services.rating_update_service import RatingUpdateService
from ...domain.value_objects.match_performance import MatchPerformance
from ...domain.value_objects.rating import Rating
from ...domain.aggregates.player_profile import PlayerProfile


logger = structlog.get_logger(__name__)


class UpdatePlayerRatingRequest:
    """Request object for player rating update."""

    def __init__(
        self,
        match_id: str,
        player_performances: List[MatchPerformance],
        team1_player_ids: List[str],
        team2_player_ids: List[str],
        save_history: bool = True,
        dry_run: bool = False
    ):
        self.match_id = match_id
        self.player_performances = player_performances
        self.team1_player_ids = team1_player_ids
        self.team2_player_ids = team2_player_ids
        self.save_history = save_history
        self.dry_run = dry_run


class UpdatePlayerRatingResponse:
    """Response object for player rating update."""

    def __init__(
        self,
        match_id: str,
        updated_ratings: Dict[str, Rating],
        calculation_details: Dict[str, Dict[str, Any]],
        success_count: int,
        error_count: int,
        errors: List[str] = None
    ):
        self.match_id = match_id
        self.updated_ratings = updated_ratings
        self.calculation_details = calculation_details
        self.success_count = success_count
        self.error_count = error_count
        self.errors = errors or []

    @property
    def is_successful(self) -> bool:
        """Check if all rating updates were successful."""
        return self.error_count == 0


class UpdatePlayerRatingUseCase(UseCase):
    """
    Use case for updating player ratings after matches.

    Handles the complete rating update process including:
    - Loading current ratings
    - Calculating new ratings using various algorithms
    - Updating player profiles
    - Saving rating history
    """

    def __init__(
        self,
        player_repository: PlayerProfileRepository,
        rating_service: RatingUpdateService
    ):
        self.player_repository = player_repository
        self.rating_service = rating_service

    async def execute(self, request: UpdatePlayerRatingRequest) -> UpdatePlayerRatingResponse:
        """
        Execute player rating updates for a match.

        Args:
            request: Rating update request

        Returns:
            UpdatePlayerRatingResponse with results

        Raises:
            UseCaseError: If rating update fails critically
        """
        try:
            logger.info(
                "Starting player rating updates",
                match_id=request.match_id,
                player_count=len(request.player_performances),
                dry_run=request.dry_run
            )

            # Validate request
            await self._validate_request(request)

            # Load current player ratings
            current_ratings = await self._load_current_ratings(request)

            # Group performances by team
            team1_performances, team2_performances = self._group_performances_by_team(
                request.player_performances,
                request.team1_player_ids,
                request.team2_player_ids
            )

            # Update ratings for all players
            rating_updates = await self.rating_service.batch_update_ratings(
                match_performances=request.player_performances,
                current_ratings=current_ratings,
                team1_performances=team1_performances,
                team2_performances=team2_performances
            )

            # Process the results
            updated_ratings = {}
            calculation_details = {}
            success_count = 0
            error_count = 0
            errors = []

            for player_id, (new_rating, details) in rating_updates.items():
                if details.get('success', False):
                    updated_ratings[player_id] = new_rating
                    calculation_details[player_id] = details
                    success_count += 1

                    # Save to repository if not dry run
                    if not request.dry_run:
                        await self._save_updated_rating(player_id, new_rating, request.save_history)

                else:
                    error_count += 1
                    error_msg = f"Player {player_id}: {details.get('error', 'Unknown error')}"
                    errors.append(error_msg)

            logger.info(
                "Player rating updates completed",
                match_id=request.match_id,
                success_count=success_count,
                error_count=error_count,
                dry_run=request.dry_run
            )

            return UpdatePlayerRatingResponse(
                match_id=request.match_id,
                updated_ratings=updated_ratings,
                calculation_details=calculation_details,
                success_count=success_count,
                error_count=error_count,
                errors=errors
            )

        except Exception as e:
            logger.error(
                "Player rating update failed",
                match_id=request.match_id,
                error=str(e)
            )
            raise UseCaseError(f"Failed to update player ratings: {str(e)}") from e

    async def _validate_request(self, request: UpdatePlayerRatingRequest):
        """Validate the rating update request."""

        # Check that we have performances for all players
        performance_player_ids = {perf.player_profile_id for perf in request.player_performances}
        team_player_ids = set(request.team1_player_ids + request.team2_player_ids)

        if performance_player_ids != team_player_ids:
            missing_performances = team_player_ids - performance_player_ids
            extra_performances = performance_player_ids - team_player_ids

            if missing_performances:
                raise UseCaseError(f"Missing performances for players: {missing_performances}")
            if extra_performances:
                raise UseCaseError(f"Extra performances for unknown players: {extra_performances}")

        # Validate team sizes
        if len(request.team1_player_ids) != len(request.team2_player_ids):
            raise UseCaseError("Teams must have equal number of players")

        # Check for duplicate player IDs
        all_player_ids = request.team1_player_ids + request.team2_player_ids
        if len(all_player_ids) != len(set(all_player_ids)):
            raise UseCaseError("Duplicate player IDs found in teams")

    async def _load_current_ratings(
        self,
        request: UpdatePlayerRatingRequest
    ) -> Dict[str, Rating]:
        """Load current ratings for all players."""

        current_ratings = {}
        all_player_ids = request.team1_player_ids + request.team2_player_ids

        for player_id in all_player_ids:
            player = await self.player_repository.find_by_id(player_id)

            if not player:
                # Create new player with initial rating
                logger.warning(
                    "Player not found, creating initial rating",
                    player_id=player_id
                )
                current_ratings[player_id] = Rating.create_initial(1200.0)
            else:
                current_ratings[player_id] = player.rating or Rating.create_initial(1200.0)

        return current_ratings

    def _group_performances_by_team(
        self,
        performances: List[MatchPerformance],
        team1_player_ids: List[str],
        team2_player_ids: List[str]
    ) -> Tuple[List[MatchPerformance], List[MatchPerformance]]:
        """Group performances by team."""

        team1_performances = []
        team2_performances = []

        for performance in performances:
            if performance.player_profile_id in team1_player_ids:
                team1_performances.append(performance)
            elif performance.player_profile_id in team2_player_ids:
                team2_performances.append(performance)

        return team1_performances, team2_performances

    async def _save_updated_rating(
        self,
        player_id: str,
        new_rating: Rating,
        save_history: bool
    ):
        """Save the updated rating to the player profile."""

        # Get the player profile
        player = await self.player_repository.find_by_id(player_id)

        if player:
            # Update the player's rating
            player.update_rating(new_rating)
            await self.player_repository.save(player)

            if save_history:
                # Save rating history (this would need a rating history repository)
                # For now, just log the update
                logger.info(
                    "Rating updated",
                    player_id=player_id,
                    old_rating=player.rating.current_score if player.rating else 0,
                    new_rating=new_rating.current_score,
                    confidence=new_rating.confidence_level
                )


class BatchUpdateRatingsUseCase(UseCase):
    """Use case for batch updating ratings from multiple matches."""

    def __init__(
        self,
        player_repository: PlayerProfileRepository,
        rating_service: RatingUpdateService
    ):
        self.player_repository = player_repository
        self.rating_service = rating_service

    async def execute(
        self,
        match_data: List[Dict[str, Any]],
        concurrent_limit: int = 5
    ) -> Dict[str, Any]:
        """
        Execute batch rating updates for multiple matches.

        Args:
            match_data: List of match data dictionaries
            concurrent_limit: Maximum concurrent match processing

        Returns:
            Summary of batch update results
        """
        try:
            logger.info(
                "Starting batch rating updates",
                match_count=len(match_data),
                concurrent_limit=concurrent_limit
            )

            results = {
                'total_matches': len(match_data),
                'successful_matches': 0,
                'failed_matches': 0,
                'total_players_updated': 0,
                'errors': []
            }

            # Process matches in batches to avoid overwhelming the system
            batch_size = concurrent_limit
            for i in range(0, len(match_data), batch_size):
                batch = match_data[i:i + batch_size]
                batch_results = await self._process_match_batch(batch)

                # Aggregate results
                for result in batch_results:
                    if result['success']:
                        results['successful_matches'] += 1
                        results['total_players_updated'] += result['player_count']
                    else:
                        results['failed_matches'] += 1
                        results['errors'].extend(result['errors'])

            logger.info(
                "Batch rating updates completed",
                successful_matches=results['successful_matches'],
                failed_matches=results['failed_matches'],
                total_players_updated=results['total_players_updated']
            )

            return results

        except Exception as e:
            logger.error("Batch rating update failed", error=str(e))
            raise UseCaseError(f"Failed to execute batch rating updates: {str(e)}") from e

    async def _process_match_batch(
        self,
        match_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process a batch of matches concurrently."""

        import asyncio

        tasks = []
        for match_data in match_batch:
            task = self._process_single_match(match_data)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'match_id': match_batch[i].get('match_id', 'unknown'),
                    'success': False,
                    'player_count': 0,
                    'errors': [str(result)]
                })
            else:
                processed_results.append(result)

        return processed_results

    async def _process_single_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process rating updates for a single match."""

        try:
            # Convert match data to UpdatePlayerRatingRequest
            # This would need proper data transformation based on your match data structure
            request = self._convert_match_data_to_request(match_data)

            # Create a temporary update use case instance
            update_use_case = UpdatePlayerRatingUseCase(
                self.player_repository,
                self.rating_service
            )

            # Execute the update
            response = await update_use_case.execute(request)

            return {
                'match_id': request.match_id,
                'success': response.is_successful,
                'player_count': response.success_count,
                'errors': response.errors
            }

        except Exception as e:
            return {
                'match_id': match_data.get('match_id', 'unknown'),
                'success': False,
                'player_count': 0,
                'errors': [str(e)]
            }

    def _convert_match_data_to_request(
        self,
        match_data: Dict[str, Any]
    ) -> UpdatePlayerRatingRequest:
        """Convert raw match data to UpdatePlayerRatingRequest."""

        # This is a placeholder - you would implement the actual conversion
        # based on your match data structure

        match_id = match_data['match_id']

        # Convert performance data
        player_performances = []
        for perf_data in match_data.get('performances', []):
            performance = MatchPerformance(
                player_profile_id=perf_data['player_id'],
                match_id=match_id,
                position=perf_data['position'],
                match_duration=perf_data['duration'],
                kills=perf_data['kills'],
                deaths=perf_data['deaths'],
                assists=perf_data['assists'],
                damage_dealt=perf_data['damage_dealt'],
                damage_taken=perf_data['damage_taken'],
                gold_earned=perf_data['gold_earned'],
                cs_score=perf_data['cs_score'],
                vision_score=perf_data['vision_score'],
                wards_placed=perf_data['wards_placed'],
                wards_cleared=perf_data['wards_cleared'],
                dragon_kills=perf_data.get('dragon_kills', 0),
                baron_kills=perf_data.get('baron_kills', 0),
                tower_kills=perf_data.get('tower_kills', 0),
                objective_damage=perf_data.get('objective_damage', 0),
                teamfight_participation=perf_data.get('teamfight_participation', 0.75),
                teamfight_damage_share=perf_data.get('teamfight_damage_share', 0.2),
                teamfight_kills=perf_data.get('teamfight_kills', 0),
                teamfight_deaths=perf_data.get('teamfight_deaths', 0),
                match_result=perf_data['match_result'],
                played_at=datetime.fromisoformat(perf_data['played_at'])
            )
            player_performances.append(performance)

        return UpdatePlayerRatingRequest(
            match_id=match_id,
            player_performances=player_performances,
            team1_player_ids=match_data['team1_players'],
            team2_player_ids=match_data['team2_players'],
            save_history=True,
            dry_run=False
        )