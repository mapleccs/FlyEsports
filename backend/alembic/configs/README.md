# Alembic 配置文件管理

## 配置文件说明

### `alembic_simple.ini` (当前使用)
- **用途**: 项目当前阶段的标准配置
- **特点**: 简洁、实用，包含核心迁移管理功能
- **维护**: 易于理解和维护
- **状态**: ✅ 当前激活

### `alembic_enterprise.ini` (备用)
- **用途**: 未来企业级部署时的高级配置
- **特点**: 包含监控、告警、多环境支持等企业级特性
- **维护**: 复杂配置，适用于大规模生产环境
- **状态**: 🔄 备用配置

## 使用方法

### 切换到简洁配置 (默认)
```bash
cp alembic/configs/alembic_simple.ini alembic.ini
```

### 切换到企业配置 (生产环境)
```bash
cp alembic/configs/alembic_enterprise.ini alembic.ini
```

## 配置选择指南

- **开发阶段**: 使用 `alembic_simple.ini`
- **测试环境**: 使用 `alembic_simple.ini`
- **生产环境**: 考虑使用 `alembic_enterprise.ini`

## 注意事项

1. 修改配置后需要重启相关服务
2. 企业配置需要额外的环境变量支持
3. 保持 `alembic.ini` 为当前使用的配置文件