#!/usr/bin/env python3
"""Deep check of Dutch Safety page 3885 and NSIA report pages."""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}

# Dutch Safety page 3885
print("=== Dutch Safety /en/page/3885/ ===")
r = requests.get('https://onderzoeksraad.nl/en/page/3885/', timeout=15, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
print(f"Title: {s.find('title').text.strip()[:80] if s.find('title') else '?'}")
all_a = s.find_all('a', href=True)
print(f"Total links: {len(all_a)}")
for a in all_a[:60]:
    href = a['href']
    if any(k in href for k in ['/case/', '/publication/', '/report', 'onderzoeksraad', '/page/']):
        print(f"  {href[:100]}")

print()
print("=== NSIA unique report pages ===")
r2 = requests.get('https://www.nsia.no/Marine/Published-reports', timeout=20, headers=headers)
s2 = BeautifulSoup(r2.text, 'html.parser')
seen = set()
report_pages = []
for a in s2.find_all('a', href=True):
    href = a['href']
    if '/Marine/Published-reports/' in href and href not in seen:
        seen.add(href)
        report_pages.append(href)
print(f"Unique report pages: {len(report_pages)}")
print("First 10:", report_pages[:10])

if report_pages:
    test_page = 'https://www.nsia.no' + report_pages[2]
    print(f"\n=== NSIA detail page {report_pages[2]} ===")
    r3 = requests.get(test_page, timeout=20, headers=headers)
    s3 = BeautifulSoup(r3.text, 'html.parser')
    print(f"Status: {r3.status_code}, {len(r3.text)} bytes")
    for a in s3.find_all('a', href=True):
        href = a['href']
        if any(k in href.lower() for k in ['.pdf', 'download', '/media/', '/globalassets/', '/files/']):
            print(f"  PDF-candidate: {href}")
    all_hrefs = [a['href'] for a in s3.find_all('a', href=True)]
    print(f"  All hrefs ({len(all_hrefs)}): {all_hrefs[:40]}")
