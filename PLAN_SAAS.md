# 扫码点餐 SaaS 化实施计划

> 项目：scan-order（扫码点餐）
> 目标：多租户 SaaS + 四档计费（trial/¥99/¥299/¥799）+ PostgreSQL + Docker
> 更新日期：2026-04-08

---

## 目标概述

| 维度 | 现状 | 目标 |
|------|------|------|
| 架构 | 单商户 SQLite | 多租户 PostgreSQL |
| 计费 | 无 | 三档：免费/¥199/月/¥299/月 |
| 部署 | 本地开发环境 | Docker 一键部署 |
| 前端 | 固定端口 | SaaS API 适配 |
| 认证 | 简单登录 | JWT + 多租户 |

---

## 三档套餐设计

| 功能 | 免费版 | 基础版（¥99） | 标准版（¥299） | 旗舰版（¥799） |
|------|--------|-------------|---------------|---------------|
| 菜单上限 | 30道 | 100道 | 无限 | 无限 |
| 桌台上限 | 10桌 | 30桌 | 无限 | 无限 |
| 订单/月 | 200单 | 1000单 | 无限 | 无限 |
| 后厨屏 KDS | ❌ | ✅ | ✅ | ✅ |
| 数据导出 | ❌ | ✅ | ✅ | ✅ |
| 自定义 logo | ❌ | ❌ | ✅ | ✅ |
| 多员工账号 | ❌ | 3人 | 10人 | 无限 |
| 自定义域名 | ❌ | ❌ | ❌ | ✅ |
| 开放 API | ❌ | ❌ | ❌ | ✅ |
| 高级报表 | ❌ | ❌ | ❌ | ✅ |
| 多商户管理 | ❌ | ❌ | ❌ | ✅ |

---

## Phase 1：PostgreSQL + 多租户数据库设计

### 目标
PostgreSQL 上线，所有表加 tenant_id，多租户隔离。

### 步骤

**1.1 环境准备**
- 安装 PostgreSQL 16（或用 Docker 启动）
- 创建数据库 `scan_order_saas`
- 创建数据库用户 `saas_user` / 密码

**1.2 重新设计表结构（带 tenant_id）**
```
tenants                # 租户主表
  - id (UUID PK)
  - name               # 商户名称
  - tier               # trial | basic | standard | enterprise
  - api_key            # 唯一 API Key
  - subdomain          # 子域名（如 dl小龙虾）
  - created_at
  - expired_at         # 到期时间
  - is_active          # 启用/禁用

merchants              # 商户附属信息（从原 merchant 表迁移）
  - id (UUID PK)
  - tenant_id (FK)     # 关联租户
  - shop_name
  - contact_phone
  - address
  - ...原有字段...

kitchen_users          # 后厨登录（PIN 码认证）
  - id (UUID PK)
  - tenant_id (FK)     # ← 必须，属于哪个租户，禁止跨租户访问
  - pin_hash           # bcrypt(PIN)，4-6位数字
  - display_name       # 如"厨房小王"
  - is_active          # 禁用可临时封禁

categories / dishes / tables / orders / order_items  # 所有业务表加 tenant_id
```

**1.2.1 厨房 PIN 安全规则**
- PIN 仅存储 bcrypt 哈希，不存储明文
- 每个 tenant 的 kitchen_users 表完全隔离，跨 tenant 访问在 SQL 层阻断
- 顾客扫码点餐时后端验证：`SELECT * FROM kitchen_users WHERE tenant_id=? AND pin_hash=?`

**1.3 创建 SQLAlchemy 模型**
- 修改 `backend/app/models/` 下所有模型
- 每个模型加 `tenant_id = Column(UUID, ForeignKey('tenants.id'), nullable=False, index=True)`
- Base 类加 `__tenant_id__` 支撑多租户筛选

**1.4 编写迁移脚本**
- `backend/scripts/migrate_sqlite_to_postgres.py`
  - 读取旧 SQLite 数据（scan_order.db）
  - 在 tenants 表创建 1 条默认租户记录
  - 将所有数据迁移到新表，加 tenant_id

**1.5 PostgreSQL RLS 策略（租户隔离）**
```sql
-- 每个租户表启用 RLS
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- 租户隔离策略（平台管理员 bypass）
CREATE POLICY tenant_isolation ON orders
  USING (
    tenant_id = current_setting('app.tenant_id', true)
    OR current_setting('app.user_type', true) = 'platform_admin'
  );

-- 代码层：平台管理员登录后执行
SET LOCAL app.tenant_id = 'platform';
SET LOCAL app.user_type = 'platform_admin';
-- 普通租户：
SET LOCAL app.tenant_id = '{tenant_uuid}';
SET LOCAL app.user_type = 'merchant';
```

