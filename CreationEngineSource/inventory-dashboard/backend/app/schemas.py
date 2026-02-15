"""
Pydantic schemas for API request/response serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ── Category Schemas ──────────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CategoryWithCount(CategoryResponse):
    product_count: int = 0


# ── Product Schemas ───────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str
    sku: str
    category_id: int
    initial_capacity: int
    current_stock: int = 0
    unit_price: float = 0.0


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_percentage: float
    is_low_stock: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductWithCategory(ProductResponse):
    category: CategoryResponse


# ── Low Stock Alert Schema ────────────────────────────────────────

class LowStockAlert(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sku: str
    current_stock: int
    initial_capacity: int
    stock_percentage: float
    category_name: str


# ── StockLog Schemas ──────────────────────────────────────────────

class StockLogBase(BaseModel):
    product_id: int
    change_amount: int
    log_type: str = "IN"
    notes: Optional[str] = None


class StockLogCreate(StockLogBase):
    pass


class StockLogResponse(StockLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime


# ── Analytics Schema ──────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_products: int
    total_categories: int
    low_stock_count: int
    total_stock_value: float
    categories: List[CategoryWithCount]
    stock_health_percentage: float
