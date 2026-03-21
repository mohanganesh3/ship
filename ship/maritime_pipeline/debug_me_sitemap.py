#!/usr/bin/env python3
"""Check Maritime Executive sitemap and alternative article discovery"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

base = "https://maritime-executive.com"

# Check sitemap
sitemap_urls = [
    "/sitemap.xml",
    "/sitemap_index.xml", 
    "/news-sitemap.xml",
    "/post-sitemap.xml",
]

for path in sitemap_urls:
    url = base + path
    r = requests.get(url, headers=headers, timeout=20)
    print(f"{path}: status={r.status_code}, size={len(r.text)}")
    if r.status_code == 200 and '<' in r.text[:100]:
        # Try to parse XML
        try:
            root = ET.fromstring(r.text)
            # Get namespace
            ns = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
            urls = []
            if 'sitemapindex' in root.tag:
                for sitemap in root.iter():
                    if 'loc' in sitemap.tag:
                        urls.append(sitemap.text)
                print(f"  Sitemap index with {len(urls)} child sitemaps")
                for u in urls[:5]:
                    print(f"    {u}")
            else:
                for loc in root.iter():
                    if 'loc' in loc.tag and loc.text:
                        urls.append(loc.text)
                article_urls = [u for u in urls if '/article/' in u or '/blog/' in u]
                print(f"  URLs: {len(urls)} total, {len(article_urls)} articles")
                for u in article_urls[:5]:
                    print(f"    {u}")
        except Exception as e:
            print(f"  Parse error: {e}")
            print(f"  Content: {r.text[:200]}")
    print()
