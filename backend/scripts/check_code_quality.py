#!/usr/bin/env python3
"""
代码质量检查脚本

运行 black、mypy 和 flake8 来检查代码质量
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, List


def run_command(command: List[str], description: str) -> Tuple[int, str, str]:
    """运行命令并返回结果"""
    print(f"\n[CHECK] {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("Stdout:")
            print(result.stdout)
        
        if result.stderr:
            print("Stderr:")
            print(result.stderr)
        
        return result.returncode, result.stdout, result.stderr
        
    except Exception as e:
        print(f"[ERROR] Command failed: {e}")
        return 1, "", str(e)


def main():
    """主函数"""
    print("[START] 开始代码质量检查")
    
    # 检查工作目录
    backend_dir = Path(__file__).parent.parent
    if not (backend_dir / "src").exists():
        print("[FAIL] 未找到 src 目录")
        sys.exit(1)
    
    print(f"工作目录: {backend_dir}")
    
    # 检查结果统计
    checks = []
    
    # 1. Black 格式检查
    print("\n" + "="*50)
    print("1. BLACK 代码格式检查")
    print("="*50)
    
    returncode, stdout, stderr = run_command(
        ["python", "-m", "black", "--check", "--diff", "src/"],
        "检查代码格式是否符合 Black 规范"
    )
    
    if returncode == 0:
        print("[PASS] Black 格式检查通过")
        checks.append(("Black 格式", True, ""))
    else:
        print("[FAIL] Black 格式检查失败")
        checks.append(("Black 格式", False, "需要格式化代码"))
    
    # 2. MyPy 类型检查
    print("\n" + "="*50)
    print("2. MYPY 类型检查")
    print("="*50)
    
    returncode, stdout, stderr = run_command(
        ["python", "-m", "mypy", "src/", "--ignore-missing-imports", "--no-strict-optional", "--show-error-codes"],
        "检查类型注解和类型安全"
    )
    
    if returncode == 0:
        print("[PASS] MyPy 类型检查通过")
        checks.append(("MyPy 类型", True, ""))
    else:
        # 统计错误数量
        error_lines = [line for line in stdout.split('\n') if 'error:' in line]
        error_count = len(error_lines)
        print(f"[FAIL] MyPy 类型检查失败 ({error_count} 个错误)")
        checks.append(("MyPy 类型", False, f"{error_count} 个类型错误"))
    
    # 3. Flake8 代码风格检查
    print("\n" + "="*50)
    print("3. FLAKE8 代码风格检查")
    print("="*50)
    
    returncode, stdout, stderr = run_command(
        ["python", "-m", "flake8", "src/", "--max-line-length=88", "--extend-ignore=E203,W503"],
        "检查代码风格和潜在问题"
    )
    
    if returncode == 0:
        print("[PASS] Flake8 检查通过")
        checks.append(("Flake8 风格", True, ""))
    else:
        # 统计警告数量
        warning_lines = stdout.split('\n')
        warning_count = len([line for line in warning_lines if line.strip()])
        print(f"[FAIL] Flake8 检查失败 ({warning_count} 个问题)")
        checks.append(("Flake8 风格", False, f"{warning_count} 个风格问题"))
    
    # 4. 生成报告
    print("\n" + "="*50)
    print("[REPORT] 代码质量检查报告")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for check_name, is_passed, details in checks:
        status = "[PASS] 通过" if is_passed else "[FAIL] 失败"
        print(f"{check_name:15} {status:10} {details}")
        
        if is_passed:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed + failed} 项检查，{passed} 项通过，{failed} 项失败")
    
    # 5. 建议和下一步
    if failed > 0:
        print("\n[TIP] 修复建议:")
        
        for check_name, is_passed, details in checks:
            if not is_passed:
                if "Black" in check_name:
                    print("• 运行 `python -m black src/` 自动格式化代码")
                elif "MyPy" in check_name:
                    print("• 添加缺失的类型注解，修复类型错误")
                elif "Flake8" in check_name:
                    print("• 修复代码风格问题，遵循 PEP 8 规范")
        
        print("\n建议逐项修复后再次运行此脚本验证")
        sys.exit(1)
    else:
        print("\n[SUCCESS] 恭喜！所有代码质量检查都通过了！")
        sys.exit(0)


if __name__ == "__main__":
    main()