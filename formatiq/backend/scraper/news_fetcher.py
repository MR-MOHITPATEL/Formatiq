"""
Fetches trending health/pharma news topics from Google News RSS and optionally SerpAPI.
"""
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def fetch_google_news_rss(query: str, max_results: int = 10) -> list[dict]:
    """Pull latest news articles from Google News RSS (free, no key needed)."""
    url = GOOGLE_NEWS_RSS.format(query=urllib.parse.quote(query))
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormatIQ/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is None:
                return items
            for item in channel.findall("item")[:max_results]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                source_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
                # source tag is inside <source>
                source_tag = item.find("source")
                source = source_tag.text.strip() if source_tag is not None and source_tag.text else "Google News"
                if title:
                    items.append({
                        "title": title,
                        "url": link,
                        "source": source,
                        "published_at": pub_date,
                    })
    except Exception as e:
        logger.warning(f"Google News RSS fetch failed for '{query}': {e}")
    return items


def fetch_serpapi_news(query: str, api_key: str, max_results: int = 10) -> list[dict]:
    """Pull news via SerpAPI (requires paid key). Falls back silently if unavailable."""
    try:
        import urllib.request
        import json
        params = urllib.parse.urlencode({
            "q": query,
            "tbm": "nws",
            "num": max_results,
            "api_key": api_key,
        })
        url = f"https://serpapi.com/search?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "FormatIQ/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        for r in data.get("news_results", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "source": r.get("source", ""),
                "published_at": r.get("date", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"SerpAPI fetch failed: {e}")
        return []


def get_trending_topics(niche: str = "doctor pharmaceutical health", api_key: str = "", max_per_source: int = 8) -> list[dict]:
    """
    Fetch trending topics from all available sources.
    Returns deduplicated list of {title, url, source, published_at}.
    """
    queries = [
        f"{niche} news",
        f"health medicine latest research",
        f"pharmaceutical drug FDA approval",
        f"doctor patient health tips trending",
    ]

    all_items = []
    seen_titles = set()

    for query in queries:
        # Always try Google News RSS (free)
        items = fetch_google_news_rss(query, max_results=max_per_source)
        for item in items:
            key = item["title"][:60].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_items.append(item)

        # Use SerpAPI if key is configured
        if api_key:
            serp_items = fetch_serpapi_news(query, api_key, max_results=max_per_source)
            for item in serp_items:
                key = item["title"][:60].lower()
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_items.append(item)

    return all_items[:40]  # cap total results
