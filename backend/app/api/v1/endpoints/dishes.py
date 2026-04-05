from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.dish import Dish
from app.models.category import Category
from app.models.merchant import Merchant
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishToggleResponse
from app.dependencies import get_current_merchant

router = APIRouter()


@router.get("", response_model=List[DishResponse])
def list_dishes(
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """获取当前商户的所有菜品（可按category_id筛选）"""
    query = db.query(Dish).filter(Dish.merchant_id == current_merchant.id)
    
    if category_id is not None:
        # 验证分类是否属于当前商户
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.merchant_id == current_merchant.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在"
            )
        query = query.filter(Dish.category_id == category_id)
    
    dishes = query.order_by(Dish.id).all()
    return dishes


@router.post("", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
def create_dish(
    dish_data: DishCreate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """创建新菜品"""
    # 验证分类是否属于当前商户
    category = db.query(Category).filter(
        Category.id == dish_data.category_id,
        Category.merchant_id == current_merchant.id
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    dish = Dish(
        merchant_id=current_merchant.id,
        category_id=dish_data.category_id,
        name=dish_data.name,
        description=dish_data.description or "",
        price=dish_data.price,
        image_url=dish_data.image_url or "",
        is_available=dish_data.is_available,
    )
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


@router.put("/{dish_id}", response_model=DishResponse)
def update_dish(
    dish_id: int,
    dish_data: DishUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """更新菜品"""
    dish = db.query(Dish).filter(
        Dish.id == dish_id,
        Dish.merchant_id == current_merchant.id
    ).first()
    
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在"
        )
    
    # 如果更新了分类ID，验证分类是否属于当前商户
    if dish_data.category_id is not None:
        category = db.query(Category).filter(
            Category.id == dish_data.category_id,
            Category.merchant_id == current_merchant.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在"
            )
    
    if dish_data.name is not None:
        dish.name = dish_data.name
    if dish_data.description is not None:
        dish.description = dish_data.description
    if dish_data.price is not None:
        dish.price = dish_data.price
    if dish_data.category_id is not None:
        dish.category_id = dish_data.category_id
    if dish_data.image_url is not None:
        dish.image_url = dish_data.image_url
    if dish_data.is_available is not None:
        dish.is_available = dish_data.is_available
    
    db.commit()
    db.refresh(dish)
    return dish


@router.patch("/{dish_id}/toggle-available", response_model=DishToggleResponse)
def toggle_dish_available(
    dish_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """切换菜品上下架状态"""
    dish = db.query(Dish).filter(
        Dish.id == dish_id,
        Dish.merchant_id == current_merchant.id
    ).first()
    
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在"
        )
    
    dish.is_available = not dish.is_available
    db.commit()
    db.refresh(dish)
    
    action = "上架" if dish.is_available else "下架"
    return DishToggleResponse(
        id=dish.id,
        is_available=dish.is_available,
        message=f"菜品已{action}"
    )


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(
    dish_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    """删除菜品"""
    dish = db.query(Dish).filter(
        Dish.id == dish_id,
        Dish.merchant_id == current_merchant.id
    ).first()
    
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在"
        )
    
    db.delete(dish)
    db.commit()
    return None
