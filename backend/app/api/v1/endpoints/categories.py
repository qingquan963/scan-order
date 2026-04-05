from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.category import Category
from app.models.dish import Dish
from app.models.merchant import Merchant
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.dependencies import get_current_merchant

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    categories = db.query(Category).filter(
        Category.merchant_id == current_merchant.id
    ).order_by(Category.sort_order, Category.id).all()
    return categories


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    category = Category(
        merchant_id=current_merchant.id,
        name=category_data.name,
        sort_order=category_data.sort_order
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.merchant_id == current_merchant.id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    if category_data.name is not None:
        category.name = category_data.name
    if category_data.sort_order is not None:
        category.sort_order = category_data.sort_order
    
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_merchant: Merchant = Depends(get_current_merchant)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.merchant_id == current_merchant.id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    # 检查是否有菜品关联
    dish_count = db.query(Dish).filter(Dish.category_id == category_id).count()
    if dish_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"该分类下有 {dish_count} 个菜品，请先删除菜品"
        )
    
    db.delete(category)
    db.commit()
    return None
