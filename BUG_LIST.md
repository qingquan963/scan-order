# Bug List - 龙虾小兵点餐系统

## 已知 Bug

### BUG-001: 数据库中文编码错误（中等严重）
- **描述**: 数据库中存储的中文字符全部乱码，API 返回的数据显示为乱码字符（如 `?oo?��?��??`）
- **影响范围**: 所有包含中文字段的 API 响应（分类名、菜品名、菜品描述、桌台名等）
- **复现步骤**: 
  1. 登录 admin 账号
  2. 调用 `GET /api/v1/admin/categories`，返回的 `name` 字段为乱码
- **根本原因**: 数据库初始化时使用了 GBK/GB2312 编码写入中文，但应用层以 UTF-8 读取
- **状态**: 待修复
- **发现时间**: 2026-04-02

### BUG-002: ~~订单状态枚举缺少服务端验证~~（已验证无此问题）
- **描述**: ~~`PUT /api/v1/admin/orders/{id}/status` 接口接受任意字符串作为状态值，没有验证是否为合法状态~~
- **核实结果**: 系统有状态转换规则验证，非法的状态转换（如 pending→invalid_status）会被拒绝，返回错误
- **验证命令**: `PUT /api/v1/admin/orders/4/status` body `{"status":"invalid_status_here"}` → 返回错误 "Cannot transition from pending to invalid_status_here"
- **状态**: 不是 bug

---

## 修复建议

### BUG-001 修复方案
需要重新初始化数据库，确保使用 UTF-8 编码：
1. 删除现有数据库文件
2. 修改初始化脚本，确保 `encoding='utf8mb4'` 
3. 重新运行初始化脚本

### BUG-002 修复方案
在 `/api/v1/admin/orders/{id}/status` 的 PUT handler 中添加状态值验证：
```python
VALID_STATUSES = ["pending", "confirmed", "paid", "cancelled", "refunded"]
if new_status not in VALID_STATUSES:
    raise HTTPException(status_code=400, detail="Invalid status value")
```
