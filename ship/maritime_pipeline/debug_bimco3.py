#!/usr/bin/env python3
"""Debug BIMCO sitemap approach."""
import requests, re, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Check sitemap
for sitemap_url in [
    "https://www.bimco.org/sitemap.xml",
    "https://www.bimco.org/robots.txt",
]:
    r = requests.get(sitemap_url, headers=HEADERS, timeout=10, verify=False)
    print(f"URL: {sitemap_url} -> Status: {r.status_code}")
    if r.status_code == 200:
        print(r.text[:500])
    print()

# Also check BIMCO Shipping Explained - long form articles
ship_exp = "https://www.bimco.org/news-insights/shipping-explained/"
r = requests.get(ship_exp, headers=HEADERS, timeout=15, verify=False)
print("Shipping Explained status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")
# Find any links
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/shipping-explained/" in href and href != "/news-insights/shipping-explained/":
        print("  Link:", href)
