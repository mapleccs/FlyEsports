"""
英雄数据模型
存储英雄联盟的英雄信息，用于BP阶段的英雄选择
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel


class Champion(BaseModel):
    """英雄模型"""
    
    __tablename__ = "champions"
    
    # 英雄唯一标识符
    champion_id = Column(Integer, unique=True, nullable=False, comment="英雄ID")
    
    # 基础信息
    key = Column(String(50), unique=True, nullable=False, comment="英雄唯一键名")
    name = Column(String(100), nullable=False, comment="英雄名称")
    title = Column(String(200), nullable=False, comment="英雄称号")
    
    # 描述信息
    lore = Column(Text, comment="英雄背景故事")
    blurb = Column(Text, comment="英雄简介")
    
    # 标签和定位
    tags = Column(ARRAY(String), comment="英雄标签")
    partype = Column(String(50), comment="资源类型 (法力、能量等)")
    
    # 数值属性
    attack = Column(Integer, default=1, comment="攻击力")
    defense = Column(Integer, default=1, comment="防御力")
    magic = Column(Integer, default=1, comment="法术强度")
    difficulty = Column(Integer, default=1, comment="难度等级")
    
    # 图片资源
    icon_url = Column(String(500), comment="头像图片URL")
    splash_url = Column(String(500), comment="加载界面图片URL")
    passive_icon_url = Column(String(500), comment="被动技能图标URL")
    
    # 技能信息（JSON格式存储）
    spells = Column(Text, comment="技能信息JSON")
    passive = Column(Text, comment="被动技能信息JSON")
    
    # 状态标识
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_free_week = Column(Boolean, default=False, comment="是否为免费周英雄")
    
    # 版本信息
    version = Column(String(20), comment="英雄数据版本")
    
    def __repr__(self) -> str:
        return f"<Champion(id={self.champion_id}, key='{self.key}', name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": str(self.id),  # 数据库主键ID，转换为字符串
            "champion_id": self.champion_id,  # 英雄游戏内ID
            "key": self.key,
            "name": self.name,
            "title": self.title,
            "lore": self.lore,
            "blurb": self.blurb,
            "tags": self.tags,
            "partype": self.partype,
            "attack": self.attack,
            "defense": self.defense,
            "magic": self.magic,
            "difficulty": self.difficulty,
            "icon_url": self.icon_url,
            "splash_url": self.splash_url,
            "passive_icon_url": self.passive_icon_url,
            "spells": self.spells,
            "passive": self.passive,
            "is_active": self.is_active,
            "is_free_week": self.is_free_week,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }