"""
Player pool API routes for FlyEsports.

Provides endpoints for querying, filtering, and analyzing player pools
including statistics, recommendations, and comparisons.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
import structlog

from src.presentation.schemas.auth import MessageResponse, ErrorResponse
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.permission import verify_permission
from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.domain.entities.user import User
from src.application.use_cases.query_player_pool import (
    QueryPlayerPoolUseCase,
    QueryPlayerPoolRequest,
    GetPlayerPoolStatisticsUseCase,
    RecommendPlayersUseCase,
    ComparePlayersUseCase
)
from src.domain.value_objects.pool_filter import PoolFilter, SortBy, SortOrder, ContractStatus
from src.infrastructure.repositories.player_profile import SQLAlchemyPlayerProfileRepository
from src.infrastructure.database.connection import database_manager
from src.domain.services.player_pool_manager import PlayerPoolManager
from src.domain.services.rating_update_service import RatingUpdateService


router = APIRouter()
logger = structlog.get_logger(__name__)


# Dependency injection helpers
async def get_player_pool_query_use_case():
    """Get player pool query use case instance."""
    async with database_manager.get_session() as session:
        player_repository = SQLAlchemyPlayerProfileRepository(session)
        pool_manager = PlayerPoolManager()
        return QueryPlayerPoolUseCase(player_repository, pool_manager)


async def get_pool_statistics_use_case():
    """Get pool statistics use case instance."""
    async with database_manager.get_session() as session:
        player_repository = SQLAlchemyPlayerProfileRepository(session)
        pool_manager = PlayerPoolManager()
        return GetPlayerPoolStatisticsUseCase(player_repository, pool_manager)


async def get_recommend_players_use_case():
    """Get recommend players use case instance."""
    async with database_manager.get_session() as session:
        player_repository = SQLAlchemyPlayerProfileRepository(session)
        pool_manager = PlayerPoolManager()
        return RecommendPlayersUseCase(player_repository, pool_manager)


async def get_compare_players_use_case():
    """Get compare players use case instance."""
    async with database_manager.get_session() as session:
        player_repository = SQLAlchemyPlayerProfileRepository(session)
        return ComparePlayersUseCase(player_repository)


@router.get("")
@router.get("/")
async def get_player_pool_root(
    region_id: Optional[int] = Query(None, description="Region ID to filter by"),
    # Filter parameters
    position: Optional[str] = Query(None, description="Filter by position (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY)"),
    contract_status: Optional[str] = Query("all", description="Filter by contract status"),
    min_rating: Optional[float] = Query(None, description="Minimum rating filter"),
    max_rating: Optional[float] = Query(None, description="Maximum rating filter"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence level"),
    min_matches: Optional[int] = Query(None, description="Minimum matches played"),
    max_matches: Optional[int] = Query(None, description="Maximum matches played"),

    # Dimension filters
    min_kda_dimension: Optional[float] = Query(None, description="Minimum KDA dimension score"),
    min_damage_dimension: Optional[float] = Query(None, description="Minimum damage dimension score"),
    min_economy_dimension: Optional[float] = Query(None, description="Minimum economy dimension score"),
    min_vision_dimension: Optional[float] = Query(None, description="Minimum vision dimension score"),
    min_objective_dimension: Optional[float] = Query(None, description="Minimum objective dimension score"),
    min_teamfight_dimension: Optional[float] = Query(None, description="Minimum teamfight dimension score"),

    # Search parameters
    player_name_search: Optional[str] = Query(None, description="Search by player name"),
    summoner_name_search: Optional[str] = Query(None, description="Search by summoner name"),
    active_within_days: Optional[int] = Query(None, description="Filter by recent activity"),

    # Sorting and pagination
    sort_by: Optional[str] = Query("rating", description="Sort by field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),

    # Additional options
    include_statistics: bool = Query(False, description="Include pool statistics"),

    # Dependencies
    query_use_case: QueryPlayerPoolUseCase = Depends(get_player_pool_query_use_case)
):
    """
    Get player pool with filtering and pagination.

    Region ID is optional - if not provided, returns players from all regions.
    Returns a paginated list of players matching the specified criteria,
    optionally including pool statistics.
    """
    try:
        logger.info(
            "Player pool query requested",
            region_id=region_id,
            position=position,
            contract_status=contract_status,
            page=page,
            page_size=page_size
        )

        # Create pool filter from query parameters
        try:
            # Parse enum values
            sort_by_enum = SortBy(sort_by) if sort_by else SortBy.RATING
            sort_order_enum = SortOrder(sort_order) if sort_order else SortOrder.DESC
            contract_status_enum = ContractStatus(contract_status) if contract_status else ContractStatus.ALL
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter value: {str(e)}"
            )

        pool_filter = PoolFilter(
            region_id=region_id,
            position=position,
            contract_status=contract_status_enum,
            min_rating=min_rating,
            max_rating=max_rating,
            min_confidence=min_confidence,
            min_matches=min_matches,
            max_matches=max_matches,
            min_kda_dimension=min_kda_dimension,
            min_damage_dimension=min_damage_dimension,
            min_economy_dimension=min_economy_dimension,
            min_vision_dimension=min_vision_dimension,
            min_objective_dimension=min_objective_dimension,
            min_teamfight_dimension=min_teamfight_dimension,
            player_name_search=player_name_search,
            summoner_name_search=summoner_name_search,
            active_within_days=active_within_days,
            sort_by=sort_by_enum,
            sort_order=sort_order_enum,
            page=page,
            page_size=page_size
        )

        # Create request
        request = QueryPlayerPoolRequest(
            region_id=region_id,
            pool_filter=pool_filter,
            include_statistics=include_statistics
        )

        # Execute query
        response = await query_use_case.execute(request)

        # Convert to API response format (flat structure matching frontend expectations)
        api_response = {
            "players": [
                {
                    "id": player.profile_id,
                    "username": player.summoner_name,
                    "display_name": player.player_name,
                    "primary_position": player.position.value if player.position else None,
                    "secondary_position": None,
                    "contract_status": player.contract_status.value if player.contract_status else "free_agent",
                    "rating": {
                        "current_score": player.rating.current_score if player.rating else 0,
                        "locked_score": player.rating.locked_score if player.rating else None,
                        "confidence_level": player.rating.confidence_level if player.rating else 0.5,
                        "total_matches": player.total_matches,
                        "six_dimensions": player.rating.six_dimensions if player.rating else {
                            "kda": 50.0,
                            "damage": 50.0,
                            "economy": 50.0,
                            "vision": 50.0,
                            "objective": 50.0,
                            "teamfight": 50.0
                        }
                    },
                    "total_matches": player.total_matches,
                    "total_wins": player.total_wins,
                    "win_rate": (player.total_wins / player.total_matches * 100) if player.total_matches > 0 else 0,
                    "last_active_at": player.last_active.isoformat() if player.last_active else None,
                    "avatar_url": None,
                    "bio": player.description,
                    "achievements": [],
                    "preferred_champions": []
                }
                for player in response.players
            ],
            "total_count": response.total_count,
            "page": response.page,
            "page_size": response.page_size,
            "total_pages": response.total_pages,
            "has_next_page": response.has_next_page,
            "has_previous_page": response.has_previous_page,
            "query_time_ms": response.query_time_ms,
            "from_cache": response.from_cache
        }

        # Add statistics if requested
        if response.statistics:
            api_response["statistics"] = {
                "total_players": response.statistics.total_players,
                "active_players": response.statistics.active_players,
                "free_agents": response.statistics.free_agents,
                "contracted_players": response.statistics.contracted_players,
                "position_distribution": response.statistics.position_distribution,
                "average_rating": response.statistics.average_rating,
                "median_rating": response.statistics.median_rating,
                "rating_std_deviation": response.statistics.rating_std_deviation,
                "min_rating": response.statistics.min_rating,
                "max_rating": response.statistics.max_rating,
                "rating_tiers": response.statistics.rating_tiers,
                "average_confidence": response.statistics.average_confidence,
                "high_confidence_players": response.statistics.high_confidence_players,
                "low_confidence_players": response.statistics.low_confidence_players,
                "matches_last_week": response.statistics.matches_last_week,
                "matches_last_month": response.statistics.matches_last_month,
                "most_active_position": response.statistics.most_active_position,
                "least_active_position": response.statistics.least_active_position,
                "highest_rated_players": [
                    {
                        "id": p.profile_id,
                        "username": p.summoner_name,
                        "rating": p.rating.current_score if p.rating else 0,
                        "position": p.position.value if p.position else None
                    }
                    for p in response.statistics.highest_rated_players
                ] if hasattr(response.statistics, 'highest_rated_players') else [],
                "most_improved_players": [
                    {
                        "id": p.profile_id,
                        "username": p.summoner_name,
                        "rating_change": getattr(p, 'rating_change', 0),
                        "position": p.position.value if p.position else None
                    }
                    for p in response.statistics.most_improved_players
                ] if hasattr(response.statistics, 'most_improved_players') else [],
                "dimension_averages": response.statistics.dimension_averages,
                "new_players_last_week": response.statistics.new_players_last_week,
                "new_players_last_month": response.statistics.new_players_last_month,
                "retention_rate_30d": response.statistics.retention_rate_30d,
                "generated_at": response.statistics.generated_at.isoformat(),
                "pool_health": "Healthy" if response.statistics.is_healthy_pool() else "Needs Attention",
                "growth_trend": response.statistics.get_growth_trend(),
                "competitive_balance": response.statistics.competitive_balance
            }

        logger.info(
            "Player pool query completed",
            region_id=region_id,
            result_count=len(response.players),
            total_count=response.total_count,
            query_time_ms=response.query_time_ms
        )

        return JSONResponse(content=api_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Player pool query failed",
            region_id=region_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve player pool"
        )


@router.get("/pool/{region_id}/statistics")
async def get_pool_statistics(
    region_id: int,
    stats_use_case: GetPlayerPoolStatisticsUseCase = Depends(get_pool_statistics_use_case)
):
    """Get comprehensive statistics for a player pool."""
    try:
        logger.info(
            "Pool statistics requested",
            region_id=region_id
        )

        statistics = await stats_use_case.execute(region_id)

        response = {
            "region_id": region_id,
            "statistics": {
                "basic_stats": {
                    "total_players": statistics.total_players,
                    "active_players": statistics.active_players,
                    "free_agents": statistics.free_agents,
                    "contracted_players": statistics.contracted_players,
                    "activity_rate": statistics.get_activity_rate(),
                    "free_agent_rate": statistics.get_free_agent_rate()
                },
                "rating_distribution": {
                    "average_rating": statistics.average_rating,
                    "median_rating": statistics.median_rating,
                    "rating_std_deviation": statistics.rating_std_deviation,
                    "min_rating": statistics.min_rating,
                    "max_rating": statistics.max_rating,
                    "rating_tiers": statistics.rating_tiers
                },
                "position_distribution": statistics.position_distribution,
                "confidence_stats": {
                    "average_confidence": statistics.average_confidence,
                    "high_confidence_players": statistics.high_confidence_players,
                    "low_confidence_players": statistics.low_confidence_players
                },
                "top_players": statistics.highest_rated_players,
                "dimension_averages": statistics.dimension_averages,
                "pool_health": {
                    "is_healthy": statistics.is_healthy_pool(),
                    "growth_trend": statistics.get_growth_trend(),
                    "competitive_balance": statistics.get_competitive_balance()
                },
                "generated_at": statistics.generated_at.isoformat()
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(
            "Pool statistics query failed",
            region_id=region_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pool statistics"
        )


@router.post("/pool/recommend")
async def recommend_players(
    team_needs: Dict[str, Any],
    region_id: Optional[int] = None,
    max_recommendations: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_permission(PermissionResource.PLAYER, PermissionAction.READ)),
    recommend_use_case: RecommendPlayersUseCase = Depends(get_recommend_players_use_case)
):
    """Get player recommendations based on team needs."""
    try:
        logger.info(
            "Player recommendations requested",
            team_needs=team_needs,
            region_id=region_id,
            user_id=current_user.id,
            max_recommendations=max_recommendations
        )

        recommendations = await recommend_use_case.execute(
            team_needs=team_needs,
            region_id=region_id,
            max_recommendations=max_recommendations
        )

        response = {
            "team_needs": team_needs,
            "region_id": region_id,
            "recommendations": [
                {
                    "player": {
                        "profile_id": rec["player"].profile_id,
                        "player_name": rec["player"].player_name,
                        "summoner_name": rec["player"].summoner_name,
                        "position": rec["player"].position.value if rec["player"].position else None,
                        "current_rating": rec["player"].rating.current_score if rec["player"].rating else 0,
                        "confidence_level": rec["player"].rating.confidence_level if rec["player"].rating else 0.5,
                        "total_matches": rec["player"].total_matches,
                        "contract_status": rec["player"].contract_status.value if rec["player"].contract_status else "free_agent"
                    },
                    "recommendation_score": rec["score"],
                    "reasons": rec["reasons"]
                }
                for rec in recommendations
            ],
            "recommendation_count": len(recommendations)
        }

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(
            "Player recommendations failed",
            team_needs=team_needs,
            region_id=region_id,
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate player recommendations"
        )


@router.post("/pool/compare")
async def compare_players(
    player_ids: List[str],
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_permission(PermissionResource.PLAYER, PermissionAction.READ)),
    compare_use_case: ComparePlayersUseCase = Depends(get_compare_players_use_case)
):
    """Compare multiple players across various metrics."""
    try:
        logger.info(
            "Player comparison requested",
            player_ids=player_ids,
            user_id=current_user.id
        )

        if len(player_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 players are required for comparison"
            )

        if len(player_ids) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compare more than 5 players at once"
            )

        comparison_data = await compare_use_case.execute(player_ids)

        # Format response
        response = {
            "players": [
                {
                    "profile_id": player.profile_id,
                    "player_name": player.player_name,
                    "summoner_name": player.summoner_name,
                    "position": player.position.value if player.position else None,
                    "current_rating": player.rating.current_score if player.rating else 0,
                    "confidence_level": player.rating.confidence_level if player.rating else 0.5,
                    "total_matches": player.total_matches,
                    "win_rate": (player.total_wins / player.total_matches * 100) if player.total_matches > 0 else 0,
                    "six_dimensions": player.rating.six_dimensions if player.rating else {}
                }
                for player in comparison_data["players"]
            ],
            "comparison": comparison_data["comparison"],
            "generated_at": comparison_data["generated_at"]
        }

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Player comparison failed",
            player_ids=player_ids,
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare players"
        )


@router.get("/pool/search")
async def search_players(
    q: str = Query(..., min_length=2, description="Search query"),
    region_id: Optional[int] = Query(None, description="Filter by region"),
    position: Optional[str] = Query(None, description="Filter by position"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    query_use_case: QueryPlayerPoolUseCase = Depends(get_player_pool_query_use_case)
):
    """Search for players by name or summoner name."""
    try:
        logger.info(
            "Player search requested",
            query=q,
            region_id=region_id,
            position=position
        )

        # Create search filter
        pool_filter = PoolFilter(
            region_id=region_id,
            position=position,
            player_name_search=q,
            summoner_name_search=q,  # Search in both fields
            sort_by=SortBy.RATING,
            sort_order=SortOrder.DESC,
            page=1,
            page_size=limit
        )

        request = QueryPlayerPoolRequest(
            region_id=region_id,
            pool_filter=pool_filter,
            include_statistics=False
        )

        response = await query_use_case.execute(request)

        # Format search results
        search_results = {
            "query": q,
            "region_id": region_id,
            "position": position,
            "results": [
                {
                    "profile_id": player.profile_id,
                    "player_name": player.player_name,
                    "summoner_name": player.summoner_name,
                    "position": player.position.value if player.position else None,
                    "current_rating": player.rating.current_score if player.rating else 0,
                    "total_matches": player.total_matches,
                    "contract_status": player.contract_status.value if player.contract_status else "free_agent"
                }
                for player in response.players
            ],
            "result_count": len(response.players),
            "total_matches": response.total_count
        }

        return JSONResponse(content=search_results)

    except Exception as e:
        logger.error(
            "Player search failed",
            query=q,
            region_id=region_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Player search failed"
        )


@router.get("/pool/filters/options")
async def get_filter_options(
    region_id: Optional[int] = Query(None, description="Region ID for region-specific options")
):
    """Get available filter options for the player pool interface."""
    try:
        # Return static filter options (could be made dynamic based on actual data)
        options = {
            "positions": [
                {"value": "TOP", "label": "Top Lane"},
                {"value": "JUNGLE", "label": "Jungle"},
                {"value": "MIDDLE", "label": "Mid Lane"},
                {"value": "BOTTOM", "label": "Bot Lane (ADC)"},
                {"value": "UTILITY", "label": "Support"}
            ],
            "contract_statuses": [
                {"value": "all", "label": "All Players"},
                {"value": "free_agent", "label": "Free Agents"},
                {"value": "contracted", "label": "Contracted"},
                {"value": "locked", "label": "Locked Rating"}
            ],
            "sort_options": [
                {"value": "rating", "label": "Rating"},
                {"value": "confidence", "label": "Confidence Level"},
                {"value": "matches", "label": "Total Matches"},
                {"value": "recent_activity", "label": "Recent Activity"},
                {"value": "player_name", "label": "Player Name"},
                {"value": "kda_dimension", "label": "KDA Dimension"},
                {"value": "damage_dimension", "label": "Damage Dimension"},
                {"value": "economy_dimension", "label": "Economy Dimension"},
                {"value": "vision_dimension", "label": "Vision Dimension"},
                {"value": "objective_dimension", "label": "Objective Dimension"},
                {"value": "teamfight_dimension", "label": "Teamfight Dimension"}
            ],
            "rating_ranges": {
                "min": 0,
                "max": 5000,
                "suggested_ranges": [
                    {"label": "Bronze", "min": 0, "max": 899},
                    {"label": "Silver", "min": 900, "max": 1199},
                    {"label": "Gold", "min": 1200, "max": 1499},
                    {"label": "Platinum", "min": 1500, "max": 1999},
                    {"label": "Diamond", "min": 2000, "max": 2499},
                    {"label": "Master", "min": 2500, "max": 2999},
                    {"label": "Challenger", "min": 3000, "max": 5000}
                ]
            },
            "dimension_ranges": {
                "min": 0,
                "max": 100,
                "descriptions": {
                    "kda": "Kill/Death/Assist performance",
                    "damage": "Damage output and efficiency",
                    "economy": "Gold earning and farming",
                    "vision": "Vision control and map awareness",
                    "objective": "Objective control and impact",
                    "teamfight": "Team fighting contribution"
                }
            }
        }

        return JSONResponse(content=options)

    except Exception as e:
        logger.error(
            "Failed to get filter options",
            region_id=region_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve filter options"
        )