#!/usr/bin/env python3
"""Debug Hellenic Shipping News URL structure."""
import requests, urllib3, re
urllib3.disable_warnings()
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Check main site
r = requests.get("https://www.hellenicshippingnews.com/", headers=HEADERS, timeout=15, verify=False)
print("Main status:", r.status_code)

soup = BeautifulSoup(r.text, "html.parser")
# Find main navigation links
nav = soup.find("nav") or soup.find("header")
if nav:
    for a in nav.find_all("a", href=True)[:20]:
        href = a["href"]
        if "hellenicshippingnews" in href or href.startswith("/"):
            print("NAV:", href[:80])

# Look at all category links
print("\nCategory links on homepage:")
for a in soup.find_all("a", href=True):
    href = a["href"]
    if re.search(r"category|section|topic", href, re.I):
        print(" ", href[:80])

# Test some different URL patterns
test_urls = [
    "https://www.hellenicshippingnews.com/category/maritime-news/",
    "https://www.hellenicshippingnews.com/category/accidents/",
    "https://www.hellenicshippingnews.com/maritime-safety-news/",
    "https://www.hellenicshippingnews.com/safety/",
]
for url in test_urls:
    r2 = requests.get(url, headers=HEADERS, timeout=10, verify=False)
    print(f"Status {r2.status_code}: {url}")
