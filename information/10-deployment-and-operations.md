# 部署与运维指南 (Deployment & Operations Guide)

## 1. 容器化部署架构

FlyEsports 平台采用 Docker 和 Kubernetes 的容器化部署方案，实现服务的自动化部署、扩缩容和高可用性管理。

### 1.1 Docker 容器化配置

#### 1.1.1 后端服务 Dockerfile

```dockerfile
# Backend API Dockerfile
FROM python:3.11-slim as builder

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 Python 依赖
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 多阶段构建：生产镜像
FROM python:3.11-slim as runtime

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash flyesp

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 设置工作目录和权限
WORKDIR /app
COPY --chown=flyesp:flyesp . .

# 切换到非 root 用户
USER flyesp

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "main:app"]
```

#### 1.1.2 前端服务 Dockerfile

```dockerfile
# Frontend Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# 复制包管理文件
COPY package*.json ./
COPY yarn.lock ./

# 安装依赖
RUN yarn install --frozen-lockfile

# 复制源码并构建
COPY . .
RUN yarn build

# 生产镜像
FROM nginx:alpine as runtime

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### 1.1.3 Nginx 配置优化

```nginx
# nginx.conf
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 前端应用配置
    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        # 安全头设置
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Vue Router 历史模式支持
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket 支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 1.2 Docker Compose 开发环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: flyesp_dev
      POSTGRES_USER: flyesp
      POSTGRES_PASSWORD: flyesp_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flyesp"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 后端 API
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://flyesp:flyesp_password@postgres:5432/flyesp_dev
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - JWT_SECRET_KEY=your-dev-secret-key
      - DEBUG=true
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - ./uploads:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Celery Worker
  celery:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://flyesp:flyesp_password@postgres:5432/flyesp_dev
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=4
    volumes:
      - .:/app
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Celery Beat 调度器
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://flyesp:flyesp_password@postgres:5432/flyesp_dev
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    command: celery -A tasks.celery_app beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # 前端应用
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    driver: bridge
```

### 1.3 生产环境 Kubernetes 部署

#### 1.3.1 Kubernetes 命名空间和配置

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: flyesp-prod
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: flyesp-config
  namespace: flyesp-prod
data:
  DATABASE_HOST: "postgres-service"
  DATABASE_NAME: "flyesp_prod"
  REDIS_HOST: "redis-service"
  CELERY_BROKER_URL: "redis://redis-service:6379/1"
  JWT_ALGORITHM: "HS256"
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
---
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: flyesp-secrets
  namespace: flyesp-prod
type: Opaque
stringData:
  DATABASE_PASSWORD: "your-secure-database-password"
  JWT_SECRET_KEY: "your-secure-jwt-secret-key"
  REDIS_PASSWORD: "your-secure-redis-password"
  EMAIL_PASSWORD: "your-email-service-password"
```

#### 1.3.2 数据库服务部署

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: flyesp-prod
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: "flyesp_prod"
        - name: POSTGRES_USER
          value: "flyesp"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: DATABASE_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - flyesp
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: flyesp-prod
spec:
  selector:
    app: postgres
  ports:
  - protocol: TCP
    port: 5432
    targetPort: 5432
  type: ClusterIP
```

#### 1.3.3 Redis 缓存服务

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: flyesp-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)", "--appendonly", "yes"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: flyesp-prod
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: flyesp-prod
spec:
  selector:
    app: redis
  ports:
  - protocol: TCP
    port: 6379
    targetPort: 6379
  type: ClusterIP
```

#### 1.3.4 后端 API 服务

```yaml
# k8s/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: flyesp-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: flyesp/backend:latest
        env:
        - name: DATABASE_URL
          value: "postgresql://flyesp:$(DATABASE_PASSWORD)@postgres-service:5432/flyesp_prod"
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: DATABASE_PASSWORD
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: JWT_SECRET_KEY
        envFrom:
        - configMapRef:
            name: flyesp-config
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: flyesp-prod
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
---
# HPA 自动扩缩容
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: flyesp-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 1.3.5 Celery 工作节点

```yaml
# k8s/celery.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: flyesp-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: flyesp/backend:latest
        command: ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
        env:
        - name: DATABASE_URL
          value: "postgresql://flyesp:$(DATABASE_PASSWORD)@postgres-service:5432/flyesp_prod"
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: DATABASE_PASSWORD
        envFrom:
        - configMapRef:
            name: flyesp-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - tasks.celery_app
            - inspect
            - ping
          initialDelaySeconds: 30
          periodSeconds: 30
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: flyesp-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
      - name: celery-beat
        image: flyesp/backend:latest
        command: ["celery", "-A", "tasks.celery_app", "beat", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          value: "postgresql://flyesp:$(DATABASE_PASSWORD)@postgres-service:5432/flyesp_prod"
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flyesp-secrets
              key: DATABASE_PASSWORD
        envFrom:
        - configMapRef:
            name: flyesp-config
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

#### 1.3.6 Ingress 和负载均衡

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: flyesp-ingress
  namespace: flyesp-prod
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.flyesp.com
    - www.flyesp.com
    secretName: flyesp-tls
  rules:
  - host: api.flyesp.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
  - host: www.flyesp.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

## 2. CI/CD 持续集成与部署

### 2.1 GitHub Actions 工作流

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: flyesp

jobs:
  # 代码质量检查
  code-quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements/dev.txt
    
    - name: Run Black formatting check
      run: black --check .
    
    - name: Run flake8 linting
      run: flake8 .
    
    - name: Run mypy type checking
      run: mypy .
    
    - name: Run pytest
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  # 安全扫描
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Bandit security check
      run: |
        pip install bandit
        bandit -r . -f json -o bandit-report.json
    
    - name: Run Safety dependency check
      run: |
        pip install safety
        safety check --json --output safety-report.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: "*-report.json"

  # 构建和推送 Docker 镜像
  build-and-push:
    needs: [code-quality, security-scan]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
    - name: Checkout
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ github.repository }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push Backend image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.backend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Build and push Frontend image
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        file: ./frontend/Dockerfile
        push: true
        tags: ${{ env.REGISTRY }}/${{ github.repository }}/frontend:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  # 部署到开发环境
  deploy-dev:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: development
    steps:
    - name: Deploy to Development
      run: |
        echo "Deploying ${{ needs.build-and-push.outputs.image-tag }} to development"
        # 这里添加部署到开发环境的逻辑
        # 例如：kubectl set image deployment/backend backend=${{ needs.build-and-push.outputs.image-tag }}

  # 部署到生产环境
  deploy-prod:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - name: Deploy to Production
      run: |
        echo "Deploying ${{ needs.build-and-push.outputs.image-tag }} to production"
        # 这里添加部署到生产环境的逻辑
        
    - name: Run smoke tests
      run: |
        # 部署后的烟雾测试
        curl -f https://api.flyesp.com/health || exit 1
        echo "Production deployment successful"
