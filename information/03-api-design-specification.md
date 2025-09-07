# FlyEsports 原子化API设计规范

## 目录
- [1. API设计原则](#1-api设计原则)
- [2. 接口规范标准](#2-接口规范标准)
- [3. 用户管理API](#3-用户管理api)
- [4. 选手档案API](#4-选手档案api)
- [5. 评分系统API](#5-评分系统api)
- [6. 赛区管理API](#6-赛区管理api)
- [7. 战队管理API](#7-战队管理api)
- [8. 转会系统API](#8-转会系统api)
- [9. 比赛系统API](#9-比赛系统api)
- [10. 数据查询API](#10-数据查询api)
- [11. 错误处理规范](#11-错误处理规范)
- [12. 认证与授权](#12-认证与授权)

## 1. API设计原则

### 1.1 核心原则
- **原子性**: 每个API接口只负责单一职责，不可再分解
- **幂等性**: 相同的请求多次调用应产生相同的结果
- **一致性**: 所有接口遵循统一的设计模式和响应格式
- **可组合性**: 原子接口可以组合实现复杂的业务流程
- **向后兼容**: 接口升级不破坏现有客户端

### 1.2 设计标准
- **RESTful设计**: 遵循REST架构风格
- **资源导向**: 以资源为中心设计URL结构
- **HTTP方法语义**: 正确使用GET、POST、PUT、DELETE等方法
- **状态码规范**: 使用标准HTTP状态码
- **分页支持**: 大数据量接口必须支持分页

### 1.3 命名规范
```
# URL结构
/api/{version}/{resource}[/{id}][/{sub-resource}][/{action}]

# 示例
GET /api/v1/users/{user_id}                    # 获取用户详情
POST /api/v1/profiles                          # 创建选手档案  
PUT /api/v1/ratings/{profile_id}/lock          # 锁定评分
GET /api/v1/regions/{region_id}/leaderboard    # 获取排行榜
```

## 2. 接口规范标准

### 2.1 请求格式

#### 通用请求头
```http
Content-Type: application/json
Authorization: Bearer {access_token}
X-Region-ID: {region_id}  // 多租户上下文
X-Request-ID: {uuid}      // 请求追踪ID
```

#### 分页参数
```json
{
  "page": 1,
  "page_size": 20,
  "sort_by": "created_at",
  "sort_order": "desc"
}
```

### 2.2 响应格式

#### 成功响应
```json
{
  "success": true,
  "data": {
    // 具体数据
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1"
  },
  "pagination": {  // 仅分页接口包含
    "current_page": 1,
    "page_size": 20,
    "total_count": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

#### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1"
  }
}
```

### 2.3 状态码规范
- `200 OK`: 成功获取资源
- `201 Created`: 成功创建资源
- `204 No Content`: 成功删除资源
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限访问
- `404 Not Found`: 资源不存在
- `409 Conflict`: 资源冲突
- `422 Unprocessable Entity`: 数据验证失败
- `429 Too Many Requests`: 请求频率限制
- `500 Internal Server Error`: 服务器内部错误

## 3. 用户管理API

### 3.1 用户注册
```http
POST /api/v1/users
Content-Type: application/json

{
  "username": "player123",
  "email": "player@example.com",
  "password": "securepassword",
  "confirm_password": "securepassword",
  "agree_terms": true
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "user_id": "usr_123456789",
    "username": "player123",
    "email": "player@example.com",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "email_verified": false
  },
  "meta": {
    "request_id": "req_123",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1"
  }
}
```

### 3.2 用户认证
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "player@example.com",
  "password": "securepassword"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "user_id": "usr_123456789",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 1800,
    "permissions": ["read:profile", "write:profile"],
    "regions": ["region_kr", "region_na"]
  }
}
```

### 3.3 获取用户详情
```http
GET /api/v1/users/{user_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "user_id": "usr_123456789",
    "username": "player123",
    "email": "player@example.com",
    "display_name": "ProPlayer",
    "avatar_url": "https://cdn.flyesports.com/avatars/123.jpg",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "last_active": "2024-01-02T12:00:00Z",
    "profile_count": 3,
    "total_matches": 150,
    "preferences": {
      "language": "zh-CN",
      "timezone": "Asia/Shanghai",
      "email_notifications": true
    }
  }
}
```

### 3.4 更新用户资料
```http
PUT /api/v1/users/{user_id}/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "display_name": "NewDisplayName",
  "avatar_url": "https://cdn.flyesports.com/avatars/new.jpg",
  "preferences": {
    "language": "en-US",
    "timezone": "UTC",
    "email_notifications": false
  }
}
```

### 3.5 刷新令牌
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 4. 选手档案API

### 4.1 创建选手档案
```http
POST /api/v1/profiles
Authorization: Bearer {token}
Content-Type: application/json

{
  "region_id": "region_kr",
  "player_name": "ProPlayer",
  "summoner_name": "SummonerName",
  "position": "MIDDLE",
  "description": "Experienced mid laner"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "user_id": "usr_123456789",
    "region_id": "region_kr",
    "player_name": "ProPlayer",
    "summoner_name": "SummonerName",
    "position": "MIDDLE",
    "status": "active",
    "rating": {
      "current_score": 45.5,
      "locked_score": null,
      "confidence_level": 0.5,
      "total_matches": 0
    },
    "rank_info": {
      "tier": "GOLD",
      "rank": "II",
      "league_points": 75,
      "wins": 42,
      "losses": 38
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 4.2 获取选手档案详情
```http
GET /api/v1/profiles/{profile_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "user_id": "usr_123456789",
    "region_id": "region_kr",
    "player_name": "ProPlayer",
    "summoner_name": "SummonerName",
    "position": "MIDDLE",
    "status": "active",
    "contract_status": "FREE",
    "rating": {
      "current_score": 67.8,
      "locked_score": null,
      "confidence_level": 0.85,
      "total_matches": 45,
      "six_dimensions": {
        "kda": 72.5,
        "damage": 68.3,
        "economy": 71.2,
        "vision": 55.7,
        "objective": 66.9,
        "teamfight": 69.4
      }
    },
    "rank_info": {
      "tier": "DIAMOND",
      "rank": "III",
      "league_points": 42,
      "wins": 87,
      "losses": 63
    },
    "statistics": {
      "total_matches": 45,
      "wins": 28,
      "losses": 17,
      "win_rate": 0.622,
      "avg_kda": 2.35,
      "recent_form": "W-W-L-W-W"
    },
    "team_info": null,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 4.3 更新段位信息
```http
PUT /api/v1/profiles/{profile_id}/rank
Authorization: Bearer {token}
Content-Type: application/json

{
  "tier": "DIAMOND",
  "rank": "II",
  "league_points": 85,
  "wins": 92,
  "losses": 68
}
```

### 4.4 获取用户的所有选手档案
```http
GET /api/v1/users/{user_id}/profiles
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "profile_id": "prf_123456789",
      "region_id": "region_kr",
      "region_name": "Korea",
      "player_name": "ProPlayer",
      "position": "MIDDLE",
      "current_rating": 67.8,
      "contract_status": "FREE",
      "last_active": "2024-01-15T10:30:00Z"
    },
    {
      "profile_id": "prf_987654321",
      "region_id": "region_na",
      "region_name": "North America",
      "player_name": "ProPlayer_NA",
      "position": "BOTTOM",
      "current_rating": 52.3,
      "contract_status": "LOCKED",
      "last_active": "2024-01-10T15:45:00Z"
    }
  ]
}
```

### 4.5 停用选手档案
```http
PUT /api/v1/profiles/{profile_id}/deactivate
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "voluntary_retirement"
}
```

## 5. 评分系统API

### 5.1 获取选手当前评分
```http
GET /api/v1/ratings/{profile_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "current_score": 67.8,
    "locked_score": null,
    "confidence_level": 0.85,
    "total_matches": 45,
    "six_dimensions": {
      "kda": {
        "score": 72.5,
        "weight": 0.20,
        "recent_trend": "rising"
      },
      "damage": {
        "score": 68.3,
        "weight": 0.25,
        "recent_trend": "stable"
      },
      "economy": {
        "score": 71.2,
        "weight": 0.15,
        "recent_trend": "rising"
      },
      "vision": {
        "score": 55.7,
        "weight": 0.10,
        "recent_trend": "falling"
      },
      "objective": {
        "score": 66.9,
        "weight": 0.15,
        "recent_trend": "stable"
      },
      "teamfight": {
        "score": 69.4,
        "weight": 0.15,
        "recent_trend": "rising"
      }
    },
    "position_ranking": {
      "region_rank": 23,
      "position_rank": 8,
      "percentile": 92.5
    },
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 5.2 获取评分历史
```http
GET /api/v1/ratings/{profile_id}/history?days=30&limit=50
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "history": [
      {
        "date": "2024-01-15",
        "rating": 67.8,
        "change": +2.3,
        "reason": "match_result",
        "match_id": "match_789",
        "confidence_level": 0.85
      },
      {
        "date": "2024-01-14",
        "rating": 65.5,
        "change": -1.2,
        "reason": "match_result",
        "match_id": "match_788",
        "confidence_level": 0.84
      }
    ],
    "statistics": {
      "period_start": "2024-01-01",
      "period_end": "2024-01-15",
      "total_change": +12.8,
      "highest_rating": 68.1,
      "lowest_rating": 54.2,
      "volatility": 3.2
    }
  },
  "pagination": {
    "current_page": 1,
    "page_size": 50,
    "total_count": 45,
    "total_pages": 1
  }
}
```

### 5.3 触发评分计算
```http
POST /api/v1/ratings/calculate
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_id": "prf_123456789",
  "match_data": {
    "match_id": "match_12345",
    "result": 1.0,
    "duration": 1845,
    "performance": {
      "kills": 8,
      "deaths": 2,
      "assists": 12,
      "damage_dealt": 25678,
      "damage_taken": 18234,
      "gold_earned": 14567,
      "cs_score": 178,
      "vision_score": 32
    }
  },
  "opponent_profiles": [
    "prf_987654321",
    "prf_456789123"
  ]
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_abc123",
    "status": "processing",
    "estimated_completion": "2024-01-01T00:01:00Z"
  }
}
```

### 5.4 锁定评分
```http
PUT /api/v1/ratings/{profile_id}/lock
Authorization: Bearer {token}
Content-Type: application/json

{
  "team_id": "team_123456",
  "reason": "player_signing"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "locked_score": 67.8,
    "locked_at": "2024-01-01T00:00:00Z",
    "locked_by": "team_123456",
    "reason": "player_signing"
  }
}
```

### 5.5 解锁评分
```http
PUT /api/v1/ratings/{profile_id}/unlock
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "player_released"
}
```

### 5.6 批量解锁评分
```http
POST /api/v1/ratings/bulk-unlock
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_ids": [
    "prf_123456789",
    "prf_987654321"
  ],
  "reason": "transfer_window_open"
}
```

## 6. 赛区管理API

### 6.1 获取赛区列表
```http
GET /api/v1/regions?status=active
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "region_id": "region_kr",
      "region_name": "Korea",
      "region_code": "KR",
      "status": "active",
      "player_count": 1247,
      "active_teams": 89,
      "current_season": "2024_spring",
      "transfer_window": {
        "is_open": false,
        "next_open": "2024-03-01T00:00:00Z",
        "next_close": "2024-03-15T23:59:59Z"
      },
      "pricing_config": {
        "base_rating": 50.0,
        "k_factor_base": 32,
        "confidence_growth_rate": 0.02
      }
    }
  ]
}
```

### 6.2 获取赛区详情
```http
GET /api/v1/regions/{region_id}
Authorization: Bearer {token}
```

### 6.3 获取赛区排行榜
```http
GET /api/v1/regions/{region_id}/leaderboard?position=MIDDLE&page=1&page_size=50&sort_by=rating
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "region_id": "region_kr",
    "position": "MIDDLE",
    "entries": [
      {
        "rank": 1,
        "profile_id": "prf_123456789",
        "player_name": "TopMidLaner",
        "current_rating": 89.5,
        "confidence_level": 0.95,
        "total_matches": 127,
        "win_rate": 0.68,
        "recent_trend": "rising",
        "rank_info": {
          "tier": "CHALLENGER",
          "league_points": 1234
        },
        "last_active": "2024-01-15T10:30:00Z"
      }
    ],
    "generated_at": "2024-01-15T12:00:00Z"
  },
  "pagination": {
    "current_page": 1,
    "page_size": 50,
    "total_count": 234,
    "total_pages": 5
  }
}
```

### 6.4 获取赛区统计数据
```http
GET /api/v1/regions/{region_id}/statistics
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "region_id": "region_kr",
    "overview": {
      "total_players": 1247,
      "active_players_7d": 892,
      "total_teams": 89,
      "active_teams": 67,
      "total_matches_today": 234
    },
    "rating_distribution": {
      "0-20": 15,
      "20-40": 187,
      "40-60": 643,
      "60-80": 298,
      "80-100": 104
    },
    "position_distribution": {
      "TOP": 249,
      "JUNGLE": 251,
      "MIDDLE": 248,
      "BOTTOM": 251,
      "UTILITY": 248
    },
    "activity_metrics": {
      "daily_active_users": 456,
      "matches_per_day": 234,
      "avg_session_duration": 145.5
    }
  }
}
```

## 7. 战队管理API

### 7.1 创建战队
```http
POST /api/v1/teams
Authorization: Bearer {token}
Content-Type: application/json

{
  "team_name": "Elite Esports",
  "team_tag": "EE",
  "region_id": "region_kr",
  "description": "Professional esports team",
  "logo_url": "https://cdn.flyesports.com/logos/ee.png"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "team_id": "team_123456789",
    "team_name": "Elite Esports",
    "team_tag": "EE",
    "region_id": "region_kr",
    "status": "active",
    "owner_id": "usr_123456789",
    "created_at": "2024-01-01T00:00:00Z",
    "roster": {
      "total_players": 0,
      "total_cost": 0.0,
      "positions": {
        "TOP": null,
        "JUNGLE": null,
        "MIDDLE": null,
        "BOTTOM": null,
        "UTILITY": null
      }
    }
  }
}
```

### 7.2 获取战队详情
```http
GET /api/v1/teams/{team_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "team_id": "team_123456789",
    "team_name": "Elite Esports",
    "team_tag": "EE",
    "region_id": "region_kr",
    "status": "active",
    "owner_id": "usr_123456789",
    "roster": {
      "total_players": 3,
      "total_cost": 195.6,
      "positions": {
        "TOP": {
          "profile_id": "prf_111",
          "player_name": "TopLaner",
          "locked_rating": 65.4,
          "contract_start": "2024-01-01T00:00:00Z"
        },
        "JUNGLE": null,
        "MIDDLE": {
          "profile_id": "prf_222",
          "player_name": "MidLaner",
          "locked_rating": 72.8,
          "contract_start": "2024-01-01T00:00:00Z"
        },
        "BOTTOM": {
          "profile_id": "prf_333",
          "player_name": "ADC",
          "locked_rating": 57.4,
          "contract_start": "2024-01-01T00:00:00Z"
        },
        "UTILITY": null
      }
    },
    "statistics": {
      "total_matches": 15,
      "wins": 9,
      "losses": 6,
      "win_rate": 0.60,
      "avg_team_rating": 65.2
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 7.3 添加选手到战队
```http
POST /api/v1/teams/{team_id}/roster/add
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_id": "prf_123456789",
  "position": "MIDDLE",
  "contract_type": "full_time"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "team_id": "team_123456789",
    "position": "MIDDLE",
    "locked_rating": 67.8,
    "contract_start": "2024-01-01T00:00:00Z",
    "contract_type": "full_time",
    "signing_cost": 67.8
  }
}
```

### 7.4 从战队移除选手
```http
DELETE /api/v1/teams/{team_id}/roster/remove
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_id": "prf_123456789",
  "reason": "voluntary_leave"
}
```

### 7.5 获取战队花名册
```http
GET /api/v1/teams/{team_id}/roster
Authorization: Bearer {token}
```

### 7.6 获取战队总成本
```http
GET /api/v1/teams/{team_id}/cost
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "team_id": "team_123456789",
    "total_cost": 325.8,
    "position_costs": {
      "TOP": 65.4,
      "JUNGLE": 0.0,
      "MIDDLE": 72.8,
      "BOTTOM": 57.4,
      "UTILITY": 0.0
    },
    "cost_breakdown": [
      {
        "profile_id": "prf_111",
        "player_name": "TopLaner",
        "position": "TOP",
        "locked_rating": 65.4,
        "signing_date": "2024-01-01T00:00:00Z"
      }
    ],
    "calculated_at": "2024-01-15T12:00:00Z"
  }
}
```

## 8. 转会系统API

### 8.1 发起转会申请
```http
POST /api/v1/transfers/initiate
Authorization: Bearer {token}
Content-Type: application/json

{
  "profile_id": "prf_123456789",
  "from_team_id": "team_111",
  "to_team_id": "team_222",
  "transfer_type": "permanent",
  "proposed_fee": 85.5
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "transfer_id": "transfer_123456",
    "profile_id": "prf_123456789",
    "from_team_id": "team_111",
    "to_team_id": "team_222",
    "transfer_type": "permanent",
    "proposed_fee": 85.5,
    "calculated_fee": 82.3,
    "status": "pending_approval",
    "initiated_by": "usr_123456789",
    "created_at": "2024-01-01T00:00:00Z",
    "expires_at": "2024-01-08T00:00:00Z"
  }
}
```

### 8.2 获取转会详情
```http
GET /api/v1/transfers/{transfer_id}
Authorization: Bearer {token}
```

### 8.3 批准转会
```http
PUT /api/v1/transfers/{transfer_id}/approve
Authorization: Bearer {token}
Content-Type: application/json

{
  "approved_by": "team_manager",
  "final_fee": 82.3,
  "notes": "Approved by team management"
}
```

### 8.4 拒绝转会
```http
PUT /api/v1/transfers/{transfer_id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "insufficient_budget",
  "notes": "Team budget constraints"
}
```

### 8.5 获取选手转会历史
```http
GET /api/v1/profiles/{profile_id}/transfers
Authorization: Bearer {token}
```

## 9. 比赛系统API

### 9.1 创建定价赛
```http
POST /api/v1/pricing-matches
Authorization: Bearer {token}
Content-Type: application/json

{
  "region_id": "region_kr",
  "match_name": "Pricing Match #1",
  "participants": [
    {
      "profile_id": "prf_1",
      "position": "TOP"
    },
    {
      "profile_id": "prf_2", 
      "position": "JUNGLE"
    }
  ],
  "scheduled_at": "2024-01-01T10:00:00Z"
}
```

### 9.2 开始比赛
```http
PUT /api/v1/pricing-matches/{match_id}/start
Authorization: Bearer {token}
```

### 9.3 结束比赛并提交结果
```http
PUT /api/v1/pricing-matches/{match_id}/end
Authorization: Bearer {token}
Content-Type: application/json

{
  "duration": 1845,
  "winning_team": "team_a",
  "participants": [
    {
      "profile_id": "prf_1",
      "team": "team_a",
      "performance": {
        "kills": 5,
        "deaths": 2,
        "assists": 8,
        "damage_dealt": 18234,
        "gold_earned": 12456,
        "cs_score": 156
      }
    }
  ]
}
```

### 9.4 提交评分员评分
```http
POST /api/v1/evaluations
Authorization: Bearer {token}
Content-Type: application/json

{
  "match_id": "match_123456",
  "evaluator_id": "usr_evaluator1",
  "evaluations": [
    {
      "profile_id": "prf_1",
      "scores": {
        "kda": 8.5,
        "damage": 7.2,
        "economy": 8.0,
        "vision": 6.5,
        "objective": 7.8,
        "teamfight": 8.2
      },
      "overall_score": 77.5,
      "notes": "Excellent performance in teamfights"
    }
  ]
}
```

### 9.5 计算加权评分
```http
POST /api/v1/evaluations/calculate-weighted
Authorization: Bearer {token}
Content-Type: application/json

{
  "match_id": "match_123456",
  "system_weight": 0.6,
  "evaluator_weight": 0.4
}
```

## 10. 数据查询API

### 10.1 获取选手统计数据
```http
GET /api/v1/profiles/{profile_id}/statistics?period=30d
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "profile_id": "prf_123456789",
    "period": "30d",
    "match_statistics": {
      "total_matches": 28,
      "wins": 18,
      "losses": 10,
      "win_rate": 0.643,
      "avg_kda": 2.45,
      "avg_damage": 23456,
      "avg_gold": 13789
    },
    "rating_statistics": {
      "current_rating": 67.8,
      "rating_change": +8.5,
      "highest_rating": 69.2,
      "lowest_rating": 59.3,
      "volatility": 2.8
    },
    "six_dimensions": {
      "kda": {
        "current": 72.5,
        "change": +3.2,
        "trend": "rising"
      },
      "damage": {
        "current": 68.3,
        "change": -1.1,
        "trend": "stable"
      }
    }
  }
}
```

### 10.2 获取赛区趋势数据
```http
GET /api/v1/regions/{region_id}/trends?metric=avg_rating&period=90d
Authorization: Bearer {token}
```

### 10.3 获取位置对比数据
```http
GET /api/v1/analytics/position-comparison?region_id=region_kr&positions=MIDDLE,BOTTOM
Authorization: Bearer {token}
```

### 10.4 获取战队表现分析
```http
GET /api/v1/teams/{team_id}/analytics?period=season
Authorization: Bearer {token}
```

## 11. 错误处理规范

### 11.1 错误代码分类
```
# 认证授权错误 (AUTH_*)
AUTH_INVALID_TOKEN      # 无效令牌
AUTH_TOKEN_EXPIRED      # 令牌过期
AUTH_INSUFFICIENT_PERMISSIONS  # 权限不足

