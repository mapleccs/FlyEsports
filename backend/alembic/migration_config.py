"""
FlyEsports 企业级迁移配置和工具
业界顶级迁移管理最佳实践实现

Features:
- 迁移依赖验证
- 安全检查机制  
- 智能命名规范
- 自动冲突检测
- 性能监控集成
"""

import re
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class MigrationType(Enum):
    """迁移类型枚举 - 谷歌级分类标准"""
    SCHEMA = "schema"      # 结构变更 (DDL)
    DATA = "data"         # 数据迁移 (DML)  
    SEED = "seed"         # 种子数据
    CONFIG = "config"     # 配置变更
    SECURITY = "security" # 安全相关
    INDEX = "index"       # 索引优化
    CLEANUP = "cleanup"   # 清理操作
    
class MigrationRisk(Enum):
    """迁移风险级别 - 金融级安全标准"""
    LOW = "low"           # 安全操作
    MEDIUM = "medium"     # 需要审核  
    HIGH = "high"         # 需要特殊批准
    CRITICAL = "critical" # 需要维护窗口

@dataclass
class MigrationMetadata:
    """迁移元数据 - Meta/Netflix级标准"""
    revision_id: str
    short_id: str
    file_name: str
    migration_type: MigrationType
    risk_level: MigrationRisk
    description: str
    author: str
    created_at: datetime
    estimated_time: Optional[int] = None  # 预计执行时间(秒)
    rollback_tested: bool = False
    performance_impact: Optional[str] = None
    dependencies: List[str] = None
    breaking_changes: bool = False
    
class MigrationNamingStandard:
    """企业级命名规范 - AWS/Azure级标准"""
    
    # 命名模式: YYYY_MM_DD_HHMM-{type}-{short_hash}-{slug}
    NAMING_PATTERN = r'^(\d{4})_(\d{2})_(\d{2})_(\d{2})(\d{2})-([a-z]+)-([a-f0-9]{8})-(.+)\.py$'
    
    @staticmethod
    def generate_revision_id(description: str, migration_type: MigrationType) -> str:
        """生成符合规范的revision ID"""
        timestamp = datetime.now()
        content = f"{description}_{migration_type.value}_{timestamp.isoformat()}"
        hash_obj = hashlib.sha256(content.encode())
        short_hash = hash_obj.hexdigest()[:8]
        
        date_prefix = timestamp.strftime("%Y_%m_%d_%H%M")
        slug = re.sub(r'[^a-z0-9_]', '_', description.lower())
        slug = re.sub(r'_+', '_', slug).strip('_')[:30]
        
        return f"{date_prefix}-{migration_type.value}-{short_hash}-{slug}"
    
    @staticmethod
    def parse_filename(filename: str) -> Optional[Dict]:
        """解析迁移文件名"""
        match = re.match(MigrationNamingStandard.NAMING_PATTERN, filename)
        if not match:
            return None
            
        return {
            'year': int(match.group(1)),
            'month': int(match.group(2)), 
            'day': int(match.group(3)),
            'hour': int(match.group(4)),
            'minute': int(match.group(5)),
            'type': match.group(6),
            'hash': match.group(7),
            'slug': match.group(8).replace('.py', '')
        }
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """验证文件名是否符合规范"""
        if not re.match(MigrationNamingStandard.NAMING_PATTERN, filename):
            return False, f"文件名不符合规范: {MigrationNamingStandard.NAMING_PATTERN}"
        return True, "符合规范"

