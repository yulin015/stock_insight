import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import json


# Setup absolute path to repository directory
LIBS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(LIBS_DIR)
REPOSITORY_DIR = os.path.join(PROJECT_ROOT, "repository")


def download_stock_history(stock_ticker: str, start_date: pd.Timestamp, end_date: pd.Timestamp, end_date_str: str, csv_file: str, is_current: bool) -> bool:
    """
    Checks if local database is up-to-date, downloads historical stock data from yfinance if needed, 
    and saves it to a local CSV database.
    
    Args:
        stock_ticker (str): The stock ticker symbol.
        start_date (pd.Timestamp): The start date for the download.
        end_date (pd.Timestamp): The end date for the download.
        end_date_str (str): String representation of the end date for logging.
        csv_file (str): Path to the CSV file to save the data.
        is_current (bool): Whether the requested period ends at the current time.
        
    Returns:
        bool: True if database is up-to-date or download was successful, False otherwise.
    """
    needs_update = True
    today = datetime.now()
    
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
                        print("Checking if newer trading days are available...")
                        try:
                            check_data = yf.Ticker(stock_ticker).history(period="5d")
                            if not check_data.empty:
                                latest_available = check_data.index.max().tz_localize(None).date()
                                if latest_available <= last_date_in_db.date():
                                    needs_update = False
                                    print(f"Database is up-to-date (no newer trading days available).")
                                else:
                                    print(f"Database is outdated (last date: {last_date_in_db.strftime('%Y-%m-%d')}, available: {latest_available}). Will update.")
                            else:
                                needs_update = False
                        except Exception:
                            print(f"Database might be outdated (last date: {last_date_in_db.strftime('%Y-%m-%d')}). Will update.")
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
        
    if not needs_update:
        return True

    try:
        stock = yf.Ticker(stock_ticker)
        # Download from a bit before start_date to ensure complete data
        download_start = (start_date - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        
        # yfinance 'end' is exclusive, so we add 1 day to ensure end_date is included
        download_end = (end_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Downloading data for {stock_ticker} from {download_start} to {end_date_str}...")
        
        historical_data = stock.history(start=download_start, end=download_end, auto_adjust=True)
        
        if historical_data.empty:
            print(f"Error: No historical data found for {stock_ticker} in the specified period.")
            return False
        
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
        return True
    except Exception as e:
        print(f"Error downloading data for {stock_ticker}: {e}")
        return False


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
        csv_dir = os.path.join(REPOSITORY_DIR, "csv")
        os.makedirs(csv_dir, exist_ok=True)
        csv_file = os.path.join(csv_dir, f"{stock_ticker}.csv")
        
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
        
        # Check and update/download database if needed
        success = download_stock_history(stock_ticker, start_date, end_date, end_date_str, csv_file, is_current)
        if not success:
            return 0.0
        
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


def stock_csv_to_json(stock_ticker: str) -> list:
    """
    Reads the local CSV database for a given ticker and returns a list of dictionaries.
    Each dictionary contains the date, open, high, low, close, and change metrics.
    All prices and metrics are formatted to 2 decimal places.
    
    Args:
        stock_ticker (str): The stock ticker symbol.
        
    Returns:
        list: A list of dictionaries containing the formatted daily data.
    """
    csv_file = os.path.join(REPOSITORY_DIR, "csv", f"{stock_ticker}.csv")
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found for {stock_ticker}")
        return []
        
    try:
        # Read the CSV file, skipping the first 3 rows as per existing code pattern
        df = pd.read_csv(csv_file, skiprows=3, names=['Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
        
        # Sort values by Date to ensure chronological order
        df['Date'] = pd.to_datetime(df['Date'], utc=True)
        df = df.sort_values('Date')
        
        result = []
        previous_alltime_highest = 0.0
        
        for _, row in df.iterrows():
            date_str = row['Date'].strftime('%Y-%m-%d')
            open_price = float(row['Open'])
            high_price = float(row['High'])
            low_price = float(row['Low'])
            close_price = float(row['Close'])
            volume = int(row['Volume'])
            
            # Calculate change1 = (close - open)/open
            if open_price != 0:
                change1 = (close_price - open_price) / open_price
            else:
                change1 = 0.0
                
            # Calculate change2 = (close - previous_alltime_highest)/previous_alltime_highest
            if previous_alltime_highest == 0.0:
                change2 = 0.0
            else:
                if close_price >= previous_alltime_highest:
                    change2 = 0.0
                else:
                    change2 = (close_price - previous_alltime_highest) / previous_alltime_highest
            
            # Update previous_alltime_highest for the next iteration (using close price)
            previous_alltime_highest = max(previous_alltime_highest, close_price)
            
            # Format prices to .2f float, and changes to .2f% string
            entity = {
                "date": date_str,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume,
                "change1": f"{change1 * 100:.2f}%",
                "change2": f"{change2 * 100:.2f}%"
            }
            result.append(entity)
            
        json_dir = os.path.join(REPOSITORY_DIR, "json")
        os.makedirs(json_dir, exist_ok=True)
        json_file = os.path.join(json_dir, f"{stock_ticker}.json")
        with open(json_file, 'w') as f:
            json.dump(result, f, indent=2)
            
        return result
        
    except Exception as e:
        print(f"Error processing CSV to JSON for {stock_ticker}: {e}")
        return []


def stock_price_check(ticker: str, term: str) -> tuple[float, float, float, float, float, str, float]:
    """
    Analyzes the stock price drop relative to historical data over a specified term.
    
    Args:
        ticker (str): The stock ticker symbol.
        term (str): The time horizon for analysis ("short", "mid", "long").
        
    Returns:
        tuple[float, float, float, float, float, str, float]: A tuple containing (close_index, buy_chance, current_drop, worst_drop, current_price, worst_drop_date, change_today).
    """
    json_file = os.path.join(REPOSITORY_DIR, "json", f"{ticker}.json")
    if not os.path.exists(json_file):
        print(f"Error: JSON file not found for {ticker}. Please generate it first.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    with open(json_file, 'r') as f:
        data = json.load(f)
        
    if not data:
        print(f"Error: JSON file for {ticker} is empty.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    today = datetime.now()
    if term == "short":
        cutoff_date = today - timedelta(days=365)
    elif term == "mid":
        cutoff_date = today - timedelta(days=365 * 3)
    elif term == "long":
        cutoff_date = today - timedelta(days=365 * 5)
    elif term == "longExt":
        cutoff_date = today - timedelta(days=365 * 10)
    else:
        print("Warning: Invalid term specified. Defaulting to 'short' (1 year).")
        cutoff_date = today - timedelta(days=365)
        
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
    filtered_data = [x for x in data if x["date"] >= cutoff_date_str]
    
    if not filtered_data:
        print(f"Error: No data available for {ticker} in the specified {term} term.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    # get ticker current price by yfinance lib
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if hist.empty:
            print(f"Error: Could not fetch current price for {ticker}.")
            return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        current_price = float(hist["Close"].iloc[-1])
        open_price = float(hist["Open"].iloc[-1])
        if open_price != 0:
            change_today = ((current_price - open_price) / open_price) * 100
        else:
            change_today = 0.0
    except Exception as e:
        print(f"Error fetching current price for {ticker}: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    # get max close price in data loaded from json as all_time_high
    all_time_high = max([x["close"] for x in filtered_data])
    
    # calculate the percentage drop as current_drop
    if all_time_high > 0:
        current_drop = ((current_price - all_time_high) / all_time_high) * 100
    else:
        current_drop = 0.0
        
    # helper to parse percentage string to float
    def parse_change(change_str):
        return float(change_str.replace('%', ''))
        
    # find out the worst change2 in data loaded from json
    worst_drop_entry = min(filtered_data, key=lambda x: parse_change(x["change2"]))
    worst_drop = parse_change(worst_drop_entry["change2"])
    worst_drop_date = worst_drop_entry["date"]
    
    # calculate close_index
    if worst_drop == 0:
        close_index = 0.0
    else:
        close_index = (worst_drop - current_drop) / worst_drop
        
    # check data and calculate how many days have change2 lower than current_drop
    drop_days = sum(1 for x in filtered_data if parse_change(x["change2"]) < current_drop)
    
    # calculate buy_chance
    total_days = len(filtered_data)
    buy_chance = drop_days / total_days if total_days > 0 else 0.0
    
    return close_index, buy_chance, current_drop, worst_drop, current_price, worst_drop_date, change_today


def stock_price_check_by_date(ticker: str, target_date_str: str, term: str) -> tuple[float, float, float, float, float, str, float]:
    """
    Analyzes the stock price drop relative to historical data over a specified term, 
    up to a specific target date.
    
    Args:
        ticker (str): The stock ticker symbol.
        target_date_str (str): The target date in 'YYYY-MM-DD' format.
        term (str): The time horizon for analysis ("short", "mid", "long").
        
    Returns:
        tuple[float, float, float, float, float, str, float]: A tuple containing (close_index, buy_chance, current_drop, worst_drop, current_price, worst_drop_date, change_today).
    """
    json_file = os.path.join(REPOSITORY_DIR, "json", f"{ticker}.json")
    if not os.path.exists(json_file):
        print(f"Error: JSON file not found for {ticker}. Please generate it first.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    with open(json_file, 'r') as f:
        data = json.load(f)
        
    if not data:
        print(f"Error: JSON file for {ticker} is empty.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Error: Invalid date format '{target_date_str}'. Use 'YYYY-MM-DD'.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    if term == "short":
        cutoff_date = target_date - timedelta(days=365)
    elif term == "mid":
        cutoff_date = target_date - timedelta(days=365 * 3)
    elif term == "long":
        cutoff_date = target_date - timedelta(days=365 * 5)
    elif term == "longExt":
        cutoff_date = target_date - timedelta(days=365 * 10)
    else:
        print("Warning: Invalid term specified. Defaulting to 'short' (1 year).")
        cutoff_date = target_date - timedelta(days=365)
        
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
    
    # Filter data to the period: [cutoff_date_str, target_date_str]
    filtered_data = [x for x in data if cutoff_date_str <= x["date"] <= target_date_str]
    
    if not filtered_data:
        print(f"Error: No data available for {ticker} between {cutoff_date_str} and {target_date_str}.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    # Get current price from the target date's data
    # Find the exact date or the closest previous date within the filtered data
    target_day_data = None
    for x in reversed(filtered_data):
        if x["date"] <= target_date_str:
            target_day_data = x
            break
            
    if not target_day_data:
        print(f"Error: Could not find trading data on or before {target_date_str}.")
        return 0.0, 0.0, 0.0, 0.0, 0.0, "", 0.0
        
    current_price = target_day_data["close"]
    target_open_price = target_day_data["open"]
    if target_open_price != 0:
        change_today = ((current_price - target_open_price) / target_open_price) * 100
    else:
        change_today = 0.0
        
    # get max close price in data loaded from json as all_time_high
    all_time_high = max([x["close"] for x in filtered_data])
    
    # calculate the percentage drop as current_drop
    if all_time_high > 0:
        current_drop = ((current_price - all_time_high) / all_time_high) * 100
    else:
        current_drop = 0.0
        
    # helper to parse percentage string to float
    def parse_change(change_str):
        return float(change_str.replace('%', ''))
        
    # find out the worst change2 in data loaded from json
    worst_drop_entry = min(filtered_data, key=lambda x: parse_change(x["change2"]))
    worst_drop = parse_change(worst_drop_entry["change2"])
    worst_drop_date = worst_drop_entry["date"]
    
    # calculate close_index
    if worst_drop == 0:
        close_index = 0.0
    else:
        close_index = (worst_drop - current_drop) / worst_drop
        
    # check data and calculate how many days have change2 lower than current_drop
    drop_days = sum(1 for x in filtered_data if parse_change(x["change2"]) < current_drop)
    
    # calculate buy_chance
    total_days = len(filtered_data)
    buy_chance = drop_days / total_days if total_days > 0 else 0.0
    
    return close_index, buy_chance, current_drop, worst_drop, current_price, worst_drop_date, change_today


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Stock Drop Percentage Calculator")
    print("=" * 80)
    
    # Example 1: Historical period
    print("\nExample 1: Historical period")
    drop1 = stock_drop_percentage('AAPL', '2000-01-01', 'CURRENT')
   
    
    # Example 2: Current time
    print("\n" + "=" * 80)
    print("\nExample 2: Current time")
    drop2 = stock_drop_percentage('NVDA', '2000-01-01', 'CURRENT')
    
    # Example 3: Recent period
    print("\n" + "=" * 80)
    print("\nExample 3: Recent period")
    drop3 = stock_drop_percentage('MSFT', '2000-01-01', 'CURRENT')
    
    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)

# Made with Bob
