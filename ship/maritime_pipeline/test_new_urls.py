#!/usr/bin/env python3
"""Test URL accessibility for new scrapers."""
import requests, urllib3
urllib3.disable_warnings()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

urls = [
    "https://www.classnk.or.jp/hp/en/publications_outlines.html",
    "https://www.hellenicshippingnews.com/maritime-news/accidents-hazards/",
    "https://www.standard-club.com/knowledge-development/loss-prevention/",
]

for url in urls:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        print(f"OK {r.status_code}: {url[:70]}")
    except Exception as exc:
        print(f"FAIL: {url[:70]} -> {exc}")
