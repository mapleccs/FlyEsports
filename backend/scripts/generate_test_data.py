#!/usr/bin/env python3
"""
测试数据生成脚本

模拟真实用户流程：
1. 用户注册
2. 创建选手档案
3. 创建战队
4. 邀请队员加入
5. 报名参赛

使用方法：
cd backend
PYTHONPATH=. python scripts/generate_test_data.py
"""

import asyncio
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4

import asyncpg

# 虚拟数据配置
REGIONS = [
    {"name": "华东赛区", "description": "覆盖上海、江苏、浙江等地区"},
    {"name": "华北赛区", "description": "覆盖北京、天津、河北等地区"}, 
    {"name": "华南赛区", "description": "覆盖广东、广西、海南等地区"},
    {"name": "西南赛区", "description": "覆盖四川、重庆、云南等地区"},
]

# 真实的英雄联盟职业选手和战队名称作为参考
REAL_PLAYER_NAMES = [
    # LPL职业选手名字
    "Rookie", "TheShy", "Ning", "JackeyLove", "Baolan",
    "Knight", "Yagao", "Doinb", "Crisp", "Meiko",
    "Uzi", "Ming", "Xiaohu", "Karsa", "Wei",
    "Bin", "SofM", "huanfeng", "ON", "ppgod",
    "Zoom", "Kanavi", "Yagao", "Hope", "Missing",
    "Flandre", "Jiejie", "Scout", "Viper", "Meiko",
    "Breathe", "Tian", "Doinb", "Lwx", "Crisp",
    "369", "Karsa", "Angel", "Gala", "Ming",
    "Ale", "Tarzan", "Rookie", "Huanfeng", "ppgod",
    "Rich", "Beishang", "Cryin", "GALA", "Ming",
    # 新手玩家名字
    "小明", "小红", "小强", "小李", "小王",
    "张三", "李四", "王五", "赵六", "钱七",
    "孙八", "周九", "吴十", "郑一", "陈二",
    "刘三", "林四", "黄五", "何六", "高七",
]

REAL_TEAM_NAMES = [
    # LPL战队名
    "IG青训", "RNG青训", "EDG青训", "FPX青训", "TES青训",
    "JDG青训", "LNG青训", "WE青训", "OMG青训", "V5青训",
    # 网吧战队风格
    "无敌战神", "王者归来", "钢铁直男", "逆风翻盘", "五杀狂魔",
    "超神战队", "绝地反击", "网咖之王", "青铜联盟", "白银军团",
    "黄金战士", "钻石精英", "最强王者", "峡谷传说", "征服者",
    "龙之传人", "凤凰涅槃", "雄鹰展翅", "猛虎下山", "饿狼传说",
    "神域公会", "永恒之刃", "暗夜精灵", "圣光骑士", "影子杀手",
    "烈火战神", "冰霜法师", "雷电术士", "风暴战士", "大地守护",
]

SUMMONER_NAMES = [
    # 有趣的召唤师名字
    "今天也要加油鸭", "不会玩ADC", "五杀收割机", "我是混子",
    "只会玩盲僧", "钩子王者", "补刀一百五", "永远不投降",
    "团战必死", "单杀专业户", "我要上王者", "铁桶阵法王",
    "ADHD超神", "奶妈救世主", "ADC是什么", "我会八个英雄",
    "菜鸟求带飞", "老司机带路", "峡谷拆迁队", "五排黑店",
    "默默无闻的小兵", "传说中的坑货", "职业挂机王",
    "咸鱼也要翻身", "青铜五的骄傲", "白银局霸主",
]

POSITIONS = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

RANKS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]

