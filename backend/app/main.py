from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta
from app.database import init_db, SessionLocal
from app.config import Settings
from app.models.order import Order
from app.api.v1 import customer, admin, public

settings = Settings()

# 全局后台任务task引用
_bg_task = None
_bg_task2 = None
_bg_task3 = None


def validate_config():
    """启动时校验配置"""
    if settings.FRONTEND_PUBLIC_URL:
        print(f"[STARTUP] FRONTEND_PUBLIC_URL validated: {settings.FRONTEND_PUBLIC_URL}")
    else:
        print("[STARTUP] FRONTEND_PUBLIC_URL not set, QR codes will use relative URLs")


async def cancel_expired_pending_orders():
    """后台任务：自动取消超过10分钟的 pending_payment 订单"""
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            expired = db.query(Order).filter(
                Order.status == "pending_payment",
                Order.created_at < cutoff
            ).all()
            for order in expired:
                order.status = "cancelled"
                order.updated_at = datetime.utcnow()
            if expired:
                db.commit()
                print(f"[CRON] Cancelled {len(expired)} expired pending_payment orders")
        except Exception as e:
            db.rollback()
            print(f"[CRON] Error cancelling expired orders: {e}")
        finally:
            db.close()


async def scan_data_isolation():
    """
    Phase 3A 后台任务：数据隔离审计扫描
    每5分钟执行一次，检查是否存在潜在的数据隔离问题
    """
    from app.services.audit_service import AuditService
    from app.services.wx_auth_service import WxAuthService

    while True:
        await asyncio.sleep(300)  # 5分钟
        db = SessionLocal()
        try:
            # 清理过期的微信 auth states
            expired_states = WxAuthService.cleanup_expired_states(db)
            if expired_states > 0:
                print(f"[CRON] Cleaned up {expired_states} expired wx_auth_states")

            # 清理90天前的审计日志
            deleted_logs = AuditService.cleanup_old_logs(db, days=90)
            if deleted_logs > 0:
                print(f"[CRON] Cleaned up {deleted_logs} old audit logs")

        except Exception as e:
            print(f"[CRON] Error in scan_data_isolation: {e}")
        finally:
            db.close()


async def expire_coupons():
    """
    Phase 3B 后台任务：优惠券过期检查
    每日 01:00 执行，将过期未使用的优惠券标记为 expired
    """
    from app.services.coupon_service import CouponService

    while True:
        await asyncio.sleep(3600)  # 每小时检查一次
        db = SessionLocal()
        try:
            expired_count = CouponService.expire_old_coupons(db)
            if expired_count > 0:
                print(f"[CRON] Expired {expired_count} unused coupons")
        except Exception as e:
            print(f"[CRON] Error in expire_coupons: {e}")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task, _bg_task2
    # Startup
    init_db()
    validate_config()
    # 启动后台定时任务
    _bg_task = asyncio.create_task(cancel_expired_pending_orders())
    _bg_task2 = asyncio.create_task(scan_data_isolation())
    _bg_task3 = asyncio.create_task(expire_coupons())
    yield
    # Shutdown
    if _bg_task:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass
    if _bg_task2:
        _bg_task2.cancel()
        try:
            await _bg_task2
        except asyncio.CancelledError:
            pass
    if _bg_task3:
        _bg_task3.cancel()
        try:
            await _bg_task3
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Scan Order API", version="1.0.0", lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api/v1", tags=["公共接口"])
app.include_router(customer.router, prefix="/api/v1/customer", tags=["顾客端"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["商户后台"])


@app.get("/")
def root():
    return {"message": "Scan Order API", "version": "1.0.0"}
