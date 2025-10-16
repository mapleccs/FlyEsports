"""
从Riot官方API获取英雄数据
自动获取最新的英雄数据并保存到FlyEsports数据库
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import httpx
import json
import asyncio
import time
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models.champion import Champion


# Riot Data Dragon API 基础URL
DDRAGON_BASE_URL = "https://ddragon.leagueoflegends.com"
DDRAGON_VERSION_URL = f"{DDRAGON_BASE_URL}/api/versions.json"

# 位置映射 (适配FlyEsports项目)
POSITION_MAP = {
    "Fighter": "top",      # 战士通常走上路
    "Tank": "top",         # 坦克通常走上路
    "Mage": "mid",         # 法师通常走中路
    "Assassin": "mid",     # 刺客通常走中路或打野
    "Marksman": "adc",     # 射手是ADC
    "Support": "support"   # 辅助
}

def get_primary_position(tags):
    """根据标签获取主要位置"""
    for tag in tags:
        if tag in POSITION_MAP:
            return POSITION_MAP[tag]
    
    # 特殊情况处理
    if "Assassin" in tags:
        return "jungle"  # 刺客通常打野
    return "mid"  # 默认中路

def get_all_positions(primary_pos, tags):
    """根据主要位置和标签获取所有可能位置"""
    positions = [primary_pos]
    
    # 刺客可以走多条路
    if "Assassin" in tags:
        if primary_pos == "mid" and "jungle" not in positions:
            positions.append("jungle")
        elif primary_pos == "jungle" and "mid" not in positions:
            positions.append("mid")
    
    # 某些法师可以辅助
    if "Mage" in tags and primary_pos == "mid":
        if "Support" in tags and "support" not in positions:
            positions.append("support")
    
    # 某些射手可以走中路
    if "Marksman" in tags and primary_pos == "adc":
        if "Mage" in tags and "mid" not in positions:
            positions.append("mid")
    
    return positions

async def fetch_champion_data():
    """从Riot API获取英雄数据"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 获取最新版本号
            print("获取最新版本号...")
            version_resp = await client.get(DDRAGON_VERSION_URL)
            versions = version_resp.json()
            latest_version = versions[0]
            print(f"最新版本: {latest_version}")
            
            # 获取英雄列表
            print("获取英雄列表...")
            champion_list_url = f"{DDRAGON_BASE_URL}/cdn/{latest_version}/data/zh_CN/champion.json"
            resp = await client.get(champion_list_url)
            data = resp.json()
            
            champions_data = []
            
            # 处理每个英雄
            for champion_key, champion_info in data['data'].items():
                print(f"处理英雄: {champion_info['name']} ({champion_key})")
                
                try:
                    # 添加延迟避免请求过快
                    await asyncio.sleep(0.3)
                    
                    # 获取英雄详细信息
                    detail_url = f"{DDRAGON_BASE_URL}/cdn/{latest_version}/data/zh_CN/champion/{champion_key}.json"
                    detail_resp = await client.get(detail_url)
                    detail_data = detail_resp.json()
                    champion_detail = detail_data['data'][champion_key]
                except Exception as e:
                    print(f"获取英雄 {champion_key} 详细信息失败: {str(e)}")
                    # 使用基础信息
                    champion_detail = champion_info
            
                # 构建英雄数据 (适配FlyEsports Champion模型)
                tags = champion_detail.get('tags', [])
                primary_position = get_primary_position(tags)
                all_positions = get_all_positions(primary_position, tags)
                
                # 获取英雄统计信息
                info = champion_detail.get('info', {})
            
                champion_data = {
                    "champion_id": int(champion_info['key']),  # 使用官方ID
                    "key": champion_key,
                    "name": champion_info['name'],
                    "title": champion_info['title'],
                    "lore": champion_detail.get('lore', ''),
                    "blurb": champion_detail.get('blurb', ''),
                    "tags": tags,
                    "partype": champion_detail.get('partype', 'MP'),
                    "attack": info.get('attack', 1),
                    "defense": info.get('defense', 1),
                    "magic": info.get('magic', 1),
                    "difficulty": info.get('difficulty', 1),
                    "icon_url": f"{DDRAGON_BASE_URL}/cdn/{latest_version}/img/champion/{champion_key}.png",
                    "splash_url": f"{DDRAGON_BASE_URL}/cdn/img/champion/splash/{champion_key}_0.jpg",
                    "passive_icon_url": champion_detail.get('passive', {}).get('image', {}).get('full', ''),
                    "spells": json.dumps([{
                        "id": spell.get('id', ''),
                        "name": spell.get('name', ''),
                        "description": spell.get('description', ''),
                        "image": spell.get('image', {}).get('full', '')
                    } for spell in champion_detail.get('spells', [])], ensure_ascii=False),
                    "passive": json.dumps({
                        "name": champion_detail.get('passive', {}).get('name', ''),
                        "description": champion_detail.get('passive', {}).get('description', ''),
                        "image": champion_detail.get('passive', {}).get('image', {}).get('full', '')
                    }, ensure_ascii=False),
                    "is_active": True,
                    "is_free_week": False,  # 周免需要单独更新
                    "version": latest_version
                }
                
                champions_data.append(champion_data)
            
            return champions_data
        
    except Exception as e:
        import traceback
        print(f"获取英雄数据失败: {str(e)}")
        print(f"详细错误信息: {traceback.format_exc()}")
        return []

