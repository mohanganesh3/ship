#!/usr/bin/env python3
"""Check Dutch shipping page and NSIA."""
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# Dutch Safety Board shipping theme
print("=== DUTCH SAFETY - /en/thema/shipping/ ===")
r = requests.get('https://onderzoeksraad.nl/en/thema/shipping/', timeout=15, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')
articles = s.find_all('article')
print(f"Status: {r.status_code} | articles: {len(articles)}")
# Look for investigation links  
for a in s.find_all('a', href=True)[:40]:
    href = a['href']
    if '/investigation' in href or '/publication' in href or '/report' in href:
        print(f"  {href[:100]}")

print()

# The investigations API
print("=== DUTCH SAFETY - INVESTIGATIONS API ===")
r2 = requests.get('https://onderzoeksraad.nl/en/home/investigations/', 
    params={'_sort': 'date:DESC', '_page': 1, '_thema_tax': 'shipping'},
    timeout=15, headers=headers)
s2 = BeautifulSoup(r2.text, 'html.parser')
print(f"Status: {r2.status_code}")
for a in s2.find_all('a', href=True):
    href = a['href']
    if '/investigation' in href or '/publication' in href:
        print(f"  {href[:100]}")

print()

# NSIA - check sjofart page  
print("=== NSIA /Sjofart ===")
r3 = requests.get('https://www.nsia.no/Sjofart', timeout=15, headers=headers)
s3 = BeautifulSoup(r3.text, 'html.parser')
print(f"Status: {r3.status_code}")
all_links = [a['href'] for a in s3.find_all('a', href=True) if a.get('href')]
print(f"Total links: {len(all_links)}")
print(f"Sample: {all_links[:10]}")
print(r3.text[1000:3000])
