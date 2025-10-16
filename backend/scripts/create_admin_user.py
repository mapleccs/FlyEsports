#!/usr/bin/env python3
"""
创建管理员用户脚本
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database.connection import database_manager
import bcrypt

async def create_admin_user():
    """创建管理员用户并分配超级管理员角色"""
    
    await database_manager.connect()
    
    try:
        async with database_manager.get_session() as session:
            # 检查是否已存在admin用户
            result = await session.execute(text("""
                SELECT id, username FROM users WHERE username = 'admin'
            """))
            admin_user = result.fetchone()
            
            if admin_user:
                print(f"[INFO] Admin user already exists (ID: {admin_user[0]})")
                admin_user_id = admin_user[0]
            else:
                # 创建admin用户
                password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                query = text("""
                    INSERT INTO users (username, email, password_hash, is_active, is_verified)
                    VALUES (:username, :email, :password_hash, true, true)
                    RETURNING id
                """)
                result = await session.execute(query, {
                    "username": "admin",
                    "email": "admin@flyesports.com",
                    "password_hash": password_hash
                })
                admin_user_id = result.fetchone()[0]
                print(f"[SUCCESS] Admin user created (ID: {admin_user_id})")
            
            # 检查是否已有超级管理员角色
            result = await session.execute(text("""
                SELECT ur.id FROM user_roles ur 
                WHERE ur.user_id = :user_id AND ur.role_id = 1 AND ur.is_active = true
            """), {"user_id": admin_user_id})
            
            if result.fetchone():
                print("[INFO] Admin user already has super admin role")
            else:
                # 分配超级管理员角色
                query = text("""
                    INSERT INTO user_roles (user_id, role_id, granted_by_user_id, is_active)
                    VALUES (:user_id, 1, :user_id, true)
                """)
                await session.execute(query, {
                    "user_id": admin_user_id,
                })
                print("[SUCCESS] Super admin role assigned to admin user")
            
            await session.commit()
            
            print(f"""
[COMPLETED] Admin user setup completed!
Username: admin
Password: admin123  
Email: admin@flyesports.com
Role: Super Admin (Level 100)

Use these credentials to test the permission system.
            """)
            
    except Exception as e:
        print(f"[ERROR] Error creating admin user: {e}")
        raise
    finally:
        await database_manager.disconnect()

async def main():
    """主函数"""
    print("Starting admin user creation...")
    await create_admin_user()

if __name__ == "__main__":
    asyncio.run(main())