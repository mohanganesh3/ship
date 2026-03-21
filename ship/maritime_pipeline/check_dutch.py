#!/usr/bin/env python3
"""Check Dutch Safety Board and NSIA URLs - deeper probe."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# Dutch Safety Board /en/investigations/ - see all links
print("=== DUTCH SAFETY - ALL LINKS ON /en/investigations/ ===")
r = requests.get('https://www.onderzoeksraad.nl/en/investigations/', timeout=15, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
for a in s.find_all('a', href=True):
    href = a['href']
    if href and not href.startswith('#'):
        print(f"  {href[:100]}")

print()
print("=== DUTCH SAFETY - RAW HTML SNIPPET ===")
print(r.text[2000:4000])
