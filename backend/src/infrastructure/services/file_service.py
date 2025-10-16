"""文件服务基础设施实现"""

import os
import uuid
import hashlib
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from datetime import datetime

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from fastapi import UploadFile
import structlog

from ...core.config import settings

logger = structlog.get_logger(__name__)


class FileStorageService:
    """文件存储服务"""
    
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.tournament_media_dir = self.upload_dir / "tournaments"
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保上传目录存在"""
        self.upload_dir.mkdir(exist_ok=True)
        self.tournament_media_dir.mkdir(exist_ok=True)
        (self.tournament_media_dir / "logos").mkdir(exist_ok=True)
        (self.tournament_media_dir / "banners").mkdir(exist_ok=True)
    
    async def save_tournament_media(
        self, 
        file: UploadFile, 
        media_type: str,
        tournament_id: Optional[str] = None
    ) -> Tuple[str, dict]:
        """
        保存赛事媒体文件
        
        Args:
            file: 上传的文件
            media_type: 媒体类型 ('logo' 或 'banner')
            tournament_id: 赛事ID (可选)
        
        Returns:
            Tuple[str, dict]: (文件路径, 文件信息)
        """
        # 验证文件类型
        if not self._is_valid_image(file.content_type):
            raise ValueError(f"不支持的文件类型: {file.content_type}")
        
        # 验证文件大小
        file_size = await self._get_file_size(file)
        if file_size > settings.max_file_size_bytes:
            raise ValueError(
                f"文件大小超限: {file_size} bytes > {settings.max_file_size_bytes} bytes"
            )
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = self._get_file_extension(file.filename)
        filename = f"{file_id}{file_extension}"
        
        # 确定存储路径
        media_dir = self.tournament_media_dir / media_type
        file_path = media_dir / filename
        
        # 保存原始文件
        await self._save_file(file, file_path)
        
        # 处理图片
        processed_info = await self._process_image(file_path, media_type)
        
        # 计算文件哈希
        file_hash = await self._calculate_file_hash(file_path)
        
        # 构建文件信息
        file_info = {
            "id": file_id,
            "original_name": file.filename,
            "filename": filename,
            "path": str(file_path.relative_to(self.upload_dir)),
            "url": f"/api/v1/files/{media_type}/{filename}",
            "size": file_size,
            "content_type": file.content_type,
            "hash": file_hash,
            "created_at": datetime.utcnow().isoformat(),
            "tournament_id": tournament_id,
            **processed_info
        }
        
        logger.info(
            "文件保存成功",
            file_id=file_id,
            filename=filename,
            size=file_size,
            content_type=file.content_type
        )
        
        return str(file_path.relative_to(self.upload_dir)), file_info
    
    async def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 相对文件路径
        
        Returns:
            bool: 删除是否成功
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info("文件删除成功", file_path=file_path)
                return True
            else:
                logger.warning("文件不存在", file_path=file_path)
                return False
        except Exception as e:
            logger.error("文件删除失败", file_path=file_path, error=str(e))
            return False
    
    def _is_valid_image(self, content_type: Optional[str]) -> bool:
        """验证是否为有效的图片类型"""
        if not content_type:
            return False
        
        allowed_types = [
            "image/jpeg",
            "image/png", 
            "image/gif",
            "image/webp"
        ]
        return content_type in allowed_types
    
    def _get_file_extension(self, filename: Optional[str]) -> str:
        """获取文件扩展名"""
        if not filename:
            return ".jpg"
        
        return Path(filename).suffix.lower() or ".jpg"
    
    async def _get_file_size(self, file: UploadFile) -> int:
        """获取文件大小"""
        # 保存当前位置
        current_position = file.file.tell()
        
        # 移动到文件末尾获取大小
        file.file.seek(0, 2)
        size = file.file.tell()
        
        # 恢复原始位置
        file.file.seek(current_position)
        
        return size
    
    async def _save_file(self, file: UploadFile, file_path: Path) -> None:
        """保存文件到磁盘"""
        if HAS_AIOFILES:
            # 使用aiofiles异步写入
            async with aiofiles.open(file_path, "wb") as f:
                # 重置文件指针
                await file.seek(0)
                
                # 分块读取并写入
                while chunk := await file.read(8192):
                    await f.write(chunk)
        else:
            # 回退到同步文件操作
            await file.seek(0)
            with open(file_path, "wb") as f:
                while chunk := await file.read(8192):
                    f.write(chunk)
    
    async def _process_image(self, file_path: Path, media_type: str) -> dict:
        """
        处理图片文件
        
        Args:
            file_path: 图片文件路径
            media_type: 媒体类型
        
        Returns:
            dict: 处理后的图片信息
        """
        if not HAS_PIL:
            # 如果没有PIL，返回基本信息
            logger.warning("PIL (Pillow) not available, skipping image processing")
            return {
                "width": 0,
                "height": 0,
                "format": "UNKNOWN",
                "aspect_ratio": 0,
            }
        
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format_name = img.format
                
                # 根据媒体类型设置不同的处理规则
                if media_type == "logo":
                    # Logo建议为正方形，最大尺寸512x512
                    max_size = 512
                    if width > max_size or height > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        img.save(file_path, optimize=True, quality=90)
                        width, height = img.size
                        
                elif media_type == "banner":
                    # Banner建议为16:9比例，最大尺寸1920x1080
                    max_width, max_height = 1920, 1080
                    if width > max_width or height > max_height:
                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                        img.save(file_path, optimize=True, quality=90)
                        width, height = img.size
                
                return {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "aspect_ratio": round(width / height, 2) if height > 0 else 0,
                }
                
        except Exception as e:
            logger.error("图片处理失败", file_path=str(file_path), error=str(e))
            # 即使处理失败也返回基本信息
            return {
                "width": 0,
                "height": 0,
                "format": "UNKNOWN",
                "aspect_ratio": 0,
            }
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件SHA256哈希值"""
        hash_sha256 = hashlib.sha256()
        
        if HAS_AIOFILES:
            async with aiofiles.open(file_path, "rb") as f:
                while chunk := await f.read(8192):
                    hash_sha256.update(chunk)
        else:
            # 回退到同步文件操作
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def get_file_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        return f"/api/v1/files/{file_path}"
    
    def get_full_path(self, file_path: str) -> Path:
        """获取文件完整路径"""
        return self.upload_dir / file_path