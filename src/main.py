import sys
import os
import time
from datetime import datetime
import pandas as pd
import json

# Add the root project directory to sys.path so we can import libs
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from libs.stock_analysis_lib import (
    stock_csv_to_json, 
    stock_price_check, 
    _is_market_open,
    download_stock_history
)

def verify_and_rebuild_data(tickers):
    """Verifies and rebuilds CSV and JSON files for the given tickers."""
    start_date = pd.to_datetime('2000-01-01')
    today = datetime.now()
    end_date = today
    end_date_str = today.strftime('%Y-%m-%d')
    
    repository_dir = os.path.join(project_root, "repository")
    csv_dir = os.path.join(repository_dir, "csv")
    json_dir = os.path.join(repository_dir, "json")
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    
    for ticker in tickers:
        print(f"\n--- Verifying data for {ticker} ---")
        csv_file = os.path.join(csv_dir, f"{ticker}.csv")
        json_file = os.path.join(json_dir, f"{ticker}.json")
        
        # Verify/rebuild CSV
        # download_stock_history automatically handles checking if it's out of date
        success = download_stock_history(
            stock_ticker=ticker, 
            start_date=start_date, 
            end_date=end_date, 
            end_date_str=end_date_str, 
            csv_file=csv_file, 
            is_current=True
        )
        if not success:
            print(f"Failed to verify/rebuild CSV for {ticker}")
            continue
            
        # Verify/rebuild JSON
        # Since stock_csv_to_json overwrites/rebuilds the JSON based on the latest CSV, 
        # we will run it to ensure the JSON is perfectly synced.
        print(f"Verifying/Rebuilding JSON for {ticker}...")
        stock_csv_to_json(ticker)


def main():
    # 1. Load list of tickers from src/tkr.json
    tkr_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tkr.json")
    if not os.path.exists(tkr_file):
        print(f"Error: ticker list file {tkr_file} not found.")
        return
        
    with open(tkr_file, 'r') as f:
        tkr_data = json.load(f)
        
    # Flatten unique tickers
    unique_tickers = set()
    for category in tkr_data:
        unique_tickers.update(category.get('etf_tickers', []))
        unique_tickers.update(category.get('tickers', []))
        
    tickers = list(unique_tickers)
        
    print(f"Loaded tickers: {tickers}")
    
    # 2 & 3. Verify and rebuild CSV and JSON files
    verify_and_rebuild_data(tickers)
    
    # 4. while-true loop
    print("\nStarting monitoring loop...")
    while True:
        now = datetime.now()
        market_open = _is_market_open(now)
        
        if market_open:
            print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Market is OPEN. Running 60s checks...")
            for ticker in tickers:
                for term in ["short", "mid", "long", "longExt"]:
                    idx, chance, cur_drop, worst_drop, current_price, worst_drop_date, change_today = stock_price_check(ticker, term)
                    # stock_price_check prints an internal summary, but per the requirement,
                    # we must explicitly print out all return values in stdout.
                    print(f"--> {ticker} {term.upper()}: CurrentPrice=${current_price:.2f}, ChangeToday={change_today:.2f}%, CloseIndex={idx:.4f}, BuyChance={chance:.2%}, CurDrop={cur_drop:.2f}%, WorstDrop={worst_drop:.2f}% (on {worst_drop_date})")
            
            # Run below steps in every 60s
            time.sleep(60)
            
        else:
            print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Current time is OFF MARKET time.")
            
            # Review all tickers ONLY one time
            for ticker in tickers:
                for term in ["short", "mid", "long", "longExt"]:
                    idx, chance, cur_drop, worst_drop, current_price, worst_drop_date, change_today = stock_price_check(ticker, term)
                    print(f"--> {ticker} {term.upper()}: CurrentPrice=${current_price:.2f}, ChangeToday={change_today:.2f}%, CloseIndex={idx:.4f}, BuyChance={chance:.2%}, CurDrop={cur_drop:.2f}%, WorstDrop={worst_drop:.2f}% (on {worst_drop_date})")
            
            # Sleep and wait for market open time
            print("\nSleeping and waiting for market to open...")
            while not _is_market_open(datetime.now()):
                time.sleep(60)


if __name__ == "__main__":
    main()
