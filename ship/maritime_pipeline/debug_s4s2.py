#!/usr/bin/env python3
"""Debug Safety4Sea URL structure - test category URLs"""
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Test various URL patterns
test_urls = [
    "https://safety4sea.com/",
    "https://safety4sea.com/news/",
    "https://safety4sea.com/incidents/",
    "https://safety4sea.com/tag/accidents/",
    "https://safety4sea.com/tag/maritime-safety/",
    "https://safety4sea.com/tag/imo/",
    "https://safety4sea.com/tag/marpol/",
    "https://safety4sea.com/tag/environment/",
    "https://safety4sea.com/tag/regulations/",
    "https://safety4sea.com/tag/crew/",
]

def get_article_links(url):
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return r.status_code, []
        soup = BeautifulSoup(r.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'safety4sea.com' in href or href.startswith('/'):
                # Article-like URLs: root-level or short path but not admin/tag/category
                from urllib.parse import urlparse
                parsed = urlparse(href)
                path = parsed.path.strip('/')
                if (path 
                    and not path.startswith('tag/')
                    and not path.startswith('category/')
                    and not path.startswith('author/')
                    and not path.startswith('page/')
                    and not path.startswith('wp-')
                    and not path.startswith('feed')
                    and '.' not in path.split('/')[-1]
                    and len(path) > 10):
                    links.append(href)
        return r.status_code, list(set(links))
    except Exception as e:
        return 0, [str(e)]

for url in test_urls:
    status, links = get_article_links(url)
    print(f"{url}: status={status}, article links={len(links)}")
    for l in links[:5]:
        print(f"  {l}")
    print()