async def save_champions_to_db(champions_data):
    """保存英雄数据到数据库"""
    try:
        success_count = 0
        update_count = 0
        skip_count = 0
        
        async with database_manager.get_session() as session:
            for champion_data in champions_data:
                try:
                    # 检查是否已存在
                    from sqlalchemy import select
                    stmt = select(Champion).where(Champion.champion_id == champion_data["champion_id"])
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # 更新现有数据
                        for key, value in champion_data.items():
                            setattr(existing, key, value)
                        update_count += 1
                        print(f"更新英雄: {champion_data['name']}")
                    else:
                        # 创建新英雄
                        champion = Champion(**champion_data)
                        session.add(champion)
                        success_count += 1
                        print(f"添加英雄: {champion_data['name']}")
                    
                    await session.commit()
                    
                except IntegrityError as e:
                    await session.rollback()
                    print(f"处理英雄 {champion_data['name']} 失败: {str(e)}")
                    skip_count += 1
                except Exception as e:
                    await session.rollback()
                    print(f"处理英雄 {champion_data['name']} 时出错: {str(e)}")
                    skip_count += 1
        
        print(f"\n处理完成！")
        print(f"新增: {success_count} 个英雄")
        print(f"更新: {update_count} 个英雄")
        print(f"跳过: {skip_count} 个英雄")
        
        # 显示总数
        async with database_manager.get_session() as session:
            from sqlalchemy import select, func
            stmt = select(func.count(Champion.id))
            result = await session.execute(stmt)
            total_count = result.scalar()
            print(f"数据库中总共有: {total_count} 个英雄")
        
    except Exception as e:
        print(f"保存失败: {str(e)}")

async def update_free_champions():
    """更新周免英雄信息"""
    # 这里可以设置一些常见的免费英雄作为示例
    free_champion_ids = [1, 22, 86, 119, 79, 35, 51, 16, 20, 21, 13, 63]  # 一些英雄的ID
    
    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import update, select
            
            # 先将所有英雄设为非免费
            stmt = update(Champion).values(is_free_week=False)
            await session.execute(stmt)
            
            # 设置免费英雄
            if free_champion_ids:
                stmt = update(Champion).where(Champion.champion_id.in_(free_champion_ids)).values(is_free_week=True)
                await session.execute(stmt)
            
            await session.commit()
            print(f"已更新 {len(free_champion_ids)} 个免费英雄")
        
    except Exception as e:
        print(f"更新免费英雄失败: {str(e)}")

async def main():
    """主函数"""
    print("开始从Riot官方API获取英雄数据...")
    print(f"开始时间: {datetime.now()}")
    
    # 连接数据库
    await database_manager.connect()
    
    try:
        # 获取英雄数据
        champions_data = await fetch_champion_data()
        
        if champions_data:
            print(f"\n成功获取 {len(champions_data)} 个英雄的数据")
            
            # 保存到数据库
            print("\n开始保存到数据库...")
            await save_champions_to_db(champions_data)
            
            # 更新免费英雄
            print("\n更新免费英雄信息...")
            await update_free_champions()
        else:
            print("未能获取英雄数据")
    
    finally:
        # 断开数据库连接
        await database_manager.disconnect()
    
    print(f"完成时间: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())