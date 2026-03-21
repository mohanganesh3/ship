#!/usr/bin/env python3
"""Check Standard Club for sitemap/RSS/API"""
import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

urls = [
    "https://www.standard-club.com/sitemap.xml",
    "https://www.standard-club.com/sitemap_index.xml",
    "https://www.standard-club.com/feed.xml",
    "https://www.standard-club.com/rss.xml",
    "https://www.standard-club.com/knowledge-development/feed/",
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"{url}: {r.status_code} ({len(r.text)} chars)")
        if r.status_code == 200:
            print(r.text[:500])
    except Exception as e:
        print(f"{url}: Error - {e}")
    print()