**注意**：platform 模式使用字符串 'platform' 而非 NULL（SQL 中 `NULL = anything` 永远为 FALSE）。

---

**1.6 迁移回滚方案**
```bash
# 迁移前完整备份
cp /opt/scan-order/db/scan_order.db /opt/scan-order/backups/pre_migration_$(date +%Y%m%d).db

# 迁移脚本支持 --dry-run（只验证不写入）
python migrate_sqlite_to_postgres.py --dry-run

# 迁移脚本支持 --rollback（从 PostgreSQL 回写 SQLite）
python migrate_sqlite_to_postgres.py --rollback

# 迁移后验证：对比原表行数
python migrate_sqlite_to_postgres.py --verify
```

---

**1.7 修改数据库配置**
- `backend/app/config.py` 支持 `.env` 切换 PostgreSQL / SQLite
- 修改 `backend/app/database.py` 连接 PostgreSQL

### 验收标准
- [ ] PostgreSQL 连接成功（本地测试）
- [ ] 所有业务表有 `tenant_id` 字段且建了索引
- [ ] 迁移脚本执行后数据完整不丢失
- [ ] 同时运行旧 SQLite 和新 PostgreSQL 数据一致

---

## Phase 2：JWT 认证 + 多租户中间件

### 目标
完整的注册/登录/JWT + 租户隔离中间件。

### 步骤

**2.1 JWT 工具模块**
- 新建 `backend/app/core/security.py`
- JWT 签发：`create_access_token(tenant_id, user_id, expires_delta)`
- JWT 验证：`verify_token(token) → {tenant_id, user_id}`
- Token 有效期：7 天

**2.2 注册/登录 API**
- `POST /api/v1/auth/register` — 注册新租户（email + password + 商户名）
- `POST /api/v1/auth/login` — 登录返回 JWT
- `POST /api/v1/auth/refresh` — 刷新 Token

**2.3 多租户中间件**
- 新建 `backend/app/middleware/tenant_context.py`
- 从 JWT 提取 `tenant_id` 注入 `request.state.tenant_id`
- 所有业务 API 强制依赖 `tenant_id`

**2.4 修改现有 API**
- 在 `backend/app/dependencies.py` 新增 `get_current_tenant()` 依赖
- 所有 `app/api/v1/endpoints/` 路由加 `@router.get(..., dependencies=[Depends(get_current_tenant)])`

**2.5 密码安全**
- 密码 bcrypt 哈希（已有）
- 登录失败次数限制（防止暴力破解）

### 验收标准
- [ ] 注册 → 登录 → 获取 JWT 全流程通
- [ ] 无 Token 请求业务接口返回 401
- [ ] Token 过期返回 401 + refresh 提示
- [ ] 不同 tenant_id 数据完全隔离（联表查询验证）

---

## Phase 3：计费套餐（Tier）实现

### 目标
三档套餐功能限制 + 用量统计 + 升级接口。

### 步骤

**3.1 定义套餐规则**
- 新建 `backend/app/billing/tiers.py`
```python
TIERS = {
    "trial": {
        "menu_limit": 30,
        "table_limit": 10,
        "order_limit_monthly": 200,
        "features": ["menu", "tables", "orders"],
    },
    "basic": {
        "menu_limit": 100,
        "table_limit": 30,
        "order_limit_monthly": 1000,
        "features": ["menu", "tables", "orders", "kitchen", "export"],
    },
    "standard": {
        "menu_limit": None,  # 无限制
        "table_limit": None,
        "order_limit_monthly": None,
        "features": ["menu", "tables", "orders", "kitchen", "export", "custom_logo", "multi_staff"],
    },
    "enterprise": {
        "menu_limit": None,
        "table_limit": None,
        "order_limit_monthly": None,
        "features": ["menu", "tables", "orders", "kitchen", "export", "custom_logo", "multi_staff",
                     "custom_domain", "open_api", "advanced_analytics", "multi_merchant"],
    },
}
```

**3.2 用量统计 API**
- `GET /api/v1/tenant/usage` — 返回当前用量
  - `menu_count`, `table_count`, `order_this_month`
  - `tier`, `expired_at`
  - `limits`（套餐上限）

**3.3 限制检查装饰器**
- 新建 `@require_tier_feature("kitchen")` 装饰器
- 在超过限制时返回 HTTP 403 + 友好的升级提示 JSON

