"""字典表管理API"""

from typing import Dict, List, Optional, Any
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel, Field

from src.infrastructure.services.dictionary_service import DictionaryService
from src.presentation.dependencies.dictionary import get_dictionary_service
from src.presentation.dependencies.auth import get_current_user
from src.presentation.dependencies.permission import (
    verify_permission,
    get_permission_checker,
    PermissionChecker,
)
from src.domain.entities.user import User
from src.domain.value_objects.role import PermissionAction, PermissionResource


router = APIRouter()
logger = structlog.get_logger(__name__)


# Pydantic 模型
class DictItemResponse(BaseModel):
    """字典项响应模型"""
    id: int
    code: str
    name: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool


class DictItemCreate(BaseModel):
    """创建字典项请求模型"""
    code: str = Field(..., min_length=1, max_length=50, description="代码值")
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    sort_order: Optional[int] = Field(None, ge=0, description="排序号")


class DictItemUpdate(BaseModel):
    """更新字典项请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="名称")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    sort_order: Optional[int] = Field(None, ge=0, description="排序号")
    is_active: Optional[bool] = Field(None, description="是否激活")


class DictionaryListResponse(BaseModel):
    """字典表列表响应模型"""
    dictionaries: List[str] = Field(..., description="字典表名称列表")


class DictItemListResponse(BaseModel):
    """字典项列表响应模型"""
    items: Dict[str, DictItemResponse] = Field(..., description="字典项映射")
    total_count: int = Field(..., description="总数量")


@router.get("/health")
async def dictionaries_health():
    """健康检查"""
    return {"status": "Dictionaries service is healthy"}


@router.get(
    "/",
    response_model=DictionaryListResponse,
    summary="获取所有字典表名称",
    description="获取系统中所有可用的字典表名称列表"
)
async def get_dictionaries(
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """获取所有字典表名称"""
    # 检查权限：需要管理员权限才能访问字典管理
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.READ
    )

    try:
        dictionaries = list(dictionary_service.DICT_MODELS.keys())
        return DictionaryListResponse(dictionaries=dictionaries)
    except Exception as e:
        logger.error(
            "获取字典表列表失败",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取字典表列表失败: {str(e)}"
        )


@router.get(
    "/{dict_name}",
    response_model=DictItemListResponse,
    summary="获取字典表的所有项",
    description="获取指定字典表的所有项目"
)
async def get_dictionary_items(
    dict_name: str,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """获取字典表的所有项"""
    # 检查权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.READ
    )

    try:
        items_dict = await dictionary_service.get_all_dict_items(dict_name)

        # 转换为响应模型
        response_items = {}
        for code, item_data in items_dict.items():
            response_items[code] = DictItemResponse(**item_data)

        return DictItemListResponse(
            items=response_items,
            total_count=len(response_items)
        )

    except ValueError as e:
        logger.warning(
            "字典表不存在",
            dict_name=dict_name,
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"字典表 '{dict_name}' 不存在"
        )
    except Exception as e:
        logger.error(
            "获取字典项失败",
            dict_name=dict_name,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取字典项失败: {str(e)}"
        )


@router.get(
    "/{dict_name}/{code}",
    response_model=DictItemResponse,
    summary="获取单个字典项",
    description="根据代码获取指定字典表的单个项目"
)
async def get_dictionary_item(
    dict_name: str,
    code: str,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """获取单个字典项"""
    # 检查权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.READ
    )

    try:
        item_data = await dictionary_service.get_dict_item(dict_name, code)

        if not item_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典项 '{code}' 在字典表 '{dict_name}' 中不存在"
            )

        return DictItemResponse(**item_data)

    except ValueError as e:
        logger.warning(
            "字典表不存在",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"字典表 '{dict_name}' 不存在"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取字典项失败",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取字典项失败: {str(e)}"
        )


@router.post(
    "/{dict_name}",
    response_model=DictItemResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建字典项",
    description="在指定字典表中创建新的项目"
)
async def create_dictionary_item(
    dict_name: str,
    item_data: DictItemCreate,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """创建字典项"""
    # 检查权限：需要管理员写权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.CREATE
    )

    try:
        created_item = await dictionary_service.create_dict_item(
            dict_name=dict_name,
            code=item_data.code,
            name=item_data.name,
            display_name=item_data.display_name,
            description=item_data.description,
            sort_order=item_data.sort_order
        )

        logger.info(
            "字典项创建成功",
            dict_name=dict_name,
            code=item_data.code,
            user_id=current_user.id,
            item_id=created_item['id']
        )

        return DictItemResponse(**created_item)

    except ValueError as e:
        logger.warning(
            "字典项创建失败",
            dict_name=dict_name,
            code=item_data.code,
            user_id=current_user.id,
            error=str(e)
        )

        if "already exists" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        elif "Unknown dictionary" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典表 '{dict_name}' 不存在"
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(
            "字典项创建失败",
            dict_name=dict_name,
            code=item_data.code,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字典项创建失败: {str(e)}"
        )


@router.put(
    "/{dict_name}/{code}",
    response_model=DictItemResponse,
    summary="更新字典项",
    description="更新指定字典表中的项目"
)
async def update_dictionary_item(
    dict_name: str,
    code: str,
    item_data: DictItemUpdate,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """更新字典项"""
    # 检查权限：需要管理员写权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.UPDATE
    )

    try:
        # 过滤掉 None 值的更新数据
        updates = {k: v for k, v in item_data.dict().items() if v is not None}

        if not updates:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="没有提供要更新的数据"
            )

        updated_item = await dictionary_service.update_dict_item(
            dict_name=dict_name,
            code=code,
            **updates
        )

        if not updated_item:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典项 '{code}' 在字典表 '{dict_name}' 中不存在"
            )

        logger.info(
            "字典项更新成功",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            updates=updates
        )

        return DictItemResponse(**updated_item)

    except ValueError as e:
        logger.warning(
            "字典项更新失败",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e)
        )

        if "Unknown dictionary" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典表 '{dict_name}' 不存在"
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "字典项更新失败",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字典项更新失败: {str(e)}"
        )


@router.delete(
    "/{dict_name}/{code}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="停用字典项",
    description="停用指定字典表中的项目（软删除）"
)
async def deactivate_dictionary_item(
    dict_name: str,
    code: str,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """停用字典项（软删除）"""
    # 检查权限：需要管理员删除权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.DELETE
    )

    try:
        success = await dictionary_service.deactivate_dict_item(dict_name, code)

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典项 '{code}' 在字典表 '{dict_name}' 中不存在"
            )

        logger.info(
            "字典项停用成功",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id
        )

    except ValueError as e:
        logger.warning(
            "字典项停用失败",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e)
        )

        if "Unknown dictionary" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典表 '{dict_name}' 不存在"
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "字典项停用失败",
            dict_name=dict_name,
            code=code,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字典项停用失败: {str(e)}"
        )


@router.post(
    "/{dict_name}/refresh",
    status_code=http_status.HTTP_200_OK,
    summary="刷新字典缓存",
    description="刷新指定字典表的缓存"
)
async def refresh_dictionary_cache(
    dict_name: str,
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """刷新字典缓存"""
    # 检查权限：需要管理员权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.UPDATE
    )

    try:
        await dictionary_service.refresh_cache(dict_name)

        logger.info(
            "字典缓存刷新成功",
            dict_name=dict_name,
            user_id=current_user.id
        )

        return {"message": f"字典表 '{dict_name}' 缓存已刷新"}

    except ValueError as e:
        logger.warning(
            "字典缓存刷新失败",
            dict_name=dict_name,
            user_id=current_user.id,
            error=str(e)
        )

        if "Unknown dictionary" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"字典表 '{dict_name}' 不存在"
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(
            "字典缓存刷新失败",
            dict_name=dict_name,
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字典缓存刷新失败: {str(e)}"
        )


@router.post(
    "/refresh-all",
    status_code=http_status.HTTP_200_OK,
    summary="刷新所有字典缓存",
    description="刷新所有字典表的缓存"
)
async def refresh_all_dictionaries_cache(
    current_user: User = Depends(get_current_user),
    checker: PermissionChecker = Depends(get_permission_checker),
    dictionary_service: DictionaryService = Depends(get_dictionary_service),
):
    """刷新所有字典缓存"""
    # 检查权限：需要管理员权限
    await checker.require_permission(
        PermissionResource.ADMIN,
        PermissionAction.UPDATE
    )

    try:
        await dictionary_service.refresh_cache()

        logger.info(
            "所有字典缓存刷新成功",
            user_id=current_user.id
        )

        return {"message": "所有字典表缓存已刷新"}

    except Exception as e:
        logger.error(
            "所有字典缓存刷新失败",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"字典缓存刷新失败: {str(e)}"
        )