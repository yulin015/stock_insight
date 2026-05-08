import sys
import os
from datetime import datetime
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file

# Add the root project directory to sys.path so we can import libs and src modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from libs.stock_analysis_lib import stock_price_check, stock_annual_change, stock_cashflow_change
from src.main import verify_and_rebuild_data

app = Flask(__name__)

# Load tickers once at startup
tkr_file = os.path.join(project_root, "config", "tkr.json")
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

@app.route('/api/annual_change_chart/<ticker>')
def annual_change_chart(ticker):
    """Generate and serve an annual change bar chart for a ticker."""
    data = stock_annual_change(ticker)
    if not data:
        return "No data found for this ticker.", 404
        
    years = []
    changes = []
    colors = []
    
    for entry in data:
        for year, val_str in entry.items():
            years.append(year)
            # Remove % and convert to float
            try:
                val = float(val_str.replace('%', '').strip())
                changes.append(val)
                colors.append('#10b981' if val >= 0 else '#ef4444') # Use theme colors
            except ValueError:
                continue
                
    if not years:
        return "No valid annual data available.", 404

    # Create the plot
    plt.figure(figsize=(12, 6), facecolor='none')
    plt.style.use('dark_background')
    
    bars = plt.bar(years, changes, color=colors, edgecolor=(1, 1, 1, 0.1), linewidth=1)
    plt.title(f'{ticker} Annual Performance', fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('Change (%)', fontsize=12, labelpad=10)
    plt.xlabel('Year', fontsize=12, labelpad=10)
    plt.xticks(rotation=45)
    
    # Customize grid and spines
    plt.grid(axis='y', linestyle='--', alpha=0.2)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_alpha(0.3)
    plt.gca().spines['bottom'].set_alpha(0.3)
    
    # Add labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + (1 if height > 0 else -3),
                 f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top', 
                 fontsize=9, color='white', alpha=0.8)

    plt.tight_layout()
    
    # Save to buffer
    img = BytesIO()
    plt.savefig(img, format='png', transparent=True, dpi=120)
    img.seek(0)
    plt.close()
    
    return send_file(img, mimetype='image/png')

def create_cashflow_plot(data, title):
    """Helper to generate a cash flow bar chart or an N/A chart."""
    from matplotlib.ticker import FuncFormatter
    
    def format_finance(x, pos):
        """Formatter for Y-axis to show Billions or Millions."""
        abs_x = abs(x)
        if abs_x >= 1e9:
            return f'${x/1e9:.1f}B'
        if abs_x >= 1e6:
            return f'${x/1e6:.1f}M'
        if abs_x >= 1e3:
            return f'${x/1e3:.1f}K'
        return f'${x:.0f}'

    plt.figure(figsize=(12, 6), facecolor='none')
    plt.style.use('dark_background')
    
    if not data:
        # Generate N/A chart
        plt.text(0.5, 0.5, 'N/A', fontsize=50, ha='center', va='center', color='gray', alpha=0.5)
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
    else:
        # Prepare data for grouped bars
        dates = [x[0] for x in data]
        ocf_vals = [x[1] for x in data]
        capex_vals = [x[2] for x in data]
        fcf_vals = [x[3] for x in data]
        
        import numpy as np
        x_indices = np.arange(len(dates))
        width = 0.25
        
        plt.bar(x_indices - width, ocf_vals, width, label='Operating CF', color='#10b981', alpha=0.8)
        plt.bar(x_indices, capex_vals, width, label='CapEx', color='#ef4444', alpha=0.8)
        plt.bar(x_indices + width, fcf_vals, width, label='Free CF', color='#3b82f6', alpha=0.8)
        
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.ylabel('Value', fontsize=12, labelpad=10)
        plt.gca().yaxis.set_major_formatter(FuncFormatter(format_finance))
        plt.xticks(x_indices, dates, rotation=45)
        plt.legend()
        
        plt.grid(axis='y', linestyle='--', alpha=0.2)
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['left'].set_alpha(0.3)
        plt.gca().spines['bottom'].set_alpha(0.3)
        
    plt.tight_layout()
    img = BytesIO()
    plt.savefig(img, format='png', transparent=True, dpi=120)
    img.seek(0)
    plt.close()
    return img

@app.route('/api/annual_cashflow_chart/<ticker>')
def annual_cashflow_chart(ticker):
    """Serve an annual cash flow bar chart."""
    annual, _ = stock_cashflow_change(ticker)
    img = create_cashflow_plot(annual, f'{ticker} Annual Cash Flow')
    return send_file(img, mimetype='image/png')

@app.route('/api/quarterly_cashflow_chart/<ticker>')
def quarterly_cashflow_chart(ticker):
    """Serve a quarterly cash flow bar chart."""
    _, quarterly = stock_cashflow_change(ticker)
    img = create_cashflow_plot(quarterly, f'{ticker} Quarterly Cash Flow')
    return send_file(img, mimetype='image/png')

if __name__ == '__main__':
    # Initialize immediately if running directly
    if tickers:
        print("Starting data verification on startup...")
        verify_and_rebuild_data(tickers)
        
    print("Starting Flask Web Server on http://127.0.0.1:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
