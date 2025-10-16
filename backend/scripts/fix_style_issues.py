#!/usr/bin/env python3
"""
自动修复常见的代码风格问题
"""
import os
import re
import subprocess
from pathlib import Path


def remove_unused_imports():
    """使用autoflake移除未使用的导入"""
    print("移除未使用的导入...")
    try:
        result = subprocess.run([
            "python", "-m", "autoflake",
            "--in-place",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--recursive",
            "src/"
        ], capture_output=True, text=True, cwd=".")
        print(f"Autoflake执行结果: {result.returncode}")
        if result.stdout:
            print(f"输出: {result.stdout}")
        if result.stderr:
            print(f"错误: {result.stderr}")
    except FileNotFoundError:
        print("Autoflake未安装，跳过自动移除未使用导入")
        return False
    return True


def fix_line_length_issues():
    """修复行长度问题"""
    print("修复行长度问题...")
    
    src_path = Path("src")
    line_fixes = 0
    
    for py_file in src_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            new_lines = []
            
            for i, line in enumerate(lines):
                # 处理长行
                if len(line.strip()) > 88 and line.strip():
                    # 处理长字符串
                    if '"""' in line or "'''" in line:
                        new_lines.append(line)
                        continue
                    
                    # 处理导入语句
                    if line.strip().startswith('from ') and ' import ' in line:
                        if len(line.strip()) > 88:
                            # 尝试换行导入
                            import_match = re.match(r'^(\s*from\s+\S+\s+import\s+)(.+)$', line)
                            if import_match:
                                prefix = import_match.group(1)
                                imports = import_match.group(2).strip()
                                if ',' in imports:
                                    import_items = [item.strip() for item in imports.split(',')]
                                    if len(import_items) > 1:
                                        # 多行导入
                                        new_lines.append(f"{prefix}(\n")
                                        for j, item in enumerate(import_items):
                                            if j == len(import_items) - 1:
                                                new_lines.append(f"    {item}\n")
                                            else:
                                                new_lines.append(f"    {item},\n")
                                        new_lines.append(")\n")
                                        modified = True
                                        line_fixes += 1
                                        continue
                    
                    # 处理函数调用和方法链
                    if '(' in line and ')' in line and len(line.strip()) > 88:
                        # 简单的换行处理
                        indentation = len(line) - len(line.lstrip())
                        if ',' in line:
                            # 在逗号处换行
                            parts = line.split(',')
                            if len(parts) > 1:
                                new_line = parts[0] + ',\n'
                                for j, part in enumerate(parts[1:], 1):
                                    if j == len(parts) - 1:
                                        new_line += ' ' * (indentation + 4) + part.strip()
                                    else:
                                        new_line += ' ' * (indentation + 4) + part.strip() + ',\n'
                                if len(new_line) < len(line):
                                    new_lines.append(new_line)
                                    modified = True
                                    line_fixes += 1
                                    continue
                
                new_lines.append(line)
            
            if modified:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print(f"修复了 {py_file}")
                
        except Exception as e:
            print(f"处理文件 {py_file} 时出错: {e}")
    
    print(f"修复了 {line_fixes} 个行长度问题")


def fix_variable_names():
    """修复模糊的变量名"""
    print("修复模糊变量名...")
    
    src_path = Path("src")
    var_fixes = 0
    
    # 常见的模糊变量名映射
    name_mappings = {
        'I': 'tier',  # 在rank_info.py中，I通常表示段位
        'l': 'items',
        'O': 'obj',
    }
    
    for py_file in src_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified = False
            new_content = content
            
            # 特殊处理 rank_info.py 中的 I 变量
            if py_file.name == 'rank_info.py':
                # 替换 I = 段位枚举 为 tier = 段位枚举
                pattern = r'\bI\s*=\s*'
                if re.search(pattern, new_content):
                    new_content = re.sub(pattern, 'tier = ', new_content)
                    # 同时替换所有引用 I 的地方
                    pattern2 = r'\bI\b'
                    new_content = re.sub(pattern2, 'tier', new_content)
                    modified = True
                    var_fixes += 1
            
            if modified:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"修复了 {py_file} 中的变量名")
                
        except Exception as e:
            print(f"处理文件 {py_file} 时出错: {e}")
    
    print(f"修复了 {var_fixes} 个变量名问题")


def main():
    """主函数"""
    print("开始自动修复代码风格问题...")
    
    # 检查是否在正确的目录
    if not os.path.exists("src"):
        print("错误：未找到src目录，请在backend目录下运行此脚本")
        return
    
    # 1. 移除未使用的导入
    remove_unused_imports()
    
    # 2. 修复行长度问题
    fix_line_length_issues()
    
    # 3. 修复变量名问题
    fix_variable_names()
    
    print("\n代码风格修复完成！建议运行以下命令验证修复效果：")
    print("python -m flake8 src/ --max-line-length=88 --ignore=E203,W503")


if __name__ == "__main__":
    main()