#!/usr/bin/env python3
"""Test fetching a BIMCO article from sitemap URL."""
import requests, re, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Test a specific article
url = "https://www.bimco.org/news-insights/bimco-news/2026/02/17-bwm-results/"
r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
print("Status:", r.status_code)

soup = BeautifulSoup(r.text, "html.parser")
h1 = soup.find("h1")
print("H1:", h1.get_text() if h1 else "NONE")

# Look for all text containers
print("\nLooking for content divs:")
for div in soup.find_all(["div", "section", "article"]):
    classes = " ".join(div.get("class", []))
    txt = div.get_text(separator=" ", strip=True)
    if 200 < len(txt) < 10000 and not any(skip in classes for skip in ["header", "nav", "menu", "footer"]):
        print(f"  {div.name} class={classes[:80]}: len={len(txt)}")
        print(f"    Preview: {txt[:200]}")
        print()
