#!/usr/bin/env python3
"""Get actual URLs from Gard sitemaps and test extraction."""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xml',
}

# Get a URL from sitemap
r = requests.get('https://gard.no/sitemaps/insights.xml', timeout=10, headers=headers)
s = BeautifulSoup(r.text, 'xml')
urls = [loc.text for loc in s.find_all('loc')]
print(f"Sitemap URLs: {len(urls)}")
print(f"First 3 URLs: {urls[:3]}")

# Test first article
if urls:
    test_url = urls[0]
    print(f"\n=== Testing {test_url} ===")
    r2 = requests.get(test_url, timeout=15, headers=headers)
    s2 = BeautifulSoup(r2.text, 'html.parser')
    print(f"Status: {r2.status_code}")
    
    # Find all block-level containers with text
    h1 = s2.find('h1')
    print(f"H1: {h1.text[:80] if h1 else 'NONE'}")
    
    # Check all divs with class containing key words
    for div in s2.find_all(['div', 'article', 'section'], class_=True):
        cls = ' '.join(div.get('class', []))
        if any(w in cls.lower() for w in ['content', 'body', 'article', 'text', 'main', 'rich']):
            ps = div.find_all('p')
            if ps and len(' '.join(p.get_text() for p in ps).split()) > 50:
                print(f"\nGOOD DIV: class={cls!r}")
                print(f"  Word count: {len(' '.join(p.get_text() for p in ps).split())}")
                print(f"  First para: {ps[0].get_text()[:100]}")
                break
    
    # Show all class names that have meaningful content
    print("\n--- All significant divs ---")
    for div in s2.find_all(['div', 'article','section'], class_=True):
        cls = ' '.join(div.get('class', []))
        ps = div.find_all('p', recursive=False)
        words = sum(len(p.get_text().split()) for p in ps)
        if words > 30:
            print(f"  {cls!r}: {len(ps)} p-tags, {words} words")
