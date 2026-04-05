"""
Phase 3C Scheduled Tasks
每日 02:00 归档日报，每月 1 日 03:00 归档月报

Usage:
    from app.tasks.finalize_reports import finalize_daily, finalize_monthly
    scheduler.add_job(finalize_daily, 'cron', hour=2, minute=0, id='finalize_daily_revenue')
    scheduler.add_job(finalize_monthly, 'cron', day=1, hour=3, minute=0, id='finalize_monthly_revenue')
"""
from datetime import date, datetime, timedelta
import logging
from app.database import SessionLocal
from app.models.merchant import Merchant
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


def finalize_daily():
    """
    每日 02:00 执行：归档昨日日报
    stat_date = 当前日期 - 1 天
    """
    yesterday = date.today() - timedelta(days=1)
    logger.info(f"[FinalizeDaily] Starting daily finalization for {yesterday}")

    db = SessionLocal()
    try:
        merchants = db.query(Merchant).filter(Merchant.status == "active").all()
        success_count = 0
        skip_count = 0

        for merchant in merchants:
            try:
                result = ReportService.finalize_daily(db, merchant.id, yesterday)
                if result:
                    success_count += 1
                    logger.info(f"[FinalizeDaily] Merchant {merchant.id} ({merchant.name}): finalized for {yesterday}")
                else:
                    skip_count += 1
                    logger.info(f"[FinalizeDaily] Merchant {merchant.id} ({merchant.name}): already finalized or no data, skipped")
            except Exception as e:
                logger.error(f"[FinalizeDaily] Merchant {merchant.id} ({merchant.name}): ERROR - {e}")

        logger.info(f"[FinalizeDaily] Completed: {success_count} finalized, {skip_count} skipped, {len(merchants)} total merchants")
    finally:
        db.close()


def finalize_monthly():
    """
    每月 1 日 03:00 执行：归档上月月报
    基于已归档日报汇总
    """
    today = date.today()
    # 上月
    if today.month == 1:
        year = today.year - 1
        month = 12
    else:
        year = today.year
        month = today.month - 1

    logger.info(f"[FinalizeMonthly] Starting monthly finalization for {year}-{month:02d}")

    db = SessionLocal()
    try:
        merchants = db.query(Merchant).filter(Merchant.status == "active").all()
        success_count = 0
        skip_count = 0

        for merchant in merchants:
            try:
                result = ReportService.finalize_monthly(db, merchant.id, year, month)
                if result:
                    success_count += 1
                    logger.info(f"[FinalizeMonthly] Merchant {merchant.id} ({merchant.name}): finalized for {year}-{month:02d}")
                else:
                    skip_count += 1
                    logger.info(f"[FinalizeMonthly] Merchant {merchant.id} ({merchant.name}): already finalized, skipped")
            except Exception as e:
                logger.error(f"[FinalizeMonthly] Merchant {merchant.id} ({merchant.name}): ERROR - {e}")

        logger.info(f"[FinalizeMonthly] Completed: {success_count} finalized, {skip_count} skipped, {len(merchants)} total merchants")
    finally:
        db.close()


def run_backfill(merchant_id: int, start_date: date, end_date: date):
    """
    批量回填指定商户指定日期范围的日报
    用于修复历史数据或补充新商户的历史报表
    """
    logger.info(f"[Backfill] Starting backfill for merchant {merchant_id}: {start_date} ~ {end_date}")

    db = SessionLocal()
    try:
        current_date = start_date
        count = 0
        while current_date <= end_date:
            try:
                # 跳过已归档的
                from app.models.daily_revenue import DailyRevenue
                existing = db.query(DailyRevenue).filter(
                    DailyRevenue.merchant_id == merchant_id,
                    DailyRevenue.stat_date == current_date,
                    DailyRevenue.is_finalized == 1,
                ).first()
                if existing:
                    logger.info(f"[Backfill] Merchant {merchant_id}: {current_date} already finalized, skipping")
                    current_date += timedelta(days=1)
                    continue

                # 先生成草稿
                data = ReportService.aggregate_orders_for_date(db, merchant_id, current_date)
                record = db.query(DailyRevenue).filter(
                    DailyRevenue.merchant_id == merchant_id,
                    DailyRevenue.stat_date == current_date,
                ).first()

                if record:
                    for key, value in data.items():
                        setattr(record, key, value)
                    record.version = (record.version or 0) + 1
                else:
                    record = DailyRevenue(
                        merchant_id=merchant_id,
                        stat_date=current_date,
                        **data,
                        is_finalized=0,
                        version=0,
                    )
                    db.add(record)

                db.commit()
                count += 1
                logger.info(f"[Backfill] Merchant {merchant_id}: {current_date} done")

            except Exception as e:
                logger.error(f"[Backfill] Merchant {merchant_id}: {current_date} ERROR - {e}")
                db.rollback()

            current_date += timedelta(days=1)

        logger.info(f"[Backfill] Completed: {count} records processed for merchant {merchant_id}")
        return count

    finally:
        db.close()
