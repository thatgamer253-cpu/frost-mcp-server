# 📦 Warehouse Inventory & Analytics Dashboard

A full-stack real-time inventory monitoring and analytics dashboard for high-volume warehouse operations.

## Architecture

| Layer        | Technology            | Port   |
| ------------ | --------------------- | ------ |
| **Frontend** | Next.js 14 (React 18) | `3000` |
| **Backend**  | FastAPI (Python 3.11) | `8000` |
| **Database** | PostgreSQL 15         | `5432` |

## Quick Start

```bash
chmod +x setup.sh
./setup.sh
```

This single command will:

1. Create `.env` from `.env.example`
2. Build all Docker containers
3. Wait for services to be healthy
4. Seed the database with demo data
5. Print the dashboard URL

## Access Points

| Service       | URL                                                      |
| ------------- | -------------------------------------------------------- |
| **Dashboard** | [http://localhost:3000](http://localhost:3000)           |
| **API**       | [http://localhost:8000](http://localhost:8000)           |
| **API Docs**  | [http://localhost:8000/docs](http://localhost:8000/docs) |

## Data Model

```
Categories 1────* Products 1────* StockLogs
```

- **Categories**: Organizational groupings (Electronics, Safety, etc.)
- **Products**: Items with `initial_capacity` and `current_stock`
- **StockLogs**: Audit trail of all stock changes (IN/OUT/ADJUSTMENT)

## Key Endpoint: `/low-stock`

Returns products where:

```
current_stock < 0.1 × initial_capacity
```

This identifies items below **10% of their initial warehouse capacity** — a critical restocking threshold.

**Response**: `[]` when all items are healthy.

## Frontend Features

- **Stock Alert Panel**: Turns **RED** when low-stock items are found, shows **GREEN "All Clear"** when empty
- **Analytics Cards**: Total products, categories, low-stock count, total stock value
- **Product Table**: Sortable with color-coded stock level bars
- **Health Gauge**: Circular SVG gauge showing overall warehouse health
- **Auto-Refresh**: Dashboard data refreshes every 30 seconds

## Manual Commands

```bash
# Start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Reset database
docker-compose down -v
docker-compose up --build -d
curl -X POST http://localhost:8000/seed
```

## Requirements

- [Docker](https://docs.docker.com/get-docker/) (20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
