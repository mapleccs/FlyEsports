# 安全与性能优化方案 (Security & Performance Optimization)

## 1. 安全架构设计

FlyEsports 平台采用多层次纵深防御的安全策略，确保用户数据和系统资源的安全性，同时满足合规性要求。

### 1.1 安全威胁模型分析

#### 1.1.1 主要安全威胁

| 威胁类型 | 风险等级 | 影响范围 | 缓解措施 |
|---------|---------|---------|---------|
| SQL注入攻击 | 高 | 数据库泄露 | ORM参数化查询、输入验证 |
| XSS攻击 | 中 | 用户会话劫持 | 输出编码、CSP策略 |
| CSRF攻击 | 中 | 未授权操作 | CSRF Token、SameSite Cookie |
| 权限提升 | 高 | 系统控制 | 最小权限原则、角色控制 |
| DDoS攻击 | 高 | 服务可用性 | 流量限制、CDN防护 |
| 数据泄露 | 极高 | 用户隐私 | 数据加密、访问审计 |
| API滥用 | 中 | 资源消耗 | 速率限制、API密钥管理 |

#### 1.1.2 安全需求分析

- **身份认证**: 多因素认证、JWT令牌管理、会话安全
- **访问控制**: 基于角色的权限控制(RBAC)、多租户数据隔离
- **数据保护**: 敏感数据加密、PII数据脱敏、数据备份安全
- **通信安全**: HTTPS强制、API安全、WebSocket安全传输
- **审计合规**: 操作日志记录、审计轨迹、合规性检查

### 1.2 身份认证与授权系统

#### 1.2.1 多因素认证实现

```python
from cryptography.fernet import Fernet
from pyotp import TOTP
import qrcode
from io import BytesIO
import base64

class MFAManager:
    """多因素认证管理器"""
    
    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())
    
    async def setup_totp(self, user_id: str, issuer: str = "FlyEsports") -> dict:
        """设置TOTP二步验证"""
        
        # 生成密钥
        secret = pyotp.random_base32()
        
        # 加密存储密钥
        encrypted_secret = self.fernet.encrypt(secret.encode())
        
        # 存储到数据库
        mfa_config = UserMFAConfig(
            user_id=user_id,
            method_type="totp",
            secret=encrypted_secret,
            is_enabled=False,  # 需要验证后启用
            created_at=datetime.utcnow()
        )
        
        await self.db.add(mfa_config)
        await self.db.commit()
        
        # 生成QR码
        totp = TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "secret": secret,
            "qr_code": qr_code_b64,
            "manual_entry_key": secret
        }
    
    async def verify_totp(self, user_id: str, token: str) -> bool:
        """验证TOTP令牌"""
        
        # 获取用户MFA配置
        mfa_config = await self.db.execute(
            select(UserMFAConfig).where(
                and_(
                    UserMFAConfig.user_id == user_id,
                    UserMFAConfig.method_type == "totp",
                    UserMFAConfig.is_enabled == True
                )
            )
        )
        
        config = mfa_config.scalar()
        if not config:
            return False
        
        # 解密密钥
        secret = self.fernet.decrypt(config.secret).decode()
        
        # 验证令牌
        totp = TOTP(secret)
        is_valid = totp.verify(token, valid_window=1)
        
        # 防重放攻击：检查令牌是否已使用
        if is_valid:
            cache_key = f"used_totp:{user_id}:{token}"
            if await self.redis.exists(cache_key):
                return False
            
            # 标记令牌已使用（30秒有效期）
            await self.redis.setex(cache_key, 30, "1")
        
        return is_valid

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=15)
        self.refresh_token_expire = timedelta(days=7)
    
    def create_access_token(self, user_id: str, permissions: List[str]) -> str:
        """创建访问令牌"""
        
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "type": "access",
            "permissions": permissions,
            "iat": now,
            "exp": now + self.access_token_expire,
            "jti": str(uuid.uuid4())  # JWT ID，用于撤销
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "type": "refresh", 
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def revoke_token(self, jti: str):
        """撤销令牌"""
        # 将令牌ID加入黑名单
        blacklist_key = f"token_blacklist:{jti}"
        await self.redis.setex(blacklist_key, 86400 * 7, "1")  # 7天过期
    
    async def is_token_revoked(self, jti: str) -> bool:
        """检查令牌是否已撤销"""
        blacklist_key = f"token_blacklist:{jti}"
        return await self.redis.exists(blacklist_key)
```

#### 1.2.2 基于角色的访问控制

```python
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

class PermissionType(str, Enum):
    """权限类型枚举"""
    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read" 
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 战队管理
    TEAM_CREATE = "team:create"
    TEAM_MANAGE = "team:manage"
    TEAM_INVITE = "team:invite"
    
    # 赛事管理
    TOURNAMENT_CREATE = "tournament:create"
    TOURNAMENT_MANAGE = "tournament:manage"
    TOURNAMENT_MODERATE = "tournament:moderate"
    
    # 转会管理
    TRANSFER_REQUEST = "transfer:request"
    TRANSFER_APPROVE = "transfer:approve"
    TRANSFER_MANAGE = "transfer:manage"
    
    # 系统管理
    ADMIN_PANEL = "admin:panel"
    SYSTEM_CONFIG = "system:config"
    AUDIT_VIEW = "audit:view"

class Role(Base):
    """角色模型"""
    __tablename__ = "roles"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    
    # 多租户支持
    region_id: Mapped[Optional[str]] = mapped_column(ForeignKey("regions.id"))
    is_system_role: Mapped[bool] = mapped_column(default=False)
    
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

class Permission(Base):
    """权限模型"""
    __tablename__ = "permissions"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[PermissionType]
    description: Mapped[str]
    resource: Mapped[str]  # 资源类型
    action: Mapped[str]    # 操作类型
    
class RolePermission(Base):
    """角色权限关联表"""
    __tablename__ = "role_permissions"
    
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), primary_key=True)
    
    # 条件权限支持
    conditions: Mapped[Optional[Dict]] = mapped_column(JSON)

class UserRole(Base):
    """用户角色关联表"""
    __tablename__ = "user_roles"
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    
    # 权限范围限制
    region_id: Mapped[Optional[str]] = mapped_column(ForeignKey("regions.id"))
    team_id: Mapped[Optional[str]] = mapped_column(ForeignKey("teams.id"))
    
    granted_at: Mapped[datetime] = mapped_column(default=func.now())
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))

class AccessControlManager:
    """访问控制管理器"""
    
    def __init__(self, db_session, cache_client):
        self.db = db_session
        self.cache = cache_client
    
    async def check_permission(
        self,
        user_id: str,
        permission: PermissionType,
        resource_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> bool:
        """检查用户权限"""
        
        # 从缓存获取用户权限
        cache_key = f"user_permissions:{user_id}"
        cached_permissions = await self.cache.get(cache_key)
        
        if cached_permissions:
            permissions = json.loads(cached_permissions)
        else:
            permissions = await self._load_user_permissions(user_id)
            await self.cache.setex(cache_key, 300, json.dumps(permissions))
        
        # 检查直接权限
        if permission in permissions.get("direct", []):
            return True
        
        # 检查条件权限
        for condition_perm in permissions.get("conditional", []):
            if (condition_perm["permission"] == permission and 
                self._check_permission_conditions(
                    condition_perm["conditions"], 
                    resource_id, 
                    context or {}
                )):
                return True
        
        return False
    
    async def _load_user_permissions(self, user_id: str) -> Dict:
        """加载用户权限"""
        
        # 查询用户角色和权限
        result = await self.db.execute("""
            SELECT DISTINCT p.name, rp.conditions
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = :user_id
        """, {"user_id": user_id})
        
        rows = result.fetchall()
        
        permissions = {
            "direct": [],
            "conditional": []
        }
        
        for row in rows:
            if row.conditions:
                permissions["conditional"].append({
                    "permission": row.name,
                    "conditions": row.conditions
                })
            else:
                permissions["direct"].append(row.name)
        
        return permissions
    
    def _check_permission_conditions(
        self,
        conditions: Dict,
        resource_id: Optional[str],
        context: Dict
    ) -> bool:
        """检查权限条件"""
        
        # 资源所有权检查
        if "resource_owner" in conditions and resource_id:
            return context.get("resource_owner_id") == context.get("user_id")
        
        # 团队成员检查
        if "team_member" in conditions:
            user_teams = context.get("user_teams", [])
            required_team = conditions["team_member"]
            return required_team in user_teams
        
        # 地区限制检查
        if "region_access" in conditions:
            user_regions = context.get("user_regions", [])
            required_regions = conditions["region_access"]
            return any(region in user_regions for region in required_regions)
        
        return True
```

