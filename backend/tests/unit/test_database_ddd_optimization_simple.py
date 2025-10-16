"""
简化版数据库DDD优化测试

验证数据库优化的核心功能，避免复杂的异步SQLAlchemy inspect操作
遵循CLAUDE.md中的单元测试要求和代码风格规范
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import database_manager


class TestDDDDatabaseOptimizationSimple:
    """简化版DDD架构数据库优化测试"""

    @pytest.fixture
    async def db_session(self) -> AsyncSession:
        """获取数据库会话的fixture"""
        # 确保数据库连接已初始化
        if database_manager._engine is None:
            await database_manager.connect()
        
        async with database_manager.get_session() as session:
            yield session

    async def test_indexes_exist_via_sql(self, db_session: AsyncSession):
        """通过SQL查询验证索引是否存在"""
        result = await db_session.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('teams', 'matches', 'user_roles', 'player_profiles', 'tournaments', 'season_registrations')
            AND indexname LIKE 'idx_%'
        """))
        
        index_names = [row[0] for row in result.fetchall()]
        
        # 验证关键索引存在
        expected_indexes = [
            'idx_teams_region_active',
            'idx_teams_region_recruiting',
            'idx_matches_season_status',
            'idx_matches_teams_status',
            'idx_user_roles_region_active',
            'idx_user_roles_user_active',
            'idx_player_profiles_region_rating',
            'idx_player_profiles_team_position',
            'idx_tournaments_region_status',
            'idx_tournaments_type_status',
            'idx_season_registrations_season_status'
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing index: {idx}"

    async def test_domain_events_table_exists(self, db_session: AsyncSession):
        """验证领域事件表存在且结构正确"""
        result = await db_session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'domain_events'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        assert len(columns) > 0, "domain_events table should exist"
        
        column_names = [col[0] for col in columns]
        expected_columns = [
            'id', 'aggregate_type', 'aggregate_id', 'event_type',
            'event_data', 'version', 'occurred_at', 'processed_at', 'created_at'
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Missing column in domain_events: {col}"

    async def test_statistics_cache_tables_exist(self, db_session: AsyncSession):
        """验证统计缓存表存在"""
        result = await db_session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%statistics_cache'
        """))
        
        cache_tables = [row[0] for row in result.fetchall()]
        
        assert 'team_statistics_cache' in cache_tables
        assert 'player_statistics_cache' in cache_tables

    async def test_read_only_views_accessible(self, db_session: AsyncSession):
        """验证只读视图可以正常访问"""
        views = [
            'team_performance_summary',
            'player_performance_summary', 
            'region_activity_summary',
            'player_leaderboard'
        ]
        
        for view in views:
            # 尝试查询每个视图，确保结构正确
            result = await db_session.execute(text(f"SELECT * FROM {view} LIMIT 1"))
            # 不需要数据存在，只要查询不报错即可
            assert result is not None, f"View {view} should be accessible"

    async def test_team_performance_summary_structure(self, db_session: AsyncSession):
        """验证战队表现汇总视图包含预期字段"""
        result = await db_session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'team_performance_summary'
            ORDER BY ordinal_position
        """))
        
        columns = [row[0] for row in result.fetchall()]
        
        expected_columns = [
            'team_id', 'team_name', 'team_tag', 'region_id', 'region_name',
            'total_matches', 'total_wins', 'total_losses', 'win_rate',
            'total_members', 'active_members', 'average_player_rating'
        ]
        
        for col in expected_columns:
            assert col in columns, f"Missing column in team_performance_summary: {col}"

    async def test_player_leaderboard_ranking_columns(self, db_session: AsyncSession):
        """验证选手排行榜视图包含排名字段"""
        result = await db_session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'player_leaderboard'
            AND column_name LIKE '%rank%'
        """))
        
        ranking_columns = [row[0] for row in result.fetchall()]
        
        expected_ranking_columns = [
            'rating_rank', 'region_rating_rank', 'position_rating_rank'
        ]
        
        for col in expected_ranking_columns:
            assert col in ranking_columns, f"Missing ranking column: {col}"

    async def test_domain_events_indexes_exist(self, db_session: AsyncSession):
        """验证领域事件表的索引存在"""
        result = await db_session.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'domain_events'
            AND indexname LIKE 'idx_%'
        """))
        
        index_names = [row[0] for row in result.fetchall()]
        
        expected_indexes = [
            'idx_domain_events_aggregate',
            'idx_domain_events_type_occurred',
            'idx_domain_events_unprocessed'
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing domain events index: {idx}"

    async def test_statistics_cache_indexes_exist(self, db_session: AsyncSession):
        """验证统计缓存表的索引存在"""
        result = await db_session.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes 
            WHERE tablename LIKE '%statistics_cache'
            AND indexname LIKE 'idx_%'
        """))
        
        indexes = result.fetchall()
        index_names = [row[0] for row in indexes]
        
        expected_indexes = [
            'idx_team_stats_team_season',
            'idx_team_stats_ranking',
            'idx_player_stats_profile_season',
            'idx_player_stats_performance'
        ]
        
        for idx in expected_indexes:
            assert idx in index_names, f"Missing statistics cache index: {idx}"

    async def test_foreign_keys_preserved(self, db_session: AsyncSession):
        """验证重要的外键约束仍然存在"""
        result = await db_session.execute(text("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name IN ('teams', 'player_profiles', 'team_members', 'matches')
        """))
        
        foreign_keys = result.fetchall()
        
        # 验证至少有一些关键外键存在
        assert len(foreign_keys) > 0, "Should have foreign key constraints"
        
        # 验证团队-用户关系
        team_fks = [fk for fk in foreign_keys if fk[0] == 'teams']
        team_fk_columns = [fk[1] for fk in team_fks]
        
        assert 'captain_user_id' in team_fk_columns, "teams.captain_user_id FK should exist"
        assert 'region_id' in team_fk_columns, "teams.region_id FK should exist"

    async def test_database_optimization_impact(self, db_session: AsyncSession):
        """测试数据库优化的整体影响"""
        # 验证所有关键表都存在
        result = await db_session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """))
        
        tables = [row[0] for row in result.fetchall()]
        
        # 验证原有表仍然存在
        original_tables = [
            'users', 'teams', 'player_profiles', 'regions', 
            'tournaments', 'matches', 'seasons'
        ]
        
        for table in original_tables:
            assert table in tables, f"Original table {table} should still exist"
        
        # 验证新增的优化表存在
        optimization_tables = [
            'domain_events', 'team_statistics_cache', 'player_statistics_cache'
        ]
        
        for table in optimization_tables:
            assert table in tables, f"Optimization table {table} should exist"