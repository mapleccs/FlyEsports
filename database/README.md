# 数据库设置说明

## 选择1：使用Docker（推荐）

如果使用Docker开发环境，数据库会自动创建和配置：

```bash
# 启动所有服务（包括数据库）
docker-compose up -d

# 运行数据库迁移
docker-compose exec backend alembic upgrade head
```

## 选择2：本地PostgreSQL设置

如果您选择使用本地PostgreSQL，请按以下步骤操作：

### 1. 安装PostgreSQL
确保本地已安装PostgreSQL并且服务正在运行。

### 2. 创建数据库
有两种方式创建数据库：

**方式A：使用SQL脚本**
```bash
# 以postgres用户身份连接到PostgreSQL
psql -U postgres -h localhost

# 运行数据库创建脚本
\i database/setup_local_db.sql
```

**方式B：使用命令行**
```bash
# 创建数据库
createdb -U postgres -h localhost flyesports

# 验证数据库创建成功
psql -U postgres -h localhost -l | grep flyesports
```

### 3. 运行数据库迁移
```bash
# 进入后端目录
cd backend

# 运行迁移
alembic upgrade head
```

### 4. 验证设置
```bash
# 连接到数据库
psql -U postgres -h localhost -d flyesports

# 查看创建的表
\dt

# 查看表结构
\d+ users
```

## 数据库连接信息

- **主机**: localhost
- **端口**: 5432
- **数据库名**: flyesports
- **用户名**: postgres
- **密码**: postgres
- **连接URL**: postgresql+asyncpg://postgres:postgres@localhost:5432/flyesports

## 故障排除

### 连接被拒绝
1. 确认PostgreSQL服务正在运行
2. 检查端口5432是否被占用
3. 确认pg_hba.conf配置允许本地连接

### 权限错误
1. 确保postgres用户有创建数据库的权限
2. 检查数据库所有者权限

### 迁移失败
1. 确保数据库连接配置正确
2. 检查alembic配置文件
3. 查看错误日志获取详细信息