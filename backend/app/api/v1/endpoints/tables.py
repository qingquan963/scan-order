from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import io
import qrcode
from app.database import get_db
from app.models.table import DiningTable
from app.models.order import Order
from app.models.merchant import Merchant
from app.schemas.table import TableCreate, TableUpdate, TableResponse
from app.dependencies import get_current_merchant
from app.config import Settings

settings = Settings()
router = APIRouter()


@router.get("", response_model=List[TableResponse])
def list_tables(
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取当前商户的所有桌台列表"""
    tables = db.query(DiningTable).filter(
        DiningTable.merchant_id == current_merchant.id
    ).order_by(DiningTable.code).all()
    return tables


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    table_data: TableCreate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """创建新桌台"""
    # 检查code是否已存在
    existing = db.query(DiningTable).filter(
        DiningTable.code == table_data.code,
        DiningTable.merchant_id == current_merchant.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="桌台编码已存在"
        )
    
    table = DiningTable(
        merchant_id=current_merchant.id,
        code=table_data.code,
        name=table_data.name,
        capacity=table_data.capacity,
        status=table_data.status
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@router.get("/{table_id}", response_model=TableResponse)
def get_table(
    table_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取桌台详情"""
    table = db.query(DiningTable).filter(
        DiningTable.id == table_id,
        DiningTable.merchant_id == current_merchant.id
    ).first()
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="桌台不存在"
        )
    
    return table


@router.put("/{table_id}", response_model=TableResponse)
def update_table(
    table_id: int,
    table_data: TableUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """更新桌台"""
    table = db.query(DiningTable).filter(
        DiningTable.id == table_id,
        DiningTable.merchant_id == current_merchant.id
    ).first()
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="桌台不存在"
        )
    
    # 如果更新code，检查是否与其他桌台冲突
    if table_data.code is not None and table_data.code != table.code:
        existing = db.query(DiningTable).filter(
            DiningTable.code == table_data.code,
            DiningTable.merchant_id == current_merchant.id,
            DiningTable.id != table_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="桌台编码已存在"
            )
        table.code = table_data.code
    
    if table_data.name is not None:
        table.name = table_data.name
    if table_data.capacity is not None:
        table.capacity = table_data.capacity
    if table_data.status is not None:
        table.status = table_data.status
    
    db.commit()
    db.refresh(table)
    return table


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """删除桌台"""
    table = db.query(DiningTable).filter(
        DiningTable.id == table_id,
        DiningTable.merchant_id == current_merchant.id
    ).first()
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="桌台不存在"
        )
    
    # 检查是否有订单关联
    order_count = db.query(Order).filter(
        Order.table_id == table_id
    ).count()
    
    if order_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该桌台存在关联订单，无法删除"
        )
    
    db.delete(table)
    db.commit()
    return None


@router.get("/{table_id}/qrcode")
def get_table_qrcode(
    table_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """生成桌台 PNG 二维码"""
    table = db.query(DiningTable).filter(
        DiningTable.id == table_id,
        DiningTable.merchant_id == current_merchant.id
    ).first()
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="桌台不存在"
        )
    
    # 构建二维码URL
    if settings.FRONTEND_PUBLIC_URL:
        qr_url = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/customer/h5?table_id={table.id}"
    else:
        # 相对URL，适用于开发环境
        qr_url = f"/customer/h5?table_id={table.id}"
    
    # 生成二维码图片
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="table-{table.code}-qrcode.png"'
        }
    )