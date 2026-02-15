"""
SQLAlchemy ORM models for the warehouse inventory system.

Relational schema:
  Categories  1 ──── * Products  1 ──── * StockLogs
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


class LogType(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationship
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    initial_capacity = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("Category", back_populates="products")
    stock_logs = relationship("StockLog", back_populates="product", cascade="all, delete-orphan")

    @property
    def stock_percentage(self) -> float:
        """Current stock as a percentage of initial capacity."""
        if self.initial_capacity == 0:
            return 0.0
        return round((self.current_stock / self.initial_capacity) * 100, 2)

    @property
    def is_low_stock(self) -> bool:
        """True when current_stock < 0.1 * initial_capacity (below 10%)."""
        return self.current_stock < 0.1 * self.initial_capacity

    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', stock={self.current_stock}/{self.initial_capacity})>"


class StockLog(Base):
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    change_amount = Column(Integer, nullable=False)
    log_type = Column(String(20), nullable=False, default=LogType.IN.value)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)

    # Relationship
    product = relationship("Product", back_populates="stock_logs")

    def __repr__(self):
        return f"<StockLog(id={self.id}, product_id={self.product_id}, change={self.change_amount})>"