```

### 2.2 自动化部署脚本

```bash
#!/bin/bash
# scripts/deploy.sh

set -euo pipefail

# 配置变量
ENVIRONMENT=${1:-"development"}
NAMESPACE="flyesp-${ENVIRONMENT}"
IMAGE_TAG=${2:-"latest"}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 验证环境
validate_environment() {
    log_info "Validating deployment environment: ${ENVIRONMENT}"
    
    if [[ ! "${ENVIRONMENT}" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment. Must be one of: development, staging, production"
        exit 1
    fi
    
    # 检查 kubectl 连接
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Environment validation passed"
}

# 创建命名空间
create_namespace() {
    log_info "Creating namespace: ${NAMESPACE}"
    
    kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
    
    # 设置资源配额（生产环境）
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: resource-quota
  namespace: ${NAMESPACE}
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "10"
EOF
    fi
}

# 部署数据库
deploy_database() {
    log_info "Deploying database..."
    
    # 应用数据库迁移
    kubectl run db-migrate-$(date +%s) \
        --namespace="${NAMESPACE}" \
        --image="flyesp/backend:${IMAGE_TAG}" \
        --rm -i --restart=Never \
        --command -- python -m alembic upgrade head
    
    log_info "Database migration completed"
}

# 部署应用服务
deploy_services() {
    log_info "Deploying application services..."
    
    # 替换镜像标签
    sed "s/IMAGE_TAG_PLACEHOLDER/${IMAGE_TAG}/g" k8s/backend.yaml | kubectl apply -f -
    sed "s/IMAGE_TAG_PLACEHOLDER/${IMAGE_TAG}/g" k8s/celery.yaml | kubectl apply -f -
    
    # 等待 deployment 就绪
    kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=300s
    kubectl rollout status deployment/celery-worker -n "${NAMESPACE}" --timeout=300s
    
    log_info "Application services deployed successfully"
}

# 运行健康检查
health_check() {
    log_info "Running health checks..."
    
    local backend_service=$(kubectl get service backend-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
    
    # 创建测试 pod
    kubectl run health-check-$(date +%s) \
        --namespace="${NAMESPACE}" \
        --image=curlimages/curl:latest \
        --rm -i --restart=Never \
        --command -- curl -f "http://${backend_service}:8000/health"
    
    if [[ $? -eq 0 ]]; then
        log_info "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
}

# 运行烟雾测试
smoke_tests() {
    log_info "Running smoke tests..."
    
    # 基础 API 测试
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        curl -f https://api.flyesp.com/health || {
            log_error "Production API health check failed"
            exit 1
        }
        
        curl -f https://www.flyesp.com || {
            log_error "Production frontend health check failed"
            exit 1
        }
    fi
    
    log_info "Smoke tests passed"
}

# 回滚函数
rollback() {
    log_warn "Deployment failed. Initiating rollback..."
    
    kubectl rollout undo deployment/backend -n "${NAMESPACE}"
    kubectl rollout undo deployment/celery-worker -n "${NAMESPACE}"
    
    log_info "Rollback completed"
}

# 清理资源
cleanup() {
    log_info "Cleaning up temporary resources..."
    
    # 清理失败的 pods
    kubectl delete pods --field-selector=status.phase=Failed -n "${NAMESPACE}"
    
    # 清理旧的 replicasets
    kubectl delete replicasets $(kubectl get rs -n "${NAMESPACE}" -o name | head -n -3) -n "${NAMESPACE}" 2>/dev/null || true
}

# 主部署流程
main() {
    log_info "Starting deployment to ${ENVIRONMENT} environment with image tag: ${IMAGE_TAG}"
    
    trap rollback ERR
    
    validate_environment
    create_namespace
    
    # 部署基础设施组件
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    kubectl apply -f k8s/postgres.yaml
    kubectl apply -f k8s/redis.yaml
    
    # 等待基础设施就绪
    kubectl wait --for=condition=ready pod -l app=postgres -n "${NAMESPACE}" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n "${NAMESPACE}" --timeout=300s
    
    deploy_database
    deploy_services
    
    # 生产环境额外检查
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        health_check
        smoke_tests
    fi
    
    cleanup
    
    log_info "Deployment to ${ENVIRONMENT} completed successfully!"
    
    # 显示部署信息
    echo "========================================"
    echo "Deployment Summary:"
    echo "Environment: ${ENVIRONMENT}"
    echo "Namespace: ${NAMESPACE}"
    echo "Image Tag: ${IMAGE_TAG}"
    echo "========================================"
    
    kubectl get pods -n "${NAMESPACE}"
}

# 执行主函数
main "$@"
```

## 3. 监控与日志系统

### 3.1 Prometheus 监控配置

```yaml
# k8s/monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "/etc/prometheus/rules/*.yml"
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093
    
    scrape_configs:
      # Kubernetes API Server
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
          action: keep
          regex: default;kubernetes;https
      
      # FlyEsp Backend Services
      - job_name: 'flyesp-backend'
        kubernetes_sd_configs:
        - role: endpoints
          namespaces:
            names:
            - flyesp-prod
        relabel_configs:
        - source_labels: [__meta_kubernetes_service_name]
          action: keep
          regex: backend-service
        - source_labels: [__meta_kubernetes_pod_name]
          target_label: instance
        - source_labels: [__meta_kubernetes_pod_container_name]
          target_label: container
      
      # Redis Exporter
      - job_name: 'redis-exporter'
        static_configs:
        - targets: ['redis-exporter:9121']
      
      # PostgreSQL Exporter  
      - job_name: 'postgres-exporter'
        static_configs:
        - targets: ['postgres-exporter:9187']
      
      # Node Exporter
      - job_name: 'node-exporter'
        kubernetes_sd_configs:
        - role: node
        relabel_configs:
        - action: labelmap
          regex: __meta_kubernetes_node_label_(.+)
---
# k8s/monitoring/prometheus-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: monitoring
data:
  flyesp.yml: |
    groups:
    - name: flyesp.rules
      rules:
      - alert: HighCPUUsage
        expr: (cpu_usage_percent) > 80
        for: 5m
        labels:
          severity: warning
          service: flyesp
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}% for more than 5 minutes"
      
      - alert: HighMemoryUsage
        expr: (memory_usage_percent) > 90
        for: 2m
        labels:
          severity: critical
          service: flyesp
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}% for more than 2 minutes"
      
      - alert: DatabaseConnectionFailure
        expr: increase(database_connection_errors_total[1m]) > 5
        for: 1m
        labels:
          severity: critical
          service: database
        annotations:
          summary: "Database connection failures"
          description: "More than 5 database connection failures in the last minute"
      
      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
          service: api
        annotations:
          summary: "Slow API response time"
          description: "95th percentile response time is {{ $value }}s for more than 5 minutes"
      
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
          service: kubernetes
        annotations:
          summary: "Pod crash looping"
          description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"