**3.4 升级接口（占位）**
- `POST /api/v1/tenant/upgrade` — 申请升级（返回支付链接或提示）
- 初期可先用微信/支付宝转账人工开通

**3.5 到期处理**
- 中间件检查 `tenant.expired_at`
- 到期前 7 天返回警告 header
- 到期后返回 403 + 续费提示

### 验收标准
- [ ] 免费版新建第 31 道菜返回 403 + `{"error": "upgrade_required", "limit": 30}`
- [ ] 免费版建第 11 桌返回 403
- [ ] `/tenant/usage` 返回完整用量数据
- [ ] 不同 tier 返回不同 `features` 列表

---

## Phase 4：Docker 化部署

### 目标
后端 + 前端 Docker Image + docker-compose 一键启动 + Nginx 反向代理。

### 步骤

**4.1 后端 Docker**
- 新建 `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**4.2 前端 Docker（Admin + Customer）**
- 新建 `frontend-admin/Dockerfile` 和 `frontend-customer/Dockerfile`
- 构建时注入 `VITE_API_BASE` 环境变量
- 使用 nginx:alpine 提供静态文件服务

**4.3 docker-compose.yml**
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: scan_order_saas
      POSTGRES_USER: saas_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://saas_user:${DB_PASSWORD}@db:5432/scan_order_saas
      - JWT_SECRET=${JWT_SECRET}
    ports:
      - "8000:8000"

  nginx:
    image: nginx:alpine
    depends_on:
      - backend
      - admin
      - customer
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"

  admin:
    build: ./frontend-admin
    ports:
      - "5174:80"

  customer:
    build: ./frontend-customer
    ports:
      - "5175:80"
```

**4.4 Nginx 配置**
- `/api` → `backend:8000`
- `/admin` → `admin:80`（管理后台）
- `/` → `customer:80`（顾客端 H5）

**4.5 部署脚本**
- `deploy/deploy.sh` — 一键构建 + 启动
- `deploy/.env.example` — 环境变量模板

### 验收标准
- [ ] `docker-compose up -d` 5 个服务全部 RUNNING
- [ ] 访问 `http://39.104.107.136/` 显示顾客端
- [ ] 访问 `http://39.104.107.136/admin` 显示管理端
- [ ] `docker-compose logs backend` 无报错

---

## Phase 5：前端 SaaS 适配

### 目标
前端全面适配多租户 API（JWT + tenant 隔离）。

### 步骤

**5.1 API 客户端改造**
- 新建 `frontend-admin/src/api/client.ts`
  - 自动从 localStorage 读取 JWT
  - 请求拦截器：加 `Authorization: Bearer <token>`
  - 响应拦截器：401 → 跳转登录页，403 → 弹升级窗口

**5.2 登录/注册页**
- `frontend-admin/src/views/LoginView.vue` — 登录页
- `frontend-admin/src/views/RegisterView.vue` — 注册页
- 注册时自动创建 tenant，返回 JWT

**5.3 Token 管理**
- JWT 存 `localStorage.token`
- 刷新 token 逻辑（Silent Refresh）
- 登出清除 token + 跳转登录页

**5.4 升级弹窗组件**
- `frontend-admin/src/components/UpgradeModal.vue`
- 拦截 403/429 响应，显示套餐对比 + 升级按钮

**5.5 用量显示**
- 管理后台侧边栏底部显示当前用量（menu_count / menu_limit）
- 快捷升级入口

**5.6 顾客端改造**
- `frontend-customer/src/api/client.ts` — 同样 JWT 逻辑
- 扫码 URL 从 `/customer/h5?table=xxx` 变为 `/customer/h5?tenant=xxx&table=xxx`

### 验收标准
- [ ] 未登录访问 `/admin` 自动跳转 `/login`
- [ ] 注册 → 登录 → 进入后台 全流程通
- [ ] 顾客端扫码点餐全流程通
- [ ] 超限 403 显示升级弹窗

---

## Phase 6：计费页面 + 支付对接（初期人工）

### 目标
套餐展示页 + 初期人工升级流程。

### 步骤

**6.1 套餐介绍页**
- `frontend-admin/src/views/PricingView.vue`
- 三档套餐对比表
- 当前套餐标识（高亮）

**6.2 升级流程**
- 点击升级 → 复制商户信息（tenant_id + 商户名）
- 提示联系客服/转账支付宝
- 客服手动后台开通 → 发货通知

**6.3 到期提醒**
- 登录后检查 `expired_at`
- 距到期 ≤ 7 天显示横幅提醒
- 到期后限制登录，强制续费

**6.4 续费逻辑（后台）**
- 管理员手动修改 `tenants.expired_at`
- 支持按月/年续费

