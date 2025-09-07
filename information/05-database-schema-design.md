# FlyEsports 数据库设计文档

## 目录
- [1. 数据库架构概述](#1-数据库架构概述)
- [2. 多租户数据模型](#2-多租户数据模型)
- [3. 核心表结构设计](#3-核心表结构设计)
- [4. 索引策略](#4-索引策略)
- [5. 数据分片与分区](#5-数据分片与分区)
- [6. 时序数据设计](#6-时序数据设计)
- [7. 缓存层设计](#7-缓存层设计)
- [8. 数据一致性保证](#8-数据一致性保证)
- [9. 备份与恢复策略](#9-备份与恢复策略)
- [10. 性能优化方案](#10-性能优化方案)

## 1. 数据库架构概述

### 1.1 技术选型

#### 主数据库：PostgreSQL 15+
```yaml
选型理由:
  - 强大的JSON支持，适合存储复杂的配置数据
  - 优秀的ACID特性保证数据一致性
  - 丰富的索引类型（B-tree, GIN, GIST等）
  - 内置的行级安全（RLS）支持多租户
  - 强大的分区表功能
  - 成熟的生态系统和运维工具
```

#### 时序数据库：TimescaleDB
```yaml
选型理由:
  - 基于PostgreSQL，保持生态一致性
  - 专门为时序数据优化
  - 自动分区和数据压缩
  - 支持连续聚合视图
  - 适合存储评分历史、比赛数据等
```

#### 缓存数据库：Redis Cluster
```yaml
选型理由:
  - 高性能内存数据库
  - 支持多种数据结构
  - 集群模式提供高可用
  - 支持持久化
  - 丰富的过期策略
```

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   PostgreSQL    │  │   TimescaleDB   │  │  Redis Cluster  ││
│  │   (Main Data)   │  │ (Time Series)   │  │    (Cache)      ││
│  │                 │  │                 │  │                 ││
│  │ • Users         │  │ • Rating History│  │ • Leaderboards  ││
│  │ • Players       │  │ • Match Data    │  │ • Session Data  ││
│  │ • Teams         │  │ • Performance   │  │ • Hot Data      ││
│  │ • Regions       │  │ • Analytics     │  │ • Queues        ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
│            • SSD Storage for Hot Data                      │
│            • Archive Storage for Cold Data                 │
│            • Backup Storage (S3-compatible)                │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 数据生命周期管理

```sql
-- 数据生命周期策略
-- Hot Data (0-30天): SSD, 频繁访问
-- Warm Data (30-365天): SSD/HDD混合, 偶尔访问  
-- Cold Data (1年+): 归档存储, 很少访问
-- Archive Data (3年+): 压缩存储, 仅合规需要

-- 自动化数据生命周期管理
CREATE OR REPLACE FUNCTION manage_data_lifecycle()
RETURNS void AS $$
BEGIN
    -- 移动30天前的评分历史到温数据分区
    PERFORM move_to_warm_partition('rating_history', '30 days');
    
    -- 压缩1年前的比赛数据
    PERFORM compress_old_data('match_records', '1 year');
    
    -- 归档3年前的数据
    PERFORM archive_old_data('audit_logs', '3 years');
END;
$$ LANGUAGE plpgsql;
```

## 2. 多租户数据模型

### 2.1 行级安全(RLS)策略

```sql
-- 启用行级安全
ALTER TABLE player_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;

-- 创建赛区访问策略
CREATE POLICY region_isolation_policy ON player_profiles
    USING (region_id = current_setting('app.current_region_id'));

CREATE POLICY team_region_policy ON teams
    USING (region_id = current_setting('app.current_region_id'));

-- 用户访问策略
CREATE POLICY user_data_policy ON users
    USING (user_id = current_setting('app.current_user_id')::uuid);
```

### 2.2 租户上下文设置

```python
# 应用层租户上下文设置
class TenantContext:
    def __init__(self, db_session, user_id: str, region_id: str):
        self.db_session = db_session
        self.user_id = user_id
        self.region_id = region_id
    
    async def __aenter__(self):
        # 设置会话变量
        await self.db_session.execute(
            text("SET app.current_user_id = :user_id"),
            {"user_id": self.user_id}
        )
        await self.db_session.execute(
            text("SET app.current_region_id = :region_id"), 
            {"region_id": self.region_id}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 清理会话变量
        await self.db_session.execute(text("RESET app.current_user_id"))
        await self.db_session.execute(text("RESET app.current_region_id"))

# 使用示例
async with TenantContext(db_session, user_id, region_id):
    players = await db_session.execute(
        select(PlayerProfile).where(PlayerProfile.status == 'active')
    )
```

## 3. 核心表结构设计

### 3.1 用户相关表

#### users 表
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    
    -- 统计字段
    profile_count INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    
    -- 用户偏好 (JSONB)
    preferences JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMPTZ,
    
    -- 索引
    CONSTRAINT users_username_check CHECK (length(username) >= 3),
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE UNIQUE INDEX idx_users_email_active ON users(email) WHERE status = 'active';

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### user_sessions 表
```sql
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    last_used TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_refresh_token ON user_sessions(refresh_token_hash);
```

### 3.2 赛区相关表

#### regions 表
```sql
CREATE TABLE regions (
    region_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_name VARCHAR(100) NOT NULL,
    region_code VARCHAR(10) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance')),
    
    -- 赛区配置
    rating_config JSONB DEFAULT '{
        "base_rating": 50.0,
        "k_factor_base": 32,
        "confidence_growth_rate": 0.02,
        "max_rating": 100.0,
        "min_rating": 0.0
    }',
    
    -- 位置权重配置
    position_weights JSONB DEFAULT '{
        "TOP": {"kda": 0.25, "damage": 0.20, "economy": 0.15, "vision": 0.10, "objective": 0.20, "teamfight": 0.10},
        "JUNGLE": {"kda": 0.20, "damage": 0.15, "economy": 0.15, "vision": 0.25, "objective": 0.25, "teamfight": 0.00},
        "MIDDLE": {"kda": 0.20, "damage": 0.25, "economy": 0.15, "vision": 0.10, "objective": 0.15, "teamfight": 0.15},
        "BOTTOM": {"kda": 0.15, "damage": 0.30, "economy": 0.25, "vision": 0.05, "objective": 0.15, "teamfight": 0.10},
        "UTILITY": {"kda": 0.10, "damage": 0.05, "economy": 0.10, "vision": 0.30, "objective": 0.20, "teamfight": 0.25}
    }',
    
    -- 统计信息
    total_players INTEGER DEFAULT 0,
    active_players INTEGER DEFAULT 0,
    total_teams INTEGER DEFAULT 0,
    active_teams INTEGER DEFAULT 0,
    
    -- 赛季信息
    current_season VARCHAR(50),
    season_start DATE,
    season_end DATE,
    
    -- 管理员列表
    admin_users UUID[] DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_regions_code ON regions(region_code);
CREATE INDEX idx_regions_status ON regions(status);
CREATE TRIGGER update_regions_updated_at
    BEFORE UPDATE ON regions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### transfer_windows 表
```sql
CREATE TABLE transfer_windows (
    window_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id UUID NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    window_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    rules JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT transfer_windows_time_check CHECK (end_time > start_time)
);

CREATE INDEX idx_transfer_windows_region ON transfer_windows(region_id);
CREATE INDEX idx_transfer_windows_time ON transfer_windows(start_time, end_time);
CREATE INDEX idx_transfer_windows_active ON transfer_windows(region_id, is_active) WHERE is_active = true;
```

### 3.3 选手相关表

#### player_profiles 表
```sql
CREATE TABLE player_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    region_id UUID NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    
    -- 基本信息
    player_name VARCHAR(50) NOT NULL,
    summoner_name VARCHAR(50) NOT NULL,
    position VARCHAR(20) NOT NULL CHECK (position IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')),
    description TEXT,
    
    -- 游戏信息
    rank_info JSONB DEFAULT '{}', -- tier, rank, lp, wins, losses
    
    -- 评分信息
    current_rating DECIMAL(5,2) DEFAULT 50.00 CHECK (current_rating >= 0 AND current_rating <= 100),
    locked_rating DECIMAL(5,2),
    confidence_level DECIMAL(3,2) DEFAULT 0.50 CHECK (confidence_level >= 0.5 AND confidence_level <= 0.95),
    total_matches INTEGER DEFAULT 0,
    
    -- 6维度评分
    six_dimensions JSONB DEFAULT '{
        "kda": 50.0,
        "damage": 50.0, 
        "economy": 50.0,
        "vision": 50.0,
        "objective": 50.0,
        "teamfight": 50.0
    }',
    
    -- 合同状态
    contract_status VARCHAR(20) DEFAULT 'FREE' CHECK (contract_status IN ('FREE', 'LOCKED', 'SUSPENDED', 'RETIRED')),
    current_team_id UUID REFERENCES teams(team_id) ON DELETE SET NULL,
    contract_start TIMESTAMPTZ,
    
    -- 统计信息
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'banned')),
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMPTZ,
    
    -- 唯一约束：一个用户在一个赛区只能有一个档案
    UNIQUE(user_id, region_id)
);

-- 索引策略
CREATE INDEX idx_player_profiles_user ON player_profiles(user_id);
CREATE INDEX idx_player_profiles_region ON player_profiles(region_id);
CREATE INDEX idx_player_profiles_position ON player_profiles(region_id, position);
CREATE INDEX idx_player_profiles_rating ON player_profiles(region_id, current_rating DESC);
CREATE INDEX idx_player_profiles_status ON player_profiles(status);
CREATE INDEX idx_player_profiles_contract ON player_profiles(contract_status);
CREATE INDEX idx_player_profiles_team ON player_profiles(current_team_id) WHERE current_team_id IS NOT NULL;
CREATE INDEX idx_player_profiles_summoner ON player_profiles(region_id, summoner_name);

-- 复合索引用于排行榜查询
CREATE INDEX idx_player_leaderboard ON player_profiles(region_id, position, current_rating DESC, confidence_level DESC)
    WHERE status = 'active' AND contract_status IN ('FREE', 'LOCKED');

-- 分区索引
CREATE INDEX idx_player_profiles_created_month ON player_profiles(region_id, date_trunc('month', created_at));

-- 触发器
CREATE TRIGGER update_player_profiles_updated_at
    BEFORE UPDATE ON player_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### rating_history 表 (时序数据)
```sql
-- 使用TimescaleDB创建超表
CREATE TABLE rating_history (
    history_id UUID DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL,
    region_id UUID NOT NULL,
    
    -- 评分变化
    old_rating DECIMAL(5,2) NOT NULL,
    new_rating DECIMAL(5,2) NOT NULL,
    rating_change DECIMAL(5,2) NOT NULL,
    
    -- 变化原因
    reason VARCHAR(50) NOT NULL, -- 'match_result', 'manual_adjustment', 'system_recalculation'
    match_id UUID,
    
    -- 6维度快照
    six_dimensions_snapshot JSONB,
    
    -- 置信度
    confidence_level DECIMAL(3,2),
    
    -- 时间戳
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (profile_id, timestamp)
);

-- 转换为TimescaleDB超表
SELECT create_hypertable('rating_history', 'timestamp', chunk_time_interval => INTERVAL '1 month');

-- 创建索引
CREATE INDEX idx_rating_history_profile ON rating_history(profile_id, timestamp DESC);
CREATE INDEX idx_rating_history_region ON rating_history(region_id, timestamp DESC);
CREATE INDEX idx_rating_history_match ON rating_history(match_id) WHERE match_id IS NOT NULL;

-- 数据保留策略（保留2年数据）
SELECT add_retention_policy('rating_history', INTERVAL '2 years');

-- 压缩策略
ALTER TABLE rating_history SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'profile_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('rating_history', INTERVAL '30 days');
```

### 3.4 战队相关表

#### teams 表
```sql
CREATE TABLE teams (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_name VARCHAR(100) NOT NULL,
    team_tag VARCHAR(10) NOT NULL,
    region_id UUID NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- 基本信息
    description TEXT,
    logo_url TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'disbanded', 'suspended')),
    
    -- 财务信息
    total_cost DECIMAL(8,2) DEFAULT 0.00,
    budget_limit DECIMAL(8,2) DEFAULT 500.00,
    
    -- 统计信息
    total_matches INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(region_id, team_name),
    UNIQUE(region_id, team_tag)
);

CREATE INDEX idx_teams_region ON teams(region_id);
CREATE INDEX idx_teams_owner ON teams(owner_id);
CREATE INDEX idx_teams_status ON teams(status);
CREATE INDEX idx_teams_name ON teams(region_id, team_name);

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### team_roster 表
```sql
CREATE TABLE team_roster (
    roster_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES player_profiles(profile_id) ON DELETE CASCADE,
    
    -- 位置信息
    position VARCHAR(20) NOT NULL CHECK (position IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')),
    
    -- 合同信息
    signing_cost DECIMAL(6,2) NOT NULL,
    contract_type VARCHAR(20) DEFAULT 'full_time' CHECK (contract_type IN ('full_time', 'substitute', 'trial')),
    
    -- 时间戳
    joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMPTZ,
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    
    -- 约束：一个队伍每个位置只能有一个主力选手
    UNIQUE(team_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_team_roster_team ON team_roster(team_id);
CREATE INDEX idx_team_roster_player ON team_roster(profile_id);
CREATE INDEX idx_team_roster_active ON team_roster(team_id, is_active) WHERE is_active = true;
```

### 3.5 比赛相关表

#### matches 表
```sql
CREATE TABLE matches (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id UUID NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    
    -- 比赛类型
    match_type VARCHAR(30) NOT NULL CHECK (match_type IN ('pricing_match', 'team_match', 'tournament_match')),
    match_name VARCHAR(200),
    
    -- 比赛状态
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    
    -- 时间信息
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- 比赛结果
    winning_team VARCHAR(10), -- 'team_a', 'team_b', 'draw'
    
    -- 比赛数据
    game_data JSONB DEFAULT '{}',
    
    -- 创建信息
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_matches_region ON matches(region_id);
CREATE INDEX idx_matches_type ON matches(match_type);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_scheduled ON matches(scheduled_at);
CREATE INDEX idx_matches_creator ON matches(created_by);
```

#### match_participants 表
```sql
CREATE TABLE match_participants (
    participant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES player_profiles(profile_id) ON DELETE CASCADE,
    
    -- 队伍信息
    team_side VARCHAR(10) NOT NULL CHECK (team_side IN ('team_a', 'team_b')),
    position VARCHAR(20) NOT NULL CHECK (position IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')),
    
    -- 英雄信息
    champion_name VARCHAR(50),
    champion_id INTEGER,
    
    -- 比赛表现数据
    performance_data JSONB DEFAULT '{}',
    
    -- 评分变化
    rating_before DECIMAL(5,2),
    rating_after DECIMAL(5,2),
    rating_change DECIMAL(5,2),
    
    -- 比赛结果
    result VARCHAR(10) CHECK (result IN ('win', 'loss', 'draw')),
    
    UNIQUE(match_id, profile_id)
);

CREATE INDEX idx_match_participants_match ON match_participants(match_id);
CREATE INDEX idx_match_participants_player ON match_participants(profile_id);
CREATE INDEX idx_match_participants_result ON match_participants(result);
```

#### match_evaluations 表
```sql
CREATE TABLE match_evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    evaluator_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES match_participants(participant_id) ON DELETE CASCADE,
    
    -- 评分数据
    scores JSONB NOT NULL, -- 6维度评分
    overall_score DECIMAL(5,2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    notes TEXT,
    
    -- 权重信息
    evaluator_weight DECIMAL(3,2) DEFAULT 1.0,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(match_id, evaluator_id, participant_id)
);

CREATE INDEX idx_match_evaluations_match ON match_evaluations(match_id);
CREATE INDEX idx_match_evaluations_evaluator ON match_evaluations(evaluator_id);
CREATE INDEX idx_match_evaluations_status ON match_evaluations(status);
```

### 3.6 转会相关表

#### transfers 表
```sql
CREATE TABLE transfers (
    transfer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES player_profiles(profile_id) ON DELETE CASCADE,
    from_team_id UUID REFERENCES teams(team_id) ON DELETE SET NULL,
    to_team_id UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    
    -- 转会类型
    transfer_type VARCHAR(20) DEFAULT 'permanent' CHECK (transfer_type IN ('permanent', 'loan', 'trial')),
    
    -- 费用信息
    proposed_fee DECIMAL(8,2),
    agreed_fee DECIMAL(8,2),
    
    -- 状态流转
    status VARCHAR(30) DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'rejected', 'completed', 'cancelled'
    )),
    
    -- 相关人员
    initiated_by UUID NOT NULL REFERENCES users(user_id),
    approved_by UUID REFERENCES users(user_id),
    
    -- 时间信息
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- 备注
    notes TEXT,
    rejection_reason TEXT
);

CREATE INDEX idx_transfers_player ON transfers(profile_id);
CREATE INDEX idx_transfers_from_team ON transfers(from_team_id);
CREATE INDEX idx_transfers_to_team ON transfers(to_team_id);
CREATE INDEX idx_transfers_status ON transfers(status);
CREATE INDEX idx_transfers_created ON transfers(created_at);
```

### 3.7 系统表

#### audit_logs 表
```sql
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 操作信息
    operation VARCHAR(50) NOT NULL,
    table_name VARCHAR(100),
    record_id UUID,
    
    -- 用户信息
    user_id UUID REFERENCES users(user_id),
    ip_address INET,
    user_agent TEXT,
    
    -- 数据变更
    old_data JSONB,
    new_data JSONB,
    changes JSONB, -- 只记录变更的字段
    
    -- 时间戳
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'
);

-- 分区表按月分区
CREATE TABLE audit_logs_y2024m01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_logs_table ON audit_logs(table_name, timestamp);
CREATE INDEX idx_audit_logs_operation ON audit_logs(operation, timestamp);
```

#### event_store 表
```sql
CREATE TABLE event_store (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL,
    event_version INTEGER NOT NULL,
    aggregate_version INTEGER NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    
    UNIQUE(stream_id, event_version)
);

CREATE INDEX idx_event_store_stream ON event_store(stream_id, event_version);
CREATE INDEX idx_event_store_type ON event_store(event_type, timestamp);
CREATE INDEX idx_event_store_timestamp ON event_store(timestamp);
```

## 4. 索引策略

### 4.1 主要索引类型

#### B-tree 索引 (默认)
```sql
-- 用于等值查询和范围查询
CREATE INDEX idx_players_rating_btree ON player_profiles(current_rating);
CREATE INDEX idx_matches_date_btree ON matches(created_at);
```

#### GIN 索引 (JSON数据)
```sql
-- 用于JSONB字段的复杂查询
CREATE INDEX idx_players_six_dimensions_gin ON player_profiles USING GIN (six_dimensions);
CREATE INDEX idx_regions_config_gin ON regions USING GIN (rating_config);
CREATE INDEX idx_matches_game_data_gin ON matches USING GIN (game_data);
```

#### 复合索引
```sql
-- 多字段组合查询优化
CREATE INDEX idx_players_region_position_rating ON player_profiles(region_id, position, current_rating DESC);
CREATE INDEX idx_transfers_status_date ON transfers(status, created_at DESC);
```

#### 部分索引
```sql
-- 只索引满足条件的行
CREATE INDEX idx_active_players ON player_profiles(region_id, current_rating DESC) 
    WHERE status = 'active';

CREATE INDEX idx_pending_transfers ON transfers(created_at DESC) 
    WHERE status = 'pending';
```

### 4.2 索引维护策略

```sql
-- 定期重建索引
CREATE OR REPLACE FUNCTION maintain_indexes()
RETURNS void AS $$
BEGIN
    -- 重建碎片化严重的索引
    REINDEX INDEX CONCURRENTLY idx_players_rating_btree;
    
    -- 更新统计信息
    ANALYZE player_profiles;
    ANALYZE matches;
    ANALYZE transfers;
END;
$$ LANGUAGE plpgsql;

-- 定时任务：每周执行一次
SELECT cron.schedule('index-maintenance', '0 2 * * SUN', 'SELECT maintain_indexes();');
```

## 5. 数据分片与分区

### 5.1 水平分区策略

#### 按时间分区 (audit_logs)
```sql
-- 创建分区表
CREATE TABLE audit_logs (
    log_id UUID DEFAULT gen_random_uuid(),
    -- ... 其他字段
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

-- 按月创建分区
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 自动化分区创建
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    table_name TEXT;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + INTERVAL '1 month');
    end_date := start_date + INTERVAL '1 month';
    table_name := 'audit_logs_' || to_char(start_date, 'YYYY_MM');
    
    EXECUTE format('CREATE TABLE %I PARTITION OF audit_logs FOR VALUES FROM (%L) TO (%L)',
                   table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

#### 按赛区分区 (player_profiles)
```sql
-- 考虑按region_id进行分区，但需要权衡查询模式
-- 如果跨赛区查询较少，可以考虑此策略

CREATE TABLE player_profiles (
    -- ... 字段定义
) PARTITION BY HASH (region_id);

-- 创建4个哈希分区
CREATE TABLE player_profiles_0 PARTITION OF player_profiles
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE player_profiles_1 PARTITION OF player_profiles
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE player_profiles_2 PARTITION OF player_profiles
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE player_profiles_3 PARTITION OF player_profiles
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

### 5.2 读写分离架构

```python
# 数据库连接管理
class DatabaseManager:
    def __init__(self):
        self.master_pool = create_async_engine(
            MASTER_DATABASE_URL,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True
        )
        
        self.replica_pools = [
            create_async_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True)
            for url in REPLICA_DATABASE_URLS
        ]
        
        self.current_replica = 0
    
    def get_master_session(self):
        """获取主库连接（写操作）"""
        return AsyncSession(self.master_pool)
    
    def get_replica_session(self):
        """获取从库连接（读操作）"""
        # 简单的轮询负载均衡
        replica_pool = self.replica_pools[self.current_replica]
        self.current_replica = (self.current_replica + 1) % len(self.replica_pools)
        return AsyncSession(replica_pool)

# 仓储模式实现读写分离
class PlayerRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def save(self, player: PlayerProfile):
        """写操作使用主库"""
        async with self.db_manager.get_master_session() as session:
            session.add(player)
            await session.commit()
    
    async def get_by_id(self, profile_id: str) -> Optional[PlayerProfile]:
        """读操作使用从库"""
        async with self.db_manager.get_replica_session() as session:
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.profile_id == profile_id)
            )
            return result.scalar_one_or_none()
```

## 6. 时序数据设计

### 6.1 TimescaleDB 超表设计

```sql
-- 选手评分历史超表
CREATE TABLE rating_history (
    profile_id UUID NOT NULL,
    region_id UUID NOT NULL,
    old_rating DECIMAL(5,2) NOT NULL,
    new_rating DECIMAL(5,2) NOT NULL,
    rating_change DECIMAL(5,2) GENERATED ALWAYS AS (new_rating - old_rating) STORED,
    reason VARCHAR(50) NOT NULL,
    match_id UUID,
    six_dimensions JSONB,
    confidence_level DECIMAL(3,2),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (profile_id, timestamp)
);

-- 转换为超表（按时间分块）
SELECT create_hypertable('rating_history', 'timestamp', chunk_time_interval => INTERVAL '1 week');

-- 连续聚合：每日平均评分
CREATE MATERIALIZED VIEW daily_avg_ratings
WITH (timescaledb.continuous) AS
SELECT 
    profile_id,
    region_id,
    time_bucket('1 day', timestamp) AS day,
    avg(new_rating) as avg_rating,
    count(*) as rating_updates,
    max(new_rating) as max_rating,
    min(new_rating) as min_rating
FROM rating_history
GROUP BY profile_id, region_id, day;

-- 设置刷新策略
SELECT add_continuous_aggregate_policy('daily_avg_ratings',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### 6.2 比赛性能数据

```sql
-- 比赛性能时序数据
CREATE TABLE match_performance_ts (
    participant_id UUID NOT NULL,
    profile_id UUID NOT NULL,
    match_id UUID NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 性能指标
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    damage_dealt BIGINT DEFAULT 0,
    damage_taken BIGINT DEFAULT 0,
    gold_earned INTEGER DEFAULT 0,
    cs_score INTEGER DEFAULT 0,
    vision_score INTEGER DEFAULT 0,
    
    -- 计算字段
    kda DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN deaths = 0 THEN (kills + assists) * 2.0
             ELSE (kills + assists)::DECIMAL / deaths
        END
    ) STORED,
    
    PRIMARY KEY (participant_id, timestamp)
);

SELECT create_hypertable('match_performance_ts', 'timestamp', chunk_time_interval => INTERVAL '1 month');

-- 数据压缩策略
ALTER TABLE match_performance_ts SET (
    timescaledb.compress = true,
    timescaledb.compress_segmentby = 'profile_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('match_performance_ts', INTERVAL '30 days');
```

## 7. 缓存层设计

### 7.1 Redis 数据结构设计

```python
# Redis 键命名规范
CACHE_KEYS = {
    # 用户相关
    'user_profile': 'user:profile:{user_id}',
    'user_sessions': 'user:sessions:{user_id}',
    
    # 选手相关
    'player_profile': 'player:profile:{profile_id}',
    'player_rating': 'player:rating:{profile_id}',
    'player_stats': 'player:stats:{profile_id}:30d',
    
    # 排行榜相关
    'region_leaderboard': 'leaderboard:{region_id}:{position}',
    'global_leaderboard': 'leaderboard:global:{position}',
    
    # 战队相关
    'team_profile': 'team:profile:{team_id}',
    'team_roster': 'team:roster:{team_id}',
    'team_cost': 'team:cost:{team_id}',
    
    # 会话和临时数据
    'user_session': 'session:{session_id}',
    'rate_limit': 'ratelimit:{user_id}:{endpoint}',
    'task_result': 'task:{task_id}',
}

# TTL 策略
CACHE_TTL = {
    'user_profile': 1800,        # 30分钟
    'player_profile': 1800,      # 30分钟
    'player_rating': 300,        # 5分钟（更新频繁）
    'leaderboard': 600,          # 10分钟
    'team_profile': 3600,        # 1小时
    'session': 86400,            # 24小时
    'rate_limit': 3600,          # 1小时
}
```

### 7.2 缓存更新策略

```python
class CacheStrategy:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def cache_aside_pattern(self, key: str, fetch_func, ttl: int = 3600):
        """缓存旁路模式"""
        # 1. 先查缓存
        cached_data = await self.redis.get(key)
        if cached_data:
            return json.loads(cached_data)
        
        # 2. 缓存未命中，查数据库
        data = await fetch_func()
        
        # 3. 写入缓存
        if data:
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
        
        return data
    
    async def write_through_pattern(self, key: str, data: dict, save_func, ttl: int = 3600):
        """写穿模式"""
        # 1. 写数据库
        await save_func(data)
        
        # 2. 写缓存
        await self.redis.setex(key, ttl, json.dumps(data, default=str))
    
    async def write_behind_pattern(self, key: str, data: dict, ttl: int = 3600):
        """异步回写模式"""
        # 1. 立即写缓存
        await self.redis.setex(key, ttl, json.dumps(data, default=str))
        
        # 2. 异步写数据库
        from .tasks import write_to_database_task
        write_to_database_task.delay(key, data)

# 排行榜缓存实现
class LeaderboardCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def update_player_ranking(self, region_id: str, profile_id: str, new_rating: float):
        """更新选手排名"""
        leaderboard_key = f"leaderboard:{region_id}:overall"
        
        # 使用有序集合存储排行榜
        await self.redis.zadd(leaderboard_key, {profile_id: new_rating})
        await self.redis.expire(leaderboard_key, 600)  # 10分钟过期
    
    async def get_leaderboard(self, region_id: str, position: str = None, start: int = 0, end: int = 49):
        """获取排行榜"""
        if position:
            leaderboard_key = f"leaderboard:{region_id}:{position}"
        else:
            leaderboard_key = f"leaderboard:{region_id}:overall"
        
        # 获取排名（降序）
        rankings = await self.redis.zrevrange(leaderboard_key, start, end, withscores=True)
        
        return [
            {
                'profile_id': profile_id.decode(),
                'rating': rating,
                'rank': start + i + 1
            }
            for i, (profile_id, rating) in enumerate(rankings)
        ]
    
    async def get_player_rank(self, region_id: str, profile_id: str, position: str = None):
        """获取选手排名"""
        if position:
            leaderboard_key = f"leaderboard:{region_id}:{position}"
        else:
            leaderboard_key = f"leaderboard:{region_id}:overall"
        
        rank = await self.redis.zrevrank(leaderboard_key, profile_id)
        return rank + 1 if rank is not None else None
```

### 7.3 缓存预热策略

```python
class CacheWarmupService:
    def __init__(self, cache_manager, db_manager):
        self.cache = cache_manager
        self.db = db_manager
    
    async def warmup_region_data(self, region_id: str):
        """预热赛区数据"""
        tasks = []
        
        # 1. 预热排行榜
        for position in ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY', None]:
            task = self.warmup_leaderboard(region_id, position)
            tasks.append(task)
        
        # 2. 预热热门选手数据
        hot_players = await self.get_hot_players(region_id, limit=100)
        for player_id in hot_players:
            task = self.warmup_player_data(player_id)
            tasks.append(task)
        
        # 3. 预热活跃战队数据
        active_teams = await self.get_active_teams(region_id, limit=50)
        for team_id in active_teams:
            task = self.warmup_team_data(team_id)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def warmup_leaderboard(self, region_id: str, position: str = None):
        """预热排行榜"""
        try:
            # 从数据库获取排行榜数据
            query = select(PlayerProfile).where(
                PlayerProfile.region_id == region_id,
                PlayerProfile.status == 'active'
            )
            
            if position:
                query = query.where(PlayerProfile.position == position)
            
            query = query.order_by(PlayerProfile.current_rating.desc()).limit(100)
            
            async with self.db.get_replica_session() as session:
                result = await session.execute(query)
                players = result.scalars().all()
            
            # 写入Redis有序集合
            leaderboard_key = f"leaderboard:{region_id}:{position or 'overall'}"
            ranking_data = {
                player.profile_id: float(player.current_rating) 
                for player in players
            }
            
            if ranking_data:
                await self.cache.redis.zadd(leaderboard_key, ranking_data)
                await self.cache.redis.expire(leaderboard_key, 600)
                
        except Exception as e:
            logger.error(f"Failed to warmup leaderboard {region_id}/{position}: {e}")
```

## 8. 数据一致性保证

### 8.1 事务管理

```python
class TransactionManager:
    def __init__(self, db_session):
        self.db_session = db_session
    
    @contextmanager
    async def atomic_transaction(self):
        """原子事务上下文管理器"""
        async with self.db_session.begin():
            try:
                yield self.db_session
                await self.db_session.commit()
            except Exception:
                await self.db_session.rollback()
                raise

# 使用示例：选手签约事务
class PlayerSigningService:
    async def sign_player_to_team(
        self, 
        profile_id: str, 
        team_id: str, 
        position: str
    ):
        async with TransactionManager(self.db_session).atomic_transaction():
            # 1. 锁定选手记录
            player = await self.db_session.execute(
                select(PlayerProfile)
                .where(PlayerProfile.profile_id == profile_id)
                .with_for_update()  # 行锁
            )
            player = player.scalar_one()
            
            if player.contract_status != 'FREE':
                raise ValueError("Player is not available")
            
            # 2. 锁定战队记录
            team = await self.db_session.execute(
                select(Team)
                .where(Team.team_id == team_id)
                .with_for_update()
            )
            team = team.scalar_one()
            
            # 3. 检查预算
            signing_cost = player.current_rating
            if team.total_cost + signing_cost > team.budget_limit:
                raise ValueError("Insufficient budget")
            
            # 4. 执行签约
            player.contract_status = 'LOCKED'
            player.current_team_id = team_id
            player.locked_rating = player.current_rating
            player.contract_start = datetime.utcnow()
            
            # 5. 更新战队
            team.total_cost += signing_cost
            
            # 6. 创建阵容记录
            roster_entry = TeamRoster(
                team_id=team_id,
                profile_id=profile_id,
                position=position,
                signing_cost=signing_cost
            )
            self.db_session.add(roster_entry)
```

### 8.2 最终一致性处理

```python
class EventualConsistencyHandler:
    def __init__(self, event_bus, cache_manager):
        self.event_bus = event_bus
        self.cache = cache_manager
    
    async def handle_player_rating_updated(self, event: PlayerRatingUpdatedEvent):
        """处理选手评分更新事件"""
        try:
            profile_id = event.profile_id
            region_id = event.region_id
            
            # 1. 更新缓存中的选手数据
            await self.update_player_cache(profile_id)
            
            # 2. 更新排行榜缓存
            await self.update_leaderboard_cache(region_id, profile_id, event.new_rating)
            
            # 3. 如果选手在队，更新战队缓存
            if event.team_id:
                await self.update_team_cache(event.team_id)
            
            # 4. 发送通知给相关用户
            await self.notify_rating_change(profile_id, event.old_rating, event.new_rating)
            
        except Exception as e:
            logger.error(f"Failed to handle rating updated event: {e}")
            # 重新排队处理
            await self.event_bus.retry_event(event)

# 分布式锁保证一致性
class DistributedLockManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    @asynccontextmanager
    async def acquire_lock(self, lock_key: str, timeout: int = 60, retry_interval: float = 0.1):
        """获取分布式锁"""
        lock_value = str(uuid.uuid4())
        acquired = False
        
        try:
            # 尝试获取锁
            while not acquired:
                acquired = await self.redis.set(
                    lock_key, 
                    lock_value, 
                    nx=True, 
                    ex=timeout
                )
                if not acquired:
                    await asyncio.sleep(retry_interval)
            
            yield
            
        finally:
            # 释放锁（使用Lua脚本保证原子性）
            release_script = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            else
                return 0
            end
            """
            await self.redis.eval(release_script, 1, lock_key, lock_value)
```

## 9. 备份与恢复策略

### 9.1 备份策略

```bash
#!/bin/bash
# 数据库备份脚本

# 配置
BACKUP_DIR="/opt/backups/flyesports"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 主数据库备份
pg_dump -h $DB_HOST -U $DB_USER -d flyesports_prod \
    --no-password \
    --verbose \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/flyesports_full_$DATE.dump"

# TimescaleDB增量备份
pg_dump -h $TIMESCALE_HOST -U $DB_USER -d flyesports_timeseries \
    --no-password \
    --verbose \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/timeseries_$DATE.dump"

# Redis备份
redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# 上传到S3
aws s3 cp "$BACKUP_DIR/" s3://flyesports-backups/daily/ --recursive

# 清理过期备份
find $BACKUP_DIR -name "*.dump" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete
```

### 9.2 恢复策略

```sql
-- 数据库恢复脚本
-- 1. 创建恢复环境
CREATE DATABASE flyesports_restore;

-- 2. 恢复主数据
pg_restore -h localhost -U postgres -d flyesports_restore \
    --verbose \
    --jobs=4 \
    /opt/backups/flyesports_full_20240115_020000.dump

-- 3. 恢复时序数据
pg_restore -h localhost -U postgres -d flyesports_timeseries_restore \
    --verbose \
    --jobs=4 \
    /opt/backups/timeseries_20240115_020000.dump

-- 4. 数据一致性检查
SELECT 
    'users' as table_name,
    count(*) as record_count,
    max(created_at) as latest_record
FROM users
UNION ALL
SELECT 
    'player_profiles',
    count(*),
    max(created_at)
FROM player_profiles
UNION ALL
SELECT 
    'matches',
    count(*),
    max(created_at)
FROM matches;
```

### 9.3 灾难恢复计划

```yaml
# 灾难恢复等级定义
RTO_RPO_Targets:
  Critical_Systems:
    RTO: 15_minutes    # 恢复时间目标
    RPO: 5_minutes     # 恢复点目标
  
  Important_Systems:
    RTO: 1_hour
    RPO: 15_minutes
  
  Standard_Systems:
    RTO: 4_hours
    RPO: 1_hour

# 恢复步骤
Recovery_Procedures:
  Phase_1_Assessment:
    - Identify scope of failure
    - Determine data loss extent
    - Notify stakeholders
  
  Phase_2_Infrastructure:
    - Provision recovery environment
    - Restore database clusters
    - Verify network connectivity
  
  Phase_3_Data:
    - Restore from latest backup
    - Apply transaction logs
    - Verify data integrity
  
  Phase_4_Application:
    - Deploy application services
    - Update configuration
    - Run smoke tests
  
  Phase_5_Validation:
    - Full system testing
    - Performance validation
    - User acceptance testing
```

## 10. 性能优化方案

### 10.1 查询优化

```sql
-- 1. 排行榜查询优化
-- 原始查询（慢）
SELECT p.*, u.username 
FROM player_profiles p 
JOIN users u ON p.user_id = u.user_id 
WHERE p.region_id = 'region_kr' 
  AND p.status = 'active'
ORDER BY p.current_rating DESC 
LIMIT 50;

-- 优化后的查询
WITH ranked_players AS (
    SELECT 
        profile_id,
        player_name,
        current_rating,
        position,
        ROW_NUMBER() OVER (ORDER BY current_rating DESC) as rank
    FROM player_profiles 
    WHERE region_id = 'region_kr' 
      AND status = 'active'
      AND current_rating > 0
    LIMIT 50
)
SELECT * FROM ranked_players;

-- 2. 复杂聚合查询优化
-- 选手统计数据（使用物化视图）
CREATE MATERIALIZED VIEW player_statistics AS
SELECT 
    profile_id,
    region_id,
    COUNT(*) as total_matches,
    AVG(rating_change) as avg_rating_change,
    SUM(CASE WHEN rating_change > 0 THEN 1 ELSE 0 END) as positive_changes,
    MAX(new_rating) as peak_rating,
    MIN(new_rating) as lowest_rating
FROM rating_history 
WHERE timestamp > CURRENT_DATE - INTERVAL '30 days'
GROUP BY profile_id, region_id;

CREATE UNIQUE INDEX idx_player_statistics_profile ON player_statistics(profile_id);

-- 定期刷新物化视图
REFRESH MATERIALIZED VIEW CONCURRENTLY player_statistics;
```

### 10.2 连接池优化

```python
# 数据库连接池配置
DATABASE_CONFIG = {
    'pool_size': 20,          # 连接池基础大小
    'max_overflow': 30,       # 最大溢出连接数
    'pool_pre_ping': True,    # 连接前ping检查
    'pool_recycle': 3600,     # 连接回收时间（1小时）
    'pool_timeout': 30,       # 获取连接超时时间
    'echo': False,            # 生产环境关闭SQL日志
}

# 连接池监控
class ConnectionPoolMonitor:
    def __init__(self, engine):
        self.engine = engine
    
    def get_pool_status(self):
        pool = self.engine.pool
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'utilization': pool.checkedout() / (pool.size() + pool.overflow()) * 100
        }
    
    async def monitor_pool_health(self):
        """监控连接池健康状态"""
        while True:
            try:
                status = self.get_pool_status()
                
                # 报警条件
                if status['utilization'] > 80:
                    logger.warning(f"High connection pool utilization: {status['utilization']:.1f}%")
                
                if status['checked_out'] == 0:
                    logger.error("No active database connections!")
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"Pool monitoring error: {e}")
                await asyncio.sleep(60)
```

### 10.3 缓存命中率优化

```python
class CacheOptimizer:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.hit_rates = {}
    
    async def track_cache_hit_rate(self, cache_key_pattern: str):
        """跟踪缓存命中率"""
        info = await self.redis.info('stats')
        
        keyspace_hits = int(info['keyspace_hits'])
        keyspace_misses = int(info['keyspace_misses'])
        total_requests = keyspace_hits + keyspace_misses
        
        hit_rate = keyspace_hits / total_requests * 100 if total_requests > 0 else 0
        
        self.hit_rates[cache_key_pattern] = {
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'timestamp': datetime.utcnow()
        }
        
        return hit_rate
    
    async def optimize_ttl_based_on_hit_rate(self, key_pattern: str):
        """基于命中率优化TTL"""
        hit_rate = await self.track_cache_hit_rate(key_pattern)
        
        # 高命中率（>80%）增加TTL
        if hit_rate > 80:
            new_ttl = int(CACHE_TTL.get(key_pattern, 3600) * 1.5)
        # 低命中率（<50%）减少TTL
        elif hit_rate < 50:
            new_ttl = int(CACHE_TTL.get(key_pattern, 3600) * 0.7)
        else:
            new_ttl = CACHE_TTL.get(key_pattern, 3600)
        
        return new_ttl
    
    async def cache_warming_strategy(self):
        """智能缓存预热策略"""
        # 分析访问模式
        access_patterns = await self.analyze_access_patterns()
        
        # 预热高频访问的数据
        for pattern in access_patterns:
            if pattern['frequency'] > 100:  # 每小时100次以上
                await self.warm_cache_for_pattern(pattern['key_pattern'])

# 数据库查询性能监控
class QueryPerformanceMonitor:
    def __init__(self, db_session):
        self.db_session = db_session
    
    async def analyze_slow_queries(self):
        """分析慢查询"""
        slow_query_sql = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements 
        WHERE mean_time > 100  -- 平均执行时间超过100ms
        ORDER BY total_time DESC 
        LIMIT 20;
        """
        
        result = await self.db_session.execute(text(slow_query_sql))
        return result.fetchall()
    
    async def suggest_optimizations(self, query_stats):
        """建议查询优化"""
        suggestions = []
        
        for stat in query_stats:
            if stat['hit_percent'] < 90:
                suggestions.append({
                    'query': stat['query'][:100] + '...',
                    'issue': 'Low buffer hit ratio',
                    'suggestion': 'Consider adding indexes or increasing shared_buffers'
                })
            
            if stat['mean_time'] > 1000:
                suggestions.append({
                    'query': stat['query'][:100] + '...',
                    'issue': 'Very slow query',
                    'suggestion': 'Review query plan and consider rewriting'
                })
        
        return suggestions
```

## 总结

FlyEsports的数据库设计采用了现代化的多层架构，通过PostgreSQL+TimescaleDB+Redis的组合，实现了高性能、高可用、可扩展的数据存储方案。

**核心特点：**
- **多租户支持**：基于行级安全的数据隔离
- **时序数据优化**：TimescaleDB处理评分历史和性能数据
- **智能缓存**：Redis多级缓存提升查询性能
- **数据一致性**：事务管理和最终一致性保证
- **可扩展架构**：分片分区支持业务增长
- **完备监控**：性能监控和自动化运维

这套设计为FlyEsports提供了坚实的数据基础，能够支撑大规模并发访问和复杂的业务逻辑处理。