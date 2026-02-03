import re
import html
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

OUTPUT = "feed.xml"

SOURCES = [
    SOURCES = [
    ("Wecandoo Toulouse", "https://wecandoo.fr/ateliers/toulouse"),
    ("Quai des Savoirs Agenda", "https://quaidessavoirs.toulouse-metropole.fr/agenda/"),
]


MAX_ITEMS_PER_SOURCE = 15

def fetch(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (toulouse-rss-bot/1.0)"}
    r = requests.get(url, headers=headers, timeout=40)
    r.raise_for_status()
    return r.text

def absolute_url(base: str, link: str) -> str:
    if link.startswith("http"):
        return link
    parsed = urlparse(base)
    return f"{parsed.scheme}://{parsed.netloc}{link if link.startswith('/') else '/' + link}"

def guess_items(base_url: str, html_text: str):
    soup = BeautifulSoup(html_text, "lxml")
    links = soup.select("a[href]")

    candidates = []
    for a in links:
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)

        if not href or not text:
            continue
        if len(text) < 6:
            continue
        if any(bad in href for bad in ["#", "javascript:", "/login", "/signup", "/account"]):
            continue
        if any(bad in text.lower() for bad in ["cookie", "privacy", "terms", "contact", "menu"]):
            continue

        full = absolute_url(base_url, href)
        candidates.append((text, full))

    seen = set()
    items = []
    for title, link in candidates:
        if link in seen:
            continue
        seen.add(link)

        looks_like_experience = (
            re.search(r"(atelier|workshop|cours|initiation|stage|masterclass)", title, re.I)
            or re.search(r"(atelier|workshop|event|evenement|billet|ticket)", link, re.I)
        )

        if looks_like_experience:
            items.append((title, link))

    return items[:MAX_ITEMS_PER_SOURCE]

def rfc822_now():
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def make_guid(title: str, link: str) -> str:
    return hashlib.sha256((title + link).encode("utf-8")).hexdigest()

def main():
    all_items = []
    for source_name, url in SOURCES:
    try:
        page = fetch(url)
    except Exception as e:
        print(f"Skipping {source_name}. Reason: {e}")
        continue

    items = guess_items(url, page)
    for title, link in items:
        all_items.append((source_name, title, link))


    seen_links = set()
    deduped = []
    for src, title, link in all_items:
        if link in seen_links:
            continue
        seen_links.add(link)
        deduped.append((src, title, link))

    build_date = rfc822_now()

    items_xml = []
    for src, title, link in deduped[:50]:
        safe_title = html.escape(f"{title} ({src})")
        safe_link = html.escape(link)
        guid = make_guid(title, link)
        desc = f"Source: {html.escape(src)}<br/>Link: {safe_link}"

        items_xml.append(f"""
        <item>
          <title>{safe_title}</title>
          <link>{safe_link}</link>
          <guid isPermaLink="false">{guid}</guid>
          <pubDate>{build_date}</pubDate>
          <description><![CDATA[{desc}]]></description>
        </item>
        """.strip())

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Toulouse. Sorties & experiences</title>
    <link>{html.escape(SOURCES[0][1])}</link>
    <description>Workshops, hands-on experiences, and events in Toulouse and nearby. Updated daily.</description>
    <language>fr</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    {''.join(items_xml)}
  </channel>
</rss>
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(rss)

if __name__ == "__main__":
    main()
