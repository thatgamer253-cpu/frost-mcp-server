{symbol}",
    response_model=MarketDataQuote,
    summary="Get real-time market quote for a symbol",
    description="Fetches simulated real-time market data (quote) for a given asset symbol. Requires authentication.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": MarketDataError, "description": "Symbol not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": MarketDataError, "description": "Market data service error"},
    },
)
async def get_market_quote(
    symbol: str = Query(..., description="The ticker symbol of the asset (e.g., 'AAPL', 'MSFT')"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),  # db dependency is included for consistency, even if not directly used by market data service
) -> MarketDataQuote:
    """
    Retrieve the latest simulated market quote for a specified asset symbol.

    This endpoint provides current price, open, high, low, volume, and change
    information for a given stock or cryptocurrency symbol.
    """
    logger.info(f"User {current_user.email} requesting market quote for symbol: {symbol}")
    market_data_service = MarketDataService(
        api_key=settings.MARKET_DATA_API_KEY,
        base_url=settings.MARKET_DATA_BASE_URL,
        provider=settings.MARKET_DATA_PROVIDER,
    )
    try:
        quote = await market_data_service.get_quote(symbol)
        if not quote:
            logger.warning(f"Market quote not found for symbol: {symbol}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market quote for symbol '{symbol}' not found.",
            )
        return quote
    except HTTPException:
        # Re-raise FastAPI HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Failed to fetch market quote for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market quote for '{symbol}'. Please try again later.",
        )


@router.get(
    "/history/{symbol}",
    response_model=List[MarketDataHistory],
    summary="Get historical market data for a symbol",
    description="Fetches simulated historical market data (e.g., daily prices) for a given asset symbol. Requires authentication.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": MarketDataError, "description": "Symbol not found or no historical data"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": MarketDataError, "description": "Market data service error"},
    },
)
async def get_market_history(
    symbol: str = Query(..., description="The ticker symbol of the asset"),
    interval: str = Query("1day", description="Data interval (e.g., '1min', '1hour', '1day', '1week', '1month')"),
    start_date: Optional[str] = Query(None, description="Start date for historical data (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for historical data (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[MarketDataHistory]:
    """
    Retrieve simulated historical market data for a specified asset symbol.

    This endpoint provides open, high, low, close, and volume data over a specified
    time interval and date range.
    """
    logger.info(
        f"User {current_user.email} requesting historical data for symbol: {symbol}, interval: {interval}, "
        f"start: {start_date}, end: {end_date}"
    )
    market_data_service = MarketDataService(
        api_key=settings.MARKET_DATA_API_KEY,
        base_url=settings.MARKET_DATA_BASE_URL,
        provider=settings.MARKET_DATA_PROVIDER,
    )
    try:
        history = await market_data_service.get_historical_data(symbol, interval, start_date, end_date)
        if not history:
            logger.warning(
                f"No historical data found for symbol: {symbol} with interval {interval}, "
                f"start: {start_date}, end: {end_date}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No historical data found for symbol '{symbol}' with the specified parameters.",
            )
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch historical data for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical data for '{symbol}'. Please try again later.",
        )


@router.get(
    "/search",
    response_model=List[MarketDataSearch],
    summary="Search for assets",
    description="Searches for assets (stocks, cryptocurrencies, etc.) by keyword. Requires authentication.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": MarketDataError, "description": "Market data service error"},
    },
)
async def search_assets(
    query: str = Query(..., min_length=1, description="Search query for asset name or symbol (e.g., 'Apple', 'BTC')"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[MarketDataSearch]:
    """
    Search for assets based on a provided query string.

    This endpoint allows users to find assets by their name or ticker symbol.
    """
    logger.info(f"User {current_user.email} searching for assets with query: {query}")
    market_data_service = MarketDataService(
        api_key=settings.MARKET_DATA_API_KEY,
        base_url=settings.MARKET_DATA_BASE_URL,
        provider=settings.MARKET_DATA_PROVIDER,
    )
    try:
        results = await market_data_service.search_assets(query)
        return results
    except Exception as e:
        logger.error(f"Failed to search assets for query '{query}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search for assets with query '{query}'. Please try again later.",
        )


@router.get(
    "/trending",
    response_model=List[TrendingAsset],
    summary="Get trending assets",
    description="Fetches a simulated list of currently trending assets. Requires authentication.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": MarketDataError, "description": "Market data service error"},
    },
)
async def get_trending_assets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[TrendingAsset]:
    """
    Retrieve a simulated list of currently trending assets.

    This endpoint provides a curated list of assets that are currently
    showing significant market activity or interest.
    """
    logger.info(f"User {current_user.email} requesting trending assets.")
    market_data_service = MarketDataService(
        api_key=settings.MARKET_DATA_API_KEY,
        base_url=settings.MARKET_DATA_BASE_URL,
        provider=settings.MARKET_DATA_PROVIDER,
    )
    try:
        trending = await market_data_service.get_trending_assets()
        return trending
    except Exception as e:
        logger.error(f"Failed to fetch trending assets: {e}