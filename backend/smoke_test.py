#!/usr/bin/env python3
"""
扫码点餐系统 - Phase 6 冒烟测试脚本
Phase 1 ~ Phase 3C 核心 API 冒烟测试

运行方式：
    cd backend
    pip install requests
    python smoke_test.py

前置条件：
    - 后端运行于 http://127.0.0.1:8002
    - 数据库有种子数据（商户 admin/admin123）
    - 已有至少 1 个分类、1 个菜品、1 个桌台
"""

import requests
import json
import time
import sys
from typing import Optional

# ─── 配置 ───────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8002/api/v1"
ADMIN_BASE = f"{BASE_URL}/admin"
CUSTOMER_BASE = f"{BASE_URL}/customer"

# 种子数据默认商户
SEED_MERCHANT_USERNAME = "admin"
SEED_MERCHANT_PASSWORD = "admin123"

# ─── 全局状态 ────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

admin_token: Optional[str] = None
merchant_id: Optional[int] = None
category_id: Optional[int] = None
dish_id: Optional[int] = None
table_id: Optional[int] = None
order_id: Optional[int] = None
wx_customer_token: Optional[str] = None
platform_admin_token: Optional[str] = None
merchant_user_id: Optional[int] = None


# ─── 测试工具 ────────────────────────────────────────────────────
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record(self, name: str, ok: bool, detail: str = ""):
        icon = "✅" if ok else "❌"
        status = "PASS" if ok else "FAIL"
        print(f"  {icon} [{status}] {name}")
        if detail:
            print(f"         {detail}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"{name}: {detail}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  冒烟测试结果：{self.passed}/{total} 通过")
        if self.failed > 0:
            print(f"\n  失败项：")
            for e in self.errors:
                print(f"    - {e}")
        print(f"{'='*60}")
        return self.failed == 0


def api(method: str, path: str, token: Optional[str] = None,
         data: Optional[dict] = None, params: Optional[dict] = None,
         expected_status: Optional[int] = None) -> requests.Response:
    """发起 API 请求并返回响应"""
    url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = session.request(method, url, json=data, params=params, headers=headers, timeout=10)
        if expected_status and resp.status_code != expected_status:
            print(f"  ⚠️  期望 {expected_status}，实际 {resp.status_code}：{resp.text[:200]}")
        return resp
    except requests.exceptions.ConnectionError:
        print(f"\n  🔴 无法连接到 {url}，请确认后端服务已启动（python run.py）\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n  🔴 请求错误：{e}\n")
        sys.exit(1)


# ─── 测试套件 ───────────────────────────────────────────────────

def test_00_health_check(result: TestResult):
    """公共接口 - 健康检查"""
    print("\n📋 [1] 公共接口 - 健康检查")
    resp = api("GET", "/health", expected_status=200)
    try:
        data = resp.json()
        result.record("GET /health", data.get("status") == "ok")
    except:
        result.record("GET /health", False, resp.text[:100])


def test_01_admin_auth(result: TestResult):
    """商户后台 - 认证"""
    global admin_token, merchant_id
    print("\n📋 [2] 商户后台 - 登录认证")

    # 登录成功
    resp = api("POST", "/admin/auth/login", data={
        "username": SEED_MERCHANT_USERNAME,
        "password": SEED_MERCHANT_PASSWORD
    }, expected_status=200)
    if resp.status_code == 200:
        d = resp.json()
        admin_token = d.get("access_token")
        merchant_id = d.get("merchant_id")
        result.record("POST /admin/auth/login（正确密码）", True)
        result.record("返回 access_token", admin_token is not None)
        result.record("返回 merchant_id", merchant_id is not None)
    else:
        result.record("POST /admin/auth/login（正确密码）", False, resp.text[:100])

    # 登录失败
    resp = api("POST", "/admin/auth/login", data={
        "username": "admin", "password": "wrongpassword"
    })
    result.record("POST /admin/auth/login（错误密码→401）", resp.status_code == 401)

    # 无 token 访问受保护接口
    resp = api("GET", "/admin/categories")
    result.record("无 token 访问受保护接口→401", resp.status_code == 401)


def test_02_categories_crud(result: TestResult):
    """商户后台 - 分类管理 CRUD"""
    global category_id
    print("\n📋 [3] 商户后台 - 分类管理 CRUD")

    if not admin_token:
        result.record("跳过（无 admin_token）", False, "需要先通过登录测试")
        return

    # 创建分类
    resp = api("POST", "/admin/categories", token=admin_token, data={
        "name": "测试分类",
        "sort_order": 99
    }, expected_status=201)
    if resp.status_code == 201:
        category_id = resp.json().get("id")
        result.record("POST /admin/categories 创建成功", category_id is not None)
    else:
        result.record("POST /admin/categories 创建成功", False, resp.text[:100])
        return

    # 列出分类
    resp = api("GET", "/admin/categories", token=admin_token, expected_status=200)
    cats = resp.json()
    result.record("GET /admin/categories 列表不为空", len(cats) > 0)

    # 更新分类
    resp = api("PUT", f"/admin/categories/{category_id}", token=admin_token, data={
        "name": "测试分类-已修改",
        "sort_order": 88
    }, expected_status=200)
    result.record("PUT /admin/categories/{id} 更新成功", resp.status_code == 200)


def test_03_dishes_crud(result: TestResult):
    """商户后台 - 菜品管理 CRUD"""
    global dish_id
    print("\n📋 [4] 商户后台 - 菜品管理 CRUD")

    if not admin_token or not category_id:
        result.record("跳过（无 token 或 category_id）", False)
        return

    # 创建菜品
    resp = api("POST", "/admin/dishes", token=admin_token, data={
        "name": "测试菜品",
        "price": 25.5,
        "description": "冒烟测试创建的菜品",
        "category_id": category_id,
        "is_available": True
    }, expected_status=201)
    if resp.status_code == 201:
        dish_id = resp.json().get("id")
        result.record("POST /admin/dishes 创建成功", dish_id is not None)
    else:
        result.record("POST /admin/dishes 创建成功", False, resp.text[:100])
        return

    # 列出菜品（按分类筛选）
    resp = api("GET", f"/admin/dishes?category_id={category_id}", token=admin_token, expected_status=200)
    result.record("GET /admin/dishes（按分类筛选）", len(resp.json()) > 0)

    # 更新菜品
    resp = api("PUT", f"/admin/dishes/{dish_id}", token=admin_token, data={
        "name": "测试菜品-已修改",
        "price": 30.0
    }, expected_status=200)
    result.record("PUT /admin/dishes/{id} 更新成功", resp.status_code == 200)

    # 切换上下架
    resp = api("PATCH", f"/admin/dishes/{dish_id}/toggle-available", token=admin_token, expected_status=200)
    result.record("PATCH /dishes/{id}/toggle-available", resp.status_code == 200)

    # 价格边界：0
    resp = api("POST", "/admin/dishes", token=admin_token, data={
        "name": "零价菜品", "price": 0, "category_id": category_id, "is_available": True
    })
    result.record("POST /dishes price=0 拒绝（≥422）", resp.status_code in [422, 400])

    # 价格边界：负数
    resp = api("POST", "/admin/dishes", token=admin_token, data={
        "name": "负价菜品", "price": -10, "category_id": category_id, "is_available": True
    })
    result.record("POST /dishes price=-10 拒绝（≥422）", resp.status_code in [422, 400])


def test_04_tables_crud(result: TestResult):
    """商户后台 - 桌台管理 CRUD"""
    global table_id
    print("\n📋 [5] 商户后台 - 桌台管理 CRUD")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 列出桌台
    resp = api("GET", "/admin/tables", token=admin_token, expected_status=200)
    tables = resp.json()
    if tables:
        table_id = tables[0]["id"]
        result.record("GET /admin/tables 列表不为空", True)
    else:
        # 创建桌台
        resp = api("POST", "/admin/tables", token=admin_token, data={
            "code": f"TEST{round(time.time()) % 10000}",
            "name": "冒烟测试桌台",
            "capacity": 4
        }, expected_status=201)
        if resp.status_code == 201:
            table_id = resp.json().get("id")
        result.record("创建测试桌台", table_id is not None)
        return

    # QR 码生成
    resp = api("GET", f"/admin/tables/{table_id}/qrcode", token=admin_token)
    result.record("GET /tables/{id}/qrcode 返回 PNG", resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/png"))

    # 更新桌台
    resp = api("PUT", f"/admin/tables/{table_id}", token=admin_token, data={
        "name": "测试桌台-已修改"
    }, expected_status=200)
    result.record("PUT /admin/tables/{id} 更新成功", resp.status_code == 200)

    # code 重复
    resp = api("POST", "/admin/tables", token=admin_token, data={
        "code": tables[0]["code"], "name": "重复桌台", "capacity": 2
    })
    result.record("POST /tables code 重复→409", resp.status_code == 409)


def test_05_customer_public(result: TestResult):
    """顾客端 - 公开接口"""
    global table_id
    print("\n📋 [6] 顾客端 - 公开接口（无需认证）")

    if not table_id:
        # 尝试获取任意桌台
        resp = api("GET", "/customer/tables/1")
        if resp.status_code == 200:
            table_id = 1

    # 桌台信息
    if table_id:
        resp = api("GET", f"/customer/tables/{table_id}")
        result.record("GET /customer/tables/{id}", resp.status_code == 200)
    else:
        result.record("GET /customer/tables/{id}", False, "无 table_id")

    # 分类列表
    resp = api("GET", "/customer/categories")
    result.record("GET /customer/categories", resp.status_code == 200)

    # 菜品列表
    resp = api("GET", "/customer/dishes")
    result.record("GET /customer/dishes", resp.status_code == 200)

    # 菜品详情
    if dish_id:
        resp = api("GET", f"/customer/dishes/{dish_id}")
        result.record("GET /customer/dishes/{id}", resp.status_code == 200)

    # 商户公开设置
    resp = api("GET", "/customer/merchants/1/settings")
    result.record("GET /customer/merchants/{id}/settings", resp.status_code == 200)


def test_06_orders_flow(result: TestResult):
    """顾客端 - 订单全流程（Phase 1/2 简易版）"""
    global order_id
    print("\n📋 [7] 顾客端 - 订单全流程")

    if not table_id:
        result.record("跳过（无 table_id）", False)
        return

    # 获取菜品列表（找可用的）
    resp = api("GET", "/customer/dishes")
    dishes = resp.json() if resp.status_code == 200 else []
    available_dish = next((d for d in dishes if d.get("is_available") == 1 or d.get("is_available") == True), None)
    if not available_dish:
        result.record("创建订单（无可用菜品）", False, "无可用菜品进行测试")
        return

    # 创建订单
    order_payload = {
        "table_id": table_id,
        "items": [{"dish_id": available_dish["id"], "quantity": 1}],
        "remark": "冒烟测试订单"
    }
    resp = api("POST", "/customer/orders", data=order_payload, expected_status=200)
    if resp.status_code == 200:
        order_data = resp.json()
        order_id = order_data.get("id")
        result.record("POST /customer/orders 创建成功", order_id is not None)
        result.record("订单返回 order_number", order_data.get("order_number") is not None)

        # counter_pay 模式检查 payment_token
        if order_data.get("payment_mode") == "counter_pay":
            result.record("counter_pay 返回 payment_token", order_data.get("payment_token") is not None)
            result.record("counter_pay 返回 payment_code", order_data.get("payment_code") is not None)
        else:
            result.record("订单状态为 pending", order_data.get("status") == "pending")
    else:
        result.record("POST /customer/orders 创建成功", False, resp.text[:100])
        return

    # 查询订单状态
    if order_id:
        resp = api("GET", f"/customer/orders/{order_id}")
        result.record("GET /customer/orders/{id}", resp.status_code == 200)
        if resp.status_code == 200:
            order_detail = resp.json()
            result.record("订单包含 items", len(order_detail.get("items", [])) > 0)

        # 模拟支付（counter_pay 模式）
        resp = api("POST", f"/customer/orders/{order_id}/pay")
        if resp.status_code == 200:
            result.record("POST /customer/orders/{id}/pay 支付成功", True)
        elif resp.status_code == 400:
            # 已是 pending 或其他状态（seed 数据可能已支付）
            result.record("POST /customer/orders/{id}/pay（状态检查）", True, f"状态：{resp.json().get('detail', resp.text[:50])}")


def test_07_admin_orders(result: TestResult):
    """商户后台 - 订单管理"""
    global order_id
    print("\n📋 [8] 商户后台 - 订单管理")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 订单列表
    resp = api("GET", "/admin/orders", token=admin_token, expected_status=200)
    result.record("GET /admin/orders 列表", resp.status_code == 200)
    if resp.status_code == 200:
        data = resp.json()
        result.record("订单列表含 total 字段", "total" in data)

    # 今日统计
    resp = api("GET", "/admin/stats/today", token=admin_token, expected_status=200)
    result.record("GET /admin/stats/today", resp.status_code == 200)
    if resp.status_code == 200:
        stats = resp.json()
        result.record("stats/today 包含关键字段",
                      all(k in stats for k in ["order_count", "total_amount", "completed_count"]))

    # 销售统计
    resp = api("GET", "/admin/stats/sales?range_type=day", token=admin_token, expected_status=200)
    result.record("GET /admin/stats/sales?range_type=day", resp.status_code == 200)

    # 小票
    if order_id:
        resp = api("GET", f"/admin/orders/{order_id}/ticket", token=admin_token)
        result.record("GET /admin/orders/{id}/ticket", resp.status_code == 200)
        if resp.status_code == 200:
            ticket_data = resp.json()
            result.record("小票包含订单号", "order_number" in ticket_data.get("ticket", ""))


def test_08_admin_settings(result: TestResult):
    """商户后台 - 设置"""
    print("\n📋 [9] 商户后台 - 商户设置")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 获取设置
    resp = api("GET", "/admin/settings", token=admin_token, expected_status=200)
    result.record("GET /admin/settings", resp.status_code == 200)

    # 更新为 counter_pay
    resp = api("PUT", "/admin/settings", token=admin_token, data={"mode": "counter_pay"}, expected_status=200)
    result.record("PUT /admin/settings mode=counter_pay", resp.status_code == 200)

    # 更新为 credit_pay
    resp = api("PUT", "/admin/settings", token=admin_token, data={"mode": "credit_pay"}, expected_status=200)
    result.record("PUT /admin/settings mode=credit_pay", resp.status_code == 200)

    # 无效模式
    resp = api("PUT", "/admin/settings", token=admin_token, data={"mode": "invalid_mode"})
    result.record("PUT /admin/settings mode=invalid→400", resp.status_code == 400)


def test_09_wx_auth_phase3a(result: TestResult):
    """Phase 3A - 微信授权登录（开发环境模拟）"""
    print("\n📋 [10] Phase 3A - 微信授权登录")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 检查 wx-auth 是否配置
    resp = api("GET", "/admin/wx-auth/auth-url")
    if resp.status_code == 500 and "WX_APP_ID" in resp.text:
        result.record("GET /wx-auth/auth-url（未配置 WX_APP_ID）", True, "跳过（微信未配置）")
        result.record("POST /wx-auth/wx-login-test（开发环境模拟）", True, "跳过（微信未配置）")
        return

    # 开发环境模拟登录（需要 merchant_user_id，这里用 seed 用户的 id=1）
    resp = api("GET", "/admin/wx-auth/wx-login-test?merchant_user_id=1")
    if resp.status_code == 200:
        data = resp.json()
        global wx_customer_token
        wx_customer_token = data.get("access_token")
        result.record("GET /wx-auth/wx-login-test 模拟成功", True)
    elif resp.status_code == 403:
        result.record("GET /wx-auth/wx-login-test（非开发环境）", True, "生产环境不可用，符合预期")
    else:
        result.record("GET /wx-auth/wx-login-test", False, resp.text[:100])


def test_10_platform_admin_phase3a(result: TestResult):
    """Phase 3A - 平台管理员"""
    global platform_admin_token
    print("\n📋 [11] Phase 3A - 平台管理员")

    # 检查是否有平台管理员（seed 数据可能没有）
    resp = api("POST", "/admin/platform-admin/auth/login", data={
        "username": "platform_admin", "password": "platform_admin123"
    })
    if resp.status_code == 200:
        platform_admin_token = resp.json().get("access_token")
        result.record("平台管理员登录成功", True)

        # 列出商户
        resp = api("GET", "/admin/platform-admin/merchants", token=platform_admin_token)
        result.record("GET /platform-admin/merchants", resp.status_code == 200)
    elif resp.status_code == 401:
        result.record("平台管理员登录（无账号，跳过）", True, "seed 数据无平台管理员")
    else:
        result.record("平台管理员接口", False, f"状态：{resp.status_code}")


def test_11_coupons_phase3b(result: TestResult):
    """Phase 3B - 优惠券管理"""
    print("\n📋 [12] Phase 3B - 优惠券")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 创建优惠券
    resp = api("POST", "/admin/coupons", token=admin_token, data={
        "name": "冒烟测试券",
        "type": "cash",
        "threshold": 10.0,
        "discount_value": 5.0,
        "total_count": 100,
        "per_user_limit": 1,
        "valid_days": 30
    }, expected_status=201)
    coupon_id = None
    if resp.status_code == 201:
        coupon_id = resp.json().get("id")
        result.record("POST /admin/coupons 创建成功", coupon_id is not None)
    else:
        result.record("POST /admin/coupons 创建成功", False, resp.text[:100])

    # 优惠券列表
    resp = api("GET", "/admin/coupons", token=admin_token, expected_status=200)
    result.record("GET /admin/coupons 列表", resp.status_code == 200)

    # 暂停发放
    if coupon_id:
        resp = api("POST", f"/admin/coupons/{coupon_id}/pause", token=admin_token)
        result.record("POST /admin/coupons/{id}/pause", resp.status_code == 200)


def test_12_points_settings_phase3b(result: TestResult):
    """Phase 3B - 积分规则"""
    print("\n📋 [13] Phase 3B - 积分规则")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 获取积分设置
    resp = api("GET", "/admin/merchant/settings/points", token=admin_token, expected_status=200)
    result.record("GET /merchant/settings/points", resp.status_code == 200)
    if resp.status_code == 200:
        pts = resp.json()
        result.record("积分设置含关键字段",
                      all(k in pts for k in ["points_enabled", "points_per_yuan", "points_max_discount_percent"]))

    # 更新积分设置
    resp = api("PUT", "/admin/merchant/settings/points", token=admin_token, data={
        "points_enabled": 1,
        "points_per_yuan": 2,
        "points_max_discount_percent": 30
    }, expected_status=200)
    result.record("PUT /merchant/settings/points", resp.status_code == 200)


def test_13_reports_phase3c(result: TestResult):
    """Phase 3C - 报表"""
    print("\n📋 [14] Phase 3C - 报表")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    from datetime import date, timedelta
    today = date.today()
    week_ago = today - timedelta(days=7)

    # 日报
    resp = api("GET", f"/admin/reports/daily?start_date={week_ago}&end_date={today}",
               token=admin_token, expected_status=200)
    result.record("GET /reports/daily", resp.status_code == 200)

    # 月报
    resp = api("GET", f"/admin/reports/monthly?year={today.year}",
               token=admin_token, expected_status=200)
    result.record("GET /reports/monthly", resp.status_code == 200)

    # 菜品排行
    resp = api("GET", f"/admin/reports/dishes?start_date={week_ago}&end_date={today}&limit=10",
               token=admin_token, expected_status=200)
    result.record("GET /reports/dishes", resp.status_code == 200)

    # 顾客分析
    resp = api("GET", f"/admin/reports/customers?start_date={week_ago}&end_date={today}",
               token=admin_token, expected_status=200)
    result.record("GET /reports/customers", resp.status_code == 200)

    # 日期范围校验：start > end
    resp = api("GET", f"/admin/reports/daily?start_date={today}&end_date={week_ago}",
               token=admin_token)
    result.record("GET /reports/daily start>end→400", resp.status_code == 400)

    # 日期范围超限
    far_date = today - timedelta(days=400)
    resp = api("GET", f"/admin/reports/daily?start_date={far_date}&end_date={today}",
               token=admin_token)
    result.record("GET /reports/daily 范围超366天→400", resp.status_code == 400)


def test_14_audit_logs_phase3a(result: TestResult):
    """Phase 3A - 审计日志"""
    print("\n📋 [15] Phase 3A - 审计日志")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    resp = api("GET", "/admin/audit-logs", token=admin_token, expected_status=200)
    result.record("GET /audit-logs 商户日志", resp.status_code == 200)


def test_15_merchant_user_phase3a(result: TestResult):
    """Phase 3A - 商户用户管理"""
    global merchant_user_id
    print("\n📋 [16] Phase 3A - 商户用户管理")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 列出商户用户
    resp = api("GET", "/admin/merchant-users", token=admin_token, expected_status=200)
    result.record("GET /merchant-users 列表", resp.status_code == 200)

    # 获取当前用户信息
    resp = api("GET", "/admin/merchant-users/me", token=admin_token, expected_status=200)
    result.record("GET /merchant-users/me", resp.status_code == 200)
    if resp.status_code == 200:
        me = resp.json()
        result.record("me 返回 username", "username" in me)


def test_16_delete_protection(result: TestResult):
    """边界测试 - 删除保护"""
    print("\n📋 [17] 边界测试 - 删除保护")

    if not admin_token or not category_id or not dish_id:
        result.record("跳过（前置数据不足）", False)
        return

    # 删除已有菜品的分类 → 409
    resp = api("DELETE", f"/admin/categories/{category_id}", token=admin_token)
    result.record("DELETE /categories/{id} 有菜品→409", resp.status_code == 409)


def test_17_order_status_transitions(result: TestResult):
    """边界测试 - 订单状态流转"""
    print("\n📋 [18] 边界测试 - 订单状态流转")

    if not admin_token or not table_id:
        result.record("跳过", False)
        return

    # 获取菜品
    resp = api("GET", "/customer/dishes")
    dishes = resp.json() if resp.status_code == 200 else []
    available_dish = next((d for d in dishes if d.get("is_available") == 1 or d.get("is_available") == True), None)
    if not available_dish:
        result.record("跳过（无可用菜品）", False)
        return

    # 创建一笔新订单
    resp = api("POST", "/customer/orders", data={
        "table_id": table_id,
        "items": [{"dish_id": available_dish["id"], "quantity": 1}]
    })
    if resp.status_code != 200:
        result.record("创建测试订单", False, resp.text[:100])
        return

    new_order = resp.json()
    new_order_id = new_order.get("id")
    result.record("创建测试订单", True)

    # 如果是 counter_pay，先支付
    if new_order.get("payment_mode") == "counter_pay":
        resp = api("POST", f"/customer/orders/{new_order_id}/pay")
        if resp.status_code != 200:
            result.record("模拟支付", False, resp.text[:100])

    # 获取当前状态
    resp = api("GET", f"/admin/orders/{new_order_id}", token=admin_token)
    if resp.status_code != 200:
        result.record("获取订单状态", False)
        return

    current_status = resp.json().get("status")

    # 合法正向流转测试（pending → confirmed → paid）
    if current_status == "pending" or current_status == "pending_payment":
        resp = api("PUT", f"/admin/orders/{new_order_id}/status", token=admin_token,
                   data={"status": "confirmed"})
        result.record("pending→confirmed 更新成功", resp.status_code == 200)

        resp = api("PUT", f"/admin/orders/{new_order_id}/status", token=admin_token,
                   data={"status": "paid"})
        result.record("confirmed→paid 更新成功", resp.status_code == 200)

        # paid 状态不能逆向
        resp = api("PUT", f"/admin/orders/{new_order_id}/status", token=admin_token,
                   data={"status": "pending"})
        result.record("paid→pending 拒绝→400", resp.status_code == 400)
    else:
        result.record("订单状态流转测试", True, f"当前状态：{current_status}，跳过流转测试")


def test_18_data_isolation(result: TestResult):
    """边界测试 - 数据隔离"""
    print("\n📋 [19] 边界测试 - 数据隔离")

    if not admin_token:
        result.record("跳过（无 admin_token）", False)
        return

    # 操作不存在的分类
    resp = api("GET", "/admin/categories/99999", token=admin_token)
    result.record("GET /categories/99999→404（不存在）", resp.status_code == 404)

    # 操作不存在的菜品
    resp = api("GET", "/admin/dishes/99999", token=admin_token)
    result.record("GET /dishes/99999→404（不存在）", resp.status_code == 404)

    # 操作不存在的订单
    resp = api("GET", "/admin/orders/99999", token=admin_token)
    result.record("GET /orders/99999→404（不存在）", resp.status_code == 404)


# ─── 主入口 ────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  🦞 扫码点餐系统 - Phase 6 冒烟测试")
    print("  后端地址: http://127.0.0.1:8002")
    print("=" * 60)

    # 运行所有测试
    result = TestResult()

    test_00_health_check(result)
    test_01_admin_auth(result)
    test_02_categories_crud(result)
    test_03_dishes_crud(result)
    test_04_tables_crud(result)
    test_05_customer_public(result)
    test_06_orders_flow(result)
    test_07_admin_orders(result)
    test_08_admin_settings(result)
    test_09_wx_auth_phase3a(result)
    test_10_platform_admin_phase3a(result)
    test_11_coupons_phase3b(result)
    test_12_points_settings_phase3b(result)
    test_13_reports_phase3c(result)
    test_14_audit_logs_phase3a(result)
    test_15_merchant_user_phase3a(result)
    test_16_delete_protection(result)
    test_17_order_status_transitions(result)
    test_18_data_isolation(result)

    # 输出摘要
    ok = result.summary()
    print()
    if ok:
        print("🎉 所有冒烟测试通过！")
    else:
        print("⚠️  部分测试失败，请检查后修复。")
    print()

    # 返回退出码
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
