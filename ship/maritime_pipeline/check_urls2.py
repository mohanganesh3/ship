#!/usr/bin/env python3
"""Check Dutch Safety Board and NSIA URLs."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# Dutch Safety Board
print("=== DUTCH SAFETY BOARD ===")
urls = [
    'https://www.onderzoeksraad.nl/en/page/3885/marine',
    'https://www.onderzoeksraad.nl/en/investigations/',
    'https://www.onderzoeksraad.nl/en/reports/?sector=marine',
    'https://www.onderzoeksraad.nl/en/publications/',
]
for url in urls:
    try:
        r = requests.get(url, timeout=15, headers=headers)
        s = BeautifulSoup(r.text, 'html.parser')
        h1 = s.find('h1')
        articles = s.find_all('article')
        links = [a['href'] for a in s.find_all('a', href=True) if '/en/' in a.get('href','') or '/page/' in a.get('href','')]
        pdfs = [a['href'] for a in s.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
        print(f"  {r.status_code} | {h1.text.strip()[:40] if h1 else ''!r} | articles={len(articles)} pdfs={len(pdfs)} links={len(links)}")
        print(f"  URL: {url}")
        if links[:3]:
            print(f"  Links: {links[:3]}")
    except Exception as e:
        print(f"  FAIL {url}: {e}")
    print()

# NSIA Norway
print("=== NSIA NORWAY ===")
urls2 = [
    'https://www.nsia.no/Maritime',
    'https://www.nsia.no/Sjofart',
    'https://www.nsia.no/en/maritime',
    'https://www.nsia.no/maritime-investigations',
]
for url in urls2:
    try:
        r = requests.get(url, timeout=15, headers=headers)
        s = BeautifulSoup(r.text, 'html.parser')
        h1 = s.find('h1')
        pdfs = [a['href'] for a in s.find_all('a', href=True) if '.pdf' in a.get('href','').lower()]
        links = [a['href'] for a in s.find_all('a', href=True) if 'maritime' in a.get('href','').lower() or 'nsia' in a.get('href','').lower()]
        print(f"  {r.status_code} | {(h1.text.strip()[:40] if h1 else '')!r} | pdfs={len(pdfs)} links={len(links)}")
        print(f"  URL: {url}")
    except Exception as e:
        print(f"  FAIL {url}: {e}")
    print()