### 1.3 数据安全与隐私保护

#### 1.3.1 敏感数据加密

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import secrets

class DataEncryptionManager:
    """数据加密管理器"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self._initialize_encryption_keys()
    
    def _initialize_encryption_keys(self):
        """初始化加密密钥"""
        
        # 为不同类型的数据使用不同的加密密钥
        self.encryption_keys = {
            "pii": self._derive_key("pii_data"),      # 个人身份信息
            "financial": self._derive_key("financial_data"),  # 财务数据
            "auth": self._derive_key("auth_data"),    # 认证数据
            "logs": self._derive_key("log_data")      # 日志数据
        }
    
    def _derive_key(self, context: str) -> Fernet:
        """派生特定上下文的加密密钥"""
        
        salt = hashlib.sha256(context.encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_pii(self, data: str) -> str:
        """加密个人身份信息"""
        if not data:
            return data
        
        encrypted_data = self.encryption_keys["pii"].encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_pii(self, encrypted_data: str) -> str:
        """解密个人身份信息"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.encryption_keys["pii"].decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception:
            return ""
    
    def encrypt_financial(self, amount: Decimal) -> str:
        """加密财务数据"""
        data = str(amount)
        encrypted_data = self.encryption_keys["financial"].encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_financial(self, encrypted_data: str) -> Decimal:
        """解密财务数据"""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.encryption_keys["financial"].decrypt(decoded_data)
            return Decimal(decrypted_data.decode())
        except Exception:
            return Decimal("0")

class DataMaskingManager:
    """数据脱敏管理器"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏"""
        if not email or "@" not in email:
            return email
        
        username, domain = email.split("@", 1)
        if len(username) <= 2:
            masked_username = "*" * len(username)
        else:
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]
        
        return f"{masked_username}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏"""
        if not phone or len(phone) < 6:
            return phone
        
        return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]
    
    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证号脱敏"""
        if not id_card or len(id_card) < 8:
            return id_card
        
        return id_card[:4] + "*" * (len(id_card) - 8) + id_card[-4:]
    
    @staticmethod
    def mask_bank_card(card_number: str) -> str:
        """银行卡号脱敏"""
        if not card_number or len(card_number) < 8:
            return card_number
        
        return "*" * (len(card_number) - 4) + card_number[-4:]

# SQLAlchemy加密字段自定义类型
from sqlalchemy import TypeDecorator, String

class EncryptedType(TypeDecorator):
    """加密字段类型"""
    
    impl = String
    
    def __init__(self, encryption_manager: DataEncryptionManager, data_type: str = "pii"):
        super().__init__()
        self.encryption_manager = encryption_manager
        self.data_type = data_type
    
    def process_bind_param(self, value, dialect):
        """存储时加密"""
        if value is None:
            return value
        
        if self.data_type == "pii":
            return self.encryption_manager.encrypt_pii(value)
        elif self.data_type == "financial":
            return self.encryption_manager.encrypt_financial(Decimal(value))
        
        return value
    
    def process_result_value(self, value, dialect):
        """读取时解密"""
        if value is None:
            return value
        
        if self.data_type == "pii":
            return self.encryption_manager.decrypt_pii(value)
        elif self.data_type == "financial":
            return self.encryption_manager.decrypt_financial(value)
        
        return value
```

#### 1.3.2 数据访问审计

```python
class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_session, encryption_manager):
        self.db = db_session
        self.encryption = encryption_manager
    
    async def log_data_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        sensitive_data_accessed: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_context: Optional[Dict] = None
    ):
        """记录数据访问日志"""
        
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            sensitive_data_accessed=sensitive_data_accessed,
            ip_address=ip_address,
            user_agent=user_agent,
            context=additional_context or {},
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        
        # 对于敏感数据访问，额外记录详细信息
        if sensitive_data_accessed:
            await self._log_sensitive_access(audit_log)
    
    async def _log_sensitive_access(self, audit_log: AuditLog):
        """记录敏感数据访问详细信息"""
        
        # 发送实时警报
        if await self._detect_suspicious_access(audit_log):
            await self._send_security_alert(audit_log)
        
        # 记录到专门的敏感访问日志
        sensitive_log = SensitiveDataAccessLog(
            audit_log_id=audit_log.id,
            risk_score=await self._calculate_access_risk_score(audit_log),
            location=await self._get_location_from_ip(audit_log.ip_address),
            device_fingerprint=await self._calculate_device_fingerprint(audit_log.user_agent)
        )
        
        self.db.add(sensitive_log)
        await self.db.commit()
    
    async def _detect_suspicious_access(self, audit_log: AuditLog) -> bool:
        """检测可疑访问行为"""
        
        # 检查访问频率
        recent_accesses = await self.db.execute(
            select(func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.user_id == audit_log.user_id,
                    AuditLog.sensitive_data_accessed == True,
                    AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=5)
                )
            )
        )
        
        if recent_accesses.scalar() > 10:  # 5分钟内访问超过10次敏感数据
            return True
        
        # 检查异常IP
        usual_ips = await self._get_user_usual_ips(audit_log.user_id)
        if audit_log.ip_address not in usual_ips:
            return True
        
        # 检查异常时间段
        hour = audit_log.timestamp.hour
        if hour < 6 or hour > 23:  # 深夜访问
            return True
        
        return False

class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str]
    resource_type: Mapped[str]
    resource_id: Mapped[str]
    
    sensitive_data_accessed: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[Optional[str]]
    user_agent: Mapped[Optional[str]]
    context: Mapped[Optional[Dict]] = mapped_column(JSON)
    
    timestamp: Mapped[datetime] = mapped_column(default=func.now())
    
    # 创建时间分区索引
    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )
```

### 1.4 API安全防护

#### 1.4.1 速率限制与防护

```python
from redis.asyncio import Redis
import time
from typing import Optional, Tuple

class RateLimitManager:
    """速率限制管理器"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        
        # 预定义速率限制规则
        self.rate_limits = {
            "auth": {"requests": 5, "window": 60},      # 认证：1分钟5次
            "api_default": {"requests": 100, "window": 60},  # 默认API：1分钟100次
            "api_sensitive": {"requests": 10, "window": 60}, # 敏感API：1分钟10次
            "transfer": {"requests": 3, "window": 300},   # 转会：5分钟3次
            "upload": {"requests": 5, "window": 60},      # 文件上传：1分钟5次
        }
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "api_default"
    ) -> Tuple[bool, Dict[str, int]]:
        """检查速率限制"""
        
        if limit_type not in self.rate_limits:
            return True, {}
        
        config = self.rate_limits[limit_type]
        key = f"rate_limit:{limit_type}:{identifier}"
        
        current_time = int(time.time())
        window_start = current_time - config["window"]
        
        # 使用Redis Lua脚本确保原子性
        lua_script = """
        local key = KEYS[1]
        local window_start = tonumber(ARGV[1])
        local current_time = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local window_size = tonumber(ARGV[4])
        
        -- 清理过期数据
        redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
        
        -- 获取当前请求数
        local current_requests = redis.call('ZCARD', key)
        
        if current_requests >= max_requests then
            -- 获取最早请求的时间，计算重置时间
            local earliest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local reset_time = 0
            if #earliest > 0 then
                reset_time = tonumber(earliest[2]) + window_size
            end
            return {0, current_requests, max_requests, reset_time}
        else
            -- 记录当前请求
            redis.call('ZADD', key, current_time, current_time .. ':' .. math.random())
            redis.call('EXPIRE', key, window_size)
            return {1, current_requests + 1, max_requests, current_time + window_size}
        end
        """
        
        result = await self.redis.eval(
            lua_script,
            1,
            key,
            window_start,
            current_time,
            config["requests"],
            config["window"]
        )
        
        allowed, current, limit, reset_time = result
        
        return bool(allowed), {
            "current": current,
            "limit": limit,
            "reset_time": reset_time,
            "remaining": max(0, limit - current)
        }

