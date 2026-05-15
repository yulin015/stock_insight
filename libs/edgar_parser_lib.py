import requests
from lxml import etree
import json
import os
from datetime import datetime
import io

# SEC Headers
HEADERS = {"User-Agent": "chenyulin.ca@gmail.com"}

def parse_ixbrl_10q(ticker, url):
    """
    Consolidated function to fetch, parse, and structure 10-Q data.
    """
    print(f"--- Processing {ticker} 10-Q ---")
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}
        
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        tree = etree.parse(io.BytesIO(resp.content), parser)
        
        def get_elements_by_tag(tag_name):
            return tree.xpath(f"//*[local-name()='{tag_name}']")

        def get_elements_by_name_attr(name_val):
            return tree.xpath(f"//*[@name='{name_val}']")

        def get_safe_text(el):
            if el is None: return ""
            return "".join(el.itertext()).strip().replace("\xa0", " ")

        # Metadata
        company_name = "Unknown"
        name_el = get_elements_by_name_attr("dei:EntityRegistrantName")
        if name_el: company_name = get_safe_text(name_el[0])

        fiscal_period = "Unknown"
        fp_el = get_elements_by_name_attr("dei:DocumentFiscalPeriodFocus")
        if fp_el: fiscal_period = get_safe_text(fp_el[0])
        
        period_end_el = get_elements_by_name_attr("dei:DocumentPeriodEndDate")
        if not period_end_el: period_end_el = get_elements_by_name_attr("DocumentPeriodEndDate")
        if not period_end_el: return {"error": "Could not find DocumentPeriodEndDate"}
        
        raw_date_str = get_safe_text(period_end_el[0])
        period_end_dt = None
        for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
            try:
                period_end_dt = datetime.strptime(raw_date_str, fmt)
                break
            except ValueError: continue
        if not period_end_dt: return {"error": f"Unsupported date format: {raw_date_str}"}
        period_end_str = period_end_dt.strftime("%Y-%m-%d")

        # Contexts
        contexts = {}
        for ctx in get_elements_by_tag("context"):
            ctx_id = ctx.get("id")
            if ctx.xpath(".//*[local-name()='segment']"): continue
            instant = ctx.xpath(".//*[local-name()='instant']/text()")
            start = ctx.xpath(".//*[local-name()='startDate']/text()")
            end = ctx.xpath(".//*[local-name()='endDate']/text()")
            if instant:
                contexts[ctx_id] = {"type": "instant", "date": instant[0]}
            elif start and end:
                s_dt = datetime.strptime(start[0], "%Y-%m-%d")
                e_dt = datetime.strptime(end[0], "%Y-%m-%d")
                months = round((e_dt - s_dt).days / 30)
                contexts[ctx_id] = {"type": "duration", "start": start[0], "end": end[0], "months": months}

        # Periods
        target_periods = {"current_3m": None, "current_ytd": None, "current_bs": None}
        ytd_months = 0
        for cid, info in contexts.items():
            if info["type"] == "instant" and info["date"] == period_end_str:
                target_periods["current_bs"] = cid
            elif info["type"] == "duration" and info["end"] == period_end_str:
                if info["months"] in [3, 4]: target_periods["current_3m"] = cid
                if info["months"] > ytd_months:
                    target_periods["current_ytd"] = cid
                    ytd_months = info["months"]

        # Tags
        tags = {
            "rev": ["us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "us-gaap:SalesRevenueNet", "us-gaap:Revenues"],
            "cos": ["us-gaap:CostOfGoodsAndServicesSold", "us-gaap:CostOfRevenue"],
            "gp": ["us-gaap:GrossProfit"],
            "oi": ["us-gaap:OperatingIncomeLoss"],
            "ni": ["us-gaap:NetIncomeLoss"],
            "eps_basic": ["us-gaap:EarningsPerShareBasic"],
            "eps_diluted": ["us-gaap:EarningsPerShareDiluted"],
            "assets": ["us-gaap:Assets"],
            "liabs": ["us-gaap:Liabilities"],
            "equity": ["us-gaap:StockholdersEquity"],
            "cash": ["us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Cash"],
            "ms_curr": ["us-gaap:MarketableSecuritiesCurrent", "us-gaap:ShortTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent"],
            "ms_noncurr": ["us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesNoncurrent"],
            "ocf": ["us-gaap:NetCashProvidedByUsedInOperatingActivities", "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
            "capex": ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"]
        }

        def get_value(tag_names, context_id):
            if not context_id: return 0.0
            for tag in tag_names:
                elements = get_elements_by_name_attr(tag)
                for el in elements:
                    if el.get("contextRef") == context_id or el.get("contextref") == context_id:
                        text = get_safe_text(el)
                        if not text: continue
                        val = text.replace(",", "").replace("(", "-").replace(")", "").strip()
                        scale = int(el.get("scale", "0"))
                        try: return float(val) * (10**scale)
                        except: continue
            return 0.0

        def get_gross_profit(rev, cos, gp):
            if gp != 0: return gp
            if rev != 0 and cos != 0: return rev - cos
            return 0.0

        def build_is_block(ctx_id):
            rev = get_value(tags["rev"], ctx_id)
            cos = get_value(tags["cos"], ctx_id)
            gp = get_value(tags["gp"], ctx_id)
            return {
                "revenue": rev,
                "cost_of_sales": cos,
                "gross_profit": get_gross_profit(rev, cos, gp),
                "operating_income": get_value(tags["oi"], ctx_id),
                "net_income": get_value(tags["ni"], ctx_id),
                "earnings_per_share": {
                    "basic": get_value(tags["eps_basic"], ctx_id),
                    "diluted": get_value(tags["eps_diluted"], ctx_id)
                }
            }

        # Calculate Cash Pile
        cash = get_value(tags["cash"], target_periods["current_bs"])
        ms_c = get_value(tags["ms_curr"], target_periods["current_bs"])
        ms_nc = get_value(tags["ms_noncurr"], target_periods["current_bs"])

        final_json = {
            "company": company_name,
            "fiscal_period": fiscal_period,
            "period_end_date": period_end_str,
            "income_statement": {
                "three_months_ended": build_is_block(target_periods["current_3m"]),
                "year_to_date": {
                    "months": ytd_months,
                    **build_is_block(target_periods["current_ytd"])
                }
            },
            "balance_sheet": {
                "as_of_date": period_end_str,
                "cash_and_equivalents": cash,
                "marketable_securities_current": ms_c,
                "marketable_securities_non_current": ms_nc,
                "total_cash_and_investments": cash + ms_c + ms_nc,
                "total_assets": get_value(tags["assets"], target_periods["current_bs"]),
                "total_liabilities": get_value(tags["liabs"], target_periods["current_bs"]),
                "total_shareholders_equity": get_value(tags["equity"], target_periods["current_bs"])
            },
            "cash_flow": {
                "year_to_date": {
                    "months": ytd_months,
                    "operating_cash_flow": get_value(tags["ocf"], target_periods["current_ytd"]),
                    "capital_expenditures": get_value(tags["capex"], target_periods["current_ytd"]),
                    "free_cash_flow": get_value(tags["ocf"], target_periods["current_ytd"]) - get_value(tags["capex"], target_periods["current_ytd"])
                }
            }
        }
        return final_json
    except Exception as e: return {"error": str(e)}