```

### 3.2 Grafana 仪表板配置

```json
{
  "dashboard": {
    "id": null,
    "title": "FlyEsports Platform Dashboard",
    "tags": ["flyesp", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests/sec"
          }
        ],
        "xAxis": {
          "show": true
        },
        "tooltip": {
          "shared": true
        }
      },
      {
        "id": 2,
        "title": "Response Time Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Active Users",
        "type": "singlestat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": ""
          }
        ],
        "valueName": "current"
      },
      {
        "id": 4,
        "title": "Database Query Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(database_query_duration_seconds_sum[5m]) / rate(database_query_duration_seconds_count[5m])",
            "legendFormat": "{{query_type}} {{table}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(cache_operations_total{status=\"hit\"}[5m]) / rate(cache_operations_total[5m]) * 100",
            "legendFormat": "Hit Rate %"
          }
        ],
        "yAxes": [
          {
            "min": 0,
            "max": 100,
            "unit": "percent"
          }
        ]
      },
      {
        "id": 6,
        "title": "Celery Task Queue",
        "type": "graph",
        "targets": [
          {
            "expr": "celery_tasks_total",
            "legendFormat": "{{state}} tasks"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### 3.3 ELK 日志聚合系统

```yaml
# k8s/logging/elasticsearch.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: logging
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        env:
        - name: cluster.name
          value: flyesp-logs
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch"
        - name: cluster.initial_master_nodes
          value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
        - name: ES_JAVA_OPTS
          value: "-Xmx512m -Xms512m"
        - name: xpack.security.enabled
          value: "false"
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
        resources:
          limits:
            memory: 1Gi
            cpu: 500m
          requests:
            memory: 1Gi
            cpu: 500m
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
---
# k8s/logging/logstash.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-config
  namespace: logging
data:
  logstash.yml: |
    http.host: "0.0.0.0"
    path.config: /usr/share/logstash/pipeline
  pipelines.yml: |
    - pipeline.id: flyesp
      path.config: "/usr/share/logstash/pipeline/flyesp.conf"
  flyesp.conf: |
    input {
      beats {
        port => 5044
      }
    }
    
    filter {
      if [fields][service] == "flyesp-backend" {
        grok {
          match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:logger} %{GREEDYDATA:message}" }
        }
        
        date {
          match => [ "timestamp", "ISO8601" ]
        }
        
        if [level] == "ERROR" {
          mutate {
            add_tag => [ "error" ]
          }
        }
      }
      
      if [fields][service] == "flyesp-frontend" {
        if [source] =~ /access/ {
          grok {
            match => { "message" => "%{COMBINEDAPACHELOG}" }
          }
        }
      }
    }
    
    output {
      elasticsearch {
        hosts => ["elasticsearch:9200"]
        index => "flyesp-logs-%{+YYYY.MM.dd}"
      }
    }
```

### 3.4 Filebeat 日志收集

```yaml
# k8s/logging/filebeat.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: logging
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*flyesp*.log
      processors:
        - add_kubernetes_metadata:
            host: ${NODE_NAME}
            matchers:
            - logs_path:
                logs_path: "/var/log/containers/"
    
    output.logstash:
      hosts: ["logstash:5044"]
    
    logging.level: info
    logging.to_files: true
    logging.files:
      path: /var/log/filebeat
      name: filebeat
      keepfiles: 7
      permissions: 0644
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: logging
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
    spec:
      serviceAccountName: filebeat
      terminationGracePeriodSeconds: 30
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:8.5.0
        args: [
          "-c", "/etc/filebeat.yml",
          "-e",
        ]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        securityContext:
          runAsUser: 0
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 100Mi
        volumeMounts:
        - name: config
          mountPath: /etc/filebeat.yml
          readOnly: true
          subPath: filebeat.yml
        - name: data
          mountPath: /usr/share/filebeat/data
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          defaultMode: 0640
          name: filebeat-config
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
      - name: data
        hostPath:
          path: /var/lib/filebeat-data
          type: DirectoryOrCreate
```

## 4. 备份与灾难恢复

### 4.1 数据库备份策略

```bash
#!/bin/bash
# scripts/backup-database.sh

set -euo pipefail

# 配置
BACKUP_DIR="/backups"
RETENTION_DAYS=30
POSTGRES_HOST="postgres-service"
POSTGRES_DB="flyesp_prod"
POSTGRES_USER="flyesp"
AWS_S3_BUCKET="flyesp-backups"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 生成备份文件名
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/flyesp_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# 执行数据库备份
perform_backup() {
    log_info "Starting database backup..."
    
    # 使用 pg_dump 创建备份
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --verbose \
        > "${BACKUP_FILE}"
    
    if [[ $? -eq 0 ]]; then
        log_info "Database backup completed: ${BACKUP_FILE}"
        
        # 压缩备份文件
        gzip "${BACKUP_FILE}"
        log_info "Backup compressed: ${COMPRESSED_FILE}"
        
        # 上传到 S3
        upload_to_s3 "${COMPRESSED_FILE}"
        
        # 验证备份
        verify_backup "${COMPRESSED_FILE}"
        
    else
        log_error "Database backup failed"
        exit 1
    fi
}

# 上传到 S3
upload_to_s3() {
    local file_path="$1"
    local s3_key="database-backups/$(basename "${file_path}")"
    
    log_info "Uploading backup to S3..."
    
    aws s3 cp "${file_path}" "s3://${AWS_S3_BUCKET}/${s3_key}" \
        --storage-class STANDARD_IA \
        --metadata timestamp="${TIMESTAMP}"
    
    if [[ $? -eq 0 ]]; then
        log_info "Backup uploaded to S3: s3://${AWS_S3_BUCKET}/${s3_key}"
    else
        log_error "Failed to upload backup to S3"
    fi
}

# 验证备份完整性
verify_backup() {
    local backup_file="$1"
    
    log_info "Verifying backup integrity..."
    
    # 检查文件大小
    local file_size=$(stat -c%s "${backup_file}")
    if [[ "${file_size}" -lt 1024 ]]; then
        log_error "Backup file is too small (${file_size} bytes), might be corrupted"
        return 1
    fi
    
    # 检查 gzip 文件完整性
    if ! gzip -t "${backup_file}"; then
        log_error "Backup file is corrupted"
        return 1
    fi
    
    log_info "Backup verification passed"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "Cleaning up old local backups..."
    
    find "${BACKUP_DIR}" -name "flyesp_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    
    log_info "Cleaning up old S3 backups..."
    
    # 使用 AWS CLI 删除旧的 S3 备份
    aws s3api list-objects-v2 \
        --bucket "${AWS_S3_BUCKET}" \
        --prefix "database-backups/" \
        --query "Contents[?LastModified<=\`$(date -d "${RETENTION_DAYS} days ago" --iso-8601)\`].Key" \
        --output text | xargs -r -I {} aws s3 rm "s3://${AWS_S3_BUCKET}/{}"
}

# 主函数
main() {
    log_info "Starting backup process for database: ${POSTGRES_DB}"
    
    perform_backup
    cleanup_old_backups
    
    log_info "Backup process completed successfully"
}

main "$@"
```

### 4.2 Kubernetes 资源备份

```bash
#!/bin/bash
# scripts/backup-k8s.sh

set -euo pipefail

BACKUP_DIR="/backups/k8s"
NAMESPACE="flyesp-prod"
AWS_S3_BUCKET="flyesp-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "${BACKUP_DIR}"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

# 备份 Kubernetes 资源
backup_k8s_resources() {
    log_info "Backing up Kubernetes resources..."
    
    local backup_file="${BACKUP_DIR}/k8s-resources_${TIMESTAMP}.yaml"
    
    # 备份关键资源类型
    resource_types=(
        "configmaps"
        "secrets"
        "services"
        "deployments"
        "statefulsets"
        "ingresses"
        "persistentvolumeclaims"
        "horizontalpodautoscalers"
    )
    
    for resource_type in "${resource_types[@]}"; do
        log_info "Backing up ${resource_type}..."
        
        kubectl get "${resource_type}" -n "${NAMESPACE}" -o yaml >> "${backup_file}"
        echo "---" >> "${backup_file}"
    done
    
    # 压缩备份文件
    gzip "${backup_file}"
    
    # 上传到 S3
    aws s3 cp "${backup_file}.gz" \
        "s3://${AWS_S3_BUCKET}/k8s-backups/k8s-resources_${TIMESTAMP}.yaml.gz"
    
    log_info "Kubernetes resources backup completed"
}

# 备份持久卷数据（使用 Velero）
backup_persistent_volumes() {
    log_info "Creating Velero backup for persistent volumes..."
    
    # 安装 Velero（如果未安装）
    if ! command -v velero &> /dev/null; then
        log_info "Installing Velero CLI..."
        curl -fsSL -o velero-v1.10.0-linux-amd64.tar.gz \
            https://github.com/vmware-tanzu/velero/releases/download/v1.10.0/velero-v1.10.0-linux-amd64.tar.gz
        tar -xzf velero-v1.10.0-linux-amd64.tar.gz
        sudo mv velero-v1.10.0-linux-amd64/velero /usr/local/bin/
        rm -rf velero-v1.10.0-linux-amd64*
    fi
    
    # 创建备份
    velero backup create "flyesp-backup-${TIMESTAMP}" \
        --include-namespaces "${NAMESPACE}" \
        --wait
    
    log_info "Velero backup completed"
}

main() {
    log_info "Starting Kubernetes backup process..."
    
    backup_k8s_resources
    backup_persistent_volumes
    
    log_info "Kubernetes backup process completed"
}

main "$@"
```

### 4.3 灾难恢复计划

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

set -euo pipefail

BACKUP_RESTORE_DIR="/tmp/restore"
NAMESPACE="flyesp-prod"
AWS_S3_BUCKET="flyesp-backups"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# 恢复数据库
restore_database() {
    local backup_date="$1"
    
    log_info "Restoring database from backup: ${backup_date}"
    
    # 下载备份文件
    local backup_file="${BACKUP_RESTORE_DIR}/flyesp_${backup_date}.sql.gz"
    aws s3 cp "s3://${AWS_S3_BUCKET}/database-backups/flyesp_${backup_date}.sql.gz" "${backup_file}"
    
    # 解压缩
    gunzip "${backup_file}"
    local sql_file="${backup_file%.gz}"
    
    # 停止应用服务以避免数据不一致
    log_info "Scaling down application services..."
    kubectl scale deployment backend --replicas=0 -n "${NAMESPACE}"
    kubectl scale deployment celery-worker --replicas=0 -n "${NAMESPACE}"
    
    # 等待服务停止
    kubectl wait --for=delete pod -l app=backend -n "${NAMESPACE}" --timeout=300s
    kubectl wait --for=delete pod -l app=celery-worker -n "${NAMESPACE}" --timeout=300s
    
    # 恢复数据库
    log_info "Restoring database..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        -f "${sql_file}"
    
    if [[ $? -eq 0 ]]; then
        log_info "Database restore completed successfully"
        
        # 重启应用服务
        log_info "Restarting application services..."
        kubectl scale deployment backend --replicas=3 -n "${NAMESPACE}"
        kubectl scale deployment celery-worker --replicas=2 -n "${NAMESPACE}"
        
        # 等待服务就绪
        kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=300s
        kubectl rollout status deployment/celery-worker -n "${NAMESPACE}" --timeout=300s
        
        # 清理临时文件
        rm -f "${sql_file}"
        
    else
        log_error "Database restore failed"
        exit 1
    fi
}

# 恢复 Kubernetes 资源
restore_k8s_resources() {
    local backup_date="$1"
    
    log_info "Restoring Kubernetes resources from backup: ${backup_date}"
    
    # 下载备份文件
    local backup_file="${BACKUP_RESTORE_DIR}/k8s-resources_${backup_date}.yaml.gz"
    aws s3 cp "s3://${AWS_S3_BUCKET}/k8s-backups/k8s-resources_${backup_date}.yaml.gz" "${backup_file}"
    
    # 解压缩并应用
    gunzip -c "${backup_file}" | kubectl apply -f -
    
    log_info "Kubernetes resources restored"
}

# 恢复持久卷（使用 Velero）
restore_persistent_volumes() {
    local backup_name="$1"
    
    log_info "Restoring persistent volumes using Velero: ${backup_name}"
    
    # 创建恢复任务
    velero restore create "restore-${backup_name}" \
        --from-backup "${backup_name}" \
        --wait
    
    # 检查恢复状态
    local restore_status=$(velero restore get "restore-${backup_name}" -o jsonpath='{.status.phase}')
    
    if [[ "${restore_status}" == "Completed" ]]; then
        log_info "Persistent volumes restored successfully"
    else
        log_error "Persistent volume restore failed with status: ${restore_status}"
        exit 1
    fi
}

# 验证恢复
verify_restore() {
    log_info "Verifying disaster recovery..."
    
    # 等待所有 pod 就绪
    kubectl wait --for=condition=ready pod -l app=backend -n "${NAMESPACE}" --timeout=600s
    kubectl wait --for=condition=ready pod -l app=postgres -n "${NAMESPACE}" --timeout=600s
    kubectl wait --for=condition=ready pod -l app=redis -n "${NAMESPACE}" --timeout=600s
    
    # 健康检查
    local backend_service=$(kubectl get service backend-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
    
    kubectl run restore-health-check-$(date +%s) \
        --namespace="${NAMESPACE}" \
        --image=curlimages/curl:latest \
        --rm -i --restart=Never \
        --command -- curl -f "http://${backend_service}:8000/health"
    
    if [[ $? -eq 0 ]]; then
        log_info "Disaster recovery verification passed"
    else
        log_error "Disaster recovery verification failed"
        exit 1
    fi
}

# 完整恢复流程
full_recovery() {
    local db_backup_date="$1"
    local k8s_backup_date="$2"
    local velero_backup_name="$3"
    
    log_info "Starting full disaster recovery process..."
    log_info "Database backup: ${db_backup_date}"
    log_info "K8s backup: ${k8s_backup_date}"
    log_info "Velero backup: ${velero_backup_name}"
    
    mkdir -p "${BACKUP_RESTORE_DIR}"
    
    # 恢复基础设施
    restore_k8s_resources "${k8s_backup_date}"
    restore_persistent_volumes "${velero_backup_name}"
    
    # 等待基础设施就绪
    sleep 60
    
    # 恢复数据
    restore_database "${db_backup_date}"
    
    # 验证恢复
    verify_restore
    
    # 清理
    rm -rf "${BACKUP_RESTORE_DIR}"
    
    log_info "Disaster recovery completed successfully!"
}

# RTO/RPO 监控
calculate_rto_rpo() {
    local incident_start="$1"
    local recovery_complete="$2"
    local last_backup="$3"
    
    # 计算 RTO（恢复时间目标）
    local rto_seconds=$(($(date -d "${recovery_complete}" +%s) - $(date -d "${incident_start}" +%s)))
    local rto_minutes=$((rto_seconds / 60))
    
    # 计算 RPO（恢复点目标）
    local rpo_seconds=$(($(date -d "${incident_start}" +%s) - $(date -d "${last_backup}" +%s)))
    local rpo_minutes=$((rpo_seconds / 60))
    
    echo "========================================"
    echo "Disaster Recovery Metrics:"
    echo "RTO (Recovery Time Objective): ${rto_minutes} minutes"
    echo "RPO (Recovery Point Objective): ${rpo_minutes} minutes"
    echo "========================================"
}

# 使用说明
usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  restore-db <backup_date>              - Restore database only"
    echo "  restore-k8s <backup_date>             - Restore K8s resources only"
    echo "  restore-volumes <backup_name>         - Restore persistent volumes only"
    echo "  full-recovery <db_date> <k8s_date> <velero_name> - Full disaster recovery"
    echo "  verify                                - Verify current system health"
    echo ""
    echo "Examples:"
    echo "  $0 restore-db 20240101_120000"
    echo "  $0 full-recovery 20240101_120000 20240101_120000 flyesp-backup-20240101_120000"
}

# 主函数
main() {
    case "${1:-}" in
        "restore-db")
            restore_database "$2"
            ;;
        "restore-k8s")
            restore_k8s_resources "$2"
            ;;
        "restore-volumes")
            restore_persistent_volumes "$2"
            ;;
        "full-recovery")
            full_recovery "$2" "$3" "$4"
            ;;
        "verify")
            verify_restore
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
```

## 5. 运维自动化脚本

### 5.1 系统健康检查脚本

```bash
#!/bin/bash
# scripts/health-check.sh

