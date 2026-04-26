import xml.etree.ElementTree as ET
import json
import argparse
import os

def process_13f(primary_xml_path, holding_xml_path, output_json_path):
    """
    Parses SEC 13F Primary and Holding XMLs, aggregates by CUSIP, and saves as JSON.
    """
    print(f"Processing Primary XML: {primary_xml_path}")
    print(f"Processing Holding XML: {holding_xml_path}")

    # Parse Primary XML
    tree_primary = ET.parse(primary_xml_path)
    root_primary = tree_primary.getroot()
    
    # Namespaces - SEC EDGAR XMLs often use these namespaces
    ns = {'ns': 'http://www.sec.gov/edgar/thirteenffiler'}
    
    # Find metadata fields
    submission_type = root_primary.find('.//ns:submissionType', ns)
    period_of_report = root_primary.find('.//ns:periodOfReport', ns)
    signature_date = root_primary.find('.//ns:signatureDate', ns)
    table_value_total = root_primary.find('.//ns:tableValueTotal', ns)
    
    form_data = {
        "submission_type": submission_type.text if submission_type is not None else "N/A",
        "period_of_report": period_of_report.text if period_of_report is not None else "N/A",
        "signature_date": signature_date.text if signature_date is not None else "N/A",
        "table_value_total": int(table_value_total.text) if table_value_total is not None else 0
    }
    
    # Parse Holding XML
    tree_holding = ET.parse(holding_xml_path)
    root_holding = tree_holding.getroot()
    
    # Namespace for information table
    ns_h = {'ns': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
    
    holdings_map = {}
    
    # Iterate through all infoTable entries
    for info in root_holding.findall('.//ns:infoTable', ns_h):
        cusip = info.find('ns:cusip', ns_h).text
        name = info.find('ns:nameOfIssuer', ns_h).text
        title = info.find('ns:titleOfClass', ns_h).text
        value = int(info.find('ns:value', ns_h).text)
        shares_node = info.find('.//ns:sshPrnamt', ns_h)
        shares = int(shares_node.text) if shares_node is not None else 0
        type_node = info.find('.//ns:sshPrnamtType', ns_h)
        shares_type = type_node.text if type_node is not None else "SH"
        
        # Aggregate by CUSIP
        if cusip in holdings_map:
            holdings_map[cusip]['value'] += value
            holdings_map[cusip]['shares_or_principal_amount']['ssh_prnamt'] += shares
        else:
            holdings_map[cusip] = {
                "name_of_issuer": name,
                "title_of_class": title,
                "cusip": cusip,
                "value": value,
                "shares_or_principal_amount": {
                    "ssh_prnamt": shares,
                    "ssh_prnamt_type": shares_type
                }
            }
            
    # Convert map back to list
    holdings_list = list(holdings_map.values())
    
    # Sort by value descending (largest positions first)
    holdings_list.sort(key=lambda x: x['value'], reverse=True)
    
    result = {
        "form_data": form_data,
        "holdings": holdings_list
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    
    with open(output_json_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Successfully saved aggregated JSON to: {output_json_path}")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process SEC 13F XML filings.")
    parser.add_argument("--primary", required=True, help="Path to primary XML file")
    parser.add_argument("--holding", required=True, help="Path to holdings XML file")
    parser.add_argument("--output", required=True, help="Path to save output JSON")
    
    args = parser.parse_args()
    
    try:
        process_13f(args.primary, args.holding, args.output)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
