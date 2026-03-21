#!/usr/bin/env python3
"""Test Gard article extraction."""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html',
}

# Test with a known Gard article
test_url = 'https://gard.no/articles/the-importance-of-accurate-emergency-responses-to-vessel-fires/'
print(f"Testing: {test_url}")
r = requests.get(test_url, timeout=15, headers=headers)
s = BeautifulSoup(r.text, 'html.parser')

print(f"Status: {r.status_code}")
print(f"Title: {s.find('h1').text[:60] if s.find('h1') else 'no h1'}")

# Try all selectors
selectors = [
    ('article .article-body', s.select_one('article .article-body')),
    ('div.rich-text', s.select_one('div.rich-text')),
    ('.article-content', s.select_one('.article-content')),
    ('main article', s.select_one('main article')),
    ('main', s.select_one('main')),
    ('.content', s.select_one('.content')),
    ('[class*=article]', s.select_one('[class*=article]')),
    ('[class*=content]', s.select_one('[class*=content]')),
]
for name, el in selectors:
    if el:
        print(f"\n✓ SELECTOR '{name}' found:")
        print(f"  tag: {el.name}, class: {el.get('class', [])}")
        paragraphs = el.find_all(["p", "li", "h2", "h3", "h4"])
        print(f"  paragraphs: {len(paragraphs)}")
        if paragraphs:
            text = '\n'.join(p.get_text(strip=True)[:80] for p in paragraphs[:3])
            print(f"  preview: {text}")

# Show all div classes
print("\n--- Main div classes ---")
for div in s.find_all('div', class_=True)[:20]:
    if any(w in str(div.get('class','')) for w in ['content', 'article', 'text', 'body', 'main']):
        print(f"  {div.get('class')}")