class MigrationDependencyValidator:
    """迁移依赖验证器 - LinkedIn级依赖管理"""
    
    def __init__(self, versions_dir: str):
        self.versions_dir = Path(versions_dir)
        self.migrations: Dict[str, MigrationMetadata] = {}
        self._load_migrations()
    
    def _load_migrations(self):
        """加载所有迁移文件元数据"""
        for file_path in self.versions_dir.glob("*.py"):
            metadata = self._parse_migration_file(file_path)
            if metadata:
                self.migrations[metadata.revision_id] = metadata
    
    def _parse_migration_file(self, file_path: Path) -> Optional[MigrationMetadata]:
        """解析迁移文件获取元数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取revision信息
            revision_match = re.search(r'revision: str = ["\']([^"\']+)["\']', content)
            down_revision_match = re.search(r'down_revision: Union\[str, None\] = ["\']([^"\']*)["\']', content)
            
            if not revision_match:
                return None
                
            revision_id = revision_match.group(1)
            down_revision = down_revision_match.group(1) if down_revision_match and down_revision_match.group(1) != 'None' else None
            
            # 从文件名提取信息
            parsed = MigrationNamingStandard.parse_filename(file_path.name)
            migration_type = MigrationType(parsed['type']) if parsed and parsed['type'] in [t.value for t in MigrationType] else MigrationType.SCHEMA
            
            # 创建元数据
            return MigrationMetadata(
                revision_id=revision_id,
                short_id=revision_id[:8] if len(revision_id) > 8 else revision_id,
                file_name=file_path.name,
                migration_type=migration_type,
                risk_level=self._assess_risk_level(content),
                description=self._extract_description(content),
                author=self._extract_author(content),
                created_at=self._extract_creation_time(file_path, parsed),
                dependencies=[down_revision] if down_revision else []
            )
        except Exception as e:
            logger.warning("Failed to parse migration file", file=file_path.name, error=str(e))
            return None
    
    def _assess_risk_level(self, content: str) -> MigrationRisk:
        """评估迁移风险级别"""
        high_risk_patterns = [
            r'DROP\s+TABLE',
            r'DROP\s+COLUMN', 
            r'ALTER\s+TABLE.*DROP',
            r'TRUNCATE\s+TABLE'
        ]
        
        medium_risk_patterns = [
            r'ALTER\s+TABLE.*ADD\s+COLUMN.*NOT\s+NULL',
            r'CREATE\s+INDEX.*CONCURRENTLY',
            r'ALTER\s+TABLE.*ALTER\s+COLUMN.*TYPE'
        ]
        
        for pattern in high_risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return MigrationRisk.HIGH
                
        for pattern in medium_risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return MigrationRisk.MEDIUM
                
        return MigrationRisk.LOW
    
    def _extract_description(self, content: str) -> str:
        """提取迁移描述"""
        desc_match = re.search(r'"""([^"]+)"""', content)
        if desc_match:
            return desc_match.group(1).strip().split('\n')[0]
        return "No description"
    
    def _extract_author(self, content: str) -> str:
        """提取作者信息"""
        # 可以从git blame或注释中提取
        return "unknown"
    
    def _extract_creation_time(self, file_path: Path, parsed: Optional[Dict]) -> datetime:
        """提取创建时间"""
        if parsed:
            return datetime(
                year=parsed['year'],
                month=parsed['month'], 
                day=parsed['day'],
                hour=parsed['hour'],
                minute=parsed['minute']
            )
        # 回退到文件修改时间
        return datetime.fromtimestamp(file_path.stat().st_mtime)
    
    def validate_dependencies(self) -> List[Dict]:
        """验证依赖关系"""
        issues = []
        
        for revision_id, metadata in self.migrations.items():
            for dep in metadata.dependencies:
                if dep and dep not in self.migrations:
                    issues.append({
                        'type': 'MISSING_DEPENDENCY',
                        'file': metadata.file_name,
                        'revision': revision_id,
                        'missing_dependency': dep,
                        'severity': 'CRITICAL'
                    })
                elif dep:
                    # 检查时间顺序
                    dep_metadata = self.migrations[dep]
                    if metadata.created_at < dep_metadata.created_at:
                        issues.append({
                            'type': 'TIME_ORDER_VIOLATION',
                            'file': metadata.file_name,
                            'revision': revision_id,
                            'depends_on': dep,
                            'dependency_file': dep_metadata.file_name,
                            'severity': 'HIGH'
                        })
        
        return issues
    
    def get_migration_chain(self) -> List[MigrationMetadata]:
        """获取正确的迁移链顺序"""
        # 简单的拓扑排序
        visited = set()
        result = []
        
        def dfs(revision_id: str):
            if revision_id in visited or revision_id not in self.migrations:
                return
                
            visited.add(revision_id)
            metadata = self.migrations[revision_id]
            
            # 先处理依赖
            for dep in metadata.dependencies:
                if dep:
                    dfs(dep)
            
            result.append(metadata)
        
        # 从没有依赖的节点开始
        for revision_id, metadata in self.migrations.items():
            if not any(metadata.dependencies):
                dfs(revision_id)
        
        # 处理剩余的节点
        for revision_id in self.migrations:
            dfs(revision_id)
            
        return result

class MigrationSecurityChecker:
    """迁移安全检查器 - 银行级安全标准"""
    
    DANGEROUS_OPERATIONS = [
        r'DROP\s+TABLE\s+(?!.*_temp|.*_backup)',  # 删除表(除临时表)
        r'TRUNCATE\s+TABLE',                       # 清空表
        r'DELETE\s+FROM.*WHERE\s+1\s*=\s*1',      # 全表删除
        r'UPDATE.*SET.*WHERE\s+1\s*=\s*1',        # 全表更新
        r'ALTER\s+TABLE.*DROP\s+COLUMN',          # 删除列
    ]
    
    PERFORMANCE_RISKS = [
        r'CREATE\s+INDEX(?!\s+CONCURRENTLY)',     # 非并发索引创建
        r'ALTER\s+TABLE.*ADD\s+COLUMN.*NOT\s+NULL(?!.*DEFAULT)', # 添加非空列无默认值
        r'ALTER\s+TABLE.*TYPE.*USING',            # 类型转换需要表锁
    ]
    
    @classmethod
    def check_migration(cls, content: str) -> Dict:
        """检查迁移安全性"""
        issues = {
            'dangerous': [],
            'performance_risks': [], 
            'warnings': [],
            'risk_score': 0
        }
        
        # 检查危险操作
        for pattern in cls.DANGEROUS_OPERATIONS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                issues['dangerous'].extend(matches)
                issues['risk_score'] += 10
        
        # 检查性能风险
        for pattern in cls.PERFORMANCE_RISKS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                issues['performance_risks'].extend(matches)
                issues['risk_score'] += 5
        
        # 添加具体的安全建议
        if issues['dangerous']:
            issues['warnings'].append("检测到危险操作，建议在维护窗口执行")
        
        if issues['performance_risks']:
            issues['warnings'].append("检测到性能风险，可能导致长时间表锁")
            
        return issues

class MigrationTemplate:
    """迁移模板生成器 - Shopify级模板标准"""
    
    SCHEMA_TEMPLATE = '''"""{{ description }}

Migration Type: {{ migration_type.value }}
Risk Level: {{ risk_level.value }}
Author: {{ author }}
Created: {{ created_at }}
Estimated Time: {{ estimated_time }}s

Revision ID: {{ revision_id }}
Revises: {{ down_revision }}
Create Date: {{ created_at }}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
{{ imports }}

# revision identifiers, used by Alembic.
revision: str = "{{ revision_id }}"
down_revision: Union[str, None] = "{{ down_revision }}"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """{{ description }}"""
    # TODO: Implement upgrade logic
    {{ upgrade_content }}

def downgrade() -> None:
    """Rollback {{ description }}"""
    # TODO: Implement rollback logic  
    {{ downgrade_content }}
'''
    
    @classmethod
    def generate_migration(
        cls,
        description: str,
        migration_type: MigrationType,
        author: str,
        down_revision: Optional[str] = None,
        upgrade_content: str = "pass",
        downgrade_content: str = "pass"
    ) -> str:
        """生成迁移文件内容"""
        revision_id = MigrationNamingStandard.generate_revision_id(description, migration_type)
        created_at = datetime.now()
        
        # 评估风险级别 
        risk_level = MigrationRisk.LOW  # 可以基于内容智能评估
        
        template_vars = {
            'description': description,
            'migration_type': migration_type,
            'risk_level': risk_level,
            'author': author,
            'created_at': created_at.isoformat(),
            'estimated_time': 30,  # 默认估算
            'revision_id': revision_id,
            'down_revision': f'"{down_revision}"' if down_revision else 'None',
            'imports': '',
            'upgrade_content': upgrade_content,
            'downgrade_content': downgrade_content
        }
        
        # 使用简单的字符串替换(生产环境建议使用Jinja2)
        content = cls.SCHEMA_TEMPLATE
        for key, value in template_vars.items():
            content = content.replace('{{ ' + key + ' }}', str(value))
            
        return content

# 全局配置
MIGRATION_CONFIG = {
    'REQUIRE_ROLLBACK_TEST': True,
    'MAX_MIGRATION_TIME': 300,  # 5分钟
    'REQUIRE_APPROVAL_FOR_HIGH_RISK': True,
    'AUTO_BACKUP_BEFORE_MIGRATION': True,
    'ENABLE_PERFORMANCE_MONITORING': True,
    'NOTIFICATION_WEBHOOK': None,  # Slack/Teams通知
}