class SecurityMiddleware:
    """安全中间件"""
    
    def __init__(self, rate_limiter: RateLimitManager):
        self.rate_limiter = rate_limiter
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r"(?i)(union|select|insert|delete|update|drop|create|alter)",  # SQL注入
            r"(?i)(<script|javascript:|onerror=|onload=)",  # XSS尝试
            r"(?i)(\.\.\/|\.\.\\|\/etc\/|\/var\/)",         # 目录遍历
            r"(?i)(cmd\.exe|/bin/bash|/bin/sh)",            # 命令注入
        ]
    
    async def __call__(self, request, call_next):
        """中间件处理函数"""
        
        # 1. IP黑名单检查
        client_ip = self._get_client_ip(request)
        if client_ip in self.blocked_ips:
            return Response(
                status_code=403,
                content={"error": "IP blocked due to suspicious activity"}
            )
        
        # 2. 恶意请求检测
        if await self._detect_malicious_request(request):
            await self._block_ip_temporarily(client_ip)
            return Response(
                status_code=403,
                content={"error": "Malicious request detected"}
            )
        
        # 3. 速率限制检查
        if hasattr(request.state, "rate_limit_type"):
            allowed, rate_info = await self.rate_limiter.check_rate_limit(
                client_ip,
                request.state.rate_limit_type
            )
            
            if not allowed:
                return Response(
                    status_code=429,
                    content={"error": "Rate limit exceeded"},
                    headers={
                        "X-RateLimit-Limit": str(rate_info["limit"]),
                        "X-RateLimit-Remaining": str(rate_info["remaining"]),
                        "X-RateLimit-Reset": str(rate_info["reset_time"])
                    }
                )
        
        # 4. 请求处理
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 5. 响应安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    async def _detect_malicious_request(self, request) -> bool:
        """检测恶意请求"""
        
        # 检查URL路径
        path = str(request.url.path)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path):
                return True
        
        # 检查查询参数
        query = str(request.url.query)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, query):
                return True
        
        # 检查User-Agent
        user_agent = request.headers.get("user-agent", "")
        suspicious_agents = ["sqlmap", "nmap", "nikto", "burpsuite"]
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            return True
        
        # 检查请求体（如果有）
        if hasattr(request, "_body") and request._body:
            try:
                body = request._body.decode("utf-8")
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, body):
                        return True
            except Exception:
                pass
        
        return False
    
    def _get_client_ip(self, request) -> str:
        """获取客户端真实IP"""
        
        # 检查代理头
        forwarded_ips = request.headers.get("X-Forwarded-For")
        if forwarded_ips:
            return forwarded_ips.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host
```

#### 1.4.2 API密钥管理

```python
import secrets
from datetime import datetime, timedelta

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, db_session, encryption_manager):
        self.db = db_session
        self.encryption = encryption_manager
    
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """创建API密钥"""
        
        # 生成密钥
        api_key = f"flyesp_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 创建密钥记录
        api_key_record = APIKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions,
            is_active=True,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            last_used_at=None
        )
        
        self.db.add(api_key_record)
        await self.db.commit()
        
        return {
            "api_key": api_key,  # 只在创建时返回原始密钥
            "key_id": api_key_record.id,
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    
    async def validate_api_key(
        self,
        api_key: str,
        required_permission: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """验证API密钥"""
        
        if not api_key.startswith("flyesp_"):
            return False, None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 查询密钥记录
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True,
                    or_(
                        APIKey.expires_at.is_(None),
                        APIKey.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        
        api_key_record = result.scalar()
        if not api_key_record:
            return False, None
        
        # 检查权限
        if required_permission and required_permission not in api_key_record.permissions:
            return False, api_key_record.user_id
        
        # 更新最后使用时间
        api_key_record.last_used_at = datetime.utcnow()
        await self.db.commit()
        
        return True, api_key_record.user_id
    
    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """撤销API密钥"""
        
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == key_id,
                    APIKey.user_id == user_id
                )
            )
        )
        
        api_key = result.scalar()
        if not api_key:
            return False
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        await self.db.commit()
        
        return True

