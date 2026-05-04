import sys
import os
from datetime import datetime
import json
from flask import Flask, render_template, jsonify, request

# Add the root project directory to sys.path so we can import libs and src modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from libs.stock_analysis_lib import stock_price_check
from src.main import verify_and_rebuild_data

app = Flask(__name__)

# Load tickers once at startup
tkr_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tkr.json")
tkr_data = []
tickers = []

if os.path.exists(tkr_file):
    with open(tkr_file, 'r') as f:
        tkr_data = json.load(f)
        
    unique_tickers = set()
    for category in tkr_data:
        unique_tickers.update(category.get('etf_tickers', []))
        unique_tickers.update(category.get('tickers', []))
    tickers = list(unique_tickers)
else:
    print(f"Error: ticker list file {tkr_file} not found.")

# Initialization happens in the __main__ block

@app.route('/')
def index():
    """Serve the main landing page with classes."""
    return render_template('main.html', tkr_data=tkr_data)

@app.route('/class/<class_name>')
def class_dashboard(class_name):
    """Serve the dashboard for a specific class."""
    return render_template('index.html', class_name=class_name)

@app.route('/api/metrics')
def api_metrics():
    """Return the latest stock metrics dynamically for the frontend."""
    if not tkr_data:
        return jsonify({"error": "No ticker configurations found.", "metrics": []}), 500
        
    class_name = request.args.get('class')
    target_tickers = []
    
    if class_name:
        for category in tkr_data:
            if category.get('class') == class_name:
                for t in category.get('etf_tickers', []):
                    if t not in target_tickers:
                        target_tickers.append(t)
                for t in category.get('tickers', []):
                    if t not in target_tickers:
                        target_tickers.append(t)
                break
    else:
        # Default: all unique tickers in order
        for category in tkr_data:
            for t in category.get('etf_tickers', []):
                if t not in target_tickers:
                    target_tickers.append(t)
            for t in category.get('tickers', []):
                if t not in target_tickers:
                    target_tickers.append(t)
        
    if not target_tickers:
        return jsonify({"error": f"No tickers found for class: {class_name}", "metrics": []}), 404
        
    data = []
    for ticker in target_tickers:
        ticker_data = {
            "ticker": ticker,
            "terms": {}
        }
        for term in ["short", "mid", "long", "longExt"]:
            idx, chance, cur_drop, worst_drop, current_price, worst_drop_date, change_today = stock_price_check(ticker, term)
            ticker_data["terms"][term] = {
                "close_index": round(idx, 4),
                "buy_chance": round(chance * 100, 2),  # send as percentage number
                "cur_drop": round(cur_drop, 2),
                "worst_drop": round(worst_drop, 2),
                "current_price": round(current_price, 2),
                "worst_drop_date": worst_drop_date,
                "change_today": round(change_today, 2)
            }
        data.append(ticker_data)
        
    return jsonify({
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "metrics": data
    })

if __name__ == '__main__':
    # Initialize immediately if running directly
    if tickers:
        print("Starting data verification on startup...")
        verify_and_rebuild_data(tickers)
        
    print("Starting Flask Web Server on http://127.0.0.1:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
