#!/usr/bin/env python3
"""
现代化字典表数据初始化脚本

使用 DictionaryService 统一初始化所有字典表数据
支持数据更新、验证和缓存预热
"""

import asyncio
import sys
import structlog
from pathlib import Path
from typing import Dict, List, Any

# 添加src目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.connection import database_manager
from src.infrastructure.services.dictionary_service import DictionaryService, create_dictionary_service

logger = structlog.get_logger(__name__)


# 字典表数据定义
DICTIONARY_DATA = {
    'tournament_statuses': [
        {'code': 'draft', 'name': '草稿', 'display_name': '草稿', 'description': '赛事正在筹备中，尚未发布', 'sort_order': 1},
        {'code': 'upcoming', 'name': '即将开始', 'display_name': '即将开始', 'description': '赛事已发布，即将开始报名', 'sort_order': 2},
        {'code': 'registration_open', 'name': '报名开放', 'display_name': '报名开放', 'description': '赛事正在接受报名', 'sort_order': 3},
        {'code': 'registration_closed', 'name': '报名结束', 'display_name': '报名结束', 'description': '报名已截止，等待比赛开始', 'sort_order': 4},
        {'code': 'ongoing', 'name': '进行中', 'display_name': '进行中', 'description': '比赛正在进行', 'sort_order': 5},
        {'code': 'completed', 'name': '已完成', 'display_name': '已完成', 'description': '比赛已结束', 'sort_order': 6},
        {'code': 'cancelled', 'name': '已取消', 'display_name': '已取消', 'description': '比赛被取消', 'sort_order': 7},
    ],

    'tournament_types': [
        {'code': 'team_based', 'name': '战队赛', 'display_name': '战队赛', 'description': '以战队为单位参赛', 'sort_order': 1},
        {'code': 'solo_based', 'name': '个人赛', 'display_name': '个人赛', 'description': '以个人为单位参赛', 'sort_order': 2},
    ],

    'tournament_formats': [
        {'code': 'single_elimination', 'name': '单败淘汰', 'display_name': '单败淘汰', 'description': '输一场即淘汰的赛制', 'sort_order': 1},
        {'code': 'double_elimination', 'name': '双败淘汰', 'display_name': '双败淘汰', 'description': '败者组重生的赛制', 'sort_order': 2},
        {'code': 'round_robin', 'name': '循环积分', 'display_name': '循环积分', 'description': '所有队伍互相对战的赛制', 'sort_order': 3},
        {'code': 'swiss', 'name': '瑞士轮', 'display_name': '瑞士轮', 'description': '按胜负分组对战的赛制', 'sort_order': 4},
        {'code': 'custom', 'name': '自定义', 'display_name': '自定义', 'description': '自定义赛制规则', 'sort_order': 5},
    ],

    'registration_statuses': [
        {'code': 'pending', 'name': '待审核', 'display_name': '待审核', 'description': '报名申请等待管理员审核', 'sort_order': 1},
        {'code': 'confirmed', 'name': '已确认', 'display_name': '已确认', 'description': '报名申请已通过审核', 'sort_order': 2},
        {'code': 'rejected', 'name': '已拒绝', 'display_name': '已拒绝', 'description': '报名申请被拒绝', 'sort_order': 3},
        {'code': 'withdrawn', 'name': '已退出', 'display_name': '已退出', 'description': '主动退出比赛', 'sort_order': 4},
    ],

    'match_statuses': [
        {'code': 'scheduled', 'name': '已安排', 'display_name': '已安排', 'description': '比赛已安排但未开始', 'sort_order': 1},
        {'code': 'waiting_for_checkin', 'name': '等待签到', 'display_name': '等待签到', 'description': '等待选手签到', 'sort_order': 2},
        {'code': 'checking_in', 'name': '签到中', 'display_name': '签到中', 'description': '正在进行签到', 'sort_order': 3},
        {'code': 'ready', 'name': '准备就绪', 'display_name': '准备就绪', 'description': '双方都已签到，准备开始', 'sort_order': 4},
        {'code': 'in_progress', 'name': '进行中', 'display_name': '进行中', 'description': '比赛正在进行', 'sort_order': 5},
        {'code': 'completed', 'name': '已完成', 'display_name': '已完成', 'description': '比赛已结束', 'sort_order': 6},
        {'code': 'cancelled', 'name': '已取消', 'display_name': '已取消', 'description': '比赛被取消', 'sort_order': 7},
    ],

    'checkin_statuses': [
        {'code': 'not_checked_in', 'name': '未签到', 'display_name': '未签到', 'description': '选手尚未签到', 'sort_order': 1},
        {'code': 'checked_in', 'name': '已签到', 'display_name': '已签到', 'description': '选手已完成签到', 'sort_order': 2},
        {'code': 'missed', 'name': '错过签到', 'display_name': '错过签到', 'description': '选手错过了签到时间', 'sort_order': 3},
    ],

    'contract_statuses': [
        {'code': 'trial', 'name': '试训', 'display_name': '试训', 'description': '试训期成员', 'sort_order': 1},
        {'code': 'contracted', 'name': '正式合约', 'display_name': '正式合约', 'description': '签署正式合约的成员', 'sort_order': 2},
        {'code': 'substitute', 'name': '替补', 'display_name': '替补', 'description': '替补成员', 'sort_order': 3},
        {'code': 'released', 'name': '已释放', 'display_name': '已释放', 'description': '合约已解除', 'sort_order': 4},
    ],

    'player_positions': [
        {'code': 'top', 'name': '上单', 'display_name': '上单', 'description': '上路位置', 'sort_order': 1},
        {'code': 'jungle', 'name': '打野', 'display_name': '打野', 'description': '野区位置', 'sort_order': 2},
        {'code': 'mid', 'name': '中单', 'display_name': '中单', 'description': '中路位置', 'sort_order': 3},
        {'code': 'adc', 'name': 'ADC', 'display_name': 'ADC', 'description': '下路输出位置', 'sort_order': 4},
        {'code': 'support', 'name': '辅助', 'display_name': '辅助', 'description': '下路辅助位置', 'sort_order': 5},
        {'code': 'coach', 'name': '教练', 'display_name': '教练', 'description': '战队教练', 'sort_order': 6},
        {'code': 'analyst', 'name': '分析师', 'display_name': '分析师', 'description': '数据分析师', 'sort_order': 7},
        {'code': 'manager', 'name': '经理', 'display_name': '经理', 'description': '战队经理', 'sort_order': 8},
    ],

    'bp_room_statuses': [
        {'code': 'waiting', 'name': '等待中', 'display_name': '等待中', 'description': '等待选手进入房间', 'sort_order': 1},
        {'code': 'ready', 'name': '准备就绪', 'display_name': '准备就绪', 'description': '双方都已进入，准备开始', 'sort_order': 2},
        {'code': 'ban_pick', 'name': 'BP中', 'display_name': 'BP中', 'description': '正在进行英雄禁选', 'sort_order': 3},
        {'code': 'completed', 'name': '已完成', 'display_name': '已完成', 'description': '禁选流程已完成', 'sort_order': 4},
        {'code': 'cancelled', 'name': '已取消', 'display_name': '已取消', 'description': '房间被取消', 'sort_order': 5},
    ],

    'bp_room_types': [
        {'code': 'ranked_5v5', 'name': '排位5V5', 'display_name': '排位5V5', 'description': '5V5排位赛模式', 'sort_order': 1},
        {'code': 'tournament', 'name': '比赛模式', 'display_name': '比赛模式', 'description': '正式比赛模式', 'sort_order': 2},
        {'code': 'practice', 'name': '训练赛', 'display_name': '训练赛', 'description': '训练赛模式', 'sort_order': 3},
    ],

    'bp_session_statuses': [
        {'code': 'waiting', 'name': '等待开始', 'display_name': '等待开始', 'description': '等待BP环节开始', 'sort_order': 1},
        {'code': 'banning', 'name': '禁用阶段', 'display_name': '禁用阶段', 'description': '正在禁用英雄', 'sort_order': 2},
        {'code': 'picking', 'name': '选择阶段', 'display_name': '选择阶段', 'description': '正在选择英雄', 'sort_order': 3},
        {'code': 'completed', 'name': '已完成', 'display_name': '已完成', 'description': 'BP环节已完成', 'sort_order': 4},
    ],

    'bp_phases': [
        {'code': 'ban1', 'name': '第一轮禁用', 'display_name': '第一轮禁用', 'description': '第一轮英雄禁用', 'sort_order': 1},
        {'code': 'pick1', 'name': '第一轮选择', 'display_name': '第一轮选择', 'description': '第一轮英雄选择', 'sort_order': 2},
        {'code': 'ban2', 'name': '第二轮禁用', 'display_name': '第二轮禁用', 'description': '第二轮英雄禁用', 'sort_order': 3},
        {'code': 'pick2', 'name': '第二轮选择', 'display_name': '第二轮选择', 'description': '第二轮英雄选择', 'sort_order': 4},
        {'code': 'ban3', 'name': '第三轮禁用', 'display_name': '第三轮禁用', 'description': '第三轮英雄禁用', 'sort_order': 5},
        {'code': 'pick3', 'name': '第三轮选择', 'display_name': '第三轮选择', 'description': '第三轮英雄选择', 'sort_order': 6},
    ],

    'bp_actions': [
        {'code': 'ban', 'name': '禁用', 'display_name': '禁用', 'description': '禁用英雄', 'sort_order': 1},
        {'code': 'pick', 'name': '选择', 'display_name': '选择', 'description': '选择英雄', 'sort_order': 2},
        {'code': 'swap', 'name': '交换', 'display_name': '交换', 'description': '交换英雄', 'sort_order': 3},
    ],

    'bp_participant_roles': [
        {'code': 'admin', 'name': '管理员', 'display_name': '管理员', 'description': '房间管理员', 'sort_order': 1},
        {'code': 'player', 'name': '选手', 'display_name': '选手', 'description': '参赛选手', 'sort_order': 2},
        {'code': 'observer', 'name': '观察者', 'display_name': '观察者', 'description': '观赛人员', 'sort_order': 3},
    ],

    'bp_teams': [
        {'code': 'team_a', 'name': 'A队', 'display_name': 'A队', 'description': 'A方队伍', 'sort_order': 1},
        {'code': 'team_b', 'name': 'B队', 'display_name': 'B队', 'description': 'B方队伍', 'sort_order': 2},
    ],
}


