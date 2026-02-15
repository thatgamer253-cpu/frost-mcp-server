{current_user.email}")

        portfolio_assets = await crud_portfolio.get_multi_by_owner(db, owner_id=current_user.id)
        if not portfolio_assets:
            logger.info(f"No portfolio assets found for user {current_user.email}. Returning empty summary.")
            return DashboardSummary(
                total_portfolio_value=0.0,
                total_cost_basis=0.0,
                total_profit_loss=0.0,
                total_profit_loss_percentage=0.0,
                daily_change=0.0,
                daily_change_percentage=0.0,
            )

        symbols = [asset.asset_symbol for asset in portfolio_assets]
        current_prices = await market_data_service.get_current_prices(symbols)

        total_portfolio_value = 0.0
        total_cost_basis = 0.0
        daily_change = 0.0
        previous_day_value = 0.0

        for asset in portfolio_assets:
            current_price = current_prices.get(asset.asset_symbol)
            if current_price is None:
                logger.warning(f"Current price not found for {asset.asset_symbol}. Skipping for summary calculation.")
                continue

            asset_current_value = asset.quantity * current_price
            total_portfolio_value += asset_current_value
            total_cost_basis += asset.cost_basis

            # Calculate daily change for each asset
            # This requires fetching historical price for yesterday.
            # For simplicity, we'll assume market_data_service can provide 24h change or yesterday's close.
            # A more robust solution would fetch yesterday's close price explicitly.
            yesterday_price = await market_data_service.get_historical_price(asset.asset_symbol, datetime.now() - timedelta(days=1))
            if yesterday_price:
                asset_previous_day_value = asset.quantity * yesterday_price
                previous_day_value += asset_previous_day_value
                daily_change += (current_price - yesterday_price) * asset.quantity
            else:
                logger.debug(f"Yesterday's price not available for {asset.asset_symbol}. Daily change for this asset will be 0.")

        total_profit_loss = total_portfolio_value - total_cost_basis
        total_profit_loss_percentage = (total_profit_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0.0

        daily_change_percentage = (daily_change / previous_day_value * 100) if previous_day_value > 0 else 0.0

        summary = DashboardSummary(
            total_portfolio_value=round(total_portfolio_value, 2),
            total_cost_basis=round(total_cost_basis, 2),
            total_profit_loss=round(total_profit_loss, 2),
            total_profit_loss_percentage=round(total_profit_loss_percentage, 2),
            daily_change=round(daily_change, 2),
            daily_change_percentage=round(daily_change_percentage, 2),
        )
        logger.info(f"Dashboard summary generated for user {current_user.email}.")
        return summary

    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard summary for user {current_user.email}: {e}", exc_info=True)
        raise DetailedHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving dashboard summary.",
            error_code="DASHBOARD_SUMMARY_FAILED",
        )


