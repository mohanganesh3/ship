#!/usr/bin/env python3
"""Test safety4sea."""
import requests, urllib3, re
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin

H = {"User-Agent": "Mozilla/5.0 Chrome/120"}

url = "https://safety4sea.com/category/marine-incidents/"
r = requests.get(url, headers=H, timeout=15, verify=False)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")

# Find articles
links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    full = urljoin("https://safety4sea.com", href) if not href.startswith("http") else href
    if "safety4sea.com" in full:
        path = full.split("safety4sea.com")[1].strip("/")
        if path and "/" not in path and len(path) > 10:
            if not any(x in path for x in ["category", "tag", "page", "author"]):
                links.append(full)

print(f"Article links found: {len(links)}")
for l in links[:10]:
    print(" ", l[:100])
