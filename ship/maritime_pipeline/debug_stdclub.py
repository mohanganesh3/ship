#!/usr/bin/env python3
"""Debug Standard Club URL structure"""
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

urls_to_test = [
    "https://www.standard-club.com/knowledge-development/",
    "https://www.standard-club.com/knowledge-development/loss-prevention/",
    "https://www.standard-club.com/media-centre/news/",
]

for url in urls_to_test:
    try:
        r = requests.get(url, headers=headers, timeout=30)
        print(f"\n=== {url} ===")
        print(f"Status: {r.status_code}")
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        article_links = []
        for a in all_links:
            href = a['href']
            # Look for article-like URLs
            if '/knowledge-development/' in href and href.count('/') > 3:
                article_links.append(href)
        
        print(f"Total links: {len(all_links)}")
        print(f"Knowledge-dev deep links: {len(article_links)}")
        for l in article_links[:15]:
            print(f"  {l}")
        
        # Check page structure
        main = soup.find('main') or soup.find('div', class_='main') or soup.find('article')
        if main:
            print(f"Main content found: {main.name} class={main.get('class', [])}")
    except Exception as e:
        print(f"Error: {e}")
