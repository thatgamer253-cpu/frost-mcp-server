{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Add custom middleware for CORS, error handling, etc.
add_middleware(app)

# Mount static files directory
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="frontend/templates")

# Global instances for background safety services
health_monitor: Optional[HealthMonitor] = None
watchdog: Optional[Watchdog] = None
backup_service: Optional[BackupService] = None

async def seed_initial_data(db: AsyncSession):
    """
    Seeds initial data into the database if it's empty.
    This includes a superuser, a regular user, and some demo portfolio data.
    """
    try:
        # Check if any user exists to prevent re-seeding
        existing_user = await crud_user.get_user_by_email(db, email=settings.FIRST_SUPERUSER_EMAIL)
        if not existing_user:
            logger.info("Seeding initial superuser...")
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER_EMAIL,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                full_name="Admin User",
                is_superuser=True,
                is_active=True,
            )
            await crud_user.create_user(db, user_in=user_in)
            logger.info("Superuser seeded successfully.")

            # Create a regular user for demo purposes
            logger.info("Seeding initial regular user...")
            regular_user_in = UserCreate(
                email="demo_user@app.com", # Using a generic internal-looking email
                password="securepassword",
                full_name="Demo User",
                is_superuser=False,
                is_active=True,
            )
            await crud_user.create_user(db, user_in=regular_user_in)
            logger.info("Regular user seeded successfully.")

            # Retrieve the demo user to link assets/transactions
            demo_user = await crud_user.get_user_by_email(db, email="demo_user@app.com")
            if demo_user:
                logger.info("Seeding initial demo assets and transactions for demo user...")
                # Create some demo assets
                asset1_in = AssetCreate(
                    symbol="AAPL",
                    name="Apple Inc.",
                    asset_type="Stock",
                    quantity=10.5,
                    purchase_price=150.00,
                    purchase_date="2023-01-15",
                    user_id=demo_user.id
                )
                asset1 = await crud_asset.create_asset(db, asset_in=asset1_in)

                asset2_in = AssetCreate(
                    symbol="GOOGL",
                    name="Alphabet Inc. (Class A)",
                    asset_type="Stock",
                    quantity=5.0,
                    purchase_price=100.00,
                    purchase_date="2023-03-01",
                    user_id=demo_user.id
                )
                asset2 = await crud_asset.create_asset(db, asset_in=asset2_in)

                # Create some demo transactions
                transaction1_in = TransactionCreate(
                    asset_id=asset1.id,
                    transaction_type="BUY",
                    quantity=10.5,
                    price=150.00,
                    transaction_date="2023-01-15",
                    user_id=demo_user.id
                )
                await crud_transaction.create_transaction(db, transaction_in=transaction1_in)

                transaction2_in = TransactionCreate(
                    asset_id=asset2.id,
                    transaction_type="BUY",
                    quantity=5.0,
                    price=100.00,
                    transaction_date="2023-03-01",
                    user_id=demo_user.id
                )
                await crud_transaction.create_transaction(db, transaction_in=transaction2_in)

                # Create a demo watchlist item
                watchlist_in = WatchlistCreate(
                    symbol="MSFT",
                    name="Microsoft Corp.",
                    user_id=demo_user.id
                )
                await crud_watchlist.create_watchlist_item(db, watchlist_in=watchlist_in)

                logger.info("Demo assets, transactions, and watchlist seeded successfully.")
            else:
                logger.warning("Demo user not found after creation, skipping demo asset/transaction seeding.")
        else:
            logger.info("Superuser already exists, skipping initial data seeding.")

    except Exception as e:
        logger.error(f"Error seeding initial data: {e}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """
    Handles application startup events:
    - Initializes the database connection.
    - Starts background health monitoring and watchdog services.
    - Initializes and starts the backup service.
    - Performs initial data seeding if enabled.
    """
    global health_monitor, watchdog, backup_service
    logger.info(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    # Mask sensitive parts of the DB URL for logging
    db_url_display = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
    logger.info(f"Database URL: {db_url_display}")

    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}. Application may not function correctly.", exc_info=True)
        # In a production environment, you might want to raise an exception or exit here.

    # Ensure backup directory exists
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)

    # Initialize and start HealthMonitor in a background task
    health_monitor = HealthMonitor(
        db_url=settings.DATABASE_URL,
        check_interval_seconds=settings.HEALTH_CHECK_INTERVAL_SECONDS
    )
    asyncio.create_task(health_monitor.start())
    logger.info("HealthMonitor started.")

    # Initialize and start Watchdog in a background task
    watchdog = Watchdog(
        disk_threshold_percent=settings.WATCHDOG_DISK_THRESHOLD_PERCENT,
        memory_threshold_percent=settings.WATCHDOG_MEMORY_THRESHOLD_PERCENT,
        check_interval_seconds=settings.WATCHDOG_CHECK_INTERVAL_SECONDS
    )
    asyncio.create_task(watchdog.start())
    logger.info("Watchdog started.")

    # Initialize BackupService and start periodic backups
    backup_service = BackupService(
        backup_dir=settings.BACKUP_DIR,
        db_url=settings.DATABASE_URL,
        backup_interval_seconds=settings.BACKUP_INTERVAL_SECONDS
    )
    asyncio.create_task(backup_service.start_periodic_backup())
    logger.info("BackupService initialized and periodic backup started.")

    # Seed initial data if enabled in settings
    if settings.SEED_DATABASE:
        logger.info("Attempting to seed initial data...")
        # Acquire a database session for seeding
        async for db_session in get_db():
            await seed_initial_data(db_session)
            break # Only need one session for this one-off task
    else:
        logger.info("Database seeding is disabled by configuration.")

    logger.info(f"✅ {settings.PROJECT_NAME} startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Handles application shutdown events:
    - Stops all background safety services.
    - Performs a final database backup.
    """
    global health_monitor, watchdog, backup_service
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")

    # Stop HealthMonitor gracefully
    if health_monitor:
        await health_monitor.stop()
        logger.info("HealthMonitor stopped.")
    
    # Stop Watchdog gracefully
    if watchdog:
        await watchdog.stop()
        logger.info("Watchdog stopped.")
    
    # Stop periodic backups and perform a final backup
    if backup_service:
        await backup_service.stop_periodic_backup()
        logger.info("BackupService periodic backup stopped.")
        try:
            await backup_service.perform_backup()
            logger.info("Final backup performed successfully on shutdown.")
        except Exception as e:
            logger.error(f"Failed to perform final backup on shutdown: {e}", exc_info=True)

    logger.info(f"👋 {settings.PROJECT_NAME} shutdown complete.")


# Include API routers under the specified API prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", response_class=HTMLResponse, name="root")
async def read_root(request: Request):
    """
    Serves the main landing page of the application.
    The frontend JavaScript will handle redirection to login/dashboard based on authentication status.
    """
    return templates.TemplateResponse("index.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """
    Serves the user login page.
    """
    return templates.TemplateResponse("auth/login.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/register", response_class=HTMLResponse, name="register")
async def register_page(request: Request):
    """
    Serves the user registration page.
    """
    return templates.TemplateResponse("auth/register.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard_page(request: Request):
    """
    Serves the user dashboard page.
    In a production setup, this route would typically be protected by authentication.
    """
    return templates.TemplateResponse("dashboard/index.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/portfolio", response_class=HTMLResponse, name="portfolio")
async def portfolio_page(request: Request):
    """
    Serves the user's portfolio management page.
    """
    return templates.TemplateResponse("portfolio/index.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/portfolio/add", response_class=HTMLResponse, name="add_asset")
async def add_asset_page(request: Request):
    """
    Serves the page for adding a new asset to the portfolio.
    """
    return templates.TemplateResponse("portfolio/add_asset.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/portfolio/edit/{asset_id}", response_class=HTMLResponse, name="edit_asset")
async def edit_asset_page(request: Request, asset_id: int):
    """
    Serves the page for editing an existing portfolio asset.
    The `asset_id` is passed to the template for dynamic content loading.
    """
    return templates.TemplateResponse("portfolio/edit_asset.html", {"request": request, "project_name": settings.PROJECT_NAME, "asset_id": asset_id})

@app.get("/transactions", response_class=HTMLResponse, name="transactions")
async def transactions_page(request: Request):
    """
    Serves the page displaying the user's transaction history.
    """
    return templates.TemplateResponse("transactions/index.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/watchlist", response_class=HTMLResponse, name="watchlist")
async def watchlist_page(request: Request):
    """
    Serves the user's watchlist page.
    """
    return templates.TemplateResponse("watchlist/index.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/profile", response_class=HTMLResponse, name="profile")
async def profile_page(request: Request):
    """
    Serves the user's profile viewing page.
    """
    return templates.TemplateResponse("user/profile.html", {"request": request, "project_name": settings.PROJECT_NAME})

@app.get("/settings", response_class=HTMLResponse, name="settings")
async def settings_page(request: Request):
    """
    Serves the user's account settings page.
    """
    return templates.TemplateResponse("user/settings.html", {"request": request, "project_name": settings.PROJECT_NAME}