class TestDataGenerator:
    def __init__(self):
        self.db: asyncpg.Connection = None
        self.users: List[Dict] = []
        self.player_profiles: List[Dict] = []
        self.teams: List[Dict] = []
        self.regions: List[Dict] = []

    async def connect_db(self):
        """连接数据库"""
        try:
            self.db = await asyncpg.connect(
                "postgresql://postgres:postgres@localhost:5432/flyesports"
            )
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    async def close_db(self):
        """关闭数据库连接"""
        if self.db:
            await self.db.close()

    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    async def clear_existing_data(self):
        """清理现有测试数据"""
        print("清理现有测试数据...")
        
        # 按依赖关系顺序删除
        tables = [
            "tournament_registrations",
            "tournament_matches", 
            "match_check_ins",
            "tournaments",
            "team_members",
            "teams", 
            "player_profiles",
            "user_roles",
            "users",
            "regions"
        ]
        
        for table in tables:
            try:
                await self.db.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                print(f"  清理表: {table}")
            except Exception as e:
                print(f"  警告: 清理表 {table} 时出错: {e}")

    async def create_regions(self):
        """创建赛区数据"""
        print("创建赛区数据...")
        
        for i, region_data in enumerate(REGIONS):
            region_id = await self.db.fetchval("""
                INSERT INTO regions (name, description, admin_user_id, is_active, max_teams_per_season, allow_public_registration)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, region_data["name"], region_data["description"], 1, True, 16, True)
            
            self.regions.append({
                "id": region_id,
                "name": region_data["name"],
                "description": region_data["description"]
            })
            print(f"  创建赛区: {region_data['name']} (ID: {region_id})")

    async def create_users(self, count: int = 100):
        """创建用户数据"""
        print(f"创建 {count} 个用户...")
        
        # 先创建管理员用户
        admin_id = await self.db.fetchval("""
            INSERT INTO users (username, email, password_hash, is_active, is_verified, riot_summoner_name)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, "admin", "admin@flyesports.com", self.hash_password("admin123"), True, True, "SuperAdmin")
        
        print(f"  创建管理员用户: admin (ID: {admin_id})")
        
        # 创建普通用户
        used_emails = set()
        used_usernames = set()
        used_summoner_names = set()
        
        for i in range(count):
            # 生成唯一的用户名和邮箱
            base_username = random.choice(REAL_PLAYER_NAMES)
            username = f"{base_username}{random.randint(1000, 9999)}"
            while username in used_usernames:
                username = f"{base_username}{random.randint(1000, 9999)}"
            used_usernames.add(username)
            
            email = f"{username.lower()}@example.com"
            while email in used_emails:
                email = f"{username.lower()}{random.randint(1, 999)}@example.com"
            used_emails.add(email)
            
            # 生成召唤师名称
            summoner_name = random.choice(SUMMONER_NAMES)
            if len(summoner_name) > 15:  # 召唤师名称长度限制
                summoner_name = summoner_name[:15]
            # 确保召唤师名称唯一
            original_summoner = summoner_name
            counter = 1
            while summoner_name in used_summoner_names:
                summoner_name = f"{original_summoner}{counter}"
                counter += 1
                if len(summoner_name) > 15:
                    summoner_name = f"{original_summoner[:13]}{counter}"
            used_summoner_names.add(summoner_name)
            
            user_id = await self.db.fetchval("""
                INSERT INTO users (username, email, password_hash, is_active, is_verified, riot_summoner_name)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, username, email, self.hash_password("password123"), True, True, summoner_name)
            
            self.users.append({
                "id": user_id,
                "username": username,
                "email": email,
                "summoner_name": summoner_name
            })
            
            if (i + 1) % 10 == 0:
                print(f"  已创建 {i + 1} 个用户...")
        
        print(f"  完成创建 {count} 个用户")

    async def create_player_profiles(self):
        """为用户创建选手档案"""
        print("创建选手档案...")
        
        for user in self.users:
            # 随机选择赛区
            region = random.choice(self.regions)
            
            # 随机选择位置和段位
            position = random.choice(POSITIONS)
            rank = random.choice(RANKS)
            
            # 生成游戏数据
            current_rating = random.randint(800, 2500)
            peak_rating = current_rating + random.randint(0, 500)
            
            # 生成唯一的profile_id
            import uuid
            profile_uuid = str(uuid.uuid4()).replace('-', '')[:32]
            
            profile_id = await self.db.fetchval("""
                INSERT INTO player_profiles (
                    profile_id, user_id, region_id, player_name, summoner_name, 
                    position, current_rating, peak_rating, contract_status,
                    description, total_matches, total_wins, total_losses
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """, 
                profile_uuid,
                user["id"], 
                region["id"], 
                user["username"], 
                user["summoner_name"],
                position,
                current_rating,
                peak_rating,
                "FREE",
                f"来自{region['name']}的{position}位选手，峰值{rank}段位",
                0, 0, 0
            )
            
            self.player_profiles.append({
                "id": profile_id,
                "user_id": user["id"],
                "region_id": region["id"],
                "username": user["username"],
                "position": position,
                "rating": current_rating
            })
        
        print(f"  完成创建 {len(self.users)} 个选手档案")

    async def create_teams(self, teams_per_region: int = 8):
        """创建战队"""
        print(f"为每个赛区创建 {teams_per_region} 支战队...")
        
        used_team_names = set()
        
        for region in self.regions:
            # 获取该赛区的选手
            region_players = [p for p in self.player_profiles if p["region_id"] == region["id"]]
            random.shuffle(region_players)
            
            for i in range(teams_per_region):
                # 选择队长（确保不是已经在其他队伍的）
                available_captains = [p for p in region_players 
                                    if not any(t.get("captain_id") == p["id"] for t in self.teams)]
                
                if not available_captains:
                    print(f"  警告: {region['name']} 没有足够的队长候选人")
                    break
                
                captain = available_captains[0]
                
                # 生成队伍名称
                team_name = random.choice(REAL_TEAM_NAMES)
                while f"{team_name}_{region['id']}" in used_team_names:
                    team_name = random.choice(REAL_TEAM_NAMES)
                used_team_names.add(f"{team_name}_{region['id']}")
                
                # 生成队伍标签
                tag = team_name[:4].upper()
                if len(tag) < 3:
                    tag += str(random.randint(10, 99))
                
                team_id = await self.db.fetchval("""
                    INSERT INTO teams (
                        name, tag, description, region_id, captain_user_id,
                        is_active, is_recruiting
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """,
                    team_name,
                    tag,
                    f"{region['name']}的强力战队，目标是夺得冠军！",
                    region["id"],
                    captain["user_id"],
                    True,
                    random.choice([True, False])
                )
                
                self.teams.append({
                    "id": team_id,
                    "name": team_name,
                    "tag": tag,
                    "region_id": region["id"],
                    "captain_id": captain["id"],
                    "captain_user_id": captain["user_id"],
                    "members": []
                })
                
                # 队长加入队伍
                await self.db.execute("""
                    INSERT INTO team_members (team_id, user_id, position, is_substitute, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                """, team_id, captain["user_id"], captain["position"], False, True)
                
                # 更新选手的队伍信息
                await self.db.execute("""
                    UPDATE player_profiles SET current_team_id = $1, contract_status = $2
                    WHERE id = $3
                """, team_id, "LOCKED", captain["id"])
                
                print(f"  创建战队: {team_name} (队长: {captain['username']})")

    async def add_team_members(self):
        """为战队添加队员"""
        print("为战队添加队员...")
        
        for team in self.teams:
            region_id = team["region_id"]
            
            # 获取该赛区未加入战队的选手
            available_players = []
            for profile in self.player_profiles:
                if profile["region_id"] == region_id and profile["id"] != team["captain_id"]:
                    # 检查是否已经在其他队伍
                    is_in_team = await self.db.fetchval("""
                        SELECT EXISTS(
                            SELECT 1 FROM team_members 
                            WHERE user_id = $1 AND is_active = true
                        )
                    """, profile["user_id"])
                    
                    if not is_in_team:
                        available_players.append(profile)
            
            # 随机添加2-4个队员
            num_members = random.randint(2, 4)
            selected_players = random.sample(available_players, min(num_members, len(available_players)))
            
            for player in selected_players:
                # 选择位置（尽量不重复）
                existing_positions = await self.db.fetch("""
                    SELECT position FROM team_members 
                    WHERE team_id = $1 AND is_active = true
                """, team["id"])
                existing_pos_list = [row["position"] for row in existing_positions]
                
                # 选择一个尚未占用的位置
                available_positions = [pos for pos in POSITIONS if pos not in existing_pos_list]
                if available_positions:
                    position = random.choice(available_positions)
                else:
                    position = random.choice(POSITIONS)  # 如果都占了就随便选一个
                
                await self.db.execute("""
                    INSERT INTO team_members (team_id, user_id, position, is_substitute, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                """, team["id"], player["user_id"], position, False, True)
                
                # 更新选手状态
                await self.db.execute("""
                    UPDATE player_profiles SET current_team_id = $1, contract_status = $2
                    WHERE id = $3
                """, team["id"], "LOCKED", player["id"])
                
                team["members"].append(player)
            
            print(f"  战队 {team['name']} 添加了 {len(selected_players)} 名队员")

    async def create_tournament(self, region_id: int) -> int:
        """创建赛事"""
        tournament_names = [
            "春季联赛", "夏季锦标赛", "秋季杯赛", "冬季总决赛",
            "青春风暴杯", "王者争霸赛", "峡谷传说杯", "钻石联赛",
            "新秀挑战赛", "老炮归来赛"
        ]
        
        tournament_name = f"{random.choice(tournament_names)} - {datetime.now().strftime('%Y')}"
        
        # 设置时间
        now = datetime.now()
        registration_start = now - timedelta(days=10)
        registration_end = now - timedelta(days=3)
        tournament_start = now + timedelta(days=1)
        tournament_end = now + timedelta(days=15)
        
        # 生成UUID
        import uuid
        tournament_uuid = uuid.uuid4()
        
        tournament_id = await self.db.fetchval("""
            INSERT INTO tournaments (
                id, region_id, name, tournament_type, status, format, max_participants,
                registration_start, registration_end, tournament_start, tournament_end,
                description, created_by, min_rank, max_rank, team_size
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            RETURNING id
        """,
            tournament_uuid,
            region_id,
            tournament_name,
            "team_based",
            "registration_closed",
            "single_elimination",
            16,
            registration_start,
            registration_end,
            tournament_start,
            tournament_end,
            f"激烈的电竞对战即将开始！{tournament_name}欢迎各路高手参加！",
            1,  # admin user
            "BRONZE",
            "CHALLENGER",
            5
        )
        
        print(f"  创建赛事: {tournament_name} (ID: {tournament_id})")
        return tournament_id

    async def register_teams_for_tournament(self, tournament_id: int, region_id: int):
        """为赛事报名战队"""
        # 获取该赛区的战队
        region_teams = [t for t in self.teams if t["region_id"] == region_id]
        
        # 随机选择8-12支队伍报名
        num_teams = min(random.randint(8, 12), len(region_teams))
        participating_teams = random.sample(region_teams, num_teams)
        
        for team in participating_teams:
            # 为每个team生成UUID作为participant_id
            import uuid
            participant_uuid = uuid.uuid4()
            registration_uuid = uuid.uuid4()
            
            from datetime import datetime
            registration_id = await self.db.fetchval("""
                INSERT INTO tournament_registrations (
                    id, tournament_id, participant_id, participant_type, 
                    status, registered_by, registered_at, is_admin_registered
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                registration_uuid,
                tournament_id,
                participant_uuid,  # 使用生成的UUID
                "team",
                "confirmed",
                team["captain_user_id"],
                datetime.now(),
                False
            )
            
            print(f"    战队 {team['name']} 报名成功")
        
        return participating_teams

    async def create_tournaments_and_registrations(self):
        """创建赛事和报名数据"""
        print("创建赛事和报名数据...")
        
        for region in self.regions:
            # 为每个赛区创建1-2个赛事
            num_tournaments = random.randint(1, 2)
            
            for i in range(num_tournaments):
                tournament_id = await self.create_tournament(region["id"])
                participating_teams = await self.register_teams_for_tournament(tournament_id, region["id"])
                print(f"    {region['name']} 的赛事有 {len(participating_teams)} 支队伍报名")

    async def generate_test_data(self):
        """生成所有测试数据"""
        print("开始生成测试数据...\n")
        
        try:
            await self.connect_db()
            await self.clear_existing_data()
            await self.create_users(80)  # 先创建用户
            await self.create_regions()  # 再创建赛区，因为需要admin_user_id
            await self.create_player_profiles()
            await self.create_teams(6)  # 每个赛区6支队伍
            await self.add_team_members()
            await self.create_tournaments_and_registrations()
            
            print("\n测试数据生成完成！")
            print("\n数据统计:")
            print(f"  - 赛区: {len(self.regions)} 个")
            print(f"  - 用户: {len(self.users)} 个")
            print(f"  - 选手档案: {len(self.player_profiles)} 个") 
            print(f"  - 战队: {len(self.teams)} 支")
            
            # 统计每个赛区的队伍数量
            for region in self.regions:
                region_team_count = len([t for t in self.teams if t["region_id"] == region["id"]])
                print(f"    - {region['name']}: {region_team_count} 支战队")
            
            print("\n测试账号:")
            print("  - 管理员: admin / admin123")
            print(f"  - 普通用户: {self.users[0]['username']} / password123")
            print(f"  - 召唤师名: {self.users[0]['summoner_name']}")
            
        except Exception as e:
            print(f"生成测试数据失败: {e}")
            raise
        finally:
            await self.close_db()

async def main():
    generator = TestDataGenerator()
    await generator.generate_test_data()

if __name__ == "__main__":
    asyncio.run(main())