"""
Phase 3C Reports API Endpoints
GET/POST /admin/reports/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, timedelta
from app.database import get_db
from app.dependencies import get_current_merchant, get_current_merchant_user
from app.models.merchant import Merchant
from app.models.merchant_user import MerchantUser
from app.schemas.report import (
    DailyRevenueResponse, DailyRevenueItem, DailyRevenueSummary, DailyRevenuePagination,
    MonthlyRevenueResponse, MonthlyRevenueItem, MonthlyRevenueSummary,
    DishRankingResponse, DishRankingItem, DishRankingSummary,
    CustomerResponse, CustomerItem, CustomerSummary, CustomerSegmentsResponse, TierDistribution,
    RegenerateRequest, RegenerateResponse,
    UndoRequest, UndoResponse,
    CorrectionListResponse, CorrectionItem,
)
from app.services.report_service import ReportService
from decimal import Decimal

router = APIRouter()


def _require_owner(user: MerchantUser):
    """仅 owner 可调用的权限校验"""
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="insufficient_permission: 仅 owner 角色可执行此操作")


# ─── GET /admin/reports/daily ───────────────────────────────────────────────

@router.get("/daily", response_model=DailyRevenueResponse)
def get_daily_report(
    start_date: date = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(31, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """营收日报查询"""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="invalid_date_range: start_date 不能晚于 end_date")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=400, detail="invalid_date_range: 日期范围不能超过 366 天")
    if end_date > date.today():
        raise HTTPException(status_code=400, detail="invalid_date_range: end_date 不能为未来日期")

    try:
        items, summary, total = ReportService.get_daily_report(
            db=db,
            merchant_id=current_merchant.id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        return DailyRevenueResponse(
            items=[DailyRevenueItem(**item) for item in items],
            summary=DailyRevenueSummary(**summary),
            pagination=DailyRevenuePagination(
                page=page,
                page_size=page_size,
                total=total,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")


# ─── GET /admin/reports/monthly ────────────────────────────────────────────

@router.get("/monthly", response_model=MonthlyRevenueResponse)
def get_monthly_report(
    year: Optional[int] = Query(None, description="统计年份"),
    month: Optional[int] = Query(None, ge=1, le=12, description="统计月份 1-12"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=12, description="每页条数"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """营收月报查询"""
    try:
        items, summary = ReportService.get_monthly_report(
            db=db,
            merchant_id=current_merchant.id,
            year=year,
            month=month,
            page=page,
            page_size=page_size,
        )
        return MonthlyRevenueResponse(
            items=[MonthlyRevenueItem(**item) for item in items],
            summary=MonthlyRevenueSummary(**summary),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")


# ─── GET /admin/reports/dishes ─────────────────────────────────────────────

@router.get("/dishes", response_model=DishRankingResponse)
def get_dish_ranking(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """菜品销量排行"""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="invalid_date_range")
    try:
        items, summary = ReportService.get_dish_ranking(
            db=db,
            merchant_id=current_merchant.id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return DishRankingResponse(
            items=[DishRankingItem(**item) for item in items],
            summary=DishRankingSummary(**summary),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")


# ─── GET /admin/reports/customers ──────────────────────────────────────────

@router.get("/customers", response_model=CustomerResponse)
def get_customer_analysis(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    sort_by: str = Query("total_amount", description="排序字段"),
    order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """顾客消费分析"""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="invalid_date_range")
    try:
        items, summary, total = ReportService.get_customer_analysis(
            db=db,
            merchant_id=current_merchant.id,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )
        return CustomerResponse(
            items=[CustomerItem(**item) for item in items],
            total=total,
            summary=CustomerSummary(**summary),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")


# ─── GET /admin/reports/customer-segments ──────────────────────────────────

@router.get("/customer-segments", response_model=CustomerSegmentsResponse)
def get_customer_segments(
    start_date: Optional[date] = Query(None, description="开始日期，默认最近30天"),
    end_date: Optional[date] = Query(None, description="结束日期，默认今日"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """顾客群体画像"""
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today - timedelta(days=30)

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="invalid_date_range")

    try:
        data = ReportService.get_customer_segments(
            db=db,
            merchant_id=current_merchant.id,
            start_date=start_date,
            end_date=end_date,
        )
        return CustomerSegmentsResponse(
            total_customers=data["total_customers"],
            new_today=data["new_today"],
            new_this_month=data["new_this_month"],
            active_this_month=data["active_this_month"],
            inactive_30d=data["inactive_30d"],
            tier_distribution=[TierDistribution(**t) for t in data["tier_distribution"]],
            avg_points_per_customer=data["avg_points_per_customer"],
            avg_visit_per_customer=data["avg_visit_per_customer"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")


# ─── POST /admin/reports/regenerate ────────────────────────────────────────

@router.post("/regenerate", response_model=RegenerateResponse)
def regenerate_report(
    request: RegenerateRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
):
    """手动重新聚合报表（仅 owner）"""
    _require_owner(current_user)

    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="invalid_date_range")
    if (request.end_date - request.start_date).days > 90:
        raise HTTPException(status_code=400, detail="invalid_date_range: 单次修正不超过 90 天")

    try:
        count = ReportService.regenerate_report(
            db=db,
            merchant_id=current_user.merchant_id,
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            corrected_by=current_user.id,
            reason=request.reason,
        )
        return RegenerateResponse(
            regenerated=count,
            message=f"{request.start_date} ~ {request.end_date} 的{('日报' if request.report_type == 'daily' else '月报')}已重新聚合",
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"finalized_data_not_modifiable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"db_write_error: {str(e)}")


# ─── POST /admin/reports/undo ──────────────────────────────────────────────

@router.post("/undo", response_model=UndoResponse)
def undo_correction(
    request: UndoRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: MerchantUser = Depends(get_current_merchant_user),
):
    """撤销最近一次修正（仅 owner）"""
    _require_owner(current_user)

    try:
        result = ReportService.undo_correction(
            db=db,
            merchant_id=current_user.merchant_id,
            report_type=request.report_type,
            stat_date=request.stat_date,
            corrected_by=current_user.id,
        )
        return UndoResponse(
            undone=True,
            message=f"已撤销 {request.stat_date} 的{('日报' if request.report_type == 'daily' else '月报')}修正，数据已恢复",
            previous_total_amount=result["previous_total_amount"],
            current_total_amount=result["current_total_amount"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"db_write_error: {str(e)}")


# ─── GET /admin/reports/corrections ───────────────────────────────────────

@router.get("/corrections", response_model=CorrectionListResponse)
def get_corrections(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    report_type: Optional[str] = Query(None, description="daily/monthly/all"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant),
):
    """查询报表修正记录"""
    try:
        items, total = ReportService.get_corrections(
            db=db,
            merchant_id=current_merchant.id,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
            page=page,
            page_size=page_size,
        )
        return CorrectionListResponse(
            items=[CorrectionItem(**item) for item in items],
            total=total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"aggregation_error: {str(e)}")