set -euo pipefail

NAMESPACE="flyesp-prod"
ALERT_WEBHOOK="${ALERT_WEBHOOK_URL:-}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 健康检查结果
HEALTH_CHECKS=()
FAILED_CHECKS=()

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

add_health_check() {
    local check_name="$1"
    local status="$2"
    local details="$3"
    
    HEALTH_CHECKS+=("${check_name}:${status}:${details}")
    
    if [[ "${status}" != "PASS" ]]; then
        FAILED_CHECKS+=("${check_name}: ${details}")
    fi
}

# 检查 Kubernetes 集群健康
check_k8s_cluster() {
    log_info "Checking Kubernetes cluster health..."
    
    # 检查节点状态
    local node_count=$(kubectl get nodes --no-headers | grep -c "Ready")
    local total_nodes=$(kubectl get nodes --no-headers | wc -l)
    
    if [[ "${node_count}" -eq "${total_nodes}" ]]; then
        add_health_check "K8s_Nodes" "PASS" "All ${total_nodes} nodes are Ready"
    else
        add_health_check "K8s_Nodes" "FAIL" "Only ${node_count}/${total_nodes} nodes are Ready"
    fi
    
    # 检查关键组件
    local components=("kube-apiserver" "kube-controller-manager" "kube-scheduler" "etcd")
    for component in "${components[@]}"; do
        if kubectl get componentstatus "${component}" &>/dev/null; then
            add_health_check "K8s_${component}" "PASS" "Component is healthy"
        else
            add_health_check "K8s_${component}" "FAIL" "Component is unhealthy"
        fi
    done
}

