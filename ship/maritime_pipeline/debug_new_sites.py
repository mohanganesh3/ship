#!/usr/bin/env python3
"""Quick test of gCaptain and Maritime Executive URL structures"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_site(base, sections, article_filter):
    for section in sections:
        url = base + section
        try:
            r = requests.get(url, headers=headers, timeout=20)
            print(f"\n{url}: status={r.status_code}")
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                articles = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if not href.startswith('http'):
                        href = urljoin(base, href)
                    if base.replace('https://', '') in href:
                        path = urlparse(href).path.strip('/')
                        if article_filter(path):
                            articles.append(href)
                articles = list(set(articles))
                print(f"  Articles found: {len(articles)}")
                for a in articles[:4]:
                    print(f"    {a}")
        except Exception as e:
            print(f"{url}: Error - {e}")

print("=== gCaptain ===")
def gc_filter(path):
    return (path and len(path) > 10 
            and not path.startswith(('category', 'tag', 'page', 'author', 'wp-', 'feed', 'contact', 'about'))
            and '?' not in path)
test_site("https://gcaptain.com", ["/maritime-news/", "/technology/", "/ports/"], gc_filter)

print("\n\n=== Maritime Executive ===")
def me_filter(path):
    return (path and (path.startswith(('article/', 'editorials/', 'blog/')))
            and len(path) > 15 and '?' not in path)
test_site("https://maritime-executive.com", ["/article/", "/editorials/", "/blog/"], me_filter)
