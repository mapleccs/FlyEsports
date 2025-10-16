"""
英雄领域实体

定义英雄的领域模型，包含业务逻辑和规则。
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json


@dataclass
class ChampionSpell:
    """英雄技能"""
    id: str
    name: str
    description: str
    tooltip: str
    cooldown: List[float]
    cost: List[int]
    range: List[int]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChampionSpell':
        """从字典创建技能对象"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tooltip=data.get("tooltip", ""),
            cooldown=data.get("cooldown", []),
            cost=data.get("cost", []),
            range=data.get("range", [])
        )


@dataclass
class ChampionPassive:
    """英雄被动技能"""
    name: str
    description: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChampionPassive':
        """从字典创建被动技能对象"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )


@dataclass
class Champion:
    """英雄领域实体"""
    
    # 标识符
    id: Optional[str]
    champion_id: int
    key: str
    
    # 基础信息
    name: str
    title: str
    lore: Optional[str] = None
    blurb: Optional[str] = None
    
    # 分类和定位
    tags: List[str] = None
    partype: Optional[str] = None
    
    # 数值属性
    attack: int = 1
    defense: int = 1
    magic: int = 1
    difficulty: int = 1
    
    # 图片资源
    icon_url: Optional[str] = None
    splash_url: Optional[str] = None
    passive_icon_url: Optional[str] = None
    
    # 技能信息
    spells: List[ChampionSpell] = None
    passive: Optional[ChampionPassive] = None
    
    # 状态
    is_active: bool = True
    is_free_week: bool = False
    version: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.tags is None:
            self.tags = []
        if self.spells is None:
            self.spells = []
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.title:
            return f"{self.name}, {self.title}"
        return self.name
    
    @property
    def is_assassin(self) -> bool:
        """是否为刺客"""
        return "Assassin" in self.tags
    
    @property
    def is_fighter(self) -> bool:
        """是否为战士"""
        return "Fighter" in self.tags
    
    @property
    def is_mage(self) -> bool:
        """是否为法师"""
        return "Mage" in self.tags
    
    @property
    def is_marksman(self) -> bool:
        """是否为射手"""
        return "Marksman" in self.tags
    
    @property
    def is_support(self) -> bool:
        """是否为辅助"""
        return "Support" in self.tags
    
    @property
    def is_tank(self) -> bool:
        """是否为坦克"""
        return "Tank" in self.tags
    
    @property
    def primary_role(self) -> Optional[str]:
        """主要定位"""
        if not self.tags:
            return None
        return self.tags[0]
    
    @property
    def secondary_role(self) -> Optional[str]:
        """次要定位"""
        if len(self.tags) < 2:
            return None
        return self.tags[1]
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有指定标签"""
        return tag in self.tags
    
    def has_any_tags(self, tags: List[str]) -> bool:
        """检查是否有任一指定标签"""
        return any(tag in self.tags for tag in tags)
    
    def has_all_tags(self, tags: List[str]) -> bool:
        """检查是否有所有指定标签"""
        return all(tag in self.tags for tag in tags)
    
    def get_spell_by_slot(self, slot: str) -> Optional[ChampionSpell]:
        """根据技能位获取技能（Q/W/E/R）"""
        slot_mapping = {"Q": 0, "W": 1, "E": 2, "R": 3}
        index = slot_mapping.get(slot.upper())
        
        if index is not None and index < len(self.spells):
            return self.spells[index]
        return None
    
    def is_suitable_for_role(self, role: str) -> bool:
        """检查是否适合指定角色"""
        role_mappings = {
            "top": ["Fighter", "Tank", "Assassin"],
            "jungle": ["Fighter", "Assassin", "Tank"],
            "mid": ["Mage", "Assassin"],
            "adc": ["Marksman"],
            "support": ["Support", "Tank"]
        }
        
        suitable_tags = role_mappings.get(role.lower(), [])
        return self.has_any_tags(suitable_tags)
    
    def get_difficulty_text(self) -> str:
        """获取难度文本描述"""
        if self.difficulty <= 3:
            return "简单"
        elif self.difficulty <= 6:
            return "中等"
        elif self.difficulty <= 8:
            return "困难"
        else:
            return "极难"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Champion':
        """从字典创建英雄对象"""
        # 处理技能信息
        spells = []
        if data.get("spells"):
            if isinstance(data["spells"], str):
                try:
                    spells_data = json.loads(data["spells"])
                    spells = [ChampionSpell.from_dict(spell) for spell in spells_data]
                except (json.JSONDecodeError, TypeError):
                    spells = []
            elif isinstance(data["spells"], list):
                spells = [ChampionSpell.from_dict(spell) for spell in data["spells"]]
        
        # 处理被动技能
        passive = None
        if data.get("passive"):
            if isinstance(data["passive"], str):
                try:
                    passive_data = json.loads(data["passive"])
                    passive = ChampionPassive.from_dict(passive_data)
                except (json.JSONDecodeError, TypeError):
                    passive = None
            elif isinstance(data["passive"], dict):
                passive = ChampionPassive.from_dict(data["passive"])
        
        return cls(
            id=data.get("id"),
            champion_id=data.get("champion_id", 0),
            key=data.get("key", ""),
            name=data.get("name", ""),
            title=data.get("title", ""),
            lore=data.get("lore"),
            blurb=data.get("blurb"),
            tags=data.get("tags", []),
            partype=data.get("partype"),
            attack=data.get("attack", 1),
            defense=data.get("defense", 1),
            magic=data.get("magic", 1),
            difficulty=data.get("difficulty", 1),
            icon_url=data.get("icon_url"),
            splash_url=data.get("splash_url"),
            passive_icon_url=data.get("passive_icon_url"),
            spells=spells,
            passive=passive,
            is_active=data.get("is_active", True),
            is_free_week=data.get("is_free_week", False),
            version=data.get("version")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "champion_id": self.champion_id,
            "key": self.key,
            "name": self.name,
            "title": self.title,
            "display_name": self.display_name,
            "lore": self.lore,
            "blurb": self.blurb,
            "tags": self.tags,
            "partype": self.partype,
            "attack": self.attack,
            "defense": self.defense,
            "magic": self.magic,
            "difficulty": self.difficulty,
            "difficulty_text": self.get_difficulty_text(),
            "icon_url": self.icon_url,
            "splash_url": self.splash_url,
            "passive_icon_url": self.passive_icon_url,
            "spells": [spell.__dict__ for spell in self.spells] if self.spells else [],
            "passive": self.passive.__dict__ if self.passive else None,
            "is_active": self.is_active,
            "is_free_week": self.is_free_week,
            "version": self.version,
            "primary_role": self.primary_role,
            "secondary_role": self.secondary_role
        }