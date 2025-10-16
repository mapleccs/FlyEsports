#!/usr/bin/env python3
"""
修复tournament_registrations表中的participant_id

将随机生成的UUID替换为实际的团队ID或选手profile_id
"""

import asyncio
import asyncpg
import random
from datetime import datetime
from typing import List, Dict, Any

# 数据库连接配置
DATABASE_URL = "postgresql://postgres:postgres@flyesports_postgres:5432/flyesports"


class ParticipantIDFixer:
    def __init__(self):
        self.db = None
        self.teams = []
        self.players = []

    async def connect(self):
        """连接数据库"""
        self.db = await asyncpg.connect(DATABASE_URL)
        print("已连接到数据库")

    async def disconnect(self):
        """断开数据库连接"""
        if self.db:
            await self.db.close()
            print("已断开数据库连接")

    async def load_teams_and_players(self):
        """加载所有团队和选手数据"""
        print("加载团队和选手数据...")

        # 加载团队数据
        teams_data = await self.db.fetch("""
            SELECT t.id, t.name, t.region_id, u.id as captain_user_id
            FROM teams t
            JOIN users u ON t.captain_user_id = u.id
            WHERE t.is_active = true
            ORDER BY t.region_id, t.id
        """)

        self.teams = [dict(row) for row in teams_data]
        print(f"加载了 {len(self.teams)} 支团队")

        # 加载选手数据
        players_data = await self.db.fetch("""
            SELECT pp.id, pp.profile_id, pp.user_id, pp.region_id, u.username
            FROM player_profiles pp
            JOIN users u ON pp.user_id = u.id
            ORDER BY pp.region_id, pp.id
        """)

        self.players = [dict(row) for row in players_data]
        print(f"加载了 {len(self.players)} 名选手")

    async def fix_tournament_registrations(self):
        """修复赛事报名记录中的participant_id"""
        print("开始修复tournament_registrations...")

        # 获取所有需要修复的报名记录
        registrations = await self.db.fetch("""
            SELECT tr.id, tr.tournament_id, tr.participant_id, tr.participant_type,
                   tr.registered_by, t.region_id as tournament_region_id
            FROM tournament_registrations tr
            JOIN tournaments t ON tr.tournament_id = t.id
            ORDER BY tr.tournament_id, tr.participant_type
        """)

        print(f"找到 {len(registrations)} 条报名记录需要修复")

        fixed_count = 0
        for reg in registrations:
            new_participant_id = None

            if reg['participant_type'] == 'team':
                # 为团队类型选择一个合适的团队ID
                # 优先选择同赛区的团队
                same_region_teams = [t for t in self.teams if t['region_id'] == reg['tournament_region_id']]
                if same_region_teams:
                    # 随机选择一个团队，但确保不重复
                    available_teams = [t for t in same_region_teams
                                     if not await self._is_team_already_registered(t['id'], reg['tournament_id'])]
                    if available_teams:
                        chosen_team = random.choice(available_teams)
                        new_participant_id = str(chosen_team['id'])
                    else:
                        # 如果同赛区没有可用团队，从其他赛区选择
                        all_available_teams = [t for t in self.teams
                                             if not await self._is_team_already_registered(t['id'], reg['tournament_id'])]
                        if all_available_teams:
                            chosen_team = random.choice(all_available_teams)
                            new_participant_id = str(chosen_team['id'])

            elif reg['participant_type'] == 'player':
                # 为选手类型选择一个合适的选手profile_id
                same_region_players = [p for p in self.players if p['region_id'] == reg['tournament_region_id']]
                if same_region_players:
                    # 随机选择一个选手，但确保不重复
                    available_players = [p for p in same_region_players
                                       if not await self._is_player_already_registered(p['profile_id'], reg['tournament_id'])]
                    if available_players:
                        chosen_player = random.choice(available_players)
                        new_participant_id = chosen_player['profile_id']
                    else:
                        # 如果同赛区没有可用选手，从其他赛区选择
                        all_available_players = [p for p in self.players
                                               if not await self._is_player_already_registered(p['profile_id'], reg['tournament_id'])]
                        if all_available_players:
                            chosen_player = random.choice(all_available_players)
                            new_participant_id = chosen_player['profile_id']

            # 更新数据库记录
            if new_participant_id:
                await self.db.execute("""
                    UPDATE tournament_registrations
                    SET participant_id = $1, updated_at = $2
                    WHERE id = $3
                """, new_participant_id, datetime.now(), reg['id'])

                fixed_count += 1
                print(f"  修复记录 {reg['id']}: {reg['participant_type']} -> {new_participant_id}")
            else:
                print(f"  警告: 无法为记录 {reg['id']} 找到合适的 {reg['participant_type']}")

        print(f"共修复了 {fixed_count} 条记录")

    async def _is_team_already_registered(self, team_id: int, tournament_id: str) -> bool:
        """检查团队是否已经报名了该赛事"""
        result = await self.db.fetchval("""
            SELECT COUNT(*) FROM tournament_registrations
            WHERE tournament_id = $1 AND participant_id = $2 AND participant_type = 'team'
        """, tournament_id, str(team_id))
        return result > 0

    async def _is_player_already_registered(self, profile_id: str, tournament_id: str) -> bool:
        """检查选手是否已经报名了该赛事"""
        result = await self.db.fetchval("""
            SELECT COUNT(*) FROM tournament_registrations
            WHERE tournament_id = $1 AND participant_id = $2 AND participant_type = 'player'
        """, tournament_id, profile_id)
        return result > 0

    async def verify_fix(self):
        """验证修复结果"""
        print("验证修复结果...")

        # 检查团队类型的participant_id是否都是有效的团队ID
        invalid_teams = await self.db.fetch("""
            SELECT tr.id, tr.participant_id, tr.participant_type
            FROM tournament_registrations tr
            LEFT JOIN teams t ON tr.participant_id::integer = t.id
            WHERE tr.participant_type = 'team' AND t.id IS NULL
        """)

        if invalid_teams:
            print(f"发现 {len(invalid_teams)} 个无效的团队participant_id:")
            for reg in invalid_teams:
                print(f"  记录ID: {reg['id']}, participant_id: {reg['participant_id']}")
        else:
            print("所有团队类型的participant_id都有效")

        # 检查选手类型的participant_id是否都是有效的profile_id
        invalid_players = await self.db.fetch("""
            SELECT tr.id, tr.participant_id, tr.participant_type
            FROM tournament_registrations tr
            LEFT JOIN player_profiles pp ON tr.participant_id = pp.profile_id
            WHERE tr.participant_type = 'player' AND pp.id IS NULL
        """)

        if invalid_players:
            print(f"发现 {len(invalid_players)} 个无效的选手participant_id:")
            for reg in invalid_players:
                print(f"  记录ID: {reg['id']}, participant_id: {reg['participant_id']}")
        else:
            print("所有选手类型的participant_id都有效")

    async def run(self):
        """运行修复程序"""
        try:
            await self.connect()
            await self.load_teams_and_players()
            await self.fix_tournament_registrations()
            await self.verify_fix()
        finally:
            await self.disconnect()


async def main():
    """主函数"""
    print("开始修复participant_id...")
    fixer = ParticipantIDFixer()
    await fixer.run()
    print("修复完成！")


if __name__ == "__main__":
    asyncio.run(main())