@router.get("/chart-data", response_model=PortfolioChartData)
async def get_portfolio_chart_data(
    timeframe: Timeframe = Timeframe.ONE_MONTH,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Retrieves historical portfolio value data for charting over a specified timeframe.
    Accurately reconstructs holdings for each historical date.
    """
    try:
        logger.info(f"Fetching portfolio chart data for user: {current_user.email}, timeframe: {timeframe.value}")

        end_date = datetime.now().date()
        if timeframe == Timeframe.ONE_DAY:
            start_date = end_date - timedelta(days=1)
        elif timeframe == Timeframe.ONE_WEEK:
            start_date = end_date - timedelta(weeks=1)
        elif timeframe == Timeframe.ONE_MONTH:
            start_date = end_date - timedelta(days=30)
        elif timeframe == Timeframe.THREE_MONTHS:
            start_date = end_date - timedelta(days=90)
        elif timeframe == Timeframe.SIX_MONTHS:
            start_date = end_date - timedelta(days=180)
        elif timeframe == Timeframe.ONE_YEAR:
            start_date = end_date - timedelta(days=365)
        elif timeframe == Timeframe.FIVE_YEARS:
            start_date = end_date - timedelta(days=5 * 365)
        else:  # ALL
            # Find the date of the first transaction
            first_transaction = await crud_transaction.get_first_transaction_date_by_owner(db, owner_id=current_user.id)
            start_date = first_transaction.date() if first_transaction else end_date - timedelta(days=30) # Default to 30 days if no transactions

        # Ensure start_date is not in the future
        if start_date > end_date:
            start_date = end_date

        # Get all transactions for the user within the relevant period
        transactions = await crud_transaction.get_multi_by_owner(
            db, owner_id=current_user.id, start_date=start_date, end_date=end_date
        )
        # Also get all transactions before the start_date to establish initial holdings
        initial_transactions = await crud_transaction.get_multi_by_owner(
            db, owner_id=current_user.id, end_date=start_date - timedelta(days=1)
        )
        all_transactions = sorted(initial_transactions + transactions, key=lambda t: t.transaction_date)

        # Get all unique asset symbols involved in transactions
        all_symbols = list(set(t.asset_symbol for t in all_transactions))
        if not all_symbols:
            logger.info(f"No transactions found for user {current_user.email}. Returning empty chart data.")
            return PortfolioChartData(data=[], timeframe=timeframe)

        # Fetch historical prices for all relevant symbols and the entire date range
        historical_prices_data = await market_data_service.get_historical_prices_range(
            symbols=all_symbols, start_date=start_date, end_date=end_date
        )
        # Reformat for easier lookup: {symbol: {date: price}}
        historical_prices = {
            symbol: {dp.date.date(): dp.close for dp in data_points}
            for symbol, data_points in historical_prices_data.items()
        }

        chart_data_points: List[PortfolioChartDataPoint] = []
        current_holdings = {}  # {symbol: quantity}
        transaction_idx = 0

        # Initialize holdings based on transactions before start_date
        for t in all_transactions:
            if t.transaction_date.date() < start_date:
                if t.transaction_type == TransactionType.BUY:
                    current_holdings[t.asset_symbol] = current_holdings.get(t.asset_symbol, 0) + t.quantity
                elif t.transaction_type == TransactionType.SELL:
                    current_holdings[t.asset_symbol] = current_holdings.get(t.asset_symbol, 0) - t.quantity
            else:
                break # Stop processing initial transactions

        # Iterate day by day from start_date to end_date
        current_date = start_date
        while current_date <= end_date:
            # Apply transactions that occurred on the current_date
            while transaction_idx < len(all_transactions) and all_transactions[transaction_idx].transaction_date.date() == current_date:
                transaction = all_transactions[transaction_idx]
                if transaction.transaction_type == TransactionType.BUY:
                    current_holdings[transaction.asset_symbol] = current_holdings.get(transaction.asset_symbol, 0) + transaction.quantity
                elif transaction.transaction_type == TransactionType.SELL:
                    current_holdings[transaction.asset_symbol] = current_holdings.get(transaction.asset_symbol, 0) - transaction.quantity
                transaction_idx += 1

            daily_portfolio_value = 0.0
            for symbol, quantity in current_holdings.items():
                if quantity > 0:
                    price_on_date = historical_prices.get(symbol, {}).get(current_date)
                    if price_on_date is not None:
                        daily_portfolio_value += quantity * price_on_date
                    else:
                        logger.debug(f"Historical price for {symbol} on {current_date} not found. Skipping for value calculation.")

            chart_data_points.append(PortfolioChartDataPoint(date=datetime.combine(current_date, datetime.min.time()), value=round(daily_portfolio_value, 2)))
            current_date += timedelta(days=1)

        logger.info(f"Portfolio chart data generated for user {current_user.email} with {len(chart_data_points)} data points.")
        return PortfolioChartData(data=chart_data_points, timeframe=timeframe)

    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio chart data for user {current_user.email}: {e}", exc_info=True)
        raise DetailedHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving portfolio chart data.",
            error_code="DASHBOARD_CHART_DATA_FAILED",
        )


@router.get("/asset-distribution", response_model=PortfolioAssetDistribution)
async def get_portfolio_asset_distribution(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Retrieves the distribution of assets in the user's portfolio,
    categorized by asset type or sector.
    """
    try:
        logger.info(f"Fetching portfolio asset distribution for user: {current_user.email}")

        portfolio_assets = await crud_portfolio.get_multi_by_owner(db, owner_id=current_user.id)
        if not portfolio_assets:
            logger.info(f"No portfolio assets found for user {current_user.email}. Returning empty distribution.")
            return PortfolioAssetDistribution(distribution=[])

        symbols = [asset.asset_symbol for asset in portfolio_assets]
        current_prices = await market_data_service.get_current_prices(symbols)

        total_portfolio_value = 0.0
        asset_values = {} # {symbol: value}

        for asset in portfolio_assets:
            current_price = current_prices.get(asset.asset_symbol)
            if current_price is None:
                logger.warning(f"Current price not found for {asset.asset_symbol}. Skipping for distribution calculation.")
                continue
            asset_value = asset.quantity * current_price
            asset_values[asset.asset_symbol] = asset_value
            total_portfolio_value += asset_value

        if total_portfolio_value == 0:
            logger.info(f"Total portfolio value is zero for user {current_user.email}. Returning empty distribution.")
            return PortfolioAssetDistribution(distribution=[])

        # For distribution, we can categorize by asset type (e.g., Stock, Crypto)
        # or by sector/industry if market_data_service provides this metadata.
        # For now, let's use a simple asset type categorization.
        # A more advanced implementation would fetch asset metadata.
        distribution_map = {} # {category: total_value_in_category}

        for asset in portfolio_assets:
            asset_value = asset_values.get(asset.asset_symbol, 0.0)
            if asset_value == 0:
                continue

            # Placeholder for actual asset type/sector lookup
            # In a real system, market_data_service.get_asset_metadata(asset.asset_symbol)
            # would provide 'type' (e.g., 'Stock', 'Crypto') or 'sector'.
            # For this example, we'll infer a simple category.
            category = "Other"
            if asset.asset_symbol.isupper() and len(asset.asset_symbol) <= 5: # Simple heuristic for stocks
                category = "Stock"
            elif len(asset.asset_symbol) > 5 and asset.asset_symbol.isalnum(): # Simple heuristic for crypto
                category = "Cryptocurrency"
            # Add more sophisticated logic here if metadata is available

            distribution_map[category] = distribution_map.get(category, 0.0) + asset_value

        distribution_items: List[PortfolioAssetDistributionItem] = []
        for category, value in distribution_map.items():
            percentage = (value / total_portfolio_value) * 100
            distribution_items.append(
                PortfolioAssetDistributionItem(
                    category=category,
                    value=round(value, 2),
                    percentage=round(percentage, 2),
                )
            )

        # Sort by value descending
        distribution_items.sort(key=lambda x: x.value, reverse=True)

        logger.info(f"Portfolio asset distribution generated for user {current_user.email}.")
        return PortfolioAssetDistribution(distribution=distribution_items)

    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio asset distribution for user {current_user.email}: {e}