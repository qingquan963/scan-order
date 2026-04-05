# 扫码点餐系统 - 后端 API

FastAPI 后端服务，提供商家后台管理 API 和顾客点餐 API。

## 技术栈

- **框架：** FastAPI
- **数据库：** SQLite (`scan_order.db`)
- **认证：** JWT (HS256)
- **ORM：** SQLAlchemy

## 快速启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

服务运行于 `http://127.0.0.1:8002`

## API 文档

启动后可访问：
- Swagger UI: http://127.0.0.1:8002/docs
- ReDoc: http://127.0.0.1:8002/redoc

## 默认管理员账号

```
用户名: admin
密码: admin123
```

## API 端点

### 公开端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/menu` | 顾客菜单 |
| POST | `/api/v1/orders` | 创建订单 |
| GET | `/api/v1/orders/{order_no}` | 查询订单 |

### 管理端点（需认证）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/auth/login` | 管理员登录 |
| GET | `/api/v1/admin/categories` | 分类列表 |
| POST | `/api/v1/admin/categories` | 新增分类 |
| PUT | `/api/v1/admin/categories/{id}` | 更新分类 |
| DELETE | `/api/v1/admin/categories/{id}` | 删除分类 |
| GET | `/api/v1/admin/dishes` | 菜品列表 |
| POST | `/api/v1/admin/dishes` | 新增菜品 |
| PUT | `/api/v1/admin/dishes/{id}` | 更新菜品 |
| DELETE | `/api/v1/admin/dishes/{id}` | 删除菜品 |
| GET | `/api/v1/admin/tables` | 桌位列表 |
| POST | `/api/v1/admin/tables` | 新增桌位 |
| PUT | `/api/v1/admin/tables/{id}` | 更新桌位 |
| DELETE | `/api/v1/admin/tables/{id}` | 删除桌位 |
| GET | `/api/v1/admin/orders` | 订单列表 |
| PUT | `/api/v1/admin/orders/{id}/status` | 更新订单状态 |
| GET | `/api/v1/admin/stats/today` | 今日统计 |
| GET | `/api/v1/admin/stats/overview` | 统计概览 |

## 项目结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/     # 路由处理
│   │       │   ├── auth.py
│   │       │   ├── categories.py
│   │       │   ├── dishes.py
│   │       │   ├── health.py
│   │       │   ├── orders.py
│   │       │   └── tables.py
│   │       ├── admin.py       # 管理端路由汇总
│   │       └── customer.py    # 顾客端路由汇总
│   ├── core/
│   │   └── security.py        # JWT 工具
│   ├── models/                # SQLAlchemy 模型
│   ├── schemas/               # Pydantic schema
│   ├── services/             # 业务逻辑
│   └── utils/                # 工具函数
├── core/
│   ├── config.py
│   └── security.py
├── models/
│   └── models.py
├── schemas/
│   └── schemas.py
├── services/
│   └── services.py
├── run.py                    # 启动入口
├── seed.py                   # 数据初始化
├── requirements.txt
└── scan_order.db             # SQLite 数据库
```

## 验证命令

```bash
# 1. 健康检查
curl http://127.0.0.1:8002/api/v1/health

# 2. 登录获取 Token
TOKEN=$(curl -s -X POST http://127.0.0.1:8002/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. 验证各端点
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/api/v1/admin/categories
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/api/v1/admin/dishes
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/api/v1/admin/tables
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/api/v1/admin/orders
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/api/v1/admin/stats/today
```

## 初始化数据

首次运行后端时会自动初始化数据库，如需重新初始化：

```bash
python seed.py
```
