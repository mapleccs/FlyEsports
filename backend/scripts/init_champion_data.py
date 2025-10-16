#!/usr/bin/env python3
"""
初始化英雄数据脚本
创建一些基础的英雄联盟英雄数据用于测试
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models.champion import Champion

# 英雄数据
CHAMPIONS_DATA = [
    {
        "champion_id": 1,
        "key": "Annie",
        "name": "安妮",
        "title": "黑暗之女",
        "blurb": "安妮是一个拥有魔法天赋的小女孩，她的魔法力量伴随着她的情绪而波动。",
        "tags": ["Mage"],
        "partype": "法力",
        "attack": 2,
        "defense": 2,
        "magic": 10,
        "difficulty": 6,
        "icon_url": "/images/champions/annie.jpg",
        "is_active": True
    },
    {
        "champion_id": 22,
        "key": "Ashe",
        "name": "艾希",
        "title": "寒冰射手",
        "blurb": "艾希是弗雷尔卓德的射手，她的弓箭能够射出寒冰之力。",
        "tags": ["Marksman", "Support"],
        "partype": "法力",
        "attack": 7,
        "defense": 3,
        "magic": 2,
        "difficulty": 4,
        "icon_url": "/images/champions/ashe.jpg",
        "is_active": True
    },
    {
        "champion_id": 86,
        "key": "Garen",
        "name": "盖伦",
        "title": "德玛西亚之力",
        "blurb": "盖伦是德玛西亚的战士，他挥舞着巨剑为正义而战。",
        "tags": ["Fighter", "Tank"],
        "partype": "无消耗",
        "attack": 7,
        "defense": 7,
        "magic": 1,
        "difficulty": 5,
        "icon_url": "/images/champions/garen.jpg",
        "is_active": True
    },
    {
        "champion_id": 157,
        "key": "Yasuo",
        "name": "亚索",
        "title": "疾风剑豪",
        "blurb": "亚索是一名来自艾欧尼亚的剑客，掌握着风之力量。",
        "tags": ["Fighter", "Assassin"],
        "partype": "气",
        "attack": 8,
        "defense": 4,
        "magic": 4,
        "difficulty": 10,
        "icon_url": "/images/champions/yasuo.jpg",
        "is_active": True
    },
    {
        "champion_id": 412,
        "key": "Thresh",
        "name": "锤石",
        "title": "魂锁典狱长",
        "blurb": "锤石是暗影岛的恶魔，他收集着灵魂的痛苦。",
        "tags": ["Support", "Fighter"],
        "partype": "法力",
        "attack": 3,
        "defense": 6,
        "magic": 6,
        "difficulty": 7,
        "icon_url": "/images/champions/thresh.jpg",
        "is_active": True
    },
    {
        "champion_id": 64,
        "key": "LeeSin",
        "name": "李青",
        "title": "盲僧",
        "blurb": "李青是一名来自艾欧尼亚的武僧，虽然失明但拥有强大的武艺。",
        "tags": ["Fighter", "Assassin"],
        "partype": "能量",
        "attack": 8,
        "defense": 5,
        "magic": 3,
        "difficulty": 6,
        "icon_url": "/images/champions/leesin.jpg",
        "is_active": True
    },
    {
        "champion_id": 143,
        "key": "Zyra",
        "name": "婕拉",
        "title": "荆棘之兴",
        "blurb": "婕拉是一名植物法师，她能够操控大自然的力量。",
        "tags": ["Mage", "Support"],
        "partype": "法力",
        "attack": 4,
        "defense": 3,
        "magic": 8,
        "difficulty": 7,
        "icon_url": "/images/champions/zyra.jpg",
        "is_active": True
    },
    {
        "champion_id": 67,
        "key": "Vayne",
        "name": "薇恩",
        "title": "暗夜猎手",
        "blurb": "薇恩是一名暗夜猎手，专门猎杀恶魔和邪恶生物。",
        "tags": ["Marksman", "Assassin"],
        "partype": "法力",
        "attack": 10,
        "defense": 1,
        "magic": 1,
        "difficulty": 8,
        "icon_url": "/images/champions/vayne.jpg",
        "is_active": True
    },
    {
        "champion_id": 91,
        "key": "Talon",
        "name": "泰隆",
        "title": "刀锋之影",
        "blurb": "泰隆是诺克萨斯的刺客，他的刀刃如影随形。",
        "tags": ["Assassin"],
        "partype": "法力",
        "attack": 9,
        "defense": 3,
        "magic": 1,
        "difficulty": 7,
        "icon_url": "/images/champions/talon.jpg",
        "is_active": True
    },
    {
        "champion_id": 25,
        "key": "Morgana",
        "name": "莫甘娜",
        "title": "堕天使",
        "blurb": "莫甘娜是一名堕落的天使，她选择了黑暗魔法的道路。",
        "tags": ["Mage", "Support"],
        "partype": "法力",
        "attack": 1,
        "defense": 5,
        "magic": 8,
        "difficulty": 1,
        "icon_url": "/images/champions/morgana.jpg",
        "is_active": True
    },
    {
        "champion_id": 11,
        "key": "MasterYi",
        "name": "易",
        "title": "无极剑圣",
        "blurb": "易是一名来自艾欧尼亚的剑圣，他追求武道的至高境界。",
        "tags": ["Assassin", "Fighter"],
        "partype": "法力",
        "attack": 10,
        "defense": 4,
        "magic": 2,
        "difficulty": 4,
        "icon_url": "/images/champions/masteryi.jpg",
        "is_active": True
    },
    {
        "champion_id": 112,
        "key": "Viktor",
        "name": "维克托",
        "title": "机械先驱",
        "blurb": "维克托是祖安的发明家，他相信科技能够提升人类。",
        "tags": ["Mage"],
        "partype": "法力",
        "attack": 2,
        "defense": 4,
        "magic": 10,
        "difficulty": 9,
        "icon_url": "/images/champions/viktor.jpg",
        "is_active": True
    },
    {
        "champion_id": 245,
        "key": "Ekko",
        "name": "艾克",
        "title": "时间刺客",
        "blurb": "艾克是祖安的少年，他发明了能够操控时间的装置。",
        "tags": ["Assassin", "Fighter"],
        "partype": "法力",
        "attack": 5,
        "defense": 3,
        "magic": 7,
        "difficulty": 8,
        "icon_url": "/images/champions/ekko.jpg",
        "is_active": True
    },
    {
        "champion_id": 99,
        "key": "Lux",
        "name": "拉克丝",
        "title": "光辉女郎",
        "blurb": "拉克丝是德玛西亚的法师，她能够操控光明的力量。",
        "tags": ["Mage", "Support"],
        "partype": "法力",
        "attack": 2,
        "defense": 4,
        "magic": 9,
        "difficulty": 5,
        "icon_url": "/images/champions/lux.jpg",
        "is_active": True
    },
    {
        "champion_id": 238,
        "key": "Zed",
        "name": "劫",
        "title": "影流之主",
        "blurb": "劫是艾欧尼亚的忍者大师，他掌握着影子的力量。",
        "tags": ["Assassin"],
        "partype": "能量",
        "attack": 9,
        "defense": 2,
        "magic": 1,
        "difficulty": 7,
        "icon_url": "/images/champions/zed.jpg",
        "is_active": True
    },
    {
        "champion_id": 115,
        "key": "Ziggs",
        "name": "吉格斯",
        "title": "爆破鬼才",
        "blurb": "吉格斯是约德尔人爆破专家，他喜欢制造各种爆炸物。",
        "tags": ["Mage"],
        "partype": "法力",
        "attack": 2,
        "defense": 4,
        "magic": 9,
        "difficulty": 4,
        "icon_url": "/images/champions/ziggs.jpg",
        "is_active": True
    },
    {
        "champion_id": 201,
        "key": "Braum",
        "name": "布隆",
        "title": "弗雷尔卓德之心",
        "blurb": "布隆是弗雷尔卓德的守护者，他用盾牌保护着朋友。",
        "tags": ["Support", "Tank"],
        "partype": "法力",
        "attack": 3,
        "defense": 9,
        "magic": 4,
        "difficulty": 3,
        "icon_url": "/images/champions/braum.jpg",
        "is_active": True
    },
    {
        "champion_id": 104,
        "key": "Graves",
        "name": "格雷夫斯",
        "title": "法外狂徒",
        "blurb": "格雷夫斯是比尔吉沃特的枪手，他的散弹枪威力巨大。",
        "tags": ["Marksman"],
        "partype": "法力",
        "attack": 8,
        "defense": 5,
        "magic": 3,
        "difficulty": 3,
        "icon_url": "/images/champions/graves.jpg",
        "is_active": True
    },
    {
        "champion_id": 84,
        "key": "Akali",
        "name": "阿卡丽",
        "title": "离群之刺",
        "blurb": "阿卡丽是均衡教派的叛逆忍者，她独自行走在暗影中。",
        "tags": ["Assassin"],
        "partype": "能量",
        "attack": 5,
        "defense": 3,
        "magic": 8,
        "difficulty": 7,
        "icon_url": "/images/champions/akali.jpg",
        "is_active": True
    },
    {
        "champion_id": 39,
        "key": "Irelia",
        "name": "艾瑞莉娅",
        "title": "刀锋舞者",
        "blurb": "艾瑞莉娅是艾欧尼亚的战士，她用刀锋舞蹈来战斗。",
        "tags": ["Fighter", "Assassin"],
        "partype": "法力",
        "attack": 7,
        "defense": 4,
        "magic": 5,
        "difficulty": 5,
        "icon_url": "/images/champions/irelia.jpg",
        "is_active": True
    }
]

async def init_champion_data():
    """初始化英雄数据"""
    print("开始初始化英雄数据...")
    
    try:
        await database_manager.connect()
        
        async with database_manager.get_session() as session:
            created_count = 0
            updated_count = 0
            
            for champion_data in CHAMPIONS_DATA:
                try:
                    # 检查英雄是否已存在
                    result = await session.execute(
                        select(Champion).where(Champion.champion_id == champion_data['champion_id'])
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        print(f"英雄 {champion_data['name']} 已存在，跳过...")
                        continue
                    
                    # 创建新英雄
                    champion = Champion(**champion_data)
                    session.add(champion)
                    created_count += 1
                    print(f"创建英雄: {champion_data['name']} ({champion_data['title']})")
                    
                except Exception as e:
                    print(f"创建英雄 {champion_data['name']} 失败: {str(e)}")
                    continue
            
            await session.commit()
            
            print(f"\n英雄数据初始化完成!")
            print(f"新建英雄: {created_count} 个")
            print(f"更新英雄: {updated_count} 个")
            
    except Exception as e:
        print(f"初始化英雄数据失败: {str(e)}")
        raise
    finally:
        await database_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(init_champion_data())