### 验收标准
- [ ] 套餐页正确显示三档内容和价格
- [ ] 当前套餐高亮显示
- [ ] 免费版升级按钮可点击
- [ ] 到期前 7 天有醒目提醒

---

## Phase 7：后厨屏 KDS（Phase Kitchen 实施）

### 目标
实施 `PHASE_KITCHEN_DESIGN.md` 中的 KDS 设计。

### 步骤
> 详细内容参考 `PHASE_KITCHEN_DESIGN.md`

**7.1 后厨 API 完善**
- `GET /api/v1/kitchen/orders` — 待处理订单列表
- `POST /api/v1/kitchen/orders/{id}/done` — 完成制作

**7.2 后厨 WebSocket**
- `WS /ws/kitchen?tenant_id=xxx` — 实时推送新订单

**7.3 KDS 前端**
- 新建 `frontend-kitchen/`（独立 Vue3 项目）
- 实时订单看板
- 桌台号 + 菜品 + 数量 + 时间
- 点击完成划掉

### 验收标准
- [ ] basic/standard/enterprise 可访问 KDS
- [ ] trial 访问 KDS 返回 403
- [ ] 新订单实时显示（WebSocket）
- [ ] 点击完成订单消失

---

## Phase 8：生产部署 + 域名 + SSL

### 目标
阿里云生产环境部署 + ndntuaw.cn 域名解析 + SSL。

### 步骤

**8.1 域名解析**
- 在阿里云 DNS 添加 A 记录：`ndntuaw.cn` → `39.104.107.136`
- 添加 `www.ndntuaw.cn` CNAME

**8.2 SSL 证书**
- 使用 Let's Encrypt（certbot）获取免费 SSL
- 或阿里云免费证书

**8.3 Nginx HTTPS 配置**
- 强制 HTTP → HTTPS 重定向
- SSL 证书路径配置

**8.4 Docker 生产启动**
- 在服务器执行 `deploy/deploy.sh`
- 设置开机自启（systemd 或 docker-compose auto-start）

**8.5 备份策略**
- PostgreSQL 数据每日自动备份
- 备份文件保留 7 天

### 验收标准
- [ ] `https://ndntuaw.cn` 可访问（有效 SSL）
- [ ] `https://www.ndntuaw.cn` 正确跳转
- [ ] 数据库每日备份正常
- [ ] 服务器重启后自动恢复服务

---

## 总体实施顺序

```
Phase 1（数据库）→ Phase 2（认证）→ Phase 3（计费）→ Phase 4（Docker）
                                                              ↓
Phase 5（前端适配）→ Phase 6（计费页）←←←←←←←←←←←←←←←←←←←←←←←┘
                                                              ↓
Phase 7（后厨屏 KDS）→ Phase 8（生产部署 + 域名 + SSL）
```

**前置依赖说明：**
- Phase 5 依赖 Phase 2（JWT 完成）
- Phase 6 依赖 Phase 3（套餐限制完成）
- Phase 8 依赖 Phase 4（Docker 完成）

---

## Architect 复审结论（2026-04-08）

| # | 修复项 | 状态 | 备注 |
|---|--------|------|------|
| 1 | 四档定价（trial/basic/standard/enterprise，¥99/¥299/¥799） | ✅ 已到位 | Phase 3 TIERS 定义正确；定价表格用"免费版"而非"trial"，属命名差异（非错误） |
| 2 | kitchen_users 表加 tenant_id FK，PIN 认证隔离 | ✅ 已到位 | SQL 层跨 tenant 访问已阻断 |
| 3 | RLS 策略 platform_admin bypass 用 'platform' 字符串 | ✅ 已到位 | 注释明确 NULL 不适用原因 |
| 4 | 迁移脚本加 --dry-run / --rollback / --verify | ✅ 已到位 | 见 1.6 迁移回滚方案 |

**结论：4 项全部通过。方案可进入实施阶段。**

---

## 附录：技术风险

| # | 风险 | 级别 | 应对 |
|---|------|------|------|
| 1 | PostgreSQL 多租户性能 | 中 | Schema-per-tenant vs shared schema 选型（推荐 shared schema + tenant_id 索引） |
| 2 | JWT 安全 | 高 | HTTPS 传输、短期 Token、refresh 机制 |
| 3 | 免费版滥用 | 中 | API 频率限制（IP + tenant 双维度） |
| 4 | 数据迁移丢失 | 高 | 迁移前完整备份 SQLite，多次验证 |
| 5 | Docker 网络问题 | 中 | 本地测试 docker-compose 网络连通性 |
