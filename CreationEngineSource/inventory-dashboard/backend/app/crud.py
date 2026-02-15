"""
CRUD operations for the warehouse inventory system.
Contains the core low-stock calculation logic.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from . import models, schemas


# ── Categories ────────────────────────────────────────────────────

def get_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).order_by(models.Category.name).all()


def get_category(db: Session, category_id: int) -> models.Category | None:
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def create_category(db: Session, category: schemas.CategoryCreate) -> models.Category:
    db_cat = models.Category(**category.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


# ── Products ──────────────────────────────────────────────────────

def get_products(db: Session, skip: int = 0, limit: int = 100) -> List[models.Product]:
    return (
        db.query(models.Product)
        .order_by(models.Product.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# ── Low Stock Query ───────────────────────────────────────────────
#
# Core formula:  current_stock < 0.1 * initial_capacity
# This identifies products that have fallen below 10% of their
# initial warehouse capacity — a critical restocking threshold.
#

def get_low_stock_products(db: Session) -> List[schemas.LowStockAlert]:
    """
    Returns all products where:
        current_stock < 0.1 × initial_capacity

    This is the custom formula for the /low-stock endpoint.
    The calculation is pushed to the database for efficiency.
    """
    results = (
        db.query(models.Product, models.Category.name.label("category_name"))
        .join(models.Category, models.Product.category_id == models.Category.id)
        .filter(models.Product.current_stock < 0.1 * models.Product.initial_capacity)
        .order_by(models.Product.current_stock.asc())
        .all()
    )

    alerts = []
    for product, category_name in results:
        alerts.append(schemas.LowStockAlert(
            id=product.id,
            name=product.name,
            sku=product.sku,
            current_stock=product.current_stock,
            initial_capacity=product.initial_capacity,
            stock_percentage=product.stock_percentage,
            category_name=category_name,
        ))

    return alerts


# ── Stock Logs ────────────────────────────────────────────────────

def get_stock_logs(db: Session, product_id: int) -> List[models.StockLog]:
    return (
        db.query(models.StockLog)
        .filter(models.StockLog.product_id == product_id)
        .order_by(models.StockLog.timestamp.desc())
        .all()
    )


def create_stock_log(db: Session, log: schemas.StockLogCreate) -> models.StockLog:
    db_log = models.StockLog(**log.model_dump())
    db.add(db_log)
    # Also update the product's current_stock
    product = get_product(db, log.product_id)
    if product:
        if log.log_type == "IN":
            product.current_stock += log.change_amount
        elif log.log_type == "OUT":
            product.current_stock -= log.change_amount
        else:  # ADJUSTMENT
            product.current_stock = log.change_amount
    db.commit()
    db.refresh(db_log)
    return db_log


# ── Analytics ─────────────────────────────────────────────────────

def get_analytics(db: Session) -> schemas.AnalyticsSummary:
    products = db.query(models.Product).all()
    categories = db.query(models.Category).all()
    low_stock = get_low_stock_products(db)

    total_value = sum(p.current_stock * p.unit_price for p in products)
    healthy = sum(1 for p in products if not p.is_low_stock)
    health_pct = round((healthy / len(products) * 100), 2) if products else 100.0

    cat_counts = []
    for cat in categories:
        count = db.query(func.count(models.Product.id)).filter(
            models.Product.category_id == cat.id
        ).scalar()
        cat_counts.append(schemas.CategoryWithCount(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            product_count=count,
        ))

    return schemas.AnalyticsSummary(
        total_products=len(products),
        total_categories=len(categories),
        low_stock_count=len(low_stock),
        total_stock_value=round(total_value, 2),
        categories=cat_counts,
        stock_health_percentage=health_pct,
    )
