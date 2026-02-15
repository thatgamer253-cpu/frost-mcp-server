"""
FastAPI application — Inventory & Analytics Dashboard backend.

Endpoints:
  GET  /                   Health check
  GET  /products           All products with category info
  GET  /categories         All categories
  GET  /low-stock          Products where current_stock < 0.1 × initial_capacity
  GET  /stock-logs/{id}    Stock change history for a product
  GET  /analytics          Summary statistics
  POST /seed               Populate demo data
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, get_db, Base
from . import crud, schemas, models
from .seed import seed_database


# ── Create tables on startup ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables when the app starts."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Warehouse Inventory & Analytics API",
    description="High-volume warehouse inventory management with low-stock alerting.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Next.js frontend) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "Warehouse Inventory API"}


@app.get("/products", response_model=List[schemas.ProductResponse], tags=["Products"])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return all products with stock information."""
    return crud.get_products(db, skip=skip, limit=limit)


@app.get("/products/{product_id}", response_model=schemas.ProductResponse, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Return a single product by ID."""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/categories", response_model=List[schemas.CategoryResponse], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    """Return all categories."""
    return crud.get_categories(db)


@app.get("/low-stock", response_model=List[schemas.LowStockAlert], tags=["Alerts"])
def get_low_stock(db: Session = Depends(get_db)):
    """
    Return products where current_stock < 0.1 × initial_capacity.

    The custom formula identifies items below 10% of their initial
    warehouse capacity. Returns an empty list [] when all items
    are sufficiently stocked.
    """
    return crud.get_low_stock_products(db)


@app.get(
    "/stock-logs/{product_id}",
    response_model=List[schemas.StockLogResponse],
    tags=["Stock Logs"],
)
def get_stock_logs(product_id: int, db: Session = Depends(get_db)):
    """Return stock change history for a specific product."""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.get_stock_logs(db, product_id)


@app.get("/analytics", response_model=schemas.AnalyticsSummary, tags=["Analytics"])
def get_analytics(db: Session = Depends(get_db)):
    """Return dashboard analytics: totals, health percentage, category breakdown."""
    return crud.get_analytics(db)


@app.post("/seed", tags=["Admin"])
def seed_data(db: Session = Depends(get_db)):
    """Populate the database with demo data. Clears existing data first."""
    result = seed_database(db)
    return {"message": "Database seeded successfully", "summary": result}
