# FlyEsports

专业的电竞赛事管理平台，旨在替代传统的"QQ群 + Excel"赛事管理模式，提供系统化、自动化的线上赛事管理解决方案。

## 项目特性

- **现代化架构**: 采用领域驱动设计(DDD) + 清洁架构
- **高性能后端**: FastAPI + SQLAlchemy 2.0 + PostgreSQL + Redis
- **现代化前端**: Vue 3 + TypeScript + Vite + Ant Design Vue
- **容器化部署**: Docker + docker-compose
- **自动化数据**: 集成Riot Games API实现比赛数据自动化处理

## 快速开始

### 环境要求

- Docker & Docker Compose
- Node.js 18+ (本地开发)
- Python 3.11+ (本地开发)

### 使用Docker运行

1. 克隆项目
```bash
git clone <repository-url>
cd FlyEsports
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，修改相关配置
```

3. 启动服务
```bash
docker-compose up -d
```

4. 访问应用
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 本地开发

#### 后端开发

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
FlyEsports/
├── backend/                    # 后端API服务
│   ├── src/
│   │   ├── domain/            # 领域层
│   │   ├── application/       # 应用层
│   │   ├── infrastructure/    # 基础设施层
│   │   ├── presentation/      # 表现层
│   │   └── core/             # 核心配置
│   ├── tests/                 # 测试文件
│   ├── requirements.txt       # Python依赖
│   └── Dockerfile            # Docker配置
├── frontend/                  # 前端Web应用
│   ├── src/
│   │   ├── features/         # 特性模块
│   │   ├── shared/           # 共享组件
│   │   └── router/           # 路由配置
│   ├── package.json          # Node.js依赖
│   └── Dockerfile           # Docker配置
├── docker-compose.yml        # 开发环境配置
├── docker-compose.prod.yml   # 生产环境配置
└── CLAUDE.md                # 项目开发指南
```

## 开发规范

请参阅 `CLAUDE.md` 文件了解详细的开发规范和架构设计。

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy 2.0
- **缓存**: Redis
- **任务队列**: Celery
- **认证**: JWT

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件**: Ant Design Vue 4.x
- **状态管理**: Pinia
- **路由**: Vue Router 4

### 基础设施
- **容器化**: Docker + Docker Compose
- **代理**: Nginx
- **监控**: 待实现
- **CI/CD**: 待实现

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。