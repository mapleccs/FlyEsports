"""文件上传用例"""

from typing import Tuple, Optional
from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile
import structlog

from ...infrastructure.services.file_service import FileStorageService
from ...domain.base import UseCase

logger = structlog.get_logger(__name__)


@dataclass
class UploadTournamentMediaCommand:
    """上传赛事媒体文件命令"""
    file: UploadFile
    media_type: str  # 'logo' 或 'banner'
    uploaded_by: UUID
    tournament_id: Optional[UUID] = None


@dataclass
class FileUploadResult:
    """文件上传结果"""
    file_id: str
    filename: str
    url: str
    path: str
    size: int
    content_type: str
    width: int
    height: int
    format: str
    hash: str


@dataclass
class DeleteFileCommand:
    """删除文件命令"""
    file_path: str
    deleted_by: UUID


class UploadTournamentMediaUseCase(UseCase[UploadTournamentMediaCommand, FileUploadResult]):
    """上传赛事媒体文件用例"""
    
    def __init__(self, file_service: FileStorageService):
        self.file_service = file_service
    
    async def execute(self, command: UploadTournamentMediaCommand) -> FileUploadResult:
        """
        执行文件上传
        
        Args:
            command: 上传命令
            
        Returns:
            FileUploadResult: 上传结果
            
        Raises:
            ValueError: 文件验证失败
            Exception: 上传过程出错
        """
        logger.info(
            "开始上传赛事媒体文件",
            media_type=command.media_type,
            filename=command.file.filename,
            content_type=command.file.content_type,
            tournament_id=str(command.tournament_id) if command.tournament_id else None,
            uploaded_by=str(command.uploaded_by)
        )
        
        # 验证媒体类型
        if command.media_type not in ["logo", "banner"]:
            raise ValueError(f"不支持的媒体类型: {command.media_type}")
        
        # 验证文件名
        if not command.file.filename:
            raise ValueError("文件名不能为空")
        
        try:
            # 执行文件上传
            file_path, file_info = await self.file_service.save_tournament_media(
                file=command.file,
                media_type=command.media_type,
                tournament_id=str(command.tournament_id) if command.tournament_id else None
            )
            
            # 构建返回结果
            result = FileUploadResult(
                file_id=file_info["id"],
                filename=file_info["filename"],
                url=file_info["url"],
                path=file_info["path"],
                size=file_info["size"],
                content_type=file_info["content_type"],
                width=file_info.get("width", 0),
                height=file_info.get("height", 0),
                format=file_info.get("format", "UNKNOWN"),
                hash=file_info["hash"]
            )
            
            logger.info(
                "赛事媒体文件上传成功",
                file_id=result.file_id,
                url=result.url,
                size=result.size,
                dimensions=f"{result.width}x{result.height}"
            )
            
            return result
            
        except ValueError:
            # 重新抛出验证错误
            raise
        except Exception as e:
            logger.error(
                "赛事媒体文件上传失败",
                media_type=command.media_type,
                filename=command.file.filename,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"文件上传失败: {str(e)}") from e


class DeleteFileUseCase(UseCase[DeleteFileCommand, bool]):
    """删除文件用例"""
    
    def __init__(self, file_service: FileStorageService):
        self.file_service = file_service
    
    async def execute(self, command: DeleteFileCommand) -> bool:
        """
        执行文件删除
        
        Args:
            command: 删除命令
            
        Returns:
            bool: 删除是否成功
        """
        logger.info(
            "开始删除文件",
            file_path=command.file_path,
            deleted_by=str(command.deleted_by)
        )
        
        try:
            result = await self.file_service.delete_file(command.file_path)
            
            if result:
                logger.info("文件删除成功", file_path=command.file_path)
            else:
                logger.warning("文件删除失败", file_path=command.file_path)
            
            return result
            
        except Exception as e:
            logger.error(
                "文件删除过程出错",
                file_path=command.file_path,
                error=str(e),
                exc_info=True
            )
            return False


# 工厂函数
def create_upload_tournament_media_use_case() -> UploadTournamentMediaUseCase:
    """创建上传赛事媒体文件用例实例"""
    file_service = FileStorageService()
    return UploadTournamentMediaUseCase(file_service)


def create_delete_file_use_case() -> DeleteFileUseCase:
    """创建删除文件用例实例"""
    file_service = FileStorageService()
    return DeleteFileUseCase(file_service)