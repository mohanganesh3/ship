#!/usr/bin/env python3
"""Fix NSIA PDF resolution and find MCA MIN."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# NSIA - check the Published-reports page for PDF links
print("=== NSIA Published-reports ===")
r = requests.get('https://nsia.no/Marine/Published-reports/2026-01', timeout=15, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
print(f"Status: {r.status_code}")
all_links = [a['href'] for a in s.find_all('a', href=True) if a.get('href')]
print(f"All links: {all_links[:20]}")
# find PDFs
pdfs = [a['href'] for a in s.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
print(f"PDFs: {pdfs}")

print()
print("=== NSIA Marine main page ===")
r2 = requests.get('https://www.nsia.no/Marine', timeout=15, headers=headers)
s2 = BeautifulSoup(r2.text, 'html.parser')
print(f"Status: {r2.status_code}")
links2 = [a['href'] for a in s2.find_all('a', href=True) if '/Marine/' in a.get('href','') or '/Sjofart/' in a.get('href','')]
print(f"Marine links: {links2[:15]}")

print()
print("=== MCA MIN - search GOV.UK ===")
# Use GOV.UK search to find the MIN collection
r3 = requests.get('https://www.gov.uk/search/all',
    params={'keywords': 'marine information notice MIN', 'organisations[]': 'maritime-and-coastguard-agency', 'content_purpose_document_supertype': 'collection'},
    timeout=15, headers=headers)
s3 = BeautifulSoup(r3.text, 'html.parser')
links3 = [a['href'] for a in s3.find_all('a', href=True) if 'min' in a.get('href','').lower() and 'collection' in a.get('href','').lower()]
print(f"MIN collection links: {links3[:5]}")
# Also try searching for MINs directly
for url in ['https://www.gov.uk/government/collections/mins-marine-information-notices',
             'https://www.gov.uk/government/collections/marine-information-notice']:
    rr = requests.get(url, timeout=5, headers=headers)
    print(f"  {rr.status_code} {url}")
