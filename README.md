# Scan Order - 扫码点餐系统

## 项目结构

```
scan-order/
├── backend/           # Python FastAPI 后端
│   ├── app/          # 应用核心代码
│   ├── models/       # ORM 模型
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # 业务逻辑
│   ├── core/         # 核心配置
│   ├── requirements.txt
│   └── run.py
├── frontend-customer/ # 顾客端 Vue3 前端 (端口 3001)
├── frontend-admin/   # 管理端 Vue3 前端 (端口 3002)
├── ARCHITECTURE.md
└── PLAN.md
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py
# 服务运行在 http://localhost:8001
```

### 顾客端前端

```bash
cd frontend-customer
npm install
npm run dev
# 服务运行在 http://localhost:3001
```

### 管理端前端

```bash
cd frontend-admin
npm install
npm run dev
# 服务运行在 http://localhost:3002
```

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **前端**: Vue3 + Vite + TypeScript
- **数据库**: SQLite
