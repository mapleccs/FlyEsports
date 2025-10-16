"""
从Riot官方API获取英雄数据

自动获取最新的英雄数据并保存到数据库
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import time
from datetime import date
from core.database import SessionLocal
from models.champion import Champion
from sqlalchemy.exc import IntegrityError

# Riot Data Dragon API 基础URL
DDRAGON_BASE_URL = "https://ddragon.leagueoflegends.com"
DDRAGON_VERSION_URL = f"{DDRAGON_BASE_URL}/api/versions.json"

# 位置映射
POSITION_MAP = {
    "Fighter": "TOP",      # 战士通常走上路
    "Tank": "TOP",         # 坦克通常走上路
    "Mage": "MID",         # 法师通常走中路
    "Assassin": "MID",     # 刺客通常走中路或打野
    "Marksman": "ADC",     # 射手是ADC
    "Support": "SUP"       # 辅助
}

# 标签中文映射
TAG_CN_MAP = {
    "Fighter": "战士",
    "Tank": "坦克",
    "Mage": "法师",
    "Assassin": "刺客",
    "Marksman": "射手",
    "Support": "辅助"
}

# 伤害类型映射
def get_damage_type(tags):
    """根据标签判断伤害类型"""
    if "Marksman" in tags:
        return "AD"
    elif "Mage" in tags:
        return "AP"
    elif "Fighter" in tags or "Tank" in tags:
        return "AD"
    else:
        return "MIXED"

# 获取主要位置
def get_primary_position(tags):
    """根据标签获取主要位置"""
    for tag in tags:
        if tag in POSITION_MAP:
            return POSITION_MAP[tag]
    
    # 特殊情况处理
    if "Assassin" in tags:
        return "JUG"  # 刺客通常打野
    return "MID"  # 默认中路

# 获取次要位置
def get_secondary_positions(primary_pos, tags):
    """根据主要位置和标签获取次要位置"""
    secondary = []
    
    # 刺客可以走多条路
    if "Assassin" in tags:
        if primary_pos == "MID":
            secondary.append("JUG")
        elif primary_pos == "JUG":
            secondary.append("MID")
    
    # 某些法师可以辅助
    if "Mage" in tags and primary_pos == "MID":
        if "Support" in tags:
            secondary.append("SUP")
    
    # 某些射手可以走中路
    if "Marksman" in tags and primary_pos == "ADC":
        if "Mage" in tags:
            secondary.append("MID")
    
    return secondary

def fetch_champion_data():
    """从Riot API获取英雄数据"""
    try:
        # 获取最新版本号
        print("获取最新版本号...")
        version_resp = requests.get(DDRAGON_VERSION_URL)
        versions = version_resp.json()
        latest_version = versions[0]
        print(f"最新版本: {latest_version}")
        
        # 获取英雄列表
        print("获取英雄列表...")
        champion_list_url = f"{DDRAGON_BASE_URL}/cdn/{latest_version}/data/zh_CN/champion.json"
        resp = requests.get(champion_list_url)
        data = resp.json()
        
        champions_data = []
        
        # 处理每个英雄
        for champion_key, champion_info in data['data'].items():
            print(f"处理英雄: {champion_info['name']} ({champion_key})")
            
            try:
                # 添加延迟避免请求过快
                time.sleep(0.5)
                
                # 获取英雄详细信息
                detail_url = f"{DDRAGON_BASE_URL}/cdn/{latest_version}/data/zh_CN/champion/{champion_key}.json"
                detail_resp = requests.get(detail_url, timeout=10)
                detail_data = detail_resp.json()
                champion_detail = detail_data['data'][champion_key]
            except Exception as e:
                print(f"获取英雄 {champion_key} 详细信息失败: {str(e)}")
                # 使用基础信息
                champion_detail = champion_info
            
            # 构建英雄数据
            tags = champion_detail.get('tags', [])
            primary_position = get_primary_position(tags)
            
            champion_data = {
                "champion_key": champion_key,
                "name_cn": champion_info['name'],
                "name_en": champion_info['id'],
                "title_cn": champion_info['title'],
                "title_en": champion_detail.get('title', champion_info.get('title', '')),
                "primary_position": primary_position,
                "secondary_positions": get_secondary_positions(primary_position, tags),
                "difficulty": champion_detail.get('info', {}).get('difficulty', 5),
                "damage_type": get_damage_type(tags),
                "tags": [TAG_CN_MAP.get(tag, tag) for tag in tags],
                "icon_url": f"https://game.gtimg.cn/images/lol/act/img/champion/{champion_key}.png",
                "splash_url": f"{DDRAGON_BASE_URL}/cdn/img/champion/splash/{champion_key}_0.jpg",
                "loading_url": f"{DDRAGON_BASE_URL}/cdn/img/champion/loading/{champion_key}_0.jpg",
                "is_active": True,
                "is_free": False,  # 需要单独获取周免信息
                "pick_rate": 0.0,  # 需要从其他数据源获取
                "ban_rate": 0.0,   # 需要从其他数据源获取
                "win_rate": 0.0    # 需要从其他数据源获取
            }
            
            champions_data.append(champion_data)
        
        return champions_data
        
    except Exception as e:
        print(f"获取英雄数据失败: {str(e)}")
        return []

def save_champions_to_db(champions_data):
    """保存英雄数据到数据库"""
    db = SessionLocal()
    
    try:
        success_count = 0
        update_count = 0
        skip_count = 0
        
        for champion_data in champions_data:
            try:
                # 检查是否已存在
                existing = db.query(Champion).filter(
                    Champion.champion_key == champion_data["champion_key"]
                ).first()
                
                if existing:
                    # 更新现有数据
                    for key, value in champion_data.items():
                        setattr(existing, key, value)
                    db.commit()
                    update_count += 1
                    print(f"更新英雄: {champion_data['name_cn']}")
                else:
                    # 创建新英雄
                    champion = Champion(**champion_data)
                    db.add(champion)
                    db.commit()
                    success_count += 1
                    print(f"添加英雄: {champion_data['name_cn']}")
                
            except IntegrityError as e:
                db.rollback()
                print(f"处理英雄 {champion_data['name_cn']} 失败: {str(e)}")
                skip_count += 1
            except Exception as e:
                db.rollback()
                print(f"处理英雄 {champion_data['name_cn']} 时出错: {str(e)}")
                skip_count += 1
        
        print(f"\n处理完成！")
        print(f"新增: {success_count} 个英雄")
        print(f"更新: {update_count} 个英雄")
        print(f"跳过: {skip_count} 个英雄")
        
        # 显示总数
        total_count = db.query(Champion).count()
        print(f"数据库中总共有: {total_count} 个英雄")
        
    except Exception as e:
        print(f"保存失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

def update_free_champions():
    """更新周免英雄信息"""
    # 这需要额外的API或数据源
    # 暂时设置一些常见的免费英雄
    free_champions = [
        "Garen", "Ashe", "MasterYi", "Annie", 
        "Ryze", "Sivir", "Soraka", "Warwick",
        "Nunu", "MissFortune", "Caitlyn", "Brand"
    ]
    
    db = SessionLocal()
    try:
        # 先将所有英雄设为非免费
        db.query(Champion).update({"is_free": False})
        
        # 设置免费英雄
        for champ_key in free_champions:
            db.query(Champion).filter(
                Champion.champion_key == champ_key
            ).update({"is_free": True})
        
        db.commit()
        print(f"已更新 {len(free_champions)} 个免费英雄")
        
    except Exception as e:
        print(f"更新免费英雄失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

def main():
    """主函数"""
    print("开始从Riot官方API获取英雄数据...")
    
    # 获取英雄数据
    champions_data = fetch_champion_data()
    
    if champions_data:
        print(f"\n成功获取 {len(champions_data)} 个英雄的数据")
        
        # 保存到数据库
        print("\n开始保存到数据库...")
        save_champions_to_db(champions_data)
        
        # 更新免费英雄
        print("\n更新免费英雄信息...")
        update_free_champions()
    else:
        print("未能获取英雄数据")

if __name__ == "__main__":
    main()