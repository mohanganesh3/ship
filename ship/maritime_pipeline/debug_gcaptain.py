#!/usr/bin/env python3
"""Check gCaptain sitemap"""
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

sitemap_urls = [
    "https://gcaptain.com/sitemap.xml",
    "https://gcaptain.com/sitemap_index.xml",
    "https://gcaptain.com/post-sitemap.xml",
    "https://gcaptain.com/news-sitemap.xml",
]

for url in sitemap_urls:
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"{url}: {r.status_code}, {len(r.text)} chars")
        if r.status_code == 200 and r.text.strip().startswith('<?xml') or r.text.strip().startswith('<'):
            try:
                root = ET.fromstring(r.text)
                locs = []
                for elem in root.iter():
                    if 'loc' in elem.tag and elem.text:
                        locs.append(elem.text.strip())
                print(f"  XML: {len(locs)} URLs")
                for l in locs[:5]:
                    print(f"    {l}")
            except Exception as e:
                print(f"  Parse error: {e}")
                print(f"  Content: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    print()
