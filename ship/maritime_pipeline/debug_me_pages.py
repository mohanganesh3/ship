#!/usr/bin/env python3
"""Test Maritime Executive pagination"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

base = "https://maritime-executive.com"

def count_articles(url):
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return r.status_code, 0
    soup = BeautifulSoup(r.text, 'html.parser')
    articles = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            href = urljoin(base, href)
        path = urlparse(href).path.strip('/')
        if path and (path.startswith('article/') or path.startswith('blog/')) and len(path) > 15:
            articles.add(href)
    return r.status_code, len(articles)

# Test different pagination formats
test_urls = [
    "/article/",
    "/article/?page=2",
    "/article/?page=3",
    "/article/page/2/",
    "/article/page/2",
]

for path in test_urls:
    url = base + path
    status, count = count_articles(url)
    print(f"{path}: status={status}, articles={count}")
