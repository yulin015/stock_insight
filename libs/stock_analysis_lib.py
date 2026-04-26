import yfinance as yf
import pandas as pd
from datetime import datetime
import os


def stock_drop_percentage(stock_ticker: str, start_time: str, end_time: str) -> float:
    """
    Calculate the drop percentage from the all-time high within a specified period.
    
    This function uses the local CSV database in repository/ directory. It automatically:
    - Downloads data if the ticker CSV doesn't exist
    - Updates the CSV if it's outdated
    - Uses cached data when it's current
    
    Args:
        stock_ticker (str): The stock ticker symbol (e.g., 'AAPL', 'NVDA')
        start_time (str): Start date in format 'YYYY-MM-DD'
        end_time (str): End date in format 'YYYY-MM-DD' or 'CURRENT' for current time
    
    Returns:
        float: Drop percentage from all-time high. Returns 0.0 if current price is ATH,
               or if there's an error in calculation.
    
    Examples:
        >>> stock_drop_percentage('AAPL', '2020-01-01', '2020-12-31')
        15.5
        >>> stock_drop_percentage('NVDA', '2023-01-01', 'CURRENT')
        5.2
    """
    
    # Validate inputs
    if not isinstance(stock_ticker, str) or not stock_ticker:
        print("Error: Stock ticker must be a non-empty string.")
        return 0.0
    
    if not isinstance(start_time, str) or not start_time:
        print("Error: Start time must be a non-empty string in format 'YYYY-MM-DD'.")
        return 0.0
    
    if not isinstance(end_time, str) or not end_time:
        print("Error: End time must be a non-empty string in format 'YYYY-MM-DD' or 'CURRENT'.")
        return 0.0
    
    # Parse and validate start_time
    try:
        start_date = pd.to_datetime(start_time)
    except ValueError:
        print(f"Error: Invalid start_time format '{start_time}'. Use 'YYYY-MM-DD'.")
        return 0.0
    
    # Determine if we need current data or historical data
    is_current = end_time.upper() == "CURRENT"
    
    try:
        # Setup local database path
        repository_dir = "repository"
        os.makedirs(repository_dir, exist_ok=True)
        csv_file = os.path.join(repository_dir, f"{stock_ticker}.csv")
        
        # Determine the end date
        if is_current:
            today = datetime.now()
            end_date_str = today.strftime('%Y-%m-%d')
            end_date = today
        else:
            try:
                end_date = pd.to_datetime(end_time)
                end_date_str = end_time
            except ValueError:
                print(f"Error: Invalid end_time format '{end_time}'. Use 'YYYY-MM-DD' or 'CURRENT'.")
                return 0.0
        
        # Validate date range
        if end_date < start_date:
            print(f"Error: End time ({end_date_str}) cannot be before start time ({start_time}).")
            return 0.0
        
        # Check if local database exists and is up-to-date
        needs_update = True
        
        if os.path.exists(csv_file):
            print(f"Found existing database: {csv_file}")
            try:
                # Read existing data (skip first 3 rows as per existing code pattern)
                existing_data = pd.read_csv(csv_file, skiprows=3, names=['Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
                existing_data['Date'] = pd.to_datetime(existing_data['Date'], utc=True)
                # Convert to timezone-naive for comparison
                if existing_data['Date'].dt.tz is not None:
                    existing_data['Date'] = existing_data['Date'].dt.tz_localize(None)
                
                if not existing_data.empty:
                    last_date_in_db = existing_data['Date'].max()
                    first_date_in_db = existing_data['Date'].min()
                    
                    print(f"Database date range: {first_date_in_db.strftime('%Y-%m-%d')} to {last_date_in_db.strftime('%Y-%m-%d')}")
                    
                    # Check if database covers the required period
                    if is_current:
                        # For current queries, update if data is older than today
                        if last_date_in_db.date() >= today.date():
                            needs_update = False
                            print("Database is up-to-date for current query.")
                        else:
                            print(f"Database is outdated (last date: {last_date_in_db.strftime('%Y-%m-%d')}). Will update.")
                    else:
                        # For historical queries, check if we have data up to end_date
                        if last_date_in_db.date() >= end_date.date() and first_date_in_db.date() <= start_date.date():
                            needs_update = False
                            print("Database covers the requested historical period.")
                        else:
                            print(f"Database doesn't cover the full period. Will update.")
                else:
                    print("Database file is empty. Will download fresh data.")
            except Exception as e:
                print(f"Error reading existing database: {e}. Will download fresh data.")
                needs_update = True
        else:
            print(f"No existing database found for {stock_ticker}. Will download data.")
        
        # Update/download database if needed
        if needs_update:
            stock = yf.Ticker(stock_ticker)
            # Download from a bit before start_date to ensure complete data
            download_start = (start_date - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
            print(f"Downloading data for {stock_ticker} from {download_start} to {end_date_str}...")
            
            historical_data = stock.history(start=download_start, end=end_date_str, auto_adjust=True)
            
            if historical_data.empty:
                print(f"Error: No historical data found for {stock_ticker} in the specified period.")
                return 0.0
            
            # Save to CSV file matching the existing repository format
            # Format: 3 header rows, then data with Date,Close,High,Low,Open,Volume
            with open(csv_file, 'w') as f:
                # Write the 3-row header
                f.write('Price,Close,High,Low,Open,Volume\n')
                f.write(f'Ticker,{stock_ticker},{stock_ticker},{stock_ticker},{stock_ticker},{stock_ticker}\n')
                f.write('Date,,,,,\n')
            
            # Append the data
            historical_data[['Close', 'High', 'Low', 'Open', 'Volume']].to_csv(csv_file, mode='a', header=False)
            print(f"Database saved/updated: {csv_file}")
        
        # Load data from local database
        print(f"Loading data from {csv_file}...")
        df = pd.read_csv(csv_file, skiprows=3, names=['Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
        df['Date'] = pd.to_datetime(df['Date'], utc=True)
        df = df.set_index('Date')
        
        if df.empty:
            print(f"Error: Database file is empty for {stock_ticker}.")
            return 0.0
        
        # Convert timezone-aware index to timezone-naive for comparison
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Filter data for the specified period
        period_data = df[
            (df.index >= start_date) &
            (df.index <= end_date)
        ]
        
        if period_data.empty:
            print(f"Error: No data available for {stock_ticker} between {start_time} and {end_date_str}.")
            return 0.0
        
        # Calculate the all-time high during the period
        ath_price = period_data['High'].max()
        ath_date = period_data['High'].idxmax()
        
        # Determine the current/end price
        if is_current:
            # Check if market is currently open
            now = datetime.now()
            market_hours = _is_market_open(now)
            
            if market_hours:
                # Market is open - try to get real-time price
                try:
                    stock = yf.Ticker(stock_ticker)
                    current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
                    if current_price is None or current_price <= 0:
                        # Fallback to last close price
                        current_price = period_data['Close'].iloc[-1]
                        price_source = "last close price (real-time unavailable)"
                    else:
                        price_source = "real-time price"
                except Exception:
                    current_price = period_data['Close'].iloc[-1]
                    price_source = "last close price (real-time unavailable)"
            else:
                # Market is closed - use last close price
                current_price = period_data['Close'].iloc[-1]
                price_source = "last close price"
            
            current_date = period_data.index[-1]
        else:
            # Historical end date - use close price of that day
            current_price = period_data['Close'].iloc[-1]
            current_date = period_data.index[-1]
            price_source = "close price"
        
        # Calculate drop percentage
        if current_price >= ath_price:
            # Current price is at or above ATH
            drop_percentage = 0.0
            print(f"\n{stock_ticker} Analysis:")
            print(f"  Period: {start_time} to {end_date_str}")
            print(f"  Current/End Price: ${current_price:.2f} ({current_date.strftime('%Y-%m-%d')}, {price_source})")
            print(f"  All-Time High: ${ath_price:.2f} ({ath_date.strftime('%Y-%m-%d')})")
            print(f"  Drop from ATH: 0.00% (Current price is at or above ATH)")
        else:
            drop_percentage = ((ath_price - current_price) / ath_price) * 100
            print(f"\n{stock_ticker} Analysis:")
            print(f"  Period: {start_time} to {end_date_str}")
            print(f"  Current/End Price: ${current_price:.2f} ({current_date.strftime('%Y-%m-%d')}, {price_source})")
            print(f"  All-Time High: ${ath_price:.2f} ({ath_date.strftime('%Y-%m-%d')})")
            print(f"  Drop from ATH: {drop_percentage:.2f}%")
        
        return round(drop_percentage, 2)
    
    except Exception as e:
        print(f"Error calculating drop percentage for {stock_ticker}: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def _is_market_open(current_time: datetime) -> bool:
    """
    Check if the US stock market is currently open.
    
    US stock market hours (Eastern Time):
    - Monday to Friday: 9:30 AM - 4:00 PM ET
    - Closed on weekends and holidays
    
    Args:
        current_time (datetime): Current datetime
    
    Returns:
        bool: True if market is open, False otherwise
    """
    # Check if it's a weekend
    if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check market hours (simplified - assumes current_time is in ET or close to it)
    # For a more accurate implementation, you would need to:
    # 1. Convert current_time to Eastern Time using pytz
    # 2. Check against actual market holidays
    hour = current_time.hour
    minute = current_time.minute
    
    # Market opens at 9:30 AM and closes at 4:00 PM ET
    market_open_minutes = 9 * 60 + 30  # 9:30 AM
    market_close_minutes = 16 * 60      # 4:00 PM
    current_minutes = hour * 60 + minute
    
    return market_open_minutes <= current_minutes < market_close_minutes


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Stock Drop Percentage Calculator")
    print("=" * 80)
    
    # Example 1: Historical period
    print("\nExample 1: Historical period")
    drop1 = stock_drop_percentage('AAPL', '2020-01-01', '2020-12-31')
    
    # Example 2: Current time
    print("\n" + "=" * 80)
    print("\nExample 2: Current time")
    drop2 = stock_drop_percentage('NVDA', '2023-01-01', 'CURRENT')
    
    # Example 3: Recent period
    print("\n" + "=" * 80)
    print("\nExample 3: Recent period")
    drop3 = stock_drop_percentage('MSFT', '2024-01-01', 'CURRENT')
    
    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)

# Made with Bob
