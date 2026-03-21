#!/usr/bin/env python3
"""Parse BIMCO sitemap and find all article URLs."""
import requests, re, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

r = requests.get("https://www.bimco.org/sitemap.xml", headers=HEADERS, timeout=15, verify=False)
soup = BeautifulSoup(r.text, "xml")

all_urls = [loc.get_text() for loc in soup.find_all("loc")]
print(f"Total URLs in sitemap: {len(all_urls)}")

# Filter for articles (news-insights pages with slugs)
article_urls = [u for u in all_urls if re.search(r"/news-insights/[^/]+/[^/]+", u)]
print(f"News/insight articles: {len(article_urls)}")

# Show sample
for u in article_urls[:20]:
    print(" ", u)

# Also check regulatory affairs articles
reg_urls = [u for u in all_urls if "/regulatory-affairs/" in u and u.count("/") > 5]
print(f"\nRegulatory articles: {len(reg_urls)}")
for u in reg_urls[:10]:
    print(" ", u)

# All pages with content
print("\nAll URLs:")
for u in all_urls[:30]:
    print(" ", u)
