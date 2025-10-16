#!/usr/bin/env python3
"""
FlyEsports 企业级迁移管理CLI工具
业界顶级迁移管理实践 - 支持Google/Meta/Netflix级别的迁移操作

Usage:
    python migration_manager.py validate     # 验证所有迁移
    python migration_manager.py create       # 创建新迁移
    python migration_manager.py fix-chain    # 修复依赖链
    python migration_manager.py lint         # 代码检查
    python migration_manager.py test         # 测试迁移
"""

import sys
import os
import json
import click
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import structlog

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent))

from migration_config import (
    MigrationDependencyValidator,
    MigrationSecurityChecker, 
    MigrationTemplate,
    MigrationType,
    MigrationRisk,
    MigrationNamingStandard,
    MIGRATION_CONFIG
)

logger = structlog.get_logger(__name__)

class MigrationManager:
    """企业级迁移管理器"""
    
    def __init__(self, alembic_dir: str = "alembic"):
        self.alembic_dir = Path(alembic_dir)
        self.versions_dir = self.alembic_dir / "versions"
        self.validator = MigrationDependencyValidator(str(self.versions_dir))
        
    def validate_migrations(self) -> Dict:
        """验证所有迁移 - Uber级验证标准"""
        print("🔍 开始验证迁移文件...")
        
        results = {
            'total_migrations': len(self.validator.migrations),
            'issues': [],
            'warnings': [],
            'security_alerts': [],
            'performance_risks': [],
            'naming_violations': []
        }
        
        # 1. 依赖关系验证
        dependency_issues = self.validator.validate_dependencies()
        results['issues'].extend(dependency_issues)
        
        # 2. 命名规范检查
        for file_path in self.versions_dir.glob("*.py"):
            is_valid, message = MigrationNamingStandard.validate_filename(file_path.name)
            if not is_valid:
                results['naming_violations'].append({
                    'file': file_path.name,
                    'issue': message
                })
        
        # 3. 安全检查
        for revision_id, metadata in self.validator.migrations.items():
            file_path = self.versions_dir / metadata.file_name
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            security_check = MigrationSecurityChecker.check_migration(content)
            if security_check['risk_score'] > 5:
                results['security_alerts'].append({
                    'file': metadata.file_name,
                    'risk_score': security_check['risk_score'],
                    'issues': security_check
                })
        
        # 打印结果
        self._print_validation_results(results)
        return results
    
    def _print_validation_results(self, results: Dict):
        """美化输出验证结果"""
        print(f"\n📊 验证报告 - 共{results['total_migrations']}个迁移文件")
        print("=" * 60)
        
        if results['issues']:
            print("❌ 依赖关系问题:")
            for issue in results['issues']:
                severity_emoji = "🚨" if issue['severity'] == 'CRITICAL' else "⚠️"
                print(f"  {severity_emoji} {issue['type']}: {issue['file']}")
                if 'missing_dependency' in issue:
                    print(f"      缺少依赖: {issue['missing_dependency']}")
                elif 'dependency_file' in issue:
                    print(f"      依赖文件: {issue['dependency_file']}")
        
        if results['naming_violations']:
            print("\n📝 命名规范违反:")
            for violation in results['naming_violations']:
                print(f"  ❌ {violation['file']}: {violation['issue']}")
        
        if results['security_alerts']:
            print("\n🛡️ 安全警告:")
            for alert in results['security_alerts']:
                print(f"  ⚠️ {alert['file']} (风险分数: {alert['risk_score']})")
                for dangerous in alert['issues']['dangerous']:
                    print(f"      🔴 危险操作: {dangerous}")
                for risk in alert['issues']['performance_risks']:
                    print(f"      🟡 性能风险: {risk}")
        
        # 总结
        total_issues = len(results['issues']) + len(results['naming_violations']) + len(results['security_alerts'])
        if total_issues == 0:
            print("\n✅ 所有检查通过! 迁移系统状态良好.")
        else:
            print(f"\n⚠️ 发现 {total_issues} 个问题需要修复.")
    
    def create_migration(
        self,
        description: str,
        migration_type: str = "schema",
        author: str = "developer",
        auto_generate: bool = False
    ):
        """创建新迁移 - Shopify级创建标准"""
        print(f"🔨 创建新迁移: {description}")
        
        # 验证类型
        try:
            mig_type = MigrationType(migration_type)
        except ValueError:
            valid_types = [t.value for t in MigrationType]
            print(f"❌ 无效的迁移类型: {migration_type}")
            print(f"   有效类型: {', '.join(valid_types)}")
            return False
        
        # 获取最新revision作为父节点
        chain = self.validator.get_migration_chain()
        down_revision = chain[-1].revision_id if chain else None
        
        # 生成文件内容
        if auto_generate:
            # 使用alembic autogenerate
            revision_id = MigrationNamingStandard.generate_revision_id(description, mig_type)
            cmd = [
                "alembic", "revision", 
                "--autogenerate",
                "--rev-id", revision_id,
                "-m", description
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print("✅ 自动生成迁移成功")
                print(f"   文件: {revision_id}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ 自动生成失败: {e.stderr}")
                return False
        else:
            # 使用模板生成
            content = MigrationTemplate.generate_migration(
                description=description,
                migration_type=mig_type,
                author=author,
                down_revision=down_revision
            )
            
            # 生成文件名
            revision_id = MigrationNamingStandard.generate_revision_id(description, mig_type)
            filename = f"{revision_id}.py"
            file_path = self.versions_dir / filename
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 迁移文件创建成功: {filename}")
            print(f"   路径: {file_path}")
            print(f"   类型: {mig_type.value}")
            print("   请编辑文件添加具体的迁移逻辑")
            return True
    
    def fix_dependency_chain(self):
        """修复依赖链 - Airbnb级依赖管理"""
        print("🔧 修复迁移依赖链...")
        
        issues = self.validator.validate_dependencies()
        if not issues:
            print("✅ 依赖链正常，无需修复")
            return True
        
        print(f"发现 {len(issues)} 个依赖问题，开始修复...")
        
        # 获取正确的时间顺序
        files = list(self.versions_dir.glob("*.py"))
        files.sort(key=lambda f: f.name.split('-')[0])
        
        # 重建依赖链
        prev_revision = None
        fixed_count = 0
        
        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取当前revision
            revision_match = re.search(r'revision: str = ["\']([^"\']+)["\']', content)
            if not revision_match:
                continue
                
            current_revision = revision_match.group(1)
            
            # 更新down_revision
            new_down_revision = f'"{prev_revision}"' if prev_revision else 'None'
            
            updated_content = re.sub(
                r'down_revision: Union\[str, None\] = ["\'][^"\']*["\']',
                f'down_revision: Union[str, None] = {new_down_revision}',
                content
            )
            
            if updated_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"  ✅ 修复 {file_path.name}")
                fixed_count += 1
            
            prev_revision = current_revision
        
        print(f"✅ 修复完成，更新了 {fixed_count} 个文件")
        return True
    
    def lint_migrations(self):
        """代码检查 - PEP8级代码质量"""
        print("🔍 执行迁移代码检查...")
        
        issues = []
        
        for file_path in self.versions_dir.glob("*.py"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_issues = []
            
            # 检查是否有TODO标记
            if "TODO" in content or "FIXME" in content:
                file_issues.append("包含未完成的TODO/FIXME")
            
            # 检查是否有空的upgrade/downgrade函数
            if re.search(r'def upgrade\(\).*?:\s*pass', content, re.DOTALL):
                file_issues.append("upgrade函数为空")
            
            if re.search(r'def downgrade\(\).*?:\s*pass', content, re.DOTALL):
                file_issues.append("downgrade函数为空")
            
            # 检查危险的硬编码
            if re.search(r'["\'][^"\']*password[^"\']*["\']', content, re.IGNORECASE):
                file_issues.append("可能包含硬编码密码")
            
            if file_issues:
                issues.append({
                    'file': file_path.name,
                    'issues': file_issues
                })
        
        if issues:
            print("⚠️ 发现代码质量问题:")
            for item in issues:
                print(f"  📄 {item['file']}:")
                for issue in item['issues']:
                    print(f"    - {issue}")
        else:
            print("✅ 代码检查通过")
        
        return len(issues) == 0
    
    def generate_migration_report(self) -> Dict:
        """生成迁移报告 - DataDog级监控报告"""
        print("📊 生成迁移系统报告...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_migrations': len(self.validator.migrations),
            'migration_chain': [],
            'risk_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
            'type_distribution': {},
            'validation_status': {},
            'recommendations': []
        }
        
        # 构建迁移链
        chain = self.validator.get_migration_chain()
        for metadata in chain:
            report['migration_chain'].append({
                'revision': metadata.revision_id[:8],
                'file': metadata.file_name,
                'type': metadata.migration_type.value,
                'risk': metadata.risk_level.value,
                'description': metadata.description,
                'created_at': metadata.created_at.isoformat()
            })
            
            # 统计风险分布
            report['risk_distribution'][metadata.risk_level.value] += 1
            
            # 统计类型分布
            type_key = metadata.migration_type.value
            report['type_distribution'][type_key] = report['type_distribution'].get(type_key, 0) + 1
        
        # 验证状态
        issues = self.validator.validate_dependencies()
        report['validation_status'] = {
            'has_issues': len(issues) > 0,
            'issue_count': len(issues),
            'issues': issues
        }
        
        # 生成建议
        if issues:
            report['recommendations'].append("修复依赖关系问题")
        
        if report['risk_distribution']['high'] > 0 or report['risk_distribution']['critical'] > 0:
            report['recommendations'].append("审查高风险迁移，考虑添加回滚测试")
        
        # 保存报告
        report_file = self.alembic_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 报告已生成: {report_file}")
        return report

# CLI命令
@click.group()
def cli():
    """FlyEsports 企业级迁移管理工具"""
    pass

@cli.command()
def validate():
    """验证迁移系统"""
    manager = MigrationManager()
    manager.validate_migrations()

@cli.command()
@click.option('--description', '-d', prompt='迁移描述', help='迁移描述')
@click.option('--type', '-t', default='schema', help='迁移类型')
@click.option('--author', '-a', default='developer', help='作者')
@click.option('--auto', is_flag=True, help='自动生成迁移')
def create(description, type, author, auto):
    """创建新迁移"""
    manager = MigrationManager()
    manager.create_migration(description, type, author, auto)

@cli.command()
def fix_chain():
    """修复依赖链"""
    manager = MigrationManager()
    manager.fix_dependency_chain()

@cli.command()
def lint():
    """代码检查"""
    manager = MigrationManager()
    manager.lint_migrations()

@cli.command()
def report():
    """生成报告"""
    manager = MigrationManager()
    manager.generate_migration_report()

@cli.command()
def status():
    """显示迁移状态"""
    manager = MigrationManager()
    results = manager.validate_migrations()
    
    print("\n🎯 快速状态概览:")
    print(f"  📁 迁移文件总数: {results['total_migrations']}")
    print(f"  ❌ 问题数量: {len(results['issues'])}")
    print(f"  ⚠️ 安全警告: {len(results['security_alerts'])}")
    print(f"  📝 命名违规: {len(results['naming_violations'])}")

if __name__ == '__main__':
    cli()