#!/usr/bin/env python3
"""Debug BIMCO article structure."""
import requests, re, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

url = "https://www.bimco.org/news-insights/bimco-news/"
r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
print("Status:", r.status_code)

soup = BeautifulSoup(r.text, "html.parser")

# Find all links
links = set()
for a in soup.find_all("a", href=True):
    href = a["href"]
    if re.search(r"/news-insights/[^/]+/.+", href):
        links.add(href)

print("Article-like links:")
for l in sorted(links)[:15]:
    print(" ", l)

# Look at one article
if links:
    art_url = "https://www.bimco.org" + sorted(links)[0]
    print("\nFetching article:", art_url)
    r2 = requests.get(art_url, headers=HEADERS, timeout=15, verify=False)
    soup2 = BeautifulSoup(r2.text, "html.parser")
    
    # Check title
    h1 = soup2.find("h1")
    print("Title:", h1.get_text(strip=True) if h1 else "No h1")
    
    # Check content containers
    for sel in ["article", "main", ".article-body", ".content", "[class*=article]", "[class*=content]"]:
        el = soup2.select_one(sel)
        if el:
            txt = el.get_text(separator=" ", strip=True)[:300]
            print(f"Selector '{sel}': {len(txt)} chars: {txt[:100]}")