class APIKey(Base):
    """API密钥模型"""
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    key_hash: Mapped[str] = mapped_column(unique=True)
    
    permissions: Mapped[List[str]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[Optional[datetime]]
    last_used_at: Mapped[Optional[datetime]]
    revoked_at: Mapped[Optional[datetime]]
    
    # 使用统计
    usage_count: Mapped[int] = mapped_column(default=0)
    monthly_quota: Mapped[Optional[int]]  # 月度配额
```

## 2. 性能优化策略

### 2.1 数据库性能优化

#### 2.1.1 查询优化与索引策略

```python
class DatabaseOptimizationManager:
    """数据库优化管理器"""
    
    def __init__(self, db_session):
        self.db = db_session
        
        # 定义关键查询的索引策略
        self.index_strategies = {
            "user_authentication": [
                "users(email)",
                "users(username)", 
                "user_sessions(user_id, expires_at)",
            ],
            "player_profiles": [
                "player_profiles(user_id, region_id)",
                "player_profiles(region_id, rating)",
                "player_ratings(player_id, created_at)",
            ],
            "match_data": [
                "matches(tournament_id, status)",
                "matches(scheduled_at)",
                "match_players(match_id, player_id)",
                "match_statistics(match_id, player_id)",
            ],
            "leaderboards": [
                "player_profiles(region_id, rating, position)",
                "team_ratings(region_id, rating, season_id)",
                "seasonal_statistics(season_id, region_id, player_id)",
            ],
            "transfers": [
                "transfer_requests(status, created_at)",
                "transfer_requests(player_id, status)",
                "transfer_history(player_id, completed_at)",
            ]
        }
    
    async def create_optimized_indexes(self):
        """创建优化索引"""
        
        index_statements = [
            # 复合索引：用户认证
            "CREATE INDEX CONCURRENTLY idx_users_email_active ON users(email) WHERE is_active = true",
            
            # 复合索引：选手评分排行榜
            "CREATE INDEX CONCURRENTLY idx_player_rankings ON player_profiles(region_id, rating DESC, position) WHERE is_active = true",
            
            # 部分索引：活跃比赛
            "CREATE INDEX CONCURRENTLY idx_active_matches ON matches(tournament_id, scheduled_at) WHERE status IN ('scheduled', 'in_progress')",
            
            # 函数索引：全文搜索
            "CREATE INDEX CONCURRENTLY idx_teams_name_search ON teams USING gin(to_tsvector('english', name))",
            
            # 时间分区索引：匹配统计
            "CREATE INDEX CONCURRENTLY idx_match_stats_time ON match_statistics(created_at) WHERE created_at >= '2024-01-01'",
        ]
        
        for statement in index_statements:
            try:
                await self.db.execute(text(statement))
                await self.db.commit()
                logger.info(f"Created index: {statement}")
            except Exception as e:
                logger.error(f"Failed to create index: {statement}, error: {e}")
    
    async def analyze_query_performance(self, query: str, params: dict = None) -> Dict:
        """分析查询性能"""
        
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        
        result = await self.db.execute(text(explain_query), params or {})
        execution_plan = result.fetchone()[0]
        
        # 提取关键性能指标
        plan_node = execution_plan[0]["Plan"]
        
        performance_metrics = {
            "total_cost": plan_node.get("Total Cost", 0),
            "execution_time": execution_plan[0].get("Execution Time", 0),
            "planning_time": execution_plan[0].get("Planning Time", 0),
            "shared_hit_blocks": self._extract_buffer_usage(plan_node, "Shared Hit Blocks"),
            "shared_read_blocks": self._extract_buffer_usage(plan_node, "Shared Read Blocks"),
            "temp_read_blocks": self._extract_buffer_usage(plan_node, "Temp Read Blocks"),
        }
        
        # 识别性能问题
        issues = self._identify_performance_issues(plan_node)
        
        return {
            "metrics": performance_metrics,
            "issues": issues,
            "recommendations": self._generate_optimization_recommendations(issues)
        }
    
    def _identify_performance_issues(self, plan_node: Dict) -> List[str]:
        """识别性能问题"""
        issues = []
        
        if plan_node.get("Node Type") == "Seq Scan":
            issues.append("Sequential scan detected - consider adding index")
        
        if plan_node.get("Total Cost", 0) > 10000:
            issues.append("High query cost - consider query optimization")
        
        if "Sort" in plan_node.get("Node Type", "") and not plan_node.get("Sort Method", "").startswith("quicksort"):
            issues.append("External sort detected - consider increasing work_mem")
        
        # 递归检查子节点
        for child in plan_node.get("Plans", []):
            issues.extend(self._identify_performance_issues(child))
        
        return issues

class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def optimize_leaderboard_query(
        region_id: str,
        position: Optional[str] = None,
        limit: int = 100
    ) -> str:
        """优化排行榜查询"""
        
        # 使用CTE和窗口函数优化排名查询
        base_query = """
        WITH ranked_players AS (
            SELECT 
                p.id,
                p.user_id,
                p.username,
                p.rating,
                p.position,
                p.region_id,
                ROW_NUMBER() OVER (PARTITION BY p.region_id, p.position ORDER BY p.rating DESC) as rank
            FROM player_profiles p
            WHERE p.region_id = :region_id
                AND p.is_active = true
                AND (:position IS NULL OR p.position = :position)
                AND p.rating > 0
        )
        SELECT 
            id,
            user_id, 
            username,
            rating,
            position,
            rank
        FROM ranked_players
        WHERE rank <= :limit
        ORDER BY rank
        """
        
        return base_query
    
    @staticmethod
    def optimize_match_history_query(
        player_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> str:
        """优化比赛历史查询"""
        
        # 使用索引优化的比赛历史查询
        query = """
        SELECT DISTINCT
            m.id,
            m.tournament_id,
            m.scheduled_at,
            m.status,
            m.duration_minutes,
            t.name as tournament_name,
            CASE 
                WHEN mp.team_id = m.winner_team_id THEN 'win'
                WHEN m.winner_team_id IS NULL THEN 'draw'
                ELSE 'loss'
            END as result,
            ms.kills,
            ms.deaths,
            ms.assists,
            ms.damage_dealt
        FROM matches m
        JOIN match_players mp ON m.id = mp.match_id
        JOIN tournaments t ON m.tournament_id = t.id
        LEFT JOIN match_statistics ms ON m.id = ms.match_id AND ms.player_id = mp.player_id
        WHERE mp.player_id = :player_id
            AND m.status = 'completed'
        ORDER BY m.scheduled_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        return query
```

#### 2.1.2 连接池优化

```python
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import create_engine

class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine = None
        self._async_engine = None
    
    def create_optimized_engine(self, is_async: bool = False):
        """创建优化的数据库引擎"""
        
        # 连接池配置
        pool_config = {
            "poolclass": QueuePool,
            "pool_size": 20,          # 基础连接数
            "max_overflow": 30,       # 最大溢出连接数  
            "pool_pre_ping": True,    # 连接预检查
            "pool_recycle": 3600,     # 连接回收时间(1小时)
            "echo": False,            # 生产环境关闭SQL日志
        }
        
        # 读写分离配置
        read_config = pool_config.copy()
        read_config.update({
            "pool_size": 10,
            "max_overflow": 20,
        })
        
        write_config = pool_config.copy()
        write_config.update({
            "pool_size": 5,
            "max_overflow": 10,
        })
        
        if is_async:
            from sqlalchemy.ext.asyncio import create_async_engine
            self._async_engine = create_async_engine(
                self.database_url.replace("postgresql://", "postgresql+asyncpg://"),
                **pool_config
            )
            return self._async_engine
        else:
            self._engine = create_engine(self.database_url, **pool_config)
            return self._engine
    
    async def monitor_connection_pool(self) -> Dict[str, Any]:
        """监控连接池状态"""
        
        pool = self._async_engine.pool if self._async_engine else self._engine.pool
        
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "pool_status": "healthy" if pool.checkedin() > 0 else "warning"
        }

class ReadWriteSplitter:
    """读写分离管理器"""
    
    def __init__(self, write_engine, read_engines: List):
        self.write_engine = write_engine
        self.read_engines = read_engines
        self.current_read_index = 0
    
    def get_read_engine(self):
        """获取读库连接（轮询负载均衡）"""
        engine = self.read_engines[self.current_read_index]
        self.current_read_index = (self.current_read_index + 1) % len(self.read_engines)
        return engine
    
    def get_write_engine(self):
        """获取写库连接"""
        return self.write_engine
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {"write": False, "read": []}
        
        # 检查写库
        try:
            async with self.write_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                results["write"] = True
        except Exception as e:
            logger.error(f"Write DB health check failed: {e}")
        
        # 检查读库
        for i, read_engine in enumerate(self.read_engines):
            try:
                async with read_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    results["read"].append(True)
            except Exception as e:
                logger.error(f"Read DB {i} health check failed: {e}")
                results["read"].append(False)
        
        return results
```

### 2.2 缓存策略优化

#### 2.2.1 多级缓存架构

```python
from abc import ABC, abstractmethod
from typing import Optional, Any, Union
import pickle
import json
from datetime import timedelta

class CacheBackend(ABC):
    """缓存后端抽象基类"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

class MemoryCache(CacheBackend):
    """内存缓存（L1缓存）"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            item = self.cache[key]
            if item["expires_at"] is None or time.time() < item["expires_at"]:
                # 更新访问顺序
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return item["value"]
            else:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # LRU淘汰
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        expires_at = time.time() + ttl if ttl else None
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        return key in self.cache

class RedisCache(CacheBackend):
    """Redis缓存（L2缓存）"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        if data:
            try:
                return pickle.loads(data)
            except Exception:
                return None
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized_data = pickle.dumps(value)
            if ttl:
                return await self.redis.setex(key, ttl, serialized_data)
            else:
                return await self.redis.set(key, serialized_data)
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        result = await self.redis.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key)

class MultilevelCache:
    """多级缓存管理器"""
    
    def __init__(self, l1_cache: MemoryCache, l2_cache: RedisCache):
        self.l1 = l1_cache  # 内存缓存
        self.l2 = l2_cache  # Redis缓存
        self.metrics = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """多级缓存获取"""
        
        # L1缓存查找
        value = await self.l1.get(key)
        if value is not None:
            self.metrics["l1_hits"] += 1
            return value
        
        # L2缓存查找
        value = await self.l2.get(key)
        if value is not None:
            self.metrics["l2_hits"] += 1
            # 回写到L1缓存
            await self.l1.set(key, value, ttl=300)  # L1缓存5分钟
            return value
        
        self.metrics["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """多级缓存设置"""
        
        # 同时设置L1和L2缓存
        l1_ttl = min(300, ttl) if ttl else 300  # L1缓存最长5分钟
        
        l1_success = await self.l1.set(key, value, l1_ttl)
        l2_success = await self.l2.set(key, value, ttl)
        
        return l1_success or l2_success
    
    async def delete(self, key: str) -> bool:
        """多级缓存删除"""
        
        l1_result = await self.l1.delete(key)
        l2_result = await self.l2.delete(key)
        
        return l1_result or l2_result
    
    async def invalidate_pattern(self, pattern: str):
        """批量失效缓存"""
        # Redis模式匹配删除
        keys = await self.l2.redis.keys(pattern)
        if keys:
            await self.l2.redis.delete(*keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = sum(self.metrics.values())
        
        return {
            "l1_hit_rate": self.metrics["l1_hits"] / total_requests if total_requests > 0 else 0,
            "l2_hit_rate": self.metrics["l2_hits"] / total_requests if total_requests > 0 else 0,
            "overall_hit_rate": (self.metrics["l1_hits"] + self.metrics["l2_hits"]) / total_requests if total_requests > 0 else 0,
            "total_requests": total_requests,
            **self.metrics
        }
```

#### 2.2.2 缓存策略管理

```python
class CacheStrategyManager:
    """缓存策略管理器"""
    
    def __init__(self, cache: MultilevelCache):
        self.cache = cache
        
        # 定义不同数据的缓存策略
        self.cache_strategies = {
            "user_session": {"ttl": 1800, "invalidate_on": ["logout", "password_change"]},
            "user_profile": {"ttl": 3600, "invalidate_on": ["profile_update"]},
            "leaderboard": {"ttl": 300, "invalidate_on": ["match_completed", "rating_updated"]},
            "team_info": {"ttl": 1800, "invalidate_on": ["team_updated", "member_changed"]},
            "tournament_schedule": {"ttl": 600, "invalidate_on": ["schedule_updated"]},
            "match_result": {"ttl": 86400, "invalidate_on": []},  # 比赛结果很少变化
            "rating_history": {"ttl": 3600, "invalidate_on": ["rating_recalculated"]},
        }
    
    def get_cache_key(self, data_type: str, identifier: str, **kwargs) -> str:
        """生成缓存键"""
        
        # 基础键
        key = f"{data_type}:{identifier}"
        
        # 添加额外参数
        if kwargs:
            sorted_params = sorted(kwargs.items())
            params_str = ":".join(f"{k}={v}" for k, v in sorted_params)
            key = f"{key}:{params_str}"
        
        return key
    
    async def get_with_strategy(
        self,
        data_type: str,
        identifier: str,
        fetch_func: callable,
        **kwargs
    ) -> Any:
        """按策略获取数据"""
        
        cache_key = self.get_cache_key(data_type, identifier, **kwargs)
        strategy = self.cache_strategies.get(data_type, {"ttl": 3600})
        
        # 尝试从缓存获取
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 缓存未命中，从数据源获取
        fresh_data = await fetch_func()
        if fresh_data is not None:
            await self.cache.set(cache_key, fresh_data, strategy["ttl"])
        
        return fresh_data
    
    async def invalidate_related_cache(self, event_type: str, related_data: Dict[str, Any]):
        """根据事件类型失效相关缓存"""
        
        invalidation_rules = {
            "match_completed": [
                "leaderboard:*",
                "rating_history:*",
                f"user_profile:{related_data.get('player_ids', [])}",
            ],
            "profile_update": [
                f"user_profile:{related_data.get('user_id')}",
                f"team_info:{related_data.get('team_ids', [])}",
            ],
            "team_updated": [
                f"team_info:{related_data.get('team_id')}",
                "leaderboard:team:*",
            ],
            "rating_updated": [
                f"rating_history:{related_data.get('player_id')}",
                f"leaderboard:*",
            ],
        }
        
        patterns_to_invalidate = invalidation_rules.get(event_type, [])
        
        for pattern in patterns_to_invalidate:
            if isinstance(pattern, list):
                # 处理具体的键列表
                for key in pattern:
                    await self.cache.delete(key)
            else:
                # 处理模式匹配
                await self.cache.invalidate_pattern(pattern)

# 缓存装饰器
def cached_result(data_type: str, ttl: Optional[int] = None, key_func: Optional[callable] = None):
    """缓存结果装饰器"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认键生成逻辑
                func_name = func.__name__
                args_str = ":".join(str(arg) for arg in args[1:])  # 跳过self
                kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{data_type}:{func_name}:{args_str}:{kwargs_str}"
            
            # 从缓存获取
            cache_manager = args[0].cache_manager  # 假设第一个参数是self，且有cache_manager属性
            cached_result = await cache_manager.cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                strategy = cache_manager.cache_strategies.get(data_type, {})
                cache_ttl = ttl or strategy.get("ttl", 3600)
                await cache_manager.cache.set(cache_key, result, cache_ttl)
            
            return result
        
        return wrapper
    return decorator

# 使用示例
class PlayerService:
    def __init__(self, cache_manager: CacheStrategyManager):
        self.cache_manager = cache_manager
    
    @cached_result("leaderboard", ttl=300, key_func=lambda self, region_id, position=None: f"leaderboard:{region_id}:{position or 'all'}")
    async def get_leaderboard(self, region_id: str, position: Optional[str] = None) -> List[Dict]:
        """获取排行榜（使用缓存）"""
        
        # 实际的数据库查询逻辑
        query = self.db.query(PlayerProfile).filter(
            PlayerProfile.region_id == region_id
        )
        
        if position:
            query = query.filter(PlayerProfile.position == position)
        
        players = await query.order_by(desc(PlayerProfile.rating)).limit(100).all()
        
        return [
            {
                "rank": idx + 1,
                "user_id": player.user_id,
                "username": player.username,
                "rating": player.rating,
                "position": player.position
            }
            for idx, player in enumerate(players)
        ]
```

### 2.3 异步任务优化

#### 2.3.1 Celery任务队列优化

```python
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import time

# Celery配置优化
class CeleryConfig:
    # 结果后端
    result_backend = 'redis://redis:6379/1'
    broker_url = 'redis://redis:6379/0'
    
    # 任务序列化
    task_serializer = 'pickle'
    result_serializer = 'pickle' 
    accept_content = ['pickle', 'json']
    
    # 任务路由
    task_routes = {
        'tasks.rating_calculation.*': {'queue': 'rating'},
        'tasks.match_processing.*': {'queue': 'matches'},
        'tasks.notifications.*': {'queue': 'notifications'},
        'tasks.reports.*': {'queue': 'reports'},
        'tasks.email.*': {'queue': 'emails'},
    }
    
    # 工作进程配置
    worker_prefetch_multiplier = 4  # 预取任务数
    worker_max_tasks_per_child = 1000  # 避免内存泄漏
    worker_disable_rate_limits = False
    
    # 任务结果过期时间
    result_expires = 3600
    
    # 任务重试配置
    task_acks_late = True
    task_reject_on_worker_lost = True
    
    # 监控配置
    worker_send_task_events = True
    task_send_sent_event = True

celery_app = Celery('flyesp')
celery_app.config_from_object(CeleryConfig)

class TaskPriorityManager:
    """任务优先级管理器"""
    
    PRIORITY_HIGH = 9
    PRIORITY_NORMAL = 5  
    PRIORITY_LOW = 1
    
    # 任务优先级映射
    TASK_PRIORITIES = {
        'match_processing': PRIORITY_HIGH,
        'rating_calculation': PRIORITY_HIGH,
        'transfer_processing': PRIORITY_HIGH,
        'notifications': PRIORITY_NORMAL,
        'reports': PRIORITY_LOW,
        'data_cleanup': PRIORITY_LOW,
    }
    
    @classmethod
    def get_task_priority(cls, task_name: str) -> int:
        """获取任务优先级"""
        for prefix, priority in cls.TASK_PRIORITIES.items():
            if task_name.startswith(prefix):
                return priority
        return cls.PRIORITY_NORMAL

# 任务性能监控
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """任务开始前的处理"""
    task.request.start_time = time.time()

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """任务完成后的处理"""
    if hasattr(task.request, 'start_time'):
        execution_time = time.time() - task.request.start_time
        
        # 记录性能指标
        metrics_client.histogram('task_execution_time').labels(
            task_name=task.name,
            state=state
        ).observe(execution_time)
        
        # 慢任务告警
        if execution_time > 60:  # 超过1分钟
            logger.warning(f"Slow task detected: {task.name} took {execution_time:.2f}s")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """任务失败处理"""
    logger.error(f"Task {sender.name} failed: {exception}")
    
    # 记录失败指标
    metrics_client.counter('task_failures').labels(
        task_name=sender.name,
        exception_type=type(exception).__name__
    ).inc()

class OptimizedTask:
    """优化的任务基类"""
    
    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.max_retries = max_retries
        self.priority = TaskPriorityManager.get_task_priority(name)
    
    def apply_async(self, args=None, kwargs=None, **options):
        """异步执行任务"""
        
        # 设置优先级
        options.setdefault('priority', self.priority)
        
        # 设置重试策略
        options.setdefault('retry', True)
        options.setdefault('retry_policy', {
            'max_retries': self.max_retries,
            'interval_start': 0,
            'interval_step': 0.2,
            'interval_max': 0.2,
        })
        
        return super().apply_async(args=args, kwargs=kwargs, **options)

# 批量任务处理
@celery_app.task(bind=True, base=OptimizedTask)
def batch_rating_calculation(self, player_ids: List[str], recalculate_all: bool = False):
    """批量评分计算"""
    
    batch_size = 50
    failed_players = []
    
    for i in range(0, len(player_ids), batch_size):
        batch = player_ids[i:i + batch_size]
        
        try:
            # 批量处理评分计算
            for player_id in batch:
                calculate_player_rating.apply_async(
                    args=[player_id, recalculate_all],
                    priority=TaskPriorityManager.PRIORITY_HIGH
                )
                
        except Exception as e:
            logger.error(f"Batch rating calculation failed for batch {i//batch_size}: {e}")
            failed_players.extend(batch)
    
    if failed_players:
        # 重试失败的选手
        self.retry(args=[failed_players, recalculate_all], countdown=60)
    
    return {
        "processed": len(player_ids) - len(failed_players),
        "failed": len(failed_players)
    }

# 智能任务调度
class TaskScheduler:
    """智能任务调度器"""
    
    def __init__(self, celery_app, redis_client):
        self.celery = celery_app
        self.redis = redis_client
    
    async def schedule_rating_update(self, player_id: str, delay_seconds: int = 0):
        """调度评分更新任务"""
        
        # 检查是否已有待处理的评分更新任务
        existing_task_key = f"pending_rating_update:{player_id}"
        
        if await self.redis.exists(existing_task_key):
            # 合并任务，避免重复计算
            logger.info(f"Merging rating update task for player {player_id}")
            return
        
        # 标记任务待处理
        await self.redis.setex(existing_task_key, 300, "1")  # 5分钟内去重
        
        # 调度任务
        task = calculate_player_rating.apply_async(
            args=[player_id],
            countdown=delay_seconds,
            priority=TaskPriorityManager.PRIORITY_HIGH
        )
        
        return task.id
    
    async def bulk_schedule_tasks(self, task_configs: List[Dict]):
        """批量调度任务"""
        
        scheduled_tasks = []
        
        for config in task_configs:
            task_name = config["task_name"]
            args = config.get("args", [])
            kwargs = config.get("kwargs", {})
            delay = config.get("delay", 0)
            
            task = self.celery.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                countdown=delay
            )
            
            scheduled_tasks.append({
                "task_id": task.id,
                "task_name": task_name,
                "scheduled_at": datetime.utcnow() + timedelta(seconds=delay)
            })
        
        return scheduled_tasks
```

### 2.4 前端性能优化

#### 2.4.1 资源优化策略

```typescript
// 组件懒加载配置
const LazyComponents = {
  // 路由级懒加载
  Tournament: () => import('@/features/tournaments/TournamentList.vue'),
  TournamentDetail: () => import('@/features/tournaments/TournamentDetail.vue'),
  TeamManagement: () => import('@/features/teams/TeamManagement.vue'),
  PlayerProfile: () => import('@/features/players/PlayerProfile.vue'),
  MatchHistory: () => import('@/features/matches/MatchHistory.vue'),
  
  // 组件级懒加载
  DataChart: () => import('@/shared/components/DataChart.vue'),
  RatingChart: () => import('@/features/players/components/RatingChart.vue'),
  TransferHistory: () => import('@/features/transfers/TransferHistory.vue'),
}

// 资源预加载策略
class ResourcePreloader {
  private preloadedResources = new Set<string>()
  
  async preloadCriticalResources() {
    const criticalResources = [
      '/api/v1/user/profile',
      '/api/v1/regions',
      '/api/v1/leaderboard/summary',
    ]
    
    const preloadPromises = criticalResources.map(url => 
      fetch(url, { credentials: 'include' })
        .then(response => response.json())
        .then(data => this.cacheResource(url, data))
    )
    
    await Promise.allSettled(preloadPromises)
  }
  
  async preloadRouteResources(routeName: string) {
    const routeResourceMap = {
      'tournaments': [
        '/api/v1/tournaments',
        '/api/v1/tournaments/featured'
      ],
      'leaderboard': [
        '/api/v1/leaderboard',
        '/api/v1/regions'
      ],
      'teams': [
        '/api/v1/teams',
        '/api/v1/teams/my-teams'
      ]
    }
    
    const resources = routeResourceMap[routeName] || []
    resources.forEach(url => this.prefetchResource(url))
  }
  
  private prefetchResource(url: string) {
    if (this.preloadedResources.has(url)) return
    
    const link = document.createElement('link')
    link.rel = 'prefetch'
    link.href = url
    document.head.appendChild(link)
    
    this.preloadedResources.add(url)
  }
  
  private cacheResource(url: string, data: any) {
    // 使用浏览器缓存或者应用级缓存存储数据
    if ('caches' in window) {
      caches.open('api-cache').then(cache => {
        cache.put(url, new Response(JSON.stringify(data)))
      })
    }
  }
}

// 图片优化
class ImageOptimizer {
  private imageCache = new Map<string, HTMLImageElement>()
  
  async loadOptimizedImage(src: string, placeholder?: string): Promise<HTMLImageElement> {
    // 检查缓存
    if (this.imageCache.has(src)) {
      return this.imageCache.get(src)!
    }
    
    return new Promise((resolve, reject) => {
      const img = new Image()
      
      // 设置加载占位图
      if (placeholder) {
        img.src = placeholder
      }
      
      img.onload = () => {
        this.imageCache.set(src, img)
        resolve(img)
      }
      
      img.onerror = reject
      
      // 使用 Intersection Observer 实现懒加载
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            img.src = src
            observer.disconnect()
          }
        })
      })
      
      // 如果图片元素已在DOM中，开始观察
      if (img.parentElement) {
        observer.observe(img)
      } else {
        // 否则直接加载
        img.src = src
      }
    })
  }
  
  generateResponsiveImageSrc(baseUrl: string, width: number): string {
    // 根据设备像素比和屏幕宽度生成合适的图片URL
    const devicePixelRatio = window.devicePixelRatio || 1
    const optimizedWidth = Math.ceil(width * devicePixelRatio)
    
    return `${baseUrl}?w=${optimizedWidth}&q=85&f=webp`
  }
}
```

#### 2.4.2 状态管理优化

```typescript
// Pinia store 优化
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useOptimizedPlayerStore = defineStore('optimizedPlayer', () => {
  // 状态
  const players = ref(new Map<string, Player>())
  const leaderboard = ref<LeaderboardEntry[]>([])
  const loadingStates = ref(new Map<string, boolean>())
  const lastUpdated = ref<Record<string, number>>({})
  
  // 计算属性（自动缓存）
  const topPlayers = computed(() => 
    leaderboard.value.slice(0, 10)
  )
  
  const playersByPosition = computed(() => {
    const grouped = new Map<string, Player[]>()
    players.value.forEach(player => {
      const position = player.position
      if (!grouped.has(position)) {
        grouped.set(position, [])
      }
      grouped.get(position)!.push(player)
    })
    return grouped
  })
  
  // 动作
  const fetchPlayer = async (playerId: string, forceRefresh = false) => {
    // 防重复请求
    if (loadingStates.value.get(playerId)) {
      return players.value.get(playerId)
    }
    
    // 检查缓存新鲜度（5分钟内不重新获取）
    const lastFetch = lastUpdated.value[playerId]
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000
    
    if (!forceRefresh && lastFetch && lastFetch > fiveMinutesAgo) {
      return players.value.get(playerId)
    }
    
    loadingStates.value.set(playerId, true)
    
    try {
      const response = await api.get(`/players/${playerId}`)
      const player = response.data
      
      players.value.set(playerId, player)
      lastUpdated.value[playerId] = Date.now()
      
      return player
    } finally {
      loadingStates.value.set(playerId, false)
    }
  }
  
  const updatePlayerRating = (playerId: string, newRating: number) => {
    const player = players.value.get(playerId)
    if (player) {
      // 使用不可变更新
      players.value.set(playerId, {
        ...player,
        rating: newRating
      })
      
      // 更新排行榜中的对应项
      const leaderboardIndex = leaderboard.value.findIndex(entry => entry.playerId === playerId)
      if (leaderboardIndex !== -1) {
        leaderboard.value[leaderboardIndex] = {
          ...leaderboard.value[leaderboardIndex],
          rating: newRating
        }
        
        // 重新排序
        leaderboard.value.sort((a, b) => b.rating - a.rating)
      }
    }
  }
  
  const batchUpdatePlayers = (updates: Array<{playerId: string, data: Partial<Player>}>) => {
    // 批量更新减少响应式触发次数
    updates.forEach(({ playerId, data }) => {
      const existingPlayer = players.value.get(playerId)
      if (existingPlayer) {
        players.value.set(playerId, { ...existingPlayer, ...data })
      }
    })
  }
  
  // 清理过期缓存
  const cleanupExpiredCache = () => {
    const oneHourAgo = Date.now() - 60 * 60 * 1000
    
    Object.entries(lastUpdated.value).forEach(([playerId, timestamp]) => {
      if (timestamp < oneHourAgo) {
        players.value.delete(playerId)
        delete lastUpdated.value[playerId]
      }
    })
  }
  
  return {
    // 状态
    players: computed(() => Array.from(players.value.values())),
    leaderboard: readonly(leaderboard),
    topPlayers,
    playersByPosition,
    
    // 动作
    fetchPlayer,
    updatePlayerRating,
    batchUpdatePlayers,
    cleanupExpiredCache,
    
    // 工具方法
    getPlayer: (id: string) => players.value.get(id),
    isPlayerLoading: (id: string) => loadingStates.value.get(id) || false,
  }
})

