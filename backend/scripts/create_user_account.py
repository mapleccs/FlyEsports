#!/usr/bin/env python3
"""
为用户创建测试账号的脚本
"""

import asyncio
import sys
import uuid
from datetime import datetime

# 添加项目路径
sys.path.append('/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
from passlib.context import CryptContext

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user_account(session: AsyncSession, username: str, email: str, password: str):
    """创建用户账号"""
    print(f"创建用户账号: {username} ({email})")
    
    # 加密密码
    hashed_password = pwd_context.hash(password)
    
    try:
        # 创建用户
        result = await session.execute(text("""
            INSERT INTO users (username, email, password_hash, riot_summoner_name, is_active, is_verified, created_at, updated_at)
            VALUES (:username, :email, :password_hash, :summoner_name, true, true, :created_at, :updated_at)
            RETURNING id
        """), {
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'summoner_name': username,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        user_id = result.scalar()
        
        # 查找默认用户角色
        role_result = await session.execute(text("""
            SELECT id FROM roles WHERE name = 'user'
        """))
        role_id = role_result.scalar()
        
        if role_id:
            # 分配用户角色
            await session.execute(text("""
                INSERT INTO user_roles (user_id, role_id, is_active, created_at, updated_at)
                VALUES (:user_id, :role_id, true, :created_at, :updated_at)
            """), {
                'user_id': user_id,
                'role_id': role_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        await session.commit()
        print(f"用户账号创建成功，用户ID: {user_id}")
        return user_id
        
    except Exception as e:
        await session.rollback()
        print(f"创建用户账号失败: {e}")
        return None

async def main():
    """主函数"""
    print("开始创建用户测试账号...")
    
    try:
        await database_manager.connect()
        
        async with database_manager.get_session() as session:
            # 创建用户请求的测试账号
            users_to_create = [
                ('testuser', '468355490@qq.com', 'password123'),
                ('user1', 'user1@example.com', 'password123'),
                ('user2', 'user2@example.com', 'password123'),
            ]
            
            created_users = []
            for username, email, password in users_to_create:
                # 检查用户是否已存在
                check_result = await session.execute(text("""
                    SELECT id FROM users WHERE username = :username OR email = :email
                """), {'username': username, 'email': email})
                
                if check_result.fetchone():
                    print(f"用户 {username} ({email}) 已存在，跳过创建")
                    continue
                
                user_id = await create_user_account(session, username, email, password)
                if user_id:
                    created_users.append((username, email))
            
            print(f"\n=== 账号创建完成 ===")
            if created_users:
                print("新创建的账号:")
                for username, email in created_users:
                    print(f"- 用户名: {username}, 邮箱: {email}, 密码: password123")
            else:
                print("没有新账号被创建")
        
        await database_manager.disconnect()
        
    except Exception as e:
        print(f"操作失败: {e}")
        import traceback
        traceback.print_exc()
        await database_manager.disconnect()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n用户账号创建成功！")
    else:
        print("\n用户账号创建失败！")
        sys.exit(1)