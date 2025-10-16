#!/usr/bin/env python3
"""
简化版迁移验证工具
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

def analyze_migrations():
    """分析迁移文件"""
    versions_dir = Path("alembic/versions")
    files = sorted([f for f in os.listdir(versions_dir) if f.endswith('.py')])
    
    dependencies = {}
    issues = []
    
    for file in files:
        with open(versions_dir / file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取revision信息
        revision_match = re.search(r'revision: str = ["\']([^"\']+)["\']', content)
        down_revision_match = re.search(r'down_revision: Union\[str, None\] = ["\']([^"\']*)["\']', content)
        
        if revision_match:
            revision = revision_match.group(1)
            down_revision = down_revision_match.group(1) if down_revision_match and down_revision_match.group(1) != 'None' else None
            
            dependencies[revision] = {
                'file': file,
                'down_revision': down_revision
            }
    
    # 检查问题
    print("Migration Validation Report")
    print("=" * 50)
    
    missing_deps = []
    time_issues = []
    
    for revision, info in dependencies.items():
        down_rev = info['down_revision']
        
        # 检查缺失依赖
        if down_rev and down_rev not in dependencies:
            missing_deps.append(f"{revision} -> missing {down_rev}")
        
        # 检查时间顺序
        elif down_rev:
            current_file = info['file']
            parent_file = dependencies[down_rev]['file']
            
            current_time = current_file.split('-')[0].replace('_', '')
            parent_time = parent_file.split('-')[0].replace('_', '')
            
            if current_time < parent_time:
                time_issues.append(f"{current_file} depends on later {parent_file}")
    
    # 输出结果
    print(f"Total migrations: {len(dependencies)}")
    print(f"Missing dependencies: {len(missing_deps)}")
    print(f"Time order issues: {len(time_issues)}")
    
    if missing_deps:
        print("\nMissing Dependencies:")
        for issue in missing_deps:
            print(f"  - {issue}")
    
    if time_issues:
        print("\nTime Order Issues:")
        for issue in time_issues:
            print(f"  - {issue}")
    
    # 安全检查
    dangerous_patterns = [
        r'DROP\s+TABLE',
        r'DROP\s+COLUMN', 
        r'TRUNCATE\s+TABLE'
    ]
    
    security_issues = []
    for revision, info in dependencies.items():
        file_path = versions_dir / info['file']
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                security_issues.append(f"{info['file']}: {pattern}")
    
    if security_issues:
        print("\nSecurity Alerts:")
        for issue in security_issues:
            print(f"  - {issue}")
    
    # 命名规范检查
    naming_issues = []
    standard_pattern = r'^\d{4}_\d{2}_\d{2}_\d{2}\d{2}-[a-f0-9]+-\w+\.py$'
    
    for file in files:
        if not re.match(standard_pattern, file):
            naming_issues.append(file)
    
    if naming_issues:
        print("\nNaming Standard Violations:")
        for file in naming_issues:
            print(f"  - {file}")
    
    # 生成修复建议
    print("\nRecommendations:")
    if missing_deps or time_issues:
        print("  1. Run fix-chain command to rebuild dependency chain")
    if naming_issues:
        print("  2. Rename files to follow standard: YYYY_MM_DD_HHMM-{hash}-{description}.py")
    if security_issues:
        print("  3. Review security alerts and add proper safeguards")
    
    if not (missing_deps or time_issues or security_issues or naming_issues):
        print("  All checks passed! Migration system is healthy.")

def fix_dependency_chain():
    """修复依赖链"""
    print("Fixing dependency chain...")
    
    versions_dir = Path("alembic/versions")
    files = list(versions_dir.glob("*.py"))
    
    # 按时间顺序排序
    files.sort(key=lambda f: f.name.split('-')[0])
    
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
            print(f"  Fixed: {file_path.name}")
            fixed_count += 1
        
        prev_revision = current_revision
    
    print(f"Fixed {fixed_count} files")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "fix-chain":
            fix_dependency_chain()
        elif command == "validate":
            analyze_migrations()
        else:
            print("Usage: python validate_migrations.py [validate|fix-chain]")
    else:
        analyze_migrations()