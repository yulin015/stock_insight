import requests
import json
import os

# SEC EDGAR API compliance headers
HEADERS = {
    "User-Agent": "chenyulin.ca@gmail.com"
}

def edgar_get_k10(ticker_symbol: str) -> bool:
    """
    Fetch 10-K and 10-Q filing metadata from SEC EDGAR and update config/edgar_company.json.
    
    Args:
        ticker_symbol (str): The stock ticker symbol.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # 1. Determine paths
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_root, "config", "edgar_company.json")
        
        if not os.path.exists(config_file):
            print(f"Error: {config_file} not found.")
            return False
            
        # 2. Load company metadata
        with open(config_file, 'r') as f:
            companies = json.load(f)
            
        # 3. Find matching company
        company = next((c for c in companies if c["ticker"] == ticker_symbol), None)
        if not company:
            print(f"Error: Ticker {ticker_symbol} not found in {config_file}.")
            return False
            
        submission_data = company["submission"]
        if isinstance(submission_data, str):
            submission_urls = [submission_data]
        else:
            submission_urls = submission_data
            
        cik = company["cik"]
        
        # Aggregate all filings from all submission JSONs
        all_recent_filings = []
        
        for submission_url in submission_urls:
            # 4. Fetch submission JSON
            print(f"Fetching metadata from {submission_url}...")
            response = requests.get(submission_url, headers=HEADERS)
            if response.status_code != 200:
                print(f"Error: Failed to fetch {submission_url} (Status: {response.status_code})")
                continue
                
            data = response.json()
            recent = data.get("filings", {}).get("recent", {})
            
            # If not nested, check if it's a flat historical file
            if not recent and "form" in data:
                recent = data
                
            if not recent:
                continue
            
            all_recent_filings.append(recent)
            
            # 4b. Discover historical submission JSONs if not already in list
            files = data.get("filings", {}).get("files", [])
            for f in files:
                f_name = f.get("name")
                if f_name:
                    f_url = f"https://data.sec.gov/submissions/{f_name}"
                    if f_url not in submission_urls:
                        print(f"Discovered historical submission file: {f_url}")
                        submission_urls.append(f_url)
                        if isinstance(company["submission"], str):
                            company["submission"] = [company["submission"], f_url]
                        elif f_url not in company["submission"]:
                            company["submission"].append(f_url)
            
        if not all_recent_filings:
            print(f"Error: No valid filings found for {ticker_symbol} across all submission URLs.")
            return False
            
        # 5. Extract 10-K and 10-Q from aggregated filings
        if "forms" not in company:
            company["forms"] = []
            
        existing_accessions = {f["accession"] for f in company["forms"]}
        new_forms_added = 0
        
        for recent in all_recent_filings:
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            docs = recent.get("primaryDocument", [])
            dates = recent.get("filingDate", [])
            
            for i in range(len(forms)):
                form_type = forms[i]
                # Track 10-K, 10-Q, and international equivalents 40-F, 20-F
                if form_type in ["10-K", "10-Q", "40-F", "20-F"]:
                    accession = accessions[i]
                    
                    if accession in existing_accessions:
                        continue
                        
                    document = docs[i] if docs[i] else ".html"
                    filing_date = dates[i]
                    
                    # Build URL
                    cik_int = int(cik)
                    accession_no_dash = accession.replace("-", "")
                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dash}/{document}"
                    
                    # Create form dict
                    form_dict = {
                        "type": form_type,
                        "date": filing_date,
                        "accession": accession,
                        "document": document,
                        "url": filing_url
                    }
                    
                    company["forms"].append(form_dict)
                    existing_accessions.add(accession)
                    new_forms_added += 1
                
        # 6. Download files
        save_dir = os.path.join(project_root, "repository", "10KQ", str(int(cik)))
        os.makedirs(save_dir, exist_ok=True)
        
        download_count = 0
        for form in company["forms"]:
            target_filename = f"{form['date']}_{form['document']}"
            target_path = os.path.join(save_dir, target_filename)
            
            if not os.path.exists(target_path):
                print(f"Downloading {form['url']} to {target_filename}...")
                try:
                    f_resp = requests.get(form['url'], headers=HEADERS)
                    if f_resp.status_code == 200:
                        with open(target_path, 'w', encoding='utf-8') as f_out:
                            f_out.write(f_resp.text)
                        download_count += 1
                    else:
                        print(f"Warning: Failed to download {form['url']} (Status: {f_resp.status_code})")
                except Exception as e:
                    print(f"Error downloading {form['url']}: {e}")

        if download_count > 0:
            print(f"Downloaded {download_count} new files.")

        # 7. Save updated metadata
        if new_forms_added > 0:
            # Sort forms by date descending (latest first)
            company["forms"].sort(key=lambda x: x["date"], reverse=True)
            
            with open(config_file, 'w') as f:
                json.dump(companies, f, indent=4)
            print(f"Successfully updated JSON for {ticker_symbol} (added {new_forms_added} entries).")
        
        return True

    except Exception as e:
        print(f"Unexpected error in edgar_get_k10 for {ticker_symbol}: {e}")
        return False
