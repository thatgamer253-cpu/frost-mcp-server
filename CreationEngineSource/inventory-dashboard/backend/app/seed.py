"""
Seed data for the warehouse inventory system.
Populates Categories, Products, and StockLogs with realistic demo data.
Includes products both above AND below the 10% low-stock threshold.
"""

from datetime import datetime, timezone, timedelta
import random
from sqlalchemy.orm import Session

from .models import Category, Product, StockLog, LogType


def seed_database(db: Session) -> dict:
    """Populate the database with demo data. Returns summary of seeded records."""

    # ── Clear existing data ───────────────────────────────────────
    db.query(StockLog).delete()
    db.query(Product).delete()
    db.query(Category).delete()
    db.commit()

    # ── Categories ────────────────────────────────────────────────
    categories_data = [
        {"name": "Electronics", "description": "Consumer electronics, cables, adapters"},
        {"name": "Safety Equipment", "description": "PPE, fire extinguishers, first aid"},
        {"name": "Raw Materials", "description": "Steel, lumber, plastics, composites"},
        {"name": "Packaging", "description": "Boxes, tape, bubble wrap, pallets"},
        {"name": "Cleaning Supplies", "description": "Solvents, wipes, mops, detergent"},
    ]

    categories = []
    for data in categories_data:
        cat = Category(**data)
        db.add(cat)
        categories.append(cat)
    db.flush()

    # ── Products ──────────────────────────────────────────────────
    # Mix of healthy stock and critically low stock items
    products_data = [
        # Electronics — some healthy, some critical
        {"name": "USB-C Charging Cable",     "sku": "ELEC-001", "category": 0, "capacity": 500,  "stock": 423,  "price": 8.99},
        {"name": "HDMI Adapter",             "sku": "ELEC-002", "category": 0, "capacity": 300,  "stock": 12,   "price": 14.50},   # LOW: 12 < 30
        {"name": "Wireless Mouse",           "sku": "ELEC-003", "category": 0, "capacity": 200,  "stock": 5,    "price": 24.99},   # LOW: 5 < 20
        {"name": "Power Strip 6-Outlet",     "sku": "ELEC-004", "category": 0, "capacity": 150,  "stock": 134,  "price": 19.99},

        # Safety Equipment
        {"name": "Hard Hat (Yellow)",        "sku": "SAFE-001", "category": 1, "capacity": 1000, "stock": 780,  "price": 12.00},
        {"name": "Safety Goggles",           "sku": "SAFE-002", "category": 1, "capacity": 800,  "stock": 50,   "price": 6.50},    # LOW: 50 < 80
        {"name": "Fire Extinguisher ABC",    "sku": "SAFE-003", "category": 1, "capacity": 100,  "stock": 3,    "price": 45.00},   # LOW: 3 < 10
        {"name": "First Aid Kit Deluxe",     "sku": "SAFE-004", "category": 1, "capacity": 200,  "stock": 188,  "price": 32.00},

        # Raw Materials
        {"name": "Steel Sheet 4x8 ft",      "sku": "RAW-001",  "category": 2, "capacity": 400,  "stock": 350,  "price": 89.00},
        {"name": "2x4 Lumber (8 ft)",        "sku": "RAW-002",  "category": 2, "capacity": 2000, "stock": 120,  "price": 5.50},    # LOW: 120 < 200
        {"name": "ABS Plastic Pellets (kg)", "sku": "RAW-003",  "category": 2, "capacity": 5000, "stock": 4200, "price": 3.20},
        {"name": "Carbon Fiber Sheet",       "sku": "RAW-004",  "category": 2, "capacity": 100,  "stock": 2,    "price": 199.99},  # LOW: 2 < 10

        # Packaging
        {"name": "Corrugated Box 12x12",     "sku": "PKG-001",  "category": 3, "capacity": 3000, "stock": 2100, "price": 1.20},
        {"name": "Packing Tape Roll",        "sku": "PKG-002",  "category": 3, "capacity": 500,  "stock": 45,   "price": 3.99},    # LOW: 45 < 50
        {"name": "Bubble Wrap 100ft",        "sku": "PKG-003",  "category": 3, "capacity": 200,  "stock": 178,  "price": 15.00},
        {"name": "Wooden Pallet",            "sku": "PKG-004",  "category": 3, "capacity": 600,  "stock": 540,  "price": 22.00},

        # Cleaning Supplies
        {"name": "Industrial Degreaser 1gal","sku": "CLN-001",  "category": 4, "capacity": 300,  "stock": 10,   "price": 18.50},   # LOW: 10 < 30
        {"name": "Microfiber Cloth (50pk)",  "sku": "CLN-002",  "category": 4, "capacity": 400,  "stock": 320,  "price": 12.00},
        {"name": "Floor Mop Heavy Duty",     "sku": "CLN-003",  "category": 4, "capacity": 80,   "stock": 65,   "price": 28.00},
        {"name": "Disinfectant Spray 32oz",  "sku": "CLN-004",  "category": 4, "capacity": 600,  "stock": 15,   "price": 7.99},    # LOW: 15 < 60
    ]

    products = []
    for data in products_data:
        product = Product(
            name=data["name"],
            sku=data["sku"],
            category_id=categories[data["category"]].id,
            initial_capacity=data["capacity"],
            current_stock=data["stock"],
            unit_price=data["price"],
        )
        db.add(product)
        products.append(product)
    db.flush()

    # ── Stock Logs ────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    log_count = 0
    for product in products:
        # Generate 3-8 historical stock log entries per product
        num_logs = random.randint(3, 8)
        for i in range(num_logs):
            days_ago = random.randint(1, 90)
            log_type = random.choice([LogType.IN.value, LogType.OUT.value])
            amount = random.randint(5, 100)
            log = StockLog(
                product_id=product.id,
                change_amount=amount,
                log_type=log_type,
                timestamp=now - timedelta(days=days_ago, hours=random.randint(0, 23)),
                notes=f"{'Received shipment' if log_type == 'IN' else 'Fulfilled order'} — batch #{random.randint(1000, 9999)}",
            )
            db.add(log)
            log_count += 1

    db.commit()

    return {
        "categories": len(categories_data),
        "products": len(products_data),
        "stock_logs": log_count,
        "low_stock_items": sum(
            1 for p in products_data if p["stock"] < 0.1 * p["capacity"]
        ),
    }
