#!/usr/bin/env python3
"""Check correct URLs for MCA, Dutch Safety Board, and NSIA scrapers."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# MCA MGN
print("=== MCA MGN ===")
r = requests.get('https://www.gov.uk/government/collections/marine-guidance-notices-mgns', timeout=10, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
links = [a['href'] for a in s.find_all('a', href=True) if '/government/publications' in a.get('href', '')]
print(f"Status: {r.status_code} | Publication links: {len(links)}")
if links:
    print(f"Sample: {links[:3]}")

# MCA MIN
print("\n=== MCA MIN ===")
r2 = requests.get('https://www.gov.uk/government/collections/marine-information-notices-mins', timeout=10, headers=headers)
s2 = BeautifulSoup(r2.text, 'html.parser')
links2 = [a['href'] for a in s2.find_all('a', href=True) if '/government/publications' in a.get('href', '')]
print(f"Status: {r2.status_code} | Publication links: {len(links2)}")

# Dutch Safety Board
print("\n=== DUTCH SAFETY BOARD ===")
for url in [
    'https://www.onderzoeksraad.nl/en/investigations/marine/',
    'https://www.onderzoeksraad.nl/en/page/4394/marine',
    'https://english.onderzoeksraad.nl/publications/accident-reports',
]:
    try:
        r3 = requests.get(url, timeout=10, headers=headers)
        s3 = BeautifulSoup(r3.text, 'html.parser')
        h1 = s3.find('h1')
        pdfs = [a['href'] for a in s3.find_all('a', href=True) if '.pdf' in a.get('href', '').lower()]
        links3 = [a['href'] for a in s3.find_all('a', href=True) if a.get('href', '').startswith('/en/')]
        print(f"Status: {r3.status_code} | {(h1.text.strip()[:40] if h1 else '')!r} | pdfs={len(pdfs)} | /en/ links={len(links3)} | {url}")
    except Exception as e:
        print(f"FAIL {url}: {e}")

# NSIA Maritime
print("\n=== NSIA NORWAY ===")
for url in [
    'https://www.nsia.no/Maritime',
    'https://www.nsia.no/en/Pages/maritime',
    'https://www.nsia.no/Sjofart',
]:
    try:
        r4 = requests.get(url, timeout=10, headers=headers)
        s4 = BeautifulSoup(r4.text, 'html.parser')
        h1 = s4.find('h1')
        pdfs = [a['href'] for a in s4.find_all('a', href=True) if '.pdf' in a.get('href', '').lower()]
        print(f"Status: {r4.status_code} | {(h1.text.strip()[:40] if h1 else '')!r} | pdfs={len(pdfs)} | {url}")
    except Exception as e:
        print(f"FAIL {url}: {e}")