// 组合式函数优化
export function useOptimizedPagination<T>(
  fetchFunction: (page: number, size: number) => Promise<{ data: T[], total: number }>,
  pageSize = 20
) {
  const currentPage = ref(1)
  const items = ref<T[]>([])
  const total = ref(0)
  const loading = ref(false)
  const cache = new Map<number, T[]>()
  
  const totalPages = computed(() => Math.ceil(total.value / pageSize))
  const hasNextPage = computed(() => currentPage.value < totalPages.value)
  const hasPrevPage = computed(() => currentPage.value > 1)
  
  const fetchPage = async (page: number) => {
    // 检查缓存
    if (cache.has(page)) {
      items.value = cache.get(page)!
      currentPage.value = page
      return
    }
    
    loading.value = true
    try {
      const response = await fetchFunction(page, pageSize)
      items.value = response.data
      total.value = response.total
      currentPage.value = page
      
      // 缓存结果
      cache.set(page, response.data)
      
      // 预加载下一页
      if (page < totalPages.value && !cache.has(page + 1)) {
        fetchFunction(page + 1, pageSize).then(nextResponse => {
          cache.set(page + 1, nextResponse.data)
        })
      }
    } finally {
      loading.value = false
    }
  }
  
  const nextPage = () => {
    if (hasNextPage.value) {
      fetchPage(currentPage.value + 1)
    }
  }
  
  const prevPage = () => {
    if (hasPrevPage.value) {
      fetchPage(currentPage.value - 1)
    }
  }
  
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
      fetchPage(page)
    }
  }
  
  // 初始加载
  fetchPage(1)
  
  return {
    items: readonly(items),
    currentPage: readonly(currentPage),
    totalPages,
    total: readonly(total),
    loading: readonly(loading),
    hasNextPage,
    hasPrevPage,
    nextPage,
    prevPage,
    goToPage,
    refresh: () => {
      cache.clear()
      fetchPage(currentPage.value)
    }
  }
}
```

## 3. 监控与告警系统

### 3.1 应用性能监控(APM)

```python
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.setup_prometheus_metrics()
        self.setup_opentelemetry()
        
    def setup_prometheus_metrics(self):
        """设置Prometheus指标"""
        
        # 请求计数器
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        # 请求耗时直方图
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        # 数据库查询指标
        self.db_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration',
            ['query_type', 'table']
        )
        
        # 缓存指标
        self.cache_operations = Counter(
            'cache_operations_total',
            'Cache operations',
            ['operation', 'status']  # hit/miss/set/delete
        )
        
        # 系统资源指标
        self.cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('memory_usage_percent', 'Memory usage percentage')
        self.disk_usage = Gauge('disk_usage_percent', 'Disk usage percentage')
        
        # 业务指标
        self.active_users = Gauge('active_users_total', 'Number of active users')
        self.active_matches = Gauge('active_matches_total', 'Number of active matches')
        self.pending_transfers = Gauge('pending_transfers_total', 'Number of pending transfers')
        
    def setup_opentelemetry(self):
        """设置OpenTelemetry分布式追踪"""
        
        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger-agent",
            agent_port=6831,
        )
        
        # 设置追踪器
        trace.set_tracer_provider(TracerProvider())
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
    
    def track_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """追踪HTTP请求"""
        
        self.request_counter.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_database_query(self, query_type: str, table: str, duration: float):
        """追踪数据库查询"""
        
        self.db_query_duration.labels(
            query_type=query_type,
            table=table
        ).observe(duration)
    
    def track_cache_operation(self, operation: str, status: str):
        """追踪缓存操作"""
        
        self.cache_operations.labels(
            operation=operation,
            status=status
        ).inc()
    
    def update_system_metrics(self):
        """更新系统指标"""
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_usage.set(cpu_percent)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        self.memory_usage.set(memory.percent)
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.disk_usage.set(disk_percent)
    
    def create_span(self, operation_name: str, **attributes):
        """创建分布式追踪Span"""
        
        span = self.tracer.start_span(operation_name)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        
        return span

