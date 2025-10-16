"""
英雄数据API路由
提供英雄信息的CRUD操作和查询功能
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...dependencies.auth import get_current_user
from ....domain.entities.user import User
from ....infrastructure.database.connection import database_manager
from ....infrastructure.database.models.champion import Champion

router = APIRouter(prefix="/champions", tags=["英雄数据"])

# Pydantic 模型

class ChampionBase(BaseModel):
    """英雄基础信息"""
    champion_id: int = Field(..., description="英雄ID")
    key: str = Field(..., description="英雄唯一键名")
    name: str = Field(..., description="英雄名称")
    title: str = Field(..., description="英雄称号")
    lore: Optional[str] = Field(None, description="背景故事")
    blurb: Optional[str] = Field(None, description="简介")
    tags: Optional[List[str]] = Field(None, description="英雄标签")
    partype: Optional[str] = Field(None, description="资源类型")
    attack: int = Field(1, description="攻击力")
    defense: int = Field(1, description="防御力")
    magic: int = Field(1, description="法术强度")
    difficulty: int = Field(1, description="难度等级")
    icon_url: Optional[str] = Field(None, description="头像URL")
    splash_url: Optional[str] = Field(None, description="加载界面URL")
    passive_icon_url: Optional[str] = Field(None, description="被动图标URL")
    spells: Optional[str] = Field(None, description="技能信息JSON")
    passive: Optional[str] = Field(None, description="被动技能JSON")
    is_active: bool = Field(True, description="是否启用")
    is_free_week: bool = Field(False, description="是否免费周")
    version: Optional[str] = Field(None, description="版本")

class ChampionCreate(ChampionBase):
    """创建英雄"""
    pass

class ChampionUpdate(BaseModel):
    """更新英雄"""
    key: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    lore: Optional[str] = None
    blurb: Optional[str] = None
    tags: Optional[List[str]] = None
    partype: Optional[str] = None
    attack: Optional[int] = None
    defense: Optional[int] = None
    magic: Optional[int] = None
    difficulty: Optional[int] = None
    icon_url: Optional[str] = None
    splash_url: Optional[str] = None
    passive_icon_url: Optional[str] = None
    spells: Optional[str] = None
    passive: Optional[str] = None
    is_active: Optional[bool] = None
    is_free_week: Optional[bool] = None
    version: Optional[str] = None

class ChampionResponse(ChampionBase):
    """英雄响应"""
    id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# API端点

@router.get("/")
async def get_champions(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔"),
    active_only: bool = Query(True, description="仅返回启用的英雄"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    获取英雄列表
    
    - **skip**: 跳过数量
    - **limit**: 返回数量
    - **search**: 搜索英雄名称或称号
    - **tags**: 按标签过滤
    - **active_only**: 仅返回启用的英雄
    """
    try:
        async with database_manager.get_session() as session:
            query = select(Champion)
            
            # 活跃状态过滤
            if active_only:
                query = query.where(Champion.is_active == True)
            
            # 搜索过滤
            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    Champion.name.ilike(search_filter) | 
                    Champion.title.ilike(search_filter) |
                    Champion.key.ilike(search_filter)
                )
            
            # 标签过滤
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",")]
                # 使用PostgreSQL的数组操作符
                from sqlalchemy import func
                query = query.where(func.array_length(Champion.tags, 1) > 0)
                for tag in tag_list:
                    query = query.where(Champion.tags.contains([tag]))
            
            # 分页
            query = query.offset(skip).limit(limit)
            
            result = await session.execute(query)
            champions = result.scalars().all()
            
            return [champion.to_dict() for champion in champions]
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取英雄列表失败: {str(e)}"
        )

@router.get("/{champion_id}")
async def get_champion(
    champion_id: int,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取单个英雄信息
    
    - **champion_id**: 英雄ID
    """
    try:
        async with database_manager.get_session() as session:
            result = await session.execute(
                select(Champion).where(Champion.champion_id == champion_id)
            )
            champion = result.scalar_one_or_none()
            
            if not champion:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="英雄不存在"
                )
            
            return champion.to_dict()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取英雄信息失败: {str(e)}"
        )

@router.post("/", response_model=ChampionResponse)
async def create_champion(
    champion_data: ChampionCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    创建英雄
    
    需要管理员权限
    """
    try:
        # TODO: 验证管理员权限
        
        async with database_manager.get_session() as session:
            # 检查英雄ID是否已存在
            existing = await session.execute(
                select(Champion).where(Champion.champion_id == champion_data.champion_id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="英雄ID已存在"
                )
            
            # 检查英雄key是否已存在
            existing_key = await session.execute(
                select(Champion).where(Champion.key == champion_data.key)
            )
            if existing_key.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="英雄key已存在"
                )
            
            # 创建英雄
            champion = Champion(**champion_data.model_dump())
            session.add(champion)
            await session.commit()
            await session.refresh(champion)
            
            return champion.to_dict()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建英雄失败: {str(e)}"
        )

@router.put("/{champion_id}", response_model=ChampionResponse)
async def update_champion(
    champion_id: int,
    champion_data: ChampionUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    更新英雄信息
    
    需要管理员权限
    """
    try:
        # TODO: 验证管理员权限
        
        async with database_manager.get_session() as session:
            result = await session.execute(
                select(Champion).where(Champion.champion_id == champion_id)
            )
            champion = result.scalar_one_or_none()
            
            if not champion:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="英雄不存在"
                )
            
            # 更新字段
            update_data = champion_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(champion, field, value)
            
            await session.commit()
            await session.refresh(champion)
            
            return champion.to_dict()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新英雄失败: {str(e)}"
        )

@router.delete("/{champion_id}")
async def delete_champion(
    champion_id: int,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    删除英雄
    
    需要管理员权限
    """
    try:
        # TODO: 验证管理员权限
        
        async with database_manager.get_session() as session:
            result = await session.execute(
                select(Champion).where(Champion.champion_id == champion_id)
            )
            champion = result.scalar_one_or_none()
            
            if not champion:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="英雄不存在"
                )
            
            await session.delete(champion)
            await session.commit()
            
            return {"success": True, "message": "英雄删除成功"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除英雄失败: {str(e)}"
        )

@router.post("/batch", response_model=Dict[str, Any])
async def batch_create_champions(
    champions_data: List[ChampionCreate],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    批量创建英雄
    
    需要管理员权限
    """
    try:
        # TODO: 验证管理员权限
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        async with database_manager.get_session() as session:
            for champion_data in champions_data:
                try:
                    # 检查是否已存在
                    existing = await session.execute(
                        select(Champion).where(
                            and_(
                                Champion.champion_id == champion_data.champion_id,
                                Champion.key == champion_data.key
                            )
                        )
                    )
                    
                    if existing.scalar_one_or_none():
                        skipped_count += 1
                        continue
                    
                    # 创建英雄
                    champion = Champion(**champion_data.model_dump())
                    session.add(champion)
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"英雄 {champion_data.name} 创建失败: {str(e)}")
                    continue
            
            await session.commit()
            
            return {
                "success": True,
                "created_count": created_count,
                "skipped_count": skipped_count,
                "errors": errors,
                "message": f"批量创建完成: 新增{created_count}个，跳过{skipped_count}个"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量创建英雄失败: {str(e)}"
        )