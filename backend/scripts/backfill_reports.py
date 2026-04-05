#!/usr/bin/env python
"""
Phase 3C 批量回填工具
backfill_reports.py

Usage:
    # 回填指定日期范围（默认日报+月报）
    python scripts/backfill_reports.py --merchant-id 5 --start-date 2026-01-01 --end-date 2026-03-31

    # 仅回填日报
    python scripts/backfill_reports.py --merchant-id 5 --start-date 2026-01-01 --end-date 2026-03-31 --type daily

    # 回填月报
    python scripts/backfill_reports.py --merchant-id 5 --year 2026 --month 3 --type monthly

    # 预览模式（不实际写入）
    python scripts/backfill_reports.py --merchant-id 5 --start-date 2026-01-01 --end-date 2026-03-31 --dry-run

    # 帮助
    python scripts/backfill_reports.py --help
"""
import sys
import os
import argparse
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.merchant import Merchant
from app.services.report_service import ReportService


def backfill_daily(db, merchant_id: int, start_date: date, end_date: date, dry_run: bool = False):
    """回填日报数据"""
    current_date = start_date
    processed = 0
    skipped = 0
    errors = 0

    while current_date <= end_date:
        try:
            # 检查是否已归档
            from app.models.daily_revenue import DailyRevenue
            existing = db.query(DailyRevenue).filter(
                DailyRevenue.merchant_id == merchant_id,
                DailyRevenue.stat_date == current_date,
                DailyRevenue.is_finalized == 1,
            ).first()

            if existing:
                print(f"  [SKIP] {current_date} - already finalized")
                skipped += 1
                current_date += timedelta(days=1)
                continue

            if dry_run:
                data = ReportService.aggregate_orders_for_date(db, merchant_id, current_date)
                print(f"  [DRY]  {current_date} - would write: orders={data['total_orders']}, amount={data['total_amount']}")
            else:
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
                print(f"  [OK]   {current_date} - orders={data['total_orders']}, amount={data['total_amount']}")

            processed += 1

        except Exception as e:
            db.rollback()
            print(f"  [ERR]  {current_date} - {e}")
            errors += 1

        current_date += timedelta(days=1)

    return processed, skipped, errors


def backfill_monthly(db, merchant_id: int, year: int, month: int, dry_run: bool = False):
    """回填月报数据"""
    from app.models.monthly_revenue import MonthlyRevenue

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    # 检查是否已归档
    existing = db.query(MonthlyRevenue).filter(
        MonthlyRevenue.merchant_id == merchant_id,
        MonthlyRevenue.stat_year == year,
        MonthlyRevenue.stat_month == month,
        MonthlyRevenue.is_finalized == 1,
    ).first()

    if existing:
        print(f"  [SKIP] {year}-{month:02d} - already finalized")
        return 0, 1, 0

    if dry_run:
        data = ReportService._aggregate_daily_range(db, merchant_id, month_start, month_end)
        print(f"  [DRY]  {year}-{month:02d} - would write: orders={data['total_orders']}, amount={data['total_amount']}")
        return 1, 0, 0

    data = ReportService._aggregate_daily_range(db, merchant_id, month_start, month_end)
    record = db.query(MonthlyRevenue).filter(
        MonthlyRevenue.merchant_id == merchant_id,
        MonthlyRevenue.stat_year == year,
        MonthlyRevenue.stat_month == month,
    ).first()

    if record:
        for key, value in data.items():
            setattr(record, key, value)
        record.version = (record.version or 0) + 1
    else:
        record = MonthlyRevenue(
            merchant_id=merchant_id,
            stat_year=year,
            stat_month=month,
            **data,
            is_finalized=0,
            version=0,
        )
        db.add(record)

    db.commit()
    print(f"  [OK]   {year}-{month:02d} - orders={data['total_orders']}, amount={data['total_amount']}")
    return 1, 0, 0


def main():
    parser = argparse.ArgumentParser(
        description="Phase 3C 批量回填报表工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--merchant-id", type=int, required=True, help="商户 ID")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--year", type=int, help="统计年份（月报模式）")
    parser.add_argument("--month", type=int, help="统计月份（月报模式，1-12）")
    parser.add_argument("--type", type=str, choices=["daily", "monthly", "all"], default="all", help="回填类型")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")

    args = parser.parse_args()

    if args.type in ("daily", "all"):
        if not args.start_date or not args.end_date:
            parser.error("--start-date and --end-date are required for daily/all type")

    if args.type == "monthly":
        if not args.year or not args.month:
            parser.error("--year and --month are required for monthly type")

    # 解析日期
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"[Backfill {mode}] Merchant ID: {args.merchant_id}")
    print(f"[Backfill] Type: {args.type}")

    db = SessionLocal()
    try:
        # 验证商户存在
        merchant = db.query(Merchant).filter(Merchant.id == args.merchant_id).first()
        if not merchant:
            print(f"[ERROR] Merchant {args.merchant_id} not found")
            sys.exit(1)
        print(f"[Backfill] Merchant: {merchant.name} ({merchant.status})")
        print("-" * 60)

        total_processed = 0
        total_skipped = 0
        total_errors = 0

        if args.type in ("daily", "all"):
            print(f"[Daily Backfill] {start_date} ~ {end_date}")
            processed, skipped, errors = backfill_daily(
                db, args.merchant_id, start_date, end_date, args.dry_run
            )
            total_processed += processed
            total_skipped += skipped
            total_errors += errors

        if args.type in ("monthly", "all"):
            if args.type == "monthly":
                year = args.year
                month = args.month
            else:
                # 从 start_date 和 end_date 推断所有涉及月份
                print(f"[Monthly Backfill] from {start_date} to {end_date}")
                current = start_date
                while current <= end_date:
                    processed, skipped, errors = backfill_monthly(
                        db, args.merchant_id, current.year, current.month, args.dry_run
                    )
                    total_processed += processed
                    total_skipped += skipped
                    total_errors += errors
                    # 跳到下月
                    if current.month == 12:
                        current = date(current.year + 1, 1, 1)
                    else:
                        current = date(current.year, current.month + 1, 1)
                current = None

            if current is not None:
                processed, skipped, errors = backfill_monthly(
                    db, args.merchant_id, year, month, args.dry_run
                )
                total_processed += processed
                total_skipped += skipped
                total_errors += errors

        print("-" * 60)
        print(f"[Backfill Summary] processed={total_processed}, skipped={total_skipped}, errors={total_errors}")

        if args.dry_run:
            print("[Backfill] DRY-RUN completed. Run without --dry-run to actually write data.")

        if total_errors > 0:
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
