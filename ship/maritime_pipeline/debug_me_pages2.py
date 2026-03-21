#!/usr/bin/env python3
"""Test Maritime Executive - find listing structure"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

base = "https://maritime-executive.com"

# Check page 1 vs page 2 - are they same?
r1 = requests.get(base + "/article/", headers=headers, timeout=20)
r2 = requests.get(base + "/article/?page=2", headers=headers, timeout=20)

soup1 = BeautifulSoup(r1.text, 'html.parser')
soup2 = BeautifulSoup(r2.text, 'html.parser')

def get_articles(soup):
    articles = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            href = urljoin(base, href)
        path = urlparse(href).path.strip('/')
        if path and (path.startswith('article/') or path.startswith('blog/')) and len(path) > 15:
            articles.add(href)
    return articles

a1 = get_articles(soup1)
a2 = get_articles(soup2)
print(f"Page 1: {len(a1)} articles")
print(f"Page 2: {len(a2)} articles")
print(f"Overlap: {len(a1 & a2)}")
print(f"Unique in p2: {len(a2 - a1)}")
print("P1 sample:", list(a1)[:3])
print("P2 unique:", list(a2 - a1)[:5])

# Try different formats
other_urls = [
    "/article/?paged=2",
    "/article/?p=2",
    "/article/2/",
    "/?cat=article&paged=2",
]
for path in other_urls:
    r = requests.get(base + path, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    arts = get_articles(soup)
    ov = len(arts & a1)
    print(f"{path}: status={r.status_code}, articles={len(arts)}, overlap with p1={ov}")