# 性能监控中间件
class PerformanceMiddleware:
    """性能监控中间件"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        
    async def __call__(self, request, call_next):
        start_time = time.time()
        
        # 创建追踪Span
        with self.monitor.create_span(
            f"{request.method} {request.url.path}",
            http_method=request.method,
            http_url=str(request.url),
            user_agent=request.headers.get("user-agent", "")
        ) as span:
            
            try:
                response = await call_next(request)
                
                # 记录成功请求
                duration = time.time() - start_time
                self.monitor.track_request(
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration
                )
                
                span.set_attribute("http_status_code", response.status_code)
                span.set_attribute("response_time", duration)
                
                # 慢请求告警
                if duration > 5.0:  # 超过5秒
                    logger.warning(f"Slow request: {request.method} {request.url.path} took {duration:.2f}s")
                
                return response
                
            except Exception as e:
                # 记录错误
                duration = time.time() - start_time
                self.monitor.track_request(
                    request.method,
                    request.url.path,
                    500,
                    duration
                )
                
                span.set_attribute("error", True)
                span.set_attribute("error_message", str(e))
                
                raise

# 数据库查询监控
class DatabaseQueryMonitor:
    """数据库查询监控"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def track_query(self, query: str, params: dict, duration: float, result_count: int = None):
        """追踪数据库查询"""
        
        # 解析查询类型和表名
        query_type = self.extract_query_type(query)
        table_name = self.extract_table_name(query)
        
        self.monitor.track_database_query(query_type, table_name, duration)
        
        # 慢查询告警
        if duration > 1.0:  # 超过1秒
            logger.warning(f"Slow query detected: {query_type} on {table_name} took {duration:.2f}s")
            
        # N+1查询检测
        if query_type == "SELECT" and result_count == 1 and duration > 0.1:
            self.detect_n_plus_one_query(query, params)
    
    def extract_query_type(self, query: str) -> str:
        """提取查询类型"""
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'
    
    def extract_table_name(self, query: str) -> str:
        """提取表名"""
        # 简化的表名提取逻辑
        import re
        
        patterns = [
            r'FROM\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'INSERT\s+INTO\s+(\w+)',
            r'DELETE\s+FROM\s+(\w+)'
        ]
        
        query_upper = query.upper()
        for pattern in patterns:
            match = re.search(pattern, query_upper)
            if match:
                return match.group(1).lower()
        
        return 'unknown'
    
    def detect_n_plus_one_query(self, query: str, params: dict):
        """检测N+1查询问题"""
        
        # 检测连续的相似查询
        query_signature = self.get_query_signature(query)
        current_time = time.time()
        
        # 使用Redis存储查询历史
        redis_key = f"query_history:{query_signature}"
        query_count = self.redis.incr(redis_key)
        self.redis.expire(redis_key, 60)  # 1分钟内的查询计数
        
        if query_count > 10:  # 1分钟内相同查询超过10次
            logger.warning(f"Potential N+1 query detected: {query_signature}")
    
    def get_query_signature(self, query: str) -> str:
        """获取查询签名"""
        # 移除参数，生成查询模式签名
        import re
        signature = re.sub(r':\w+|\$\d+|\?', '?', query)
        return hashlib.md5(signature.encode()).hexdigest()[:8]
