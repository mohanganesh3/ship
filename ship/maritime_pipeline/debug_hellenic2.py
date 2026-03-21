#!/usr/bin/env python3
"""Debug Hellenic article links."""
import requests, urllib3, re
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

url = "https://www.hellenicshippingnews.com/category/shipping-news/international-shipping-news/"
r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")

print("\nAll article links (sample):")
count = 0
for a in soup.find_all("a", href=True):
    href = a["href"]
    full = urljoin("https://www.hellenicshippingnews.com", href) if not href.startswith("http") else href
    if "hellenicshippingnews.com" in full and full != url:
        print(" ", full[:100])
        count += 1
        if count >= 20:
            break

# Check if site uses /?p=... pattern instead of date
print("\nLooking for article URLs with date pattern:")
for a in soup.find_all("a", href=True):
    href = a.get("href", "")
    if re.search(r"/20\d{2}/", href):
        print(" DATE:", href[:100])
        break
    elif re.search(r"/p=\d+", href):
        print(" QUERY:", href[:100])
        break
