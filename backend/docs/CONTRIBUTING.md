# Contributing to FlyEsports

感谢您对FlyEsports项目的贡献！这份文档将帮助您了解如何有效地为项目做出贡献。

## 📋 目录

- [行为准则](#行为准则)
- [开发环境设置](#开发环境设置)
- [贡献类型](#贡献类型)
- [开发流程](#开发流程)
- [代码风格](#代码风格)
- [测试](#测试)
- [提交规范](#提交规范)
- [Pull Request流程](#pull-request流程)
- [发布流程](#发布流程)

## 🤝 行为准则

在参与本项目时，请遵循以下准则：

- 保持友善和专业的态度
- 尊重不同的观点和经验
- 接受建设性的批评
- 专注于对社区最有益的事情
- 对新贡献者表示同理心

## 🛠️ 开发环境设置

### 环境要求

- **Python**: 3.11+
- **Node.js**: 18+
- **Docker**: 最新版本
- **Docker Compose**: 最新版本
- **Git**: 2.28+

### 本地设置

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/FlyEsports.git
   cd FlyEsports
   ```

2. **设置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库和其他服务
   ```

3. **安装Pre-commit Hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **后端设置**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **前端设置**
   ```bash
   cd frontend
   npm install
   ```

6. **启动开发环境**
   ```bash
   # 使用Docker (推荐)
   docker-compose up -d
   
   # 或者分别启动服务
   # 后端
   cd backend && uvicorn src.presentation.api.main:app --reload
   # 前端  
   cd frontend && npm run dev
   ```

## 🎯 贡献类型

我们欢迎以下类型的贡献：

### 🐛 Bug报告
- 使用Bug报告模板
- 提供详细的复现步骤
- 包含系统信息和错误日志

### ✨ 功能请求
- 使用功能请求模板
- 清楚描述用例和预期行为
- 考虑实现的技术可行性

### 💻 代码贡献
- Bug修复
- 新功能实现
- 性能优化
- 重构和代码质量改进

### 📚 文档改进
- API文档
- 用户指南
- 开发者文档
- 代码注释

### 🧪 测试
- 单元测试
- 集成测试
- E2E测试
- 性能测试

## 🔄 开发流程

### Git工作流

我们使用**Git Flow**工作流：

- `main`: 生产分支，始终保持稳定
- `develop`: 开发分支，用于集成功能
- `feature/*`: 功能分支，从develop分出
- `release/*`: 发布分支，准备新版本
- `hotfix/*`: 热修复分支，从main分出

### 分支命名规范

```
feature/user-authentication      # 新功能
bugfix/fix-login-error          # Bug修复
hotfix/critical-security-patch  # 热修复
release/v1.2.0                  # 发布准备
docs/update-api-documentation   # 文档更新
refactor/optimize-database      # 重构
test/add-user-service-tests     # 测试添加
```

## 🎨 代码风格

### 后端 (Python)

我们使用以下工具确保代码质量：

- **Black**: 代码格式化 (line-length=88)
- **isort**: 导入排序
- **flake8**: 代码检查
- **mypy**: 类型检查
- **bandit**: 安全检查

```bash
# 运行代码格式化
cd backend
black src/ tests/
isort src/ tests/

# 运行代码检查
flake8 src/ tests/
mypy src/
```

### 前端 (Vue 3 + TypeScript)

- **Prettier**: 代码格式化
- **ESLint**: 代码检查
- **Vue 3 Composition API**: 优先使用
- **TypeScript**: 严格类型检查

```bash
# 运行代码格式化和检查
cd frontend
npm run lint:fix
npm run format
npm run type-check
```

### 架构约定

#### 后端架构

严格遵循**领域驱动设计 (DDD)** + **清洁架构**：

```
src/
├── domain/           # 领域层 (核心业务逻辑)
├── application/      # 应用层 (用例编排)
├── infrastructure/   # 基础设施层 (外部依赖)
└── presentation/     # 表现层 (API接口)
```

#### 前端架构

采用**特性驱动开发**模式：

```
src/
├── features/         # 按业务功能组织
├── shared/          # 共享组件和工具
└── router/          # 路由配置
```

## 🧪 测试

### 测试要求

- **单元测试**: 覆盖率 > 80%
- **集成测试**: 关键业务流程
- **E2E测试**: 用户核心使用场景

### 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v --cov=src

# 前端测试
cd frontend
npm run test:unit
npm run test:component
npm run test:e2e
```

## 📝 提交规范

我们使用**Conventional Commits**规范：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### 类型 (Type)

- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式(不影响代码运行)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化
- `ci`: CI配置文件和脚本的变动

### 范围 (Scope)

- `backend`: 后端相关
- `frontend`: 前端相关  
- `api`: API相关
- `auth`: 认证相关
- `db`: 数据库相关
- `docker`: Docker相关
- `docs`: 文档相关

### 示例

```
feat(auth): add JWT token refresh functionality

Implement automatic token refresh when tokens are about to expire.
This improves user experience by avoiding forced re-logins.

Closes #123
```

## 🔀 Pull Request流程

### PR准备清单

在提交PR前，请确保：

- [ ] 代码通过所有pre-commit检查
- [ ] 所有测试通过
- [ ] 代码覆盖率没有下降
- [ ] 更新了相关文档
- [ ] 提交信息符合规范
- [ ] PR描述清楚说明了变更内容

### PR模板

使用PR模板填写以下信息：

- **变更类型**: Bug修复/新功能/重构等
- **变更描述**: 详细说明做了什么
- **测试计划**: 如何验证这些变更
- **相关Issue**: 关联的Issue编号
- **截图/演示**: 如果有UI变更

### 代码审查

- 所有PR需要至少一位维护者审查
- 自动CI检查必须通过
- 解决所有审查意见后才能合并
- 使用"Squash and merge"保持提交历史整洁

## 🚀 发布流程

### 版本号规范

我们使用**语义化版本控制 (SemVer)**：

- `MAJOR.MINOR.PATCH` (例如: 1.2.3)
- `MAJOR`: 不兼容的API变更
- `MINOR`: 向后兼容的功能添加
- `PATCH`: 向后兼容的Bug修复

### 发布步骤

1. **创建发布分支**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.2.0
   ```

2. **更新版本信息**
   - 更新package.json版本号
   - 更新CHANGELOG.md
   - 提交变更

3. **合并到main并打标签**
   ```bash
   git checkout main
   git merge release/v1.2.0
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin main --tags
   ```

4. **自动部署**
   - GitHub Actions自动触发部署
   - 监控部署状态和应用健康

## 🆘 获取帮助

如果您需要帮助，可以：

- 查看[项目文档](README.md)
- 浏览[Issue列表](https://github.com/your-repo/issues)
- 加入我们的讨论区
- 联系项目维护者

## 🙏 致谢

感谢所有为FlyEsports项目做出贡献的开发者！每一个贡献都让这个项目变得更好。

---

Happy coding! 🎮✨