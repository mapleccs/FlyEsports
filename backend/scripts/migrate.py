#!/usr/bin/env python3
"""
数据库迁移管理脚本 - 小白友好版本

这个脚本简化了Alembic数据库迁移操作，让没有经验的用户也能安全地管理数据库变更。

使用方法:
    python scripts/migrate.py --help                    # 显示帮助
    python scripts/migrate.py status                    # 查看迁移状态  
    python scripts/migrate.py create "添加用户表"        # 创建新迁移
    python scripts/migrate.py upgrade                   # 应用所有待处理的迁移
    python scripts/migrate.py downgrade                 # 回滚最后一个迁移
    python scripts/migrate.py history                   # 查看迁移历史
    python scripts/migrate.py reset                     # 重置数据库（危险操作）

注意: 在生产环境使用前，请务必备份数据库！
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine, text
except ImportError as e:
    print("❌ 错误: 缺少必要的依赖包。请先运行: pip install alembic sqlalchemy")
    print(f"详细错误信息: {e}")
    sys.exit(1)


class DatabaseMigrator:
    """数据库迁移管理器"""
    
    def __init__(self):
        """初始化迁移管理器"""
        self.project_root = Path(__file__).parent.parent
        self.alembic_cfg = Config(str(self.project_root / "alembic.ini"))
        
        # 设置脚本目录
        self.alembic_cfg.set_main_option("script_location", str(self.project_root / "alembic"))
        
        # 从环境变量获取数据库URL
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5433/flyesports"
        )
        
        # 转换asyncpg为psycopg2（Alembic需要）
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
        self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        self.database_url = database_url
        
    def print_header(self, title: str):
        """打印格式化的标题"""
        print(f"\n{'=' * 60}")
        print(f"🚀 {title}")
        print(f"{'=' * 60}")
        
    def print_step(self, step: str, success: bool = True):
        """打印操作步骤"""
        icon = "✅" if success else "❌"
        print(f"{icon} {step}")
        
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            print("\n💡 解决建议:")
            print("1. 确保Docker服务正在运行: docker-compose ps")
            print("2. 检查数据库服务状态: docker-compose logs postgres")
            print("3. 重启数据库服务: docker-compose restart postgres")
            return False
            
    def get_migration_status(self) -> dict:
        """获取迁移状态信息"""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            engine = create_engine(self.database_url)
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                
            head_rev = script.get_current_head()
            revisions = list(script.walk_revisions())
            
            return {
                'current': current_rev,
                'head': head_rev,
                'total_migrations': len(revisions),
                'is_up_to_date': current_rev == head_rev,
                'revisions': revisions
            }
        except Exception as e:
            print(f"❌ 获取迁移状态失败: {e}")
            return {}
    
    def status(self):
        """显示数据库迁移状态"""
        self.print_header("数据库迁移状态")
        
        if not self.check_database_connection():
            return
            
        status_info = self.get_migration_status()
        if not status_info:
            return
            
        print(f"📊 当前版本: {status_info['current'] or '未初始化'}")
        print(f"📊 最新版本: {status_info['head'] or '无迁移文件'}")
        print(f"📊 迁移文件总数: {status_info['total_migrations']}")
        
        if status_info['is_up_to_date']:
            self.print_step("数据库已是最新版本")
        else:
            self.print_step("数据库需要更新", False)
            print("💡 运行 'python scripts/migrate.py upgrade' 来更新数据库")
            
    def create_migration(self, message: str):
        """创建新的迁移文件"""
        self.print_header(f"创建迁移: {message}")
        
        if not message.strip():
            print("❌ 错误: 迁移消息不能为空")
            print("💡 示例: python scripts/migrate.py create '添加用户头像字段'")
            return
            
        try:
            print("🔄 正在检查模型变更...")
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            self.print_step(f"迁移文件创建成功: {message}")
            
            print("\n📝 下一步操作:")
            print("1. 检查生成的迁移文件内容是否正确")
            print("2. 运行 'python scripts/migrate.py upgrade' 应用迁移")
            print("3. 测试应用功能确保迁移成功")
            
        except Exception as e:
            print(f"❌ 创建迁移失败: {e}")
            print("\n💡 可能的原因:")
            print("1. 模型文件中存在语法错误")
            print("2. 数据库连接失败")
            print("3. 没有检测到模型变更")
            
    def upgrade(self, revision: Optional[str] = None):
        """升级数据库到指定版本"""
        target = revision or "head"
        self.print_header(f"升级数据库到: {target}")
        
        if not self.check_database_connection():
            return
            
        # 检查当前状态
        status_info = self.get_migration_status()
        if status_info and status_info['is_up_to_date'] and target == "head":
            self.print_step("数据库已是最新版本，无需升级")
            return
            
        try:
            print("🔄 正在应用数据库迁移...")
            
            # 应用迁移前备份提醒
            print("\n⚠️  重要提醒: 在生产环境中，请务必先备份数据库！")
            
            if target == "head":
                confirm = input("是否继续应用所有待处理的迁移？(y/N): ").strip().lower()
            else:
                confirm = input(f"是否继续升级到版本 {target}？(y/N): ").strip().lower()
                
            if confirm != 'y':
                print("❌ 操作已取消")
                return
                
            command.upgrade(self.alembic_cfg, revision or "head")
            self.print_step("数据库升级成功")
            
            # 显示更新后的状态
            print("\n📊 更新后状态:")
            self.status()
            
        except Exception as e:
            print(f"❌ 数据库升级失败: {e}")
            print("\n💡 故障排除:")
            print("1. 检查迁移文件是否有语法错误")
            print("2. 确认数据库中的数据与迁移兼容")
            print("3. 查看完整错误日志进行诊断")
            
    def downgrade(self, steps: int = 1):
        """回滚数据库迁移"""
        self.print_header(f"回滚数据库 ({steps} 步)")
        
        if not self.check_database_connection():
            return
            
        status_info = self.get_migration_status()
        if not status_info or not status_info['current']:
            print("❌ 数据库未初始化，无法回滚")
            return
            
        try:
            print("⚠️  警告: 回滚操作可能导致数据丢失！")
            print(f"当前版本: {status_info['current']}")
            
            confirm = input(f"确定要回滚 {steps} 步吗？这可能会丢失数据！(yes/NO): ").strip()
            if confirm.lower() != 'yes':
                print("❌ 操作已取消")
                return
                
            # 计算目标版本
            if steps == 1:
                target = "-1"
            else:
                target = f"-{steps}"
                
            print(f"🔄 正在回滚到: {target}")
            command.downgrade(self.alembic_cfg, target)
            self.print_step("数据库回滚成功")
            
            # 显示回滚后的状态
            print("\n📊 回滚后状态:")
            self.status()
            
        except Exception as e:
            print(f"❌ 数据库回滚失败: {e}")
            print("\n💡 如果回滚失败，请检查:")
            print("1. 迁移文件中的downgrade()方法是否正确")
            print("2. 数据是否与回滚操作兼容")
            
    def history(self, verbose: bool = False):
        """显示迁移历史"""
        self.print_header("数据库迁移历史")
        
        try:
            if verbose:
                command.history(self.alembic_cfg, verbose=True)
            else:
                script = ScriptDirectory.from_config(self.alembic_cfg)
                revisions = list(script.walk_revisions())
                
                if not revisions:
                    print("📝 暂无迁移记录")
                    return
                    
                print(f"📝 共有 {len(revisions)} 个迁移:")
                print("-" * 80)
                
                for i, rev in enumerate(revisions, 1):
                    # 格式化日期
                    if hasattr(rev, 'create_date') and rev.create_date:
                        date_str = rev.create_date.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = "未知时间"
                        
                    print(f"{i:2d}. {rev.revision[:8]} - {rev.doc or '无描述'}")
                    print(f"    时间: {date_str}")
                    if verbose and rev.message:
                        print(f"    详情: {rev.message}")
                    print()
                    
        except Exception as e:
            print(f"❌ 获取迁移历史失败: {e}")
            
    def reset_database(self):
        """重置数据库（危险操作）"""
        self.print_header("重置数据库")
        
        print("⚠️⚠️⚠️  警告：这是一个危险操作！ ⚠️⚠️⚠️")
        print("此操作将:")
        print("1. 删除所有数据表和数据")
        print("2. 重新创建所有表结构")
        print("3. 不可逆转地丢失所有现有数据")
        print()
        
        confirm1 = input("确定要重置数据库吗？输入 'RESET' 继续: ").strip()
        if confirm1 != 'RESET':
            print("❌ 操作已取消")
            return
            
        confirm2 = input("最后确认: 这将删除所有数据，输入 'YES DELETE ALL' 继续: ").strip()
        if confirm2 != 'YES DELETE ALL':
            print("❌ 操作已取消")
            return
            
        try:
            print("🔄 正在重置数据库...")
            
            # 删除所有迁移记录
            command.downgrade(self.alembic_cfg, "base")
            self.print_step("已回滚到初始状态")
            
            # 重新应用所有迁移
            command.upgrade(self.alembic_cfg, "head")
            self.print_step("已重新应用所有迁移")
            
            print("\n✅ 数据库重置完成")
            print("💡 建议: 运行数据初始化脚本恢复基础数据")
            
        except Exception as e:
            print(f"❌ 数据库重置失败: {e}")
            print("💡 如果数据库处于不一致状态，请手动删除数据库并重新创建")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FlyEsports 数据库迁移管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/migrate.py status                    # 查看迁移状态
  python scripts/migrate.py create "添加用户表"        # 创建新迁移
  python scripts/migrate.py upgrade                   # 应用所有迁移
  python scripts/migrate.py downgrade                 # 回滚最后一个迁移
  python scripts/migrate.py history                   # 查看迁移历史
  
注意: 在生产环境使用前，请务必备份数据库！
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='显示数据库迁移状态')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新的迁移文件')
    create_parser.add_argument('message', help='迁移描述信息')
    
    # upgrade 命令
    upgrade_parser = subparsers.add_parser('upgrade', help='升级数据库')
    upgrade_parser.add_argument('--revision', '-r', help='升级到指定版本（默认为最新）')
    
    # downgrade 命令
    downgrade_parser = subparsers.add_parser('downgrade', help='回滚数据库迁移')
    downgrade_parser.add_argument('--steps', '-s', type=int, default=1, help='回滚步数（默认1步）')
    
    # history 命令
    history_parser = subparsers.add_parser('history', help='显示迁移历史')
    history_parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    # reset 命令
    subparsers.add_parser('reset', help='重置数据库（危险操作）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    migrator = DatabaseMigrator()
    
    try:
        if args.command == 'status':
            migrator.status()
        elif args.command == 'create':
            migrator.create_migration(args.message)
        elif args.command == 'upgrade':
            migrator.upgrade(getattr(args, 'revision', None))
        elif args.command == 'downgrade':
            migrator.downgrade(getattr(args, 'steps', 1))
        elif args.command == 'history':
            migrator.history(getattr(args, 'verbose', False))
        elif args.command == 'reset':
            migrator.reset_database()
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n❌ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        print("💡 请将错误信息报告给开发团队")


if __name__ == "__main__":
    main()