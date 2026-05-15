from flask import Flask, render_template, send_from_directory, abort
import json
import os

app = Flask(__name__)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/')
def index():
    # Load EDGAR company data
    config_path = os.path.join(project_root, "config", "edgar_company.json")
    with open(config_path, 'r') as f:
        companies = json.load(f)
    return render_template('filing_portal.html', companies=companies, selected_company=None)

@app.route('/ticker/<ticker>')
def ticker_portal(ticker):
    # Load EDGAR company data
    config_path = os.path.join(project_root, "config", "edgar_company.json")
    with open(config_path, 'r') as f:
        companies = json.load(f)
    
    selected = next((c for c in companies if c["ticker"] == ticker), None)
    return render_template('filing_portal.html', companies=companies, selected_company=selected)

@app.route('/view/<cik>/<filename>')
def view_filing(cik, filename):
    # Ensure CIK is the integer version used in the folder name
    try:
        cik_folder = str(int(cik))
    except:
        cik_folder = cik
        
    directory = os.path.join(project_root, "repository", "10KQ", cik_folder)
    if not os.path.exists(os.path.join(directory, filename)):
        abort(404)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("EDGAR TEST SERVER STARTING")
    print("URL: http://127.0.0.1:5005")
    print("="*50 + "\n")
    app.run(debug=True, port=5005)
