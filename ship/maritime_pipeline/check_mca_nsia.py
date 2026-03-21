#!/usr/bin/env python3
"""Find correct MCA MIN URL and check NSIA PDF issue."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# MCA MIN - try various spellings
print("=== MCA MIN URLs ===")
for url in [
    'https://www.gov.uk/government/collections/marine-information-notices-mins',
    'https://www.gov.uk/government/collections/marine-information-notices-min',
    'https://www.gov.uk/government/collections/min-marine-information-notices',
    'https://www.gov.uk/government/collections/marine-information-notices',
]:
    r = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
    h1 = BeautifulSoup(r.text, 'html.parser').find('h1')
    print(f"  {r.status_code} {r.url[:80]} | {h1.text.strip()[:40] if h1 else ''}")

# NSIA - check if downloads are failing due to URL mismatch
print()
print("=== NSIA RSS items ===")
r2 = requests.get('https://www.nsia.no/rss?lcid=1033&type=3', timeout=15, headers=headers)
s2 = BeautifulSoup(r2.content, 'xml')
items = s2.find_all('item')
print(f"RSS items: {len(items)}")
for item in items[:3]:
    link = item.find('link')
    enc = item.find('enclosure')  
    print(f"  Title: {item.find('title').text[:50] if item.find('title') else ''}")
    print(f"  Link: {link.text if link else ''}")
    print(f"  Enclosure: {enc.get('url','') if enc else 'none'}")
    
    # Try to get actual PDF from detail page
    if link:
        r3 = requests.get(link.text.strip(), timeout=10, headers=headers)
        s3 = BeautifulSoup(r3.text, 'html.parser')
        pdfs = [a['href'] for a in s3.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
        print(f"  PDFs on detail page: {pdfs[:2]}")
    print()