# 验证错误 (VALIDATION_*)  
VALIDATION_ERROR        # 通用验证错误
VALIDATION_MISSING_FIELD  # 缺少必填字段
VALIDATION_INVALID_FORMAT  # 格式不正确

# 业务逻辑错误 (BUSINESS_*)
BUSINESS_DUPLICATE_REGISTRATION  # 重复注册
BUSINESS_INVALID_TRANSFER       # 无效转会
BUSINESS_INSUFFICIENT_BUDGET    # 预算不足

# 资源错误 (RESOURCE_*)
RESOURCE_NOT_FOUND      # 资源不存在
RESOURCE_CONFLICT       # 资源冲突
RESOURCE_LOCKED         # 资源被锁定

# 系统错误 (SYSTEM_*)
SYSTEM_INTERNAL_ERROR   # 内部错误
SYSTEM_SERVICE_UNAVAILABLE  # 服务不可用
SYSTEM_RATE_LIMITED     # 请求频率限制
```

### 11.2 详细错误响应示例
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "Email format is invalid",
        "value": "invalid-email"
      },
      {
        "field": "rating",
        "code": "OUT_OF_RANGE", 
        "message": "Rating must be between 0 and 100",
        "value": 150
      }
    ]
  },
  "meta": {
    "request_id": "req_123456",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1",
    "documentation_url": "https://docs.flyesports.com/errors#VALIDATION_ERROR"
  }
}
```

