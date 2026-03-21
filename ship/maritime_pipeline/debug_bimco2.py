#!/usr/bin/env python3
"""Debug BIMCO - check if there's an API or alternate method."""
import requests, re, urllib3, json
urllib3.disable_warnings()
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Try the Umbraco REST API endpoint BIMCO often uses
api_urls = [
    "https://www.bimco.org/umbraco/api/news/getnews?page=1&pageSize=20",
    "https://www.bimco.org/api/search/news?q=&page=1&pageSize=20",
    "https://www.bimco.org/api/news?page=1",
    "https://www.bimco.org/news-insights/bimco-news/?page=1",
]

for api_url in api_urls:
    r = requests.get(api_url, headers=HEADERS, timeout=10, verify=False)
    print(f"URL: {api_url} -> Status: {r.status_code}, Content-Type: {r.headers.get('content-type','')[:50]}")
    if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
        data = r.json()
        print("JSON keys:", list(data.keys()) if isinstance(data, dict) else type(data))
        print()

# Try fetching a known BIMCO article directly
known_article = "https://www.bimco.org/news-insights/bimco-news/2024/01/10-key-topics-for-shipping-in-2024"
print("\nFetching known article:", known_article)
r = requests.get(known_article, headers=HEADERS, timeout=15, verify=False)
print("Status:", r.status_code)
if r.status_code == 200:
    soup = BeautifulSoup(r.text, "html.parser")
    h1 = soup.find("h1")
    print("Title:", h1.get_text() if h1 else "No h1")
    # Check all divs for content
    for div in soup.find_all("div", class_=True):
        classes = " ".join(div.get("class", []))
        txt = div.get_text(strip=True)
        if len(txt) > 200 and len(txt) < 5000:
            print(f"  DIV class={classes[:60]}: {txt[:150]}")
