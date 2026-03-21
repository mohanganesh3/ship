#!/usr/bin/env python3
"""Final checks for NSIA and MCA MIN."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# MCA MIN - the correct URL found from search
print("=== MCA MIN collection ===")
r = requests.get('https://www.gov.uk/government/collections/marine-information-notes-mins', timeout=10, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
h1 = s.find('h1')
links = [a['href'] for a in s.find_all('a', href=True) if '/government/publications' in a.get('href','')]
print(f"Status: {r.status_code} | {h1.text.strip()[:60] if h1 else ''} | pubs: {len(links)}")

print()

# NSIA - Published-reports page
print("=== NSIA /Marine/Published-reports ===")
r2 = requests.get('https://www.nsia.no/Marine/Published-reports', timeout=15, headers=headers)
s2 = BeautifulSoup(r2.text, 'html.parser')
print(f"Status: {r2.status_code}")
# Find all links
links2 = [a['href'] for a in s2.find_all('a', href=True) if '/Marine/' in a.get('href','')]
print(f"Marine links: {links2[:15]}")
# Find PDFs
pdfs2 = [a['href'] for a in s2.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
print(f"PDFs: {pdfs2[:5]}")

# Check one report detail page
print()
print("=== NSIA detail page 2026-01 ===")
r3 = requests.get('https://www.nsia.no/Marine/Published-reports/2026-01', timeout=15, headers=headers)
s3 = BeautifulSoup(r3.text, 'html.parser')
for a in s3.find_all('a', href=True):
    href = a['href']
    if '.pdf' in href.lower() or 'download' in href.lower() or '/media/' in href.lower():
        print(f"  {href}")
print("All hrefs:", [a['href'] for a in s3.find_all('a', href=True)])