```

### 3.2 告警系统

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"

@dataclass
class Alert:
    title: str
    message: str
    level: AlertLevel
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "message": self.message,
            "level": self.level,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notification_channels = self._setup_notification_channels()
        self.alert_rules = self._load_alert_rules()
        self.alert_history = []
        
    def _setup_notification_channels(self) -> Dict[str, Any]:
        """设置通知渠道"""
        
        channels = {}
        
        # 邮件通知
        if self.config.get("email"):
            channels[AlertChannel.EMAIL] = EmailNotifier(self.config["email"])
        
        # Slack通知
        if self.config.get("slack"):
            channels[AlertChannel.SLACK] = SlackNotifier(self.config["slack"])
        
        # 短信通知
        if self.config.get("sms"):
            channels[AlertChannel.SMS] = SMSNotifier(self.config["sms"])
        
        # Webhook通知
        if self.config.get("webhook"):
            channels[AlertChannel.WEBHOOK] = WebhookNotifier(self.config["webhook"])
        
        return channels
    
    def _load_alert_rules(self) -> Dict[str, Dict]:
        """加载告警规则"""
        
        return {
            "high_cpu_usage": {
                "condition": lambda metrics: metrics.get("cpu_usage", 0) > 80,
                "level": AlertLevel.WARNING,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK],
                "cooldown": 300,  # 5分钟冷却
                "message_template": "CPU usage is {cpu_usage}%, exceeding 80% threshold"
            },
            "high_memory_usage": {
                "condition": lambda metrics: metrics.get("memory_usage", 0) > 90,
                "level": AlertLevel.CRITICAL,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SMS],
                "cooldown": 180,
                "message_template": "Memory usage is {memory_usage}%, exceeding 90% threshold"
            },
            "database_connection_failure": {
                "condition": lambda metrics: metrics.get("db_connection_errors", 0) > 5,
                "level": AlertLevel.ERROR,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK],
                "cooldown": 60,
                "message_template": "Database connection failures: {db_connection_errors} in the last minute"
            },
            "slow_api_response": {
                "condition": lambda metrics: metrics.get("avg_response_time", 0) > 5,
                "level": AlertLevel.WARNING,
                "channels": [AlertChannel.EMAIL],
                "cooldown": 600,
                "message_template": "Average API response time is {avg_response_time}s, exceeding 5s threshold"
            },
            "transfer_processing_failure": {
                "condition": lambda metrics: metrics.get("failed_transfers", 0) > 3,
                "level": AlertLevel.ERROR,
                "channels": [AlertChannel.EMAIL, AlertChannel.SLACK],
                "cooldown": 300,
                "message_template": "Transfer processing failures: {failed_transfers} in the last hour"
            }
        }
    
    async def check_metrics(self, metrics: Dict[str, Any]):
        """检查指标并触发告警"""
        
        for rule_name, rule in self.alert_rules.items():
            if rule["condition"](metrics):
                
                # 检查冷却时间
                if self._is_in_cooldown(rule_name):
                    continue
                
                # 创建告警
                alert = Alert(
                    title=f"Alert: {rule_name.replace('_', ' ').title()}",
                    message=rule["message_template"].format(**metrics),
                    level=rule["level"],
                    source="system_monitor",
                    timestamp=datetime.utcnow(),
                    metadata={"rule_name": rule_name, "metrics": metrics}
                )
                
                # 发送告警
                await self._send_alert(alert, rule["channels"])
                
                # 记录告警历史
                self._record_alert(rule_name, alert)
    
    async def _send_alert(self, alert: Alert, channels: List[AlertChannel]):
        """发送告警"""
        
        send_tasks = []
        for channel in channels:
            if channel in self.notification_channels:
                notifier = self.notification_channels[channel]
                send_tasks.append(notifier.send(alert))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """检查告警是否在冷却期"""
        
        rule = self.alert_rules[rule_name]
        cooldown_seconds = rule.get("cooldown", 0)
        
        if cooldown_seconds == 0:
            return False
        
        # 查找最近的告警
        cutoff_time = datetime.utcnow() - timedelta(seconds=cooldown_seconds)
        recent_alerts = [
            alert for alert in self.alert_history
            if (alert["rule_name"] == rule_name and 
                alert["timestamp"] > cutoff_time)
        ]
        
        return len(recent_alerts) > 0
    
    def _record_alert(self, rule_name: str, alert: Alert):
        """记录告警历史"""
        
        self.alert_history.append({
            "rule_name": rule_name,
            "alert": alert.to_dict(),
            "timestamp": alert.timestamp
        })
        
        # 保持历史记录大小
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]

class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, config: Dict[str, str]):
        self.smtp_host = config["smtp_host"]
        self.smtp_port = config["smtp_port"]
        self.username = config["username"]
        self.password = config["password"]
        self.from_email = config["from_email"]
        self.recipients = config["recipients"]
    
    async def send(self, alert: Alert):
        """发送邮件告警"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = f"[{alert.level.upper()}] {alert.title}"
            
            # 构建邮件正文
            body = self._build_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
                
            logger.info(f"Alert email sent successfully: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
    
    def _build_email_body(self, alert: Alert) -> str:
        """构建邮件正文"""
        
        color_map = {
            AlertLevel.INFO: "#17a2b8",
            AlertLevel.WARNING: "#ffc107", 
            AlertLevel.ERROR: "#dc3545",
            AlertLevel.CRITICAL: "#721c24"
        }
        
        color = color_map.get(alert.level, "#6c757d")
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h2>{alert.title}</h2>
                </div>
                <div style="padding: 20px; border: 1px solid #ddd;">
                    <p><strong>Level:</strong> {alert.level.upper()}</p>
                    <p><strong>Source:</strong> {alert.source}</p>
                    <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Message:</strong></p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid {color};">
                        {alert.message}
                    </div>
                    {self._format_metadata(alert.metadata)}
                </div>
                <div style="padding: 10px; text-align: center; color: #6c757d; font-size: 12px;">
                    FlyEsports Platform Monitoring System
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """格式化元数据"""
        
        if not metadata:
            return ""
        
        items = []
        for key, value in metadata.items():
            if key != "rule_name":  # 跳过内部字段
                items.append(f"<li><strong>{key}:</strong> {value}</li>")
        
        if not items:
            return ""
        
        return f"""
        <p><strong>Details:</strong></p>
        <ul>
            {"".join(items)}
        </ul>
        """

class SlackNotifier:
    """Slack通知器"""
    
    def __init__(self, config: Dict[str, str]):
        self.webhook_url = config["webhook_url"]
        self.channel = config.get("channel", "#alerts")
        self.username = config.get("username", "AlertBot")
    
    async def send(self, alert: Alert):
        """发送Slack告警"""
        
        try:
            color_map = {
                AlertLevel.INFO: "good",
                AlertLevel.WARNING: "warning",
                AlertLevel.ERROR: "danger", 
                AlertLevel.CRITICAL: "danger"
            }
            
            payload = {
                "channel": self.channel,
                "username": self.username,
                "attachments": [{
                    "color": color_map.get(alert.level, "warning"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {"title": "Level", "value": alert.level.upper(), "short": True},
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), "short": False}
                    ],
                    "footer": "FlyEsports Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Alert sent to Slack successfully: {alert.title}")
                    else:
                        logger.error(f"Failed to send Slack alert: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
```

## 4. 总结

FlyEsports平台的安全与性能优化方案涵盖了从应用层到基础设施层的全方位保护和优化。通过多层次的安全防护、智能化的性能优化策略和完善的监控告警系统，确保平台能够在复杂的业务场景下保持高安全性、高性能和高可用性。

关键优化亮点：
- 多因素认证和基于角色的访问控制确保账户安全
- 敏感数据加密和访问审计保护用户隐私
- 多级缓存架构显著提升响应速度
- 数据库查询优化和连接池管理保障数据层性能
- 智能任务调度和批量处理提高异步处理效率
- 实时监控和告警系统保证运维响应及时性

该安全与性能优化方案为FlyEsports平台提供了企业级的安全防护能力和高性能处理能力，能够支撑平台的快速发展和大规模用户访问需求。