## 12. 认证与授权

### 12.1 JWT Token格式
```json
{
  "user_id": "usr_123456789",
  "username": "player123",
  "permissions": [
    "read:profile",
    "write:profile", 
    "manage:team"
  ],
  "regions": [
    "region_kr",
    "region_na"
  ],
  "token_type": "access",
  "iat": 1640995200,
  "exp": 1640998800
}
```

### 12.2 权限级别
- `read:profile`: 读取选手档案
- `write:profile`: 修改选手档案
- `manage:team`: 管理战队
- `evaluate:matches`: 评分比赛
- `admin:region`: 赛区管理员
- `admin:system`: 系统管理员

### 12.3 赛区权限检查
每个涉及赛区数据的请求都需要验证用户是否有该赛区的访问权限：

```http
# 请求头中包含赛区上下文
X-Region-ID: region_kr

# 服务器验证逻辑
if region_id not in user.regions:
    return 403 Forbidden
```

### 12.4 API限流
```http
# 响应头中返回限流信息
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640998800

# 超出限制时的错误响应
HTTP/1.1 429 Too Many Requests
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

## 总结

FlyEsports的API设计严格遵循原子化原则，每个接口都有明确的单一职责。通过统一的请求/响应格式、完善的错误处理和权限管理，确保了系统的一致性和安全性。这种设计为未来的功能扩展和第三方集成提供了坚实的基础。