async def init_dictionary_data():
    """使用 DictionaryService 初始化字典表数据"""
    logger.info("开始使用 DictionaryService 初始化字典表数据")

    try:
        # 连接数据库
        await database_manager.connect()

        # 获取数据库会话
        async with database_manager.get_session() as session:
            # 创建字典服务
            dictionary_service = await create_dictionary_service(session)

            total_created = 0
            total_updated = 0
            total_skipped = 0

            # 遍历所有字典表
            for dict_name, items in DICTIONARY_DATA.items():
                logger.info(f"正在处理字典表: {dict_name}")

                try:
                    # 获取现有数据
                    existing_items = await dictionary_service.get_all_dict_items(dict_name, use_cache=False)

                    created_count = 0
                    updated_count = 0
                    skipped_count = 0

                    for item_data in items:
                        code = item_data['code']

                        if code in existing_items:
                            # 检查是否需要更新
                            existing_item = existing_items[code]
                            needs_update = False

                            for key, value in item_data.items():
                                if key in existing_item and existing_item[key] != value:
                                    needs_update = True
                                    break

                            if needs_update:
                                # 更新现有项
                                updated_item = await dictionary_service.update_dict_item(
                                    dict_name, code, **item_data
                                )
                                if updated_item:
                                    updated_count += 1
                                    logger.debug(f"更新字典项: {dict_name}.{code}")
                                else:
                                    skipped_count += 1
                                    logger.warning(f"更新失败: {dict_name}.{code}")
                            else:
                                skipped_count += 1
                                logger.debug(f"跳过字典项: {dict_name}.{code} (无变化)")
                        else:
                            # 创建新项
                            try:
                                created_item = await dictionary_service.create_dict_item(
                                    dict_name=dict_name,
                                    **item_data
                                )
                                created_count += 1
                                logger.debug(f"创建字典项: {dict_name}.{code}")
                            except Exception as e:
                                logger.warning(f"创建字典项失败: {dict_name}.{code}, 错误: {e}")
                                skipped_count += 1

                    total_created += created_count
                    total_updated += updated_count
                    total_skipped += skipped_count

                    logger.info(
                        f"字典表 {dict_name} 处理完成",
                        created=created_count,
                        updated=updated_count,
                        skipped=skipped_count
                    )

                except Exception as e:
                    logger.error(f"处理字典表 {dict_name} 时出错: {e}")
                    continue

            logger.info(
                "字典表数据初始化完成",
                total_created=total_created,
                total_updated=total_updated,
                total_skipped=total_skipped
            )

            # 刷新所有缓存
            await dictionary_service.refresh_cache()
            logger.info("字典表缓存已刷新")

            return True

    except Exception as e:
        logger.error(f"初始化字典表数据失败: {e}", exc_info=True)
        return False

    finally:
        # 清理数据库连接
        try:
            await database_manager.disconnect()
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")


async def verify_data():
    """验证数据完整性"""
    logger.info("开始验证字典表数据完整性")

    try:
        # 连接数据库
        await database_manager.connect()

        # 获取数据库会话
        async with database_manager.get_session() as session:
            # 创建字典服务
            dictionary_service = await create_dictionary_service(session)

            verification_passed = True

            for dict_name, expected_items in DICTIONARY_DATA.items():
                try:
                    # 获取实际数据
                    actual_items = await dictionary_service.get_all_dict_items(dict_name, use_cache=False)

                    # 检查数量
                    expected_count = len(expected_items)
                    actual_count = len(actual_items)

                    if actual_count < expected_count:
                        logger.error(
                            f"字典表 {dict_name} 数据不完整",
                            expected=expected_count,
                            actual=actual_count
                        )
                        verification_passed = False

                    # 检查必要的code是否存在
                    for expected_item in expected_items:
                        code = expected_item['code']
                        if code not in actual_items:
                            logger.error(f"字典表 {dict_name} 缺少项目: {code}")
                            verification_passed = False

                    if actual_count >= expected_count:
                        logger.info(f"字典表 {dict_name} 验证通过 ({actual_count}/{expected_count})")

                except Exception as e:
                    logger.error(f"验证字典表 {dict_name} 时出错: {e}")
                    verification_passed = False

            if verification_passed:
                logger.info("所有字典表数据验证通过")
            else:
                logger.error("字典表数据验证失败")

            return verification_passed

    except Exception as e:
        logger.error(f"验证字典表数据时出错: {e}", exc_info=True)
        return False

    finally:
        # 清理数据库连接
        try:
            await database_manager.disconnect()
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="现代化字典表数据初始化脚本")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证数据，不执行初始化"
    )

    args = parser.parse_args()

    if args.verify_only:
        success = await verify_data()
        sys.exit(0 if success else 1)

    # 执行初始化
    success = await init_dictionary_data()

    if success:
        # 验证结果
        verification_success = await verify_data()
        if verification_success:
            logger.info("字典表数据初始化和验证全部成功")
            print("字典表数据初始化成功！")
            sys.exit(0)
        else:
            logger.error("数据初始化成功，但验证失败")
            print("数据验证失败")
            sys.exit(1)
    else:
        logger.error("字典表数据初始化失败")
        print("字典表数据初始化失败")
        sys.exit(1)


if __name__ == "__main__":
    # 配置日志
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 运行主函数
    asyncio.run(main())