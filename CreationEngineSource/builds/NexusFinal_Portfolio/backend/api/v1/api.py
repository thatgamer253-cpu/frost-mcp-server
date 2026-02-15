from fastapi import APIRouter

from backend.api.v1.endpoints import auth
from backend.api.v1.endpoints import dashboard
from backend.api.v1.endpoints import health
from backend.api.v1.endpoints import market
from backend.api.v1.endpoints import portfolio
from backend.api.v1.endpoints import transactions
from backend.api.v1.endpoints import users
from backend.api.v1.endpoints import watchlist

# Create the main API router for version 1
# This router will aggregate all specific endpoint routers for API v1.
api_router = APIRouter()

# Include individual endpoint routers.
# Each router is mounted with a specific prefix and tags for OpenAPI documentation.
# The prefixes here are relative to the base path where `api_router` itself will be mounted
# in the main FastAPI application (e.g., if `api_router` is mounted at `/api/v1`,
# then `/health` here becomes `/api/v1/health`).

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(market.router, prefix="/market", tags=["Market Data"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])