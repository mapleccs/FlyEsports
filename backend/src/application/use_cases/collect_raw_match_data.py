"""
原始比赛数据采集用例
处理比赛数据的收集、验证和存储
"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import structlog

from ..base import UseCase, UseCaseError
from ...domain.entities.raw_match_data import RawMatchDataEntity, RawDataParsingJobEntity
from ...domain.repositories.raw_match_data import RawMatchDataRepository, RawDataParsingJobRepository


logger = structlog.get_logger(__name__)


class CollectRawMatchDataRequest:
    """原始比赛数据采集请求"""

    def __init__(
        self,
        game_id: int,
        raw_data: Dict[str, Any],
        bp_room_id: Optional[str] = None,
        tournament_id: Optional[UUID] = None,
        match_id: Optional[str] = None,
        auto_parse: bool = True,
        validate_data: bool = True
    ):
        self.game_id = game_id
        self.raw_data = raw_data
        self.bp_room_id = bp_room_id
        self.tournament_id = tournament_id
        self.match_id = match_id
        self.auto_parse = auto_parse
        self.validate_data = validate_data


class CollectRawMatchDataResponse:
    """原始比赛数据采集响应"""

    def __init__(
        self,
        raw_match_data: RawMatchDataEntity,
        is_duplicate: bool = False,
        validation_passed: bool = True,
        parsing_jobs_created: int = 0,
        warnings: list = None
    ):
        self.raw_match_data = raw_match_data
        self.is_duplicate = is_duplicate
        self.validation_passed = validation_passed
        self.parsing_jobs_created = parsing_jobs_created
        self.warnings = warnings or []

    @property
    def success(self) -> bool:
        """检查采集是否成功"""
        return not self.is_duplicate and self.validation_passed


class CollectRawMatchDataUseCase(UseCase):
    """
    原始比赛数据采集用例

    负责处理从LOL客户端收集到的原始比赛数据，包括：
    - 数据去重检查
    - 数据验证
    - 数据存储
    - 自动创建解析任务
    """

    def __init__(
        self,
        raw_match_data_repository: RawMatchDataRepository,
        parsing_job_repository: RawDataParsingJobRepository
    ):
        self.raw_match_data_repository = raw_match_data_repository
        self.parsing_job_repository = parsing_job_repository

    async def execute(self, request: CollectRawMatchDataRequest) -> CollectRawMatchDataResponse:
        """
        执行原始比赛数据采集

        Args:
            request: 采集请求

        Returns:
            CollectRawMatchDataResponse: 采集结果

        Raises:
            UseCaseError: 当采集过程出现错误时
        """
        try:
            logger.info(
                "开始采集原始比赛数据",
                game_id=request.game_id,
                bp_room_id=request.bp_room_id,
                tournament_id=str(request.tournament_id) if request.tournament_id else None
            )

            # 1. 检查数据是否已存在
            existing_data = await self.raw_match_data_repository.find_by_game_id(request.game_id)
            if existing_data:
                logger.warning(
                    "比赛数据已存在，跳过采集",
                    game_id=request.game_id,
                    existing_id=existing_data.id
                )
                return CollectRawMatchDataResponse(
                    raw_match_data=existing_data,
                    is_duplicate=True
                )

            # 2. 创建原始比赛数据实体
            raw_match_data = RawMatchDataEntity.create_from_raw_data(
                game_id=request.game_id,
                raw_data=request.raw_data,
                bp_room_id=request.bp_room_id,
                tournament_id=request.tournament_id
            )

            # 设置内部比赛ID
            if request.match_id:
                raw_match_data.match_id = request.match_id

            warnings = []

            # 3. 数据验证
            validation_passed = True
            if request.validate_data:
                validation_passed = raw_match_data.validate_data()
                if not validation_passed:
                    logger.warning(
                        "比赛数据验证失败",
                        game_id=request.game_id,
                        errors=raw_match_data.validation_errors
                    )
                    warnings.append(f"数据验证失败: {raw_match_data.validation_errors}")

            # 4. 保存原始数据
            raw_match_data = await self.raw_match_data_repository.save(raw_match_data)

            logger.info(
                "原始比赛数据保存成功",
                game_id=request.game_id,
                raw_match_data_id=raw_match_data.id,
                player_count=len(raw_match_data.player_performances)
            )

            # 5. 创建解析任务
            parsing_jobs_created = 0
            if request.auto_parse and validation_passed:
                parsing_jobs_created = await self._create_parsing_jobs(raw_match_data)

            return CollectRawMatchDataResponse(
                raw_match_data=raw_match_data,
                is_duplicate=False,
                validation_passed=validation_passed,
                parsing_jobs_created=parsing_jobs_created,
                warnings=warnings
            )

        except Exception as e:
            logger.error(
                "原始比赛数据采集失败",
                game_id=request.game_id,
                error=str(e)
            )
            raise UseCaseError(f"比赛数据采集失败: {str(e)}") from e

    async def _create_parsing_jobs(self, raw_match_data: RawMatchDataEntity) -> int:
        """创建数据解析任务"""
        jobs = []

        # 1. 数据解析任务（最高优先级）
        parse_job = RawDataParsingJobEntity.create_parse_job(
            raw_match_data_id=raw_match_data.id,
            priority=1
        )
        jobs.append(parse_job)

        # 2. 选手关联任务（中等优先级）
        link_job = RawDataParsingJobEntity.create_link_players_job(
            raw_match_data_id=raw_match_data.id,
            priority=3
        )
        jobs.append(link_job)

        # 3. 评分计算任务（低优先级，依赖前面任务完成）
        rating_job = RawDataParsingJobEntity.create_calculate_ratings_job(
            raw_match_data_id=raw_match_data.id,
            priority=5
        )
        jobs.append(rating_job)

        # 批量保存任务
        saved_jobs = await self.parsing_job_repository.batch_create_jobs(jobs)

        logger.info(
            "解析任务创建完成",
            raw_match_data_id=raw_match_data.id,
            job_count=len(saved_jobs)
        )

        return len(saved_jobs)


class BatchCollectRawMatchDataRequest:
    """批量原始比赛数据采集请求"""

    def __init__(
        self,
        match_data_list: list[Dict[str, Any]],
        bp_room_id: Optional[str] = None,
        tournament_id: Optional[UUID] = None,
        auto_parse: bool = True,
        validate_data: bool = True,
        continue_on_error: bool = True
    ):
        self.match_data_list = match_data_list
        self.bp_room_id = bp_room_id
        self.tournament_id = tournament_id
        self.auto_parse = auto_parse
        self.validate_data = validate_data
        self.continue_on_error = continue_on_error


class BatchCollectRawMatchDataResponse:
    """批量原始比赛数据采集响应"""

    def __init__(
        self,
        successful_count: int = 0,
        duplicate_count: int = 0,
        failed_count: int = 0,
        total_parsing_jobs: int = 0,
        results: list = None,
        errors: list = None
    ):
        self.successful_count = successful_count
        self.duplicate_count = duplicate_count
        self.failed_count = failed_count
        self.total_parsing_jobs = total_parsing_jobs
        self.results = results or []
        self.errors = errors or []

    @property
    def total_processed(self) -> int:
        """获取总处理数量"""
        return self.successful_count + self.duplicate_count + self.failed_count

    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total_processed == 0:
            return 0.0
        return self.successful_count / self.total_processed


class BatchCollectRawMatchDataUseCase(UseCase):
    """
    批量原始比赛数据采集用例

    支持批量处理多个比赛数据，适用于：
    - 比赛结束后的批量数据采集
    - 历史数据导入
    - 数据补全和修复
    """

    def __init__(
        self,
        collect_use_case: CollectRawMatchDataUseCase
    ):
        self.collect_use_case = collect_use_case

    async def execute(self, request: BatchCollectRawMatchDataRequest) -> BatchCollectRawMatchDataResponse:
        """
        执行批量原始比赛数据采集

        Args:
            request: 批量采集请求

        Returns:
            BatchCollectRawMatchDataResponse: 批量采集结果
        """
        logger.info(
            "开始批量采集原始比赛数据",
            total_matches=len(request.match_data_list),
            bp_room_id=request.bp_room_id,
            tournament_id=str(request.tournament_id) if request.tournament_id else None
        )

        successful_count = 0
        duplicate_count = 0
        failed_count = 0
        total_parsing_jobs = 0
        results = []
        errors = []

        for i, match_data in enumerate(request.match_data_list):
            try:
                # 提取游戏ID
                game_id = match_data.get('gameId')
                if not game_id:
                    error_msg = f"Match {i+1}: Missing gameId in match data"
                    errors.append(error_msg)
                    failed_count += 1
                    continue

                # 创建单个采集请求
                collect_request = CollectRawMatchDataRequest(
                    game_id=game_id,
                    raw_data=match_data,
                    bp_room_id=request.bp_room_id,
                    tournament_id=request.tournament_id,
                    auto_parse=request.auto_parse,
                    validate_data=request.validate_data
                )

                # 执行采集
                response = await self.collect_use_case.execute(collect_request)

                # 统计结果
                if response.is_duplicate:
                    duplicate_count += 1
                elif response.success:
                    successful_count += 1
                    total_parsing_jobs += response.parsing_jobs_created
                else:
                    failed_count += 1

                results.append({
                    "game_id": game_id,
                    "success": response.success,
                    "is_duplicate": response.is_duplicate,
                    "warnings": response.warnings
                })

            except Exception as e:
                error_msg = f"Match {i+1} (gameId: {match_data.get('gameId', 'unknown')}): {str(e)}"
                errors.append(error_msg)
                failed_count += 1

                logger.error(
                    "单个比赛数据采集失败",
                    match_index=i+1,
                    game_id=match_data.get('gameId'),
                    error=str(e)
                )

                if not request.continue_on_error:
                    break

        logger.info(
            "批量采集完成",
            total_processed=successful_count + duplicate_count + failed_count,
            successful_count=successful_count,
            duplicate_count=duplicate_count,
            failed_count=failed_count,
            total_parsing_jobs=total_parsing_jobs
        )

        return BatchCollectRawMatchDataResponse(
            successful_count=successful_count,
            duplicate_count=duplicate_count,
            failed_count=failed_count,
            total_parsing_jobs=total_parsing_jobs,
            results=results,
            errors=errors
        )


class ProcessRawMatchDataRequest:
    """原始比赛数据处理请求"""

    def __init__(
        self,
        raw_match_data_id: int,
        force_reprocess: bool = False,
        skip_validation: bool = False
    ):
        self.raw_match_data_id = raw_match_data_id
        self.force_reprocess = force_reprocess
        self.skip_validation = skip_validation


class ProcessRawMatchDataResponse:
    """原始比赛数据处理响应"""

    def __init__(
        self,
        raw_match_data: RawMatchDataEntity,
        processing_completed: bool,
        linked_players: int = 0,
        ratings_updated: int = 0,
        errors: list = None
    ):
        self.raw_match_data = raw_match_data
        self.processing_completed = processing_completed
        self.linked_players = linked_players
        self.ratings_updated = ratings_updated
        self.errors = errors or []


class ProcessRawMatchDataUseCase(UseCase):
    """
    原始比赛数据处理用例

    处理已采集的原始数据，包括：
    - 选手身份关联
    - 评分计算和更新
    - 数据完整性检查
    """

    def __init__(
        self,
        raw_match_data_repository: RawMatchDataRepository,
        parsing_job_repository: RawDataParsingJobRepository
    ):
        self.raw_match_data_repository = raw_match_data_repository
        self.parsing_job_repository = parsing_job_repository

    async def execute(self, request: ProcessRawMatchDataRequest) -> ProcessRawMatchDataResponse:
        """
        执行原始比赛数据处理

        Args:
            request: 处理请求

        Returns:
            ProcessRawMatchDataResponse: 处理结果

        Raises:
            UseCaseError: 当处理过程出现错误时
        """
        try:
            # 获取原始比赛数据
            raw_match_data = await self.raw_match_data_repository.find_by_id(
                request.raw_match_data_id
            )

            if not raw_match_data:
                raise UseCaseError(f"Raw match data with id {request.raw_match_data_id} not found")

            logger.info(
                "开始处理原始比赛数据",
                raw_match_data_id=request.raw_match_data_id,
                game_id=raw_match_data.game_id
            )

            errors = []
            linked_players = 0
            ratings_updated = 0

            # 检查是否需要重新处理
            if raw_match_data.is_parsed and not request.force_reprocess:
                logger.info(
                    "比赛数据已处理，跳过处理",
                    raw_match_data_id=request.raw_match_data_id
                )
                return ProcessRawMatchDataResponse(
                    raw_match_data=raw_match_data,
                    processing_completed=True,
                    linked_players=len([p for p in raw_match_data.player_performances if p.is_linked_to_profile]),
                    ratings_updated=0
                )

            # 数据验证
            if not request.skip_validation:
                is_valid = raw_match_data.validate_data()
                if not is_valid:
                    errors.append(f"数据验证失败: {raw_match_data.validation_errors}")

            # TODO: 实现具体的处理逻辑
            # 1. 选手身份关联
            # 2. 评分计算
            # 3. 统计更新

            # 标记为已处理
            raw_match_data.mark_as_parsed()
            await self.raw_match_data_repository.save(raw_match_data)

            logger.info(
                "原始比赛数据处理完成",
                raw_match_data_id=request.raw_match_data_id,
                linked_players=linked_players,
                ratings_updated=ratings_updated
            )

            return ProcessRawMatchDataResponse(
                raw_match_data=raw_match_data,
                processing_completed=True,
                linked_players=linked_players,
                ratings_updated=ratings_updated,
                errors=errors
            )

        except Exception as e:
            logger.error(
                "原始比赛数据处理失败",
                raw_match_data_id=request.raw_match_data_id,
                error=str(e)
            )
            raise UseCaseError(f"比赛数据处理失败: {str(e)}") from e