#!/usr/bin/env python3
"""Find all working Safety4Sea tag URLs and paginated pages"""
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Test tag pagination
test_tags = [
    "maritime-safety", "imo", "marpol", "accident", "fire", "collision",
    "grounding", "pollution", "solas", "port-state-control", "vessel",
    "seafarer", "navigation", "tanker", "container-ship", "bulk-carrier",
    "psc", "detention", "accident-investigation", "emergency",
]

working_tags = []
for tag in test_tags:
    url = f"https://safety4sea.com/tag/{tag}/"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True) 
                     if 'safety4sea.com' in a.get('href','')
                     and '/tag/' not in a['href'] and '/page/' not in a['href']
                     and '/author/' not in a['href']
                     and len(a['href'].replace('https://safety4sea.com/','').strip('/')) > 10]
            article_links = list(set(l for l in links if len(l.replace('https://safety4sea.com/','').strip('/').split('/')) == 1))
            if len(article_links) > 5:
                working_tags.append((tag, len(article_links)))
                print(f"OK /tag/{tag}/: {len(article_links)} articles, first: {article_links[0] if article_links else 'none'}")
    except Exception as e:
        pass

print(f"\nWorking tags: {len(working_tags)}")
for t, count in working_tags:
    print(f"  /tag/{t}/: {count} articles")

# Also test page 2 on a working tag to check pagination
print("\nTesting pagination on /tag/maritime-safety/")
for page in range(1, 6):
    url = f"https://safety4sea.com/tag/maritime-safety/page/{page}/"
    r = requests.get(url, headers=headers, timeout=15)
    print(f"  Page {page}: status={r.status_code}, len={len(r.text)}")