# 检查应用服务健康
check_application_health() {
    log_info "Checking application services health..."
    
    # 检查 Deployment 状态
    local deployments=("backend" "celery-worker")
    for deployment in "${deployments[@]}"; do
        local ready_replicas=$(kubectl get deployment "${deployment}" -n "${NAMESPACE}" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        local desired_replicas=$(kubectl get deployment "${deployment}" -n "${NAMESPACE}" -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
        
        if [[ "${ready_replicas}" -eq "${desired_replicas}" && "${ready_replicas}" -gt 0 ]]; then
            add_health_check "App_${deployment}" "PASS" "${ready_replicas}/${desired_replicas} replicas ready"
        else
            add_health_check "App_${deployment}" "FAIL" "Only ${ready_replicas}/${desired_replicas} replicas ready"
        fi
    done
    
    # 检查 StatefulSet 状态
    local statefulsets=("postgres")
    for statefulset in "${statefulsets[@]}"; do
        local ready_replicas=$(kubectl get statefulset "${statefulset}" -n "${NAMESPACE}" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        local desired_replicas=$(kubectl get statefulset "${statefulset}" -n "${NAMESPACE}" -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
        
        if [[ "${ready_replicas}" -eq "${desired_replicas}" && "${ready_replicas}" -gt 0 ]]; then
            add_health_check "DB_${statefulset}" "PASS" "${ready_replicas}/${desired_replicas} replicas ready"
        else
            add_health_check "DB_${statefulset}" "FAIL" "Only ${ready_replicas}/${desired_replicas} replicas ready"
        fi
    done
}

# 检查服务端点健康
check_service_endpoints() {
    log_info "Checking service endpoints..."
    
    # 检查内部服务健康端点
    local services=("backend-service:8000/health" "postgres-service:5432" "redis-service:6379")
    
    for service_endpoint in "${services[@]}"; do
        local service_name=$(echo "${service_endpoint}" | cut -d':' -f1)
        local endpoint=$(echo "${service_endpoint}" | cut -d':' -f2-)
        
        # 创建临时 pod 进行健康检查
        local check_result
        if [[ "${endpoint}" =~ ^[0-9]+$ ]]; then
            # 端口连接检查
            check_result=$(kubectl run health-check-$(date +%s) \
                --namespace="${NAMESPACE}" \
                --image=busybox:latest \
                --rm -i --restart=Never \
                --command -- timeout 10 sh -c "echo > /dev/tcp/${service_name}/${endpoint}" 2>&1 || echo "FAILED")
        else
            # HTTP 健康检查
            check_result=$(kubectl run health-check-$(date +%s) \
                --namespace="${NAMESPACE}" \
                --image=curlimages/curl:latest \
                --rm -i --restart=Never \
                --command -- timeout 10 curl -f "http://${service_name}:${endpoint}" 2>&1 || echo "FAILED")
        fi
        
        if [[ "${check_result}" != *"FAILED"* ]]; then
            add_health_check "Endpoint_${service_name}" "PASS" "Endpoint is responding"
        else
            add_health_check "Endpoint_${service_name}" "FAIL" "Endpoint is not responding"
        fi
    done
}

# 检查资源使用情况
check_resource_usage() {
    log_info "Checking resource usage..."
    
    # 检查节点资源使用
    local node_metrics=$(kubectl top nodes --no-headers 2>/dev/null || echo "")
    if [[ -n "${node_metrics}" ]]; then
        while IFS= read -r line; do
            local node_name=$(echo "${line}" | awk '{print $1}')
            local cpu_usage=$(echo "${line}" | awk '{print $2}' | sed 's/[^0-9]//g')
            local memory_usage=$(echo "${line}" | awk '{print $4}' | sed 's/[^0-9]//g')
            
            if [[ "${cpu_usage}" -lt 80 && "${memory_usage}" -lt 80 ]]; then
                add_health_check "Resource_${node_name}" "PASS" "CPU: ${cpu_usage}%, Memory: ${memory_usage}%"
            else
                add_health_check "Resource_${node_name}" "WARN" "High usage - CPU: ${cpu_usage}%, Memory: ${memory_usage}%"
            fi
        done <<< "${node_metrics}"
    fi
    
    # 检查 PVC 存储使用
    local pvcs=$(kubectl get pvc -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")
    if [[ -n "${pvcs}" ]]; then
        while IFS= read -r line; do
            local pvc_name=$(echo "${line}" | awk '{print $1}')
            local status=$(echo "${line}" | awk '{print $2}')
            
            if [[ "${status}" == "Bound" ]]; then
                add_health_check "Storage_${pvc_name}" "PASS" "PVC is bound"
            else
                add_health_check "Storage_${pvc_name}" "FAIL" "PVC status: ${status}"
            fi
        done <<< "${pvcs}"
    fi
}

# 检查证书过期时间
check_certificates() {
    log_info "Checking TLS certificates..."
    
    local ingress_hosts=$(kubectl get ingress -n "${NAMESPACE}" -o jsonpath='{.items[*].spec.rules[*].host}' 2>/dev/null || echo "")
    
    for host in ${ingress_hosts}; do
        local cert_expiry=$(echo | openssl s_client -servername "${host}" -connect "${host}:443" 2>/dev/null | \
                          openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
        
        if [[ -n "${cert_expiry}" ]]; then
            local expiry_timestamp=$(date -d "${cert_expiry}" +%s)
            local current_timestamp=$(date +%s)
            local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [[ "${days_until_expiry}" -gt 30 ]]; then
                add_health_check "Cert_${host}" "PASS" "Certificate expires in ${days_until_expiry} days"
            elif [[ "${days_until_expiry}" -gt 7 ]]; then
                add_health_check "Cert_${host}" "WARN" "Certificate expires in ${days_until_expiry} days"
            else
                add_health_check "Cert_${host}" "FAIL" "Certificate expires in ${days_until_expiry} days"
            fi
        else
            add_health_check "Cert_${host}" "FAIL" "Could not check certificate"
        fi
    done
}

# 生成健康报告
generate_health_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local total_checks=${#HEALTH_CHECKS[@]}
    local failed_count=${#FAILED_CHECKS[@]}
    local success_count=$((total_checks - failed_count))
    
    echo "========================================"
    echo "FlyEsports Platform Health Check Report"
    echo "========================================"
    echo "Timestamp: ${timestamp}"
    echo "Total Checks: ${total_checks}"
    echo "Passed: ${success_count}"
    echo "Failed: ${failed_count}"
    echo ""
    
    if [[ "${failed_count}" -eq 0 ]]; then
        echo -e "${GREEN}✅ All health checks passed!${NC}"
    else
        echo -e "${RED}❌ ${failed_count} health check(s) failed:${NC}"
        for failed_check in "${FAILED_CHECKS[@]}"; do
            echo -e "${RED}  - ${failed_check}${NC}"
        done
    fi
    
    echo ""
    echo "Detailed Results:"
    echo "=================="
    
    for check in "${HEALTH_CHECKS[@]}"; do
        local name=$(echo "${check}" | cut -d':' -f1)
        local status=$(echo "${check}" | cut -d':' -f2)
        local details=$(echo "${check}" | cut -d':' -f3)
        
        case "${status}" in
            "PASS")
                echo -e "${GREEN}✅ ${name}${NC}: ${details}"
                ;;
            "WARN")
                echo -e "${YELLOW}⚠️  ${name}${NC}: ${details}"
                ;;
            "FAIL")
                echo -e "${RED}❌ ${name}${NC}: ${details}"
                ;;
        esac
    done
    
    echo "========================================"
}

# 发送告警通知
send_alert_notification() {
    if [[ -n "${ALERT_WEBHOOK}" && ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        log_info "Sending alert notification..."
        
        local alert_payload=$(cat <<EOF
{
  "text": "🚨 FlyEsports Platform Health Check Alert",
  "attachments": [
    {
      "color": "danger",
      "title": "Health Check Failed",
      "fields": [
        {
          "title": "Failed Checks",
          "value": "${#FAILED_CHECKS[@]}",
          "short": true
        },
        {
          "title": "Total Checks", 
          "value": "${#HEALTH_CHECKS[@]}",
          "short": true
        }
      ],
      "text": "$(printf '%s\n' "${FAILED_CHECKS[@]}")"
    }
  ]
}
EOF
        )
        
        curl -X POST -H 'Content-type: application/json' \
            --data "${alert_payload}" \
            "${ALERT_WEBHOOK}"
    fi
}

# 主函数
main() {
    log_info "Starting comprehensive health check..."
    
    check_k8s_cluster
    check_application_health
    check_service_endpoints
    check_resource_usage
    check_certificates
    
    generate_health_report
    send_alert_notification
    
    # 返回适当的退出码
    if [[ ${#FAILED_CHECKS[@]} -eq 0 ]]; then
        log_info "Health check completed successfully"
        exit 0
    else
        log_error "Health check found ${#FAILED_CHECKS[@]} issue(s)"
        exit 1
    fi
}

main "$@"
```

### 5.2 性能优化脚本

```bash
#!/bin/bash
# scripts/performance-optimization.sh

set -euo pipefail

NAMESPACE="flyesp-prod"
METRICS_DURATION="5m"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

# 分析并优化数据库性能
optimize_database_performance() {
    log_info "Analyzing database performance..."
    
    # 获取慢查询
    local slow_queries=$(kubectl exec -n "${NAMESPACE}" deployment/postgres -- \
        psql -U flyesp -d flyesp_prod -c "
        SELECT query, mean_exec_time, calls, rows
        FROM pg_stat_statements
        WHERE mean_exec_time > 1000
        ORDER BY mean_exec_time DESC
        LIMIT 10;" 2>/dev/null || echo "No slow queries found")
    
    echo "Top slow queries:"
    echo "${slow_queries}"
    
    # 检查数据库连接数
    local connection_count=$(kubectl exec -n "${NAMESPACE}" deployment/postgres -- \
        psql -U flyesp -d flyesp_prod -c "SELECT count(*) FROM pg_stat_activity;" -t 2>/dev/null | tr -d ' ')
    
    log_info "Current database connections: ${connection_count}"
    
    # 推荐连接池优化
    if [[ "${connection_count}" -gt 100 ]]; then
        log_info "Recommendation: Consider increasing connection pool size or optimizing queries"
    fi
    
    # 检查缓存命中率
    local cache_hit_ratio=$(kubectl exec -n "${NAMESPACE}" deployment/postgres -- \
        psql -U flyesp -d flyesp_prod -c "
        SELECT sum(blks_hit) * 100 / (sum(blks_hit) + sum(blks_read)) as cache_hit_ratio
        FROM pg_stat_database;" -t 2>/dev/null | tr -d ' ')
    
    log_info "Database cache hit ratio: ${cache_hit_ratio}%"
    
    if [[ $(echo "${cache_hit_ratio} < 95" | bc -l) -eq 1 ]]; then
        log_info "Recommendation: Consider increasing shared_buffers"
    fi
}

# 优化应用资源分配
optimize_resource_allocation() {
    log_info "Analyzing resource allocation..."
    
    # 获取 pod 资源使用情况
    local pod_metrics=$(kubectl top pods -n "${NAMESPACE}" --no-headers 2>/dev/null || echo "")
    
    if [[ -n "${pod_metrics}" ]]; then
        echo "Current pod resource usage:"
        echo "Pod Name                CPU(cores)  Memory(bytes)"
        echo "=================================================="
        echo "${pod_metrics}"
        
        # 分析并给出建议
        while IFS= read -r line; do
            local pod_name=$(echo "${line}" | awk '{print $1}')
            local cpu_usage=$(echo "${line}" | awk '{print $2}' | sed 's/m//')
            local memory_usage=$(echo "${line}" | awk '{print $3}' | sed 's/Mi//')
            
            # 获取资源限制
            local cpu_limit=$(kubectl get pod "${pod_name}" -n "${NAMESPACE}" \
                -o jsonpath='{.spec.containers[0].resources.limits.cpu}' 2>/dev/null | sed 's/m//')
            local memory_limit=$(kubectl get pod "${pod_name}" -n "${NAMESPACE}" \
                -o jsonpath='{.spec.containers[0].resources.limits.memory}' 2>/dev/null | sed 's/Mi//')
            
            # 计算使用率
            if [[ -n "${cpu_limit}" && "${cpu_limit}" -gt 0 ]]; then
                local cpu_utilization=$((cpu_usage * 100 / cpu_limit))
                if [[ "${cpu_utilization}" -lt 20 ]]; then
                    log_info "Recommendation: ${pod_name} CPU limit can be reduced"
                elif [[ "${cpu_utilization}" -gt 80 ]]; then
                    log_info "Recommendation: ${pod_name} needs more CPU resources"
                fi
            fi
            
            if [[ -n "${memory_limit}" && "${memory_limit}" -gt 0 ]]; then
                local memory_utilization=$((memory_usage * 100 / memory_limit))
                if [[ "${memory_utilization}" -lt 20 ]]; then
                    log_info "Recommendation: ${pod_name} memory limit can be reduced"
                elif [[ "${memory_utilization}" -gt 80 ]]; then
                    log_info "Recommendation: ${pod_name} needs more memory"
                fi
            fi
        done <<< "${pod_metrics}"
    fi
}

# 分析网络性能
analyze_network_performance() {
    log_info "Analyzing network performance..."
    
    # 检查服务间延迟
    local services=("backend-service" "postgres-service" "redis-service")
    
    for service in "${services[@]}"; do
        local latency=$(kubectl run network-test-$(date +%s) \
            --namespace="${NAMESPACE}" \
            --image=busybox:latest \
            --rm -i --restart=Never \
            --command -- sh -c "time echo > /dev/tcp/${service}/$(kubectl get service ${service} -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].port}')" 2>&1 | grep real | awk '{print $2}')
        
        log_info "${service} connection latency: ${latency}"
    done
    
    # 检查 Ingress 性能
    local ingress_hosts=$(kubectl get ingress -n "${NAMESPACE}" -o jsonpath='{.items[*].spec.rules[*].host}' 2>/dev/null)
    
    for host in ${ingress_hosts}; do
        local response_time=$(curl -w "@curl-format.txt" -o /dev/null -s "https://${host}/health" 2>/dev/null || echo "N/A")
        log_info "${host} response time: ${response_time}"
    done
}

# 优化缓存配置
optimize_cache_configuration() {
    log_info "Analyzing cache performance..."
    
    # Redis 缓存命中率分析
    local redis_stats=$(kubectl exec -n "${NAMESPACE}" deployment/redis -- \
        redis-cli info stats 2>/dev/null | grep -E "keyspace_hits|keyspace_misses" || echo "")
    
    if [[ -n "${redis_stats}" ]]; then
        local hits=$(echo "${redis_stats}" | grep keyspace_hits | cut -d: -f2 | tr -d '\r')
        local misses=$(echo "${redis_stats}" | grep keyspace_misses | cut -d: -f2 | tr -d '\r')
        
        if [[ "${hits}" -gt 0 ]] && [[ "${misses}" -gt 0 ]]; then
            local hit_ratio=$((hits * 100 / (hits + misses)))
            log_info "Redis cache hit ratio: ${hit_ratio}%"
            
            if [[ "${hit_ratio}" -lt 80 ]]; then
                log_info "Recommendation: Cache hit ratio is low, consider reviewing cache strategy"
            fi
        fi
    fi
    
    # 检查缓存内存使用
    local redis_memory=$(kubectl exec -n "${NAMESPACE}" deployment/redis -- \
        redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "N/A")
    
    log_info "Redis memory usage: ${redis_memory}"
}

# 生成优化建议报告
generate_optimization_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > /tmp/performance-report.txt <<EOF
======================================
FlyEsports Platform Performance Report
======================================
Generated: ${timestamp}

This report contains performance analysis and optimization recommendations
for the FlyEsports platform based on current metrics and resource usage.

Database Performance:
- Slow query analysis completed
- Connection pool utilization checked
- Cache hit ratio analyzed

Resource Allocation:
- Pod resource usage analyzed
- Optimization recommendations provided

Network Performance:
- Service latency measured
- Ingress response times checked

Cache Performance:
- Redis hit ratio analyzed
- Memory usage reviewed

For detailed recommendations, see the log output above.

Next Steps:
1. Review slow database queries and optimize them
2. Adjust resource limits based on actual usage
3. Implement recommended cache optimizations
4. Monitor the impact of changes

EOF

    log_info "Performance report generated: /tmp/performance-report.txt"
}

# 主函数
main() {
    log_info "Starting performance optimization analysis..."
    
    # 创建 curl 格式化文件
    cat > curl-format.txt <<'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
    
    optimize_database_performance
    optimize_resource_allocation
    analyze_network_performance
    optimize_cache_configuration
    
    generate_optimization_report
    
    # 清理
    rm -f curl-format.txt
    
    log_info "Performance optimization analysis completed"
}

main "$@"
```

## 6. 总结

本部署与运维指南为 FlyEsports 平台提供了完整的容器化部署方案和运维自动化流程。主要亮点包括：

### 6.1 部署架构特点
- **多环境支持**: 开发、测试、生产环境的统一部署方案
- **高可用性**: 通过 Kubernetes 集群实现服务的自动故障转移
- **弹性扩缩容**: HPA 自动扩缩容和资源配额管理
- **安全加固**: 安全上下文、网络策略和资源隔离

### 6.2 CI/CD 流水线
- **自动化测试**: 代码质量检查、安全扫描和单元测试
- **容器化构建**: Docker 多阶段构建优化镜像大小
- **蓝绿部署**: 零停机部署策略
- **回滚机制**: 快速回滚到前一个稳定版本

### 6.3 监控运维体系
- **全方位监控**: Prometheus + Grafana 实现指标监控和可视化
- **日志聚合**: ELK Stack 集中式日志管理和分析
- **告警系统**: 多渠道告警通知和智能告警规则
- **健康检查**: 自动化健康检查和故障预警

### 6.4 备份恢复方案
- **多层备份**: 数据库、应用配置和持久卷的全面备份
- **异地存储**: AWS S3 云存储确保数据安全
- **快速恢复**: 标准化的灾难恢复流程和 RTO/RPO 监控
- **定期演练**: 备份恢复流程的定期验证

### 6.5 运维自动化
- **性能优化**: 自动化性能分析和优化建议
- **资源管理**: 智能资源分配和成本优化
- **故障排查**: 自动化故障检测和初步处理
- **运维工具**: 丰富的运维脚本和工具集

该部署与运维方案确保 FlyEsports 平台能够稳定、高效地运行在生产环境中，同时具备良好的可扩展性和可维护性，为平台的长期发展提供坚实的基础设施保障。