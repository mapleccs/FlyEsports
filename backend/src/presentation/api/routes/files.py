"""文件管理API路由"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi import status as http_status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import structlog

from ....application.use_cases.file_upload import (
    UploadTournamentMediaCommand,
    UploadTournamentMediaUseCase,
    DeleteFileCommand,
    DeleteFileUseCase,
    create_upload_tournament_media_use_case,
    create_delete_file_use_case,
)
from ....infrastructure.services.file_service import FileStorageService
from ...dependencies.auth import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["文件管理"])


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str = Field(..., description="文件唯一标识")
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="文件访问URL")
    size: int = Field(..., description="文件大小(字节)")
    content_type: str = Field(..., description="文件MIME类型")
    width: int = Field(0, description="图片宽度")
    height: int = Field(0, description="图片高度")
    format: str = Field(..., description="图片格式")
    hash: str = Field(..., description="文件SHA256哈希值")


class FileDeleteResponse(BaseModel):
    """文件删除响应模型"""
    success: bool = Field(..., description="删除是否成功")
    message: str = Field(..., description="响应消息")


@router.post(
    "/tournament-media/upload",
    response_model=FileUploadResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="上传赛事媒体文件",
    description="上传赛事Logo或横幅图片，支持JPEG、PNG、GIF、WebP格式"
)
async def upload_tournament_media(
    file: UploadFile = File(..., description="要上传的图片文件"),
    media_type: str = Form(..., description="媒体类型: logo 或 banner"),
    tournament_id: Optional[str] = Form(None, description="赛事ID(可选)"),
    current_user = Depends(get_current_user),
    upload_use_case: UploadTournamentMediaUseCase = Depends(create_upload_tournament_media_use_case),
):
    """
    上传赛事媒体文件
    
    - **file**: 图片文件 (最大10MB)
    - **media_type**: 媒体类型 ('logo' 或 'banner')
    - **tournament_id**: 赛事ID (可选，用于关联特定赛事)
    
    支持的格式: JPEG, PNG, GIF, WebP
    """
    try:
        # 验证媒体类型
        if media_type not in ["logo", "banner"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的媒体类型: {media_type}"
            )
        
        # 构建上传命令
        tournament_uuid = UUID(tournament_id) if tournament_id else None
        command = UploadTournamentMediaCommand(
            file=file,
            media_type=media_type,
            uploaded_by=UUID(str(current_user)),  # 假设current_user是用户ID
            tournament_id=tournament_uuid
        )
        
        # 执行上传
        result = await upload_use_case.execute(command)
        
        # 返回结果
        return FileUploadResponse(
            file_id=result.file_id,
            filename=result.filename,
            url=result.url,
            size=result.size,
            content_type=result.content_type,
            width=result.width,
            height=result.height,
            format=result.format,
            hash=result.hash
        )
        
    except ValueError as e:
        logger.warning("文件上传验证失败", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "文件上传失败",
            error=str(e),
            user_id=str(current_user.id),
            media_type=media_type,
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败，请稍后重试"
        )


@router.delete(
    "/{file_path:path}",
    response_model=FileDeleteResponse,
    status_code=http_status.HTTP_200_OK,
    summary="删除文件",
    description="删除指定路径的文件"
)
async def delete_file(
    file_path: str,
    current_user = Depends(get_current_user),
    delete_use_case: DeleteFileUseCase = Depends(create_delete_file_use_case),
):
    """
    删除文件
    
    - **file_path**: 文件相对路径
    
    需要管理员权限或文件所有者权限
    """
    try:
        # 构建删除命令
        command = DeleteFileCommand(
            file_path=file_path,
            deleted_by=UUID(str(current_user))
        )
        
        # 执行删除
        result = await delete_use_case.execute(command)
        
        if result:
            return FileDeleteResponse(
                success=True,
                message="文件删除成功"
            )
        else:
            return FileDeleteResponse(
                success=False,
                message="文件不存在或删除失败"
            )
            
    except Exception as e:
        logger.error(
            "文件删除失败",
            error=str(e),
            user_id=str(current_user.id),
            file_path=file_path,
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件删除失败，请稍后重试"
        )


@router.get(
    "/{file_path:path}",
    response_class=FileResponse,
    summary="获取文件",
    description="获取指定路径的文件内容"
)
async def get_file(file_path: str):
    """
    获取文件内容
    
    - **file_path**: 文件相对路径
    
    返回文件的二进制内容
    """
    try:
        file_service = FileStorageService()
        full_path = file_service.get_full_path(file_path)
        
        if not full_path.exists():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 根据文件扩展名设置媒体类型
        media_type = "application/octet-stream"
        if full_path.suffix.lower() in ['.jpg', '.jpeg']:
            media_type = "image/jpeg"
        elif full_path.suffix.lower() == '.png':
            media_type = "image/png"
        elif full_path.suffix.lower() == '.gif':
            media_type = "image/gif"
        elif full_path.suffix.lower() == '.webp':
            media_type = "image/webp"
        
        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            filename=full_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "文件访问失败",
            error=str(e),
            file_path=file_path,
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件访问失败"
        )


@router.get(
    "/tournament-media/presets",
    response_model=List[dict],
    summary="获取预设媒体素材",
    description="获取可用的预设Logo和横幅图片列表"
)
async def get_tournament_media_presets():
    """
    获取预设媒体素材列表
    
    返回可用的预设Logo和横幅图片
    """
    try:
        # 这里可以从配置文件或数据库中读取预设素材
        presets = {
            "logos": [
                {
                    "id": "default-logo-1",
                    "name": "默认Logo 1",
                    "url": "/api/v1/files/presets/logos/default-1.png",
                    "thumbnail": "/api/v1/files/presets/logos/thumbnails/default-1.png"
                },
                {
                    "id": "default-logo-2", 
                    "name": "默认Logo 2",
                    "url": "/api/v1/files/presets/logos/default-2.png",
                    "thumbnail": "/api/v1/files/presets/logos/thumbnails/default-2.png"
                }
            ],
            "banners": [
                {
                    "id": "default-banner-1",
                    "name": "默认横幅 1",
                    "url": "/api/v1/files/presets/banners/default-1.jpg",
                    "thumbnail": "/api/v1/files/presets/banners/thumbnails/default-1.jpg"
                },
                {
                    "id": "default-banner-2",
                    "name": "默认横幅 2",
                    "url": "/api/v1/files/presets/banners/default-2.jpg",
                    "thumbnail": "/api/v1/files/presets/banners/thumbnails/default-2.jpg"
                }
            ]
        }
        
        return presets
        
    except Exception as e:
        logger.error("获取预设素材失败", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取预设素材失败"
        )