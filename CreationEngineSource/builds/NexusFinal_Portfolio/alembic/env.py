{e}. Ensure backend directory is in PYTHONPATH.")
    sys.exit(1)

# Setup logging for Alembic
setup_logging()
logger = get_logger(__name__)

# this is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python's standard logging.
# This uses the logging configuration from alembic.ini.
fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support.
# This tells Alembic which SQLAlchemy models to track for schema changes.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    The metadata is made available to the context as a non-db specific object.
    When completing an offline migration, the output is written to a file.
    """
    # Get the database URL from alembic.ini, but prioritize application settings
    url = config.get_main_option("sqlalchemy.url")
    if settings.DATABASE_URL:
        url = settings.DATABASE_URL
        logger.info(f"Using DATABASE_URL from settings for offline migrations: {url}")
    else:
        logger.warning("DATABASE_URL not found in settings, falling back to alembic.ini URL for offline migrations.")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Enable type comparison for autogenerate
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Helper function to run migrations within a given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True, # Enable type comparison for autogenerate
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario, we need to create an AsyncEngine
    and associate an asynchronous connection with the context.
    """
    # Get the database URL from alembic.ini, but prioritize application settings
    connectable_url = config.get_main_option("sqlalchemy.url")
    if settings.DATABASE_URL:
        connectable_url = settings.DATABASE_URL
        logger.info(f"Using DATABASE_URL from settings for online migrations: {connectable_url}")
    else:
        logger.error("DATABASE_URL not found in settings. Cannot run online migrations without a database URL.")
        raise ValueError("DATABASE_URL is not configured for online migrations.")

    # Create an async engine using the configured URL
    # NullPool is often used for Alembic to avoid connection pooling issues during schema changes.
    engine = create_async_engine(
        connectable_url,
        poolclass=pool.NullPool,
        future=True # Use SQLAlchemy 2.0 style
    )

    try:
        async with engine.connect() as connection:
            # Run synchronous migration operations within the async connection
            await connection.run_sync(do_run_migrations)
    except Exception as e:
        logger.critical(f"Error during online migrations: {e}", exc_info=True)
        raise # Re-raise to ensure the script exits with an error
    finally:
        # Ensure the engine is properly disposed after migrations
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    try:
        asyncio.run(run_migrations_online())
    except Exception as e:
        logger.critical(f"Alembic migration failed: {e}