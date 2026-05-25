from flask import Flask, render_template, send_from_directory, abort, jsonify
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

@app.route('/funds')
def funds_index():
    config_path = os.path.join(project_root, "config", "edgar_fund.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            funds = json.load(f)
    else:
        funds = []
    return render_template('fund_portal.html', funds=funds, selected_fund=None, thirteen_f_dates=[])

@app.route('/fund/<cik>')
def fund_portal(cik):
    config_path = os.path.join(project_root, "config", "edgar_fund.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            funds = json.load(f)
    else:
        funds = []
        
    selected = next((f for f in funds if str(f["cik"]) == str(cik)), None)
    
    thirteen_f_dates = []
    if selected:
        try:
            cik_folder = f"CIK_{int(selected['cik'])}"
        except:
            cik_folder = f"CIK_{selected['cik']}"
            
        tf_dir = os.path.join(project_root, "repository", "13F", cik_folder)
        if os.path.exists(tf_dir):
            for file in os.listdir(tf_dir):
                if file.endswith('.json') and file != 'base.json':
                    thirteen_f_dates.append(file.replace('.json', ''))
            thirteen_f_dates.sort(reverse=True)
            
    return render_template('fund_portal.html', funds=funds, selected_fund=selected, thirteen_f_dates=thirteen_f_dates)

@app.route('/api/13f/<cik>/<date>')
def get_13f_json(cik, date):
    try:
        cik_folder = f"CIK_{int(cik)}"
    except:
        cik_folder = f"CIK_{cik}"
        
    file_path = os.path.join(project_root, "repository", "13F", cik_folder, f"{date}.json")
    if not os.path.exists(file_path):
        abort(404)
        
    with open(file_path, 'r') as f:
        data = json.load(f)
    return jsonify(data)

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
