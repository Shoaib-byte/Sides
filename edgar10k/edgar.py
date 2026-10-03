import os
import requests

HEADERS = {"User-agent": "Syed Harooni saharooni68@gmail.com"}

def ticker_to_cik(ticker: str) -> int:
    data = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS).json()
    for row in data.values():
        if row["ticker"] == ticker.upper():
            return row["cik_str"]
    raise ValueError(f"Unknown ticker {ticker}")

def latest_10k_url(cik: int) -> str:
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    recent = requests.get(url, headers=HEADERS).json()["filings"]["recent"]
    i = recent["form"].index("10-K")        
    acc = recent["accessionNumber"][i].replace("-", "")
    doc = recent["primaryDocument"][i]
    
    filing_date = recent["filingDate"][i]
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
    return filing_date, filing_url  

def get_and_cache10k(ticker: str):
    cik = ticker_to_cik(ticker)
    filing_date, url  = latest_10k_url(cik)

    filename = f"{ticker.upper()}_{filing_date}_10k.html"

    if os.path.exists(filename):
        print(f"Loading {filename} from cache...")
        with open(filename, "r", encoding="UTF-8") as file:
            html_content = file.read()
    else:
        print(f"Fetching {ticker} 10-K from SEC website...")
        response = requests.get(url, headers=HEADERS)
        html_content = response.text
        
        
        with open(filename, "w", encoding="utf-8") as file:
            file.write(html_content)
            
    print(f"Filing Date: {filing_date}")
    return html_content
