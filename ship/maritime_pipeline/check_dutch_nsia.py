#!/usr/bin/env python3
"""Quick test of Dutch Safety sitemap + NSIA Marine/Published-reports."""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}

# 1. Dutch Safety Board - try their sitemap
print("=== Dutch Safety Board sitemap ===")
try:
    r = requests.get('https://www.onderzoeksraad.nl/sitemap.xml', timeout=10, headers=headers)
    print(f"sitemap.xml: {r.status_code}, {len(r.text)} bytes")
    if r.status_code == 200:
        print(r.text[:500])
except Exception as e:
    print(f"Error: {e}")

# 2. Dutch Safety - try direct old URL style
print()
print("=== Dutch Safety /en/home/publications/ ===")
try:
    r2 = requests.get('https://onderzoeksraad.nl/en/home/publications/', timeout=10, headers=headers)
    print(f"Status: {r2.status_code}, {len(r2.text)} bytes")
    s2 = BeautifulSoup(r2.text, 'html.parser')
    links = [a['href'] for a in s2.find_all('a', href=True) if 'case' in a['href'] or 'report' in a.get('href','').lower()]
    print(f"Case/report links: {links[:10]}")
except Exception as e:
    print(f"Error: {e}")

# 3. Dutch Safety - try page 3885 old URL (was marine)
print()
print("=== Dutch Safety /en/page/3885 ===")
try:
    r3 = requests.get('https://onderzoeksraad.nl/en/page/3885/', timeout=10, headers=headers)
    print(f"Status: {r3.status_code}")
except Exception as e:
    print(f"Error: {e}")

# 4. NSIA Published-reports listing (with short timeout)
print()
print("=== NSIA Marine/Published-reports ===")
try:
    r4 = requests.get('https://www.nsia.no/Marine/Published-reports', timeout=20, headers=headers)
    print(f"Status: {r4.status_code}, {len(r4.text)} bytes")
    s4 = BeautifulSoup(r4.text, 'html.parser')
    # Find all links in page
    all_links = [a['href'] for a in s4.find_all('a', href=True) if '/Marine/' in a.get('href','')]
    print(f"Marine links ({len(all_links)}): {all_links[:20]}")
    pdfs = [a['href'] for a in s4.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
    print(f"PDF links: {pdfs[:5]}")
except Exception as e:
    print(f"Error: {e}")
