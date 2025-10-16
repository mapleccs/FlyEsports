#!/usr/bin/env python3
"""初始化上传目录结构"""

import os
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


def init_upload_directories():
    """初始化上传目录结构"""
    
    # 创建基础目录结构
    directories = [
        "uploads",
        "uploads/tournaments",
        "uploads/tournaments/logos",
        "uploads/tournaments/banners",
        "uploads/tournaments/presets",
        "uploads/tournaments/presets/logos",
        "uploads/tournaments/presets/banners",
        "uploads/tournaments/presets/logos/thumbnails",
        "uploads/tournaments/presets/banners/thumbnails",
        "uploads/teams",
        "uploads/teams/logos",
        "uploads/players",
        "uploads/players/avatars",
        "uploads/temp"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {directory}")
    
    # 创建 .gitkeep 文件以确保空目录被Git追踪
    gitkeep_dirs = [
        "uploads/tournaments/logos",
        "uploads/tournaments/banners", 
        "uploads/teams/logos",
        "uploads/players/avatars",
        "uploads/temp"
    ]
    
    for directory in gitkeep_dirs:
        gitkeep_path = Path(directory) / ".gitkeep"
        gitkeep_path.touch()
        logger.info(f"创建 .gitkeep: {gitkeep_path}")
    
    # 创建README文件说明目录用途
    readme_content = """# 上传文件目录

本目录用于存储用户上传的文件和媒体资源。

## 目录结构

- `tournaments/` - 赛事相关媒体文件
  - `logos/` - 赛事Logo
  - `banners/` - 赛事横幅图片
  - `presets/` - 预设素材
- `teams/` - 战队相关媒体文件
  - `logos/` - 战队Logo
- `players/` - 选手相关媒体文件
  - `avatars/` - 选手头像
- `temp/` - 临时文件存储

## 安全说明

- 所有上传文件都经过类型和大小验证
- 图片文件会自动处理和优化
- 定期清理临时文件

## 维护

建议定期备份重要的媒体文件，并监控磁盘使用情况。
"""
    
    readme_path = Path("uploads/README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info("上传目录初始化完成")


if __name__ == "__main__":
    init_upload_directories()