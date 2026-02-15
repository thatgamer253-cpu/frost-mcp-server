{e}", exc_info=True)
        return HealthCheckDetail(
            component="database",
            status=HealthStatus.DOWN,
            message=f"Database operational error: {e}"
        )
    except SQLAlchemyError as e:
        # Catch any other SQLAlchemy-related errors
        logger.error(f"Database SQLAlchemy error during health check: {e}", exc_info=True)
        return HealthCheckDetail(
            component="database",
            status=HealthStatus.DOWN,
            message=f"Database connection failed: {e}"
        )
    except Exception as e:
        # Catch any other unexpected errors during the database check
        logger.error(f"An unexpected error occurred during database check: {e}", exc_info=True)
        return HealthCheckDetail(
            component="database",
            status=HealthStatus.DOWN,
            message=f"Unexpected error during database check: {e}"
        )

def check_disk_usage() -> HealthCheckDetail:
    """
    Checks the disk usage of the root partition where the application is running.
    Compares current usage against a configured threshold.
    Anticipates failures like `FileNotFoundError` or other `OSError`.
    """
    try:
        # Get disk usage for the current working directory's partition.
        # This typically reflects the root partition in a containerized environment.
        total, used, free = shutil.disk_usage(os.getcwd())
        used_percent = (used / total) * 100 if total > 0 else 0

        status_enum = HealthStatus.UP
        message = (
            f"Disk usage: {used_percent:.2f}% "
            f"(Total: {total / (1024**3):.2f} GB, Used: {used / (1024**3):.2f} GB)"
        )

        if used_percent > settings.DISK_USAGE_THRESHOLD_PERCENT:
            status_enum = HealthStatus.WARNING
            message = (
                f"Disk usage is high: {used_percent:.2f}% exceeds threshold of "
                f"{settings.DISK_USAGE_THRESHOLD_PERCENT}%."
            )
            logger.warning(message)

        return HealthCheckDetail(
            component="disk",
            status=status_enum,
            message=message,
            details={
                "used_percent": round(used_percent, 2),
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2)
            }
        )
    except FileNotFoundError:
        logger.error("Disk usage check failed: Target path not found.", exc_info=True)
        return HealthCheckDetail(
            component="disk",
            status=HealthStatus.DOWN,
            message="Disk usage check failed: Target path not found."
        )
    except Exception as e:
        logger.error(f"Disk usage check failed: {e}", exc_info=True)
        return HealthCheckDetail(
            component="disk",
            status=HealthStatus.DOWN,
            message=f"Disk usage check failed: {e}"
        )

def check_memory_usage() -> HealthCheckDetail:
    """
    Checks the system's virtual memory usage.
    Compares current usage against a configured threshold.
    Requires the `psutil` library.
    """
    try:
        memory = psutil.virtual_memory()
        used_percent = memory.percent

        status_enum = HealthStatus.UP
        message = (
            f"Memory usage: {used_percent:.2f}% "
            f"(Total: {memory.total / (1024**3):.2f} GB, Used: {memory.used / (1024**3):.2f} GB)"
        )

        if used_percent > settings.MEMORY_USAGE_THRESHOLD_PERCENT:
            status_enum = HealthStatus.WARNING
            message = (
                f"Memory usage is high: {used_percent:.2f}% exceeds threshold of "
                f"{settings.MEMORY_USAGE_THRESHOLD_PERCENT}%."
            )
            logger.warning(message)

        return HealthCheckDetail(
            component="memory",
            status=status_enum,
            message=message,
            details={
                "used_percent": round(used_percent, 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2)
            }
        )
    except Exception as e:
        logger.error(f"Memory usage check failed: {e}", exc_info=True)
        return HealthCheckDetail(
            component="memory",
            status=HealthStatus.DOWN,
            message=f"Memory usage check failed: {e}"
        )

def check_cache_status() -> HealthCheckDetail:
    """
    Placeholder for cache health check.
    In a production environment, this would connect to an actual cache service
    (e.g., Redis, Memcached) and perform a PING or a simple GET/SET operation
    to verify connectivity and responsiveness.
    For this project, assuming no external cache is critically configured yet,
    or it's considered operational by default.
    """
    # Example of how a real cache check might look (e.g., for Redis):
    # try:
    #     redis_client = get_redis_client() # Assuming a dependency for Redis client
    #     redis_client.ping()
    #     return HealthCheckDetail(component="cache", status=HealthStatus.UP, message="Cache service operational.")
    # except Exception as e:
    #     logger.error(f"Cache health check failed: {e}", exc_info=True)
    #     return HealthCheckDetail(component="cache", status=HealthStatus.DOWN, message=f"Cache service failed: {e}")

    return HealthCheckDetail(
        component="cache",
        status=HealthStatus.UP,  # Defaulting to UP as no external cache is explicitly configured
        message="Cache service not configured or assumed operational."
    )

@router.get("/", response_model=HealthCheckResponse, summary="Application Health Check",
            description="Returns the overall health status of the application, including uptime, version, and checks for database, disk, memory, and cache.")
async def get_health_status(
    db: AsyncSession = Depends(get_db_session)
) -> HealthCheckResponse:
    """
    Endpoint to provide a comprehensive health check of the application.

    This endpoint aggregates the status of various critical components
    (database, disk, memory, cache) and provides overall application
    status, uptime, and version information.

    Args:
        db (AsyncSession): Asynchronous database session dependency.

    Returns:
        HealthCheckResponse: A Pydantic model containing the application's status,
                             uptime, version, and detailed checks for various components.
    """
    current_time = datetime.now(timezone.utc)
    uptime_seconds = (current_time - _app_start_time).total_seconds()
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    # Perform individual component checks.
    # The database check is asynchronous, others are synchronous.
    # For more complex async checks, asyncio.gather could be used to run them concurrently.
    db_check = await check_database_status(db)
    disk_check = check_disk_usage()
    memory_check = check_memory_usage()
    cache_check = check_cache_status()  # Placeholder for now

    # Aggregate all component checks into a list
    checks = [db_check, disk_check, memory_check, cache_check]

    # Determine overall status based on individual component statuses
    overall_status = HealthStatus.UP
    for check in checks:
        if check.status == HealthStatus.DOWN:
            overall_status = HealthStatus.DOWN
            break  # If any critical component is DOWN, the overall status is DOWN
        elif check.status == HealthStatus.WARNING:
            # If not already DOWN, a WARNING from any component makes the overall status WARNING
            if overall_status == HealthStatus.UP:
                overall_status = HealthStatus.WARNING

    # Construct the final health check response
    response = HealthCheckResponse(
        status=overall_status,
        uptime=uptime_str,
        version=__version__,
        timestamp=current_time,
        checks=checks,
        system_info={
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "architecture": platform.machine(),
        }
    )

    logger.info(f"Health check performed. Overall status: {overall_status.value}