# app/welco_crawler.py
"""Same-domain website crawler that builds the raw-text knowledge base for a
Kaptila Welco agent. v1 has no embeddings/vector search — the crawled text is
small enough (bounded below) to paste directly into the LLM's context window
on every chat call, see welco_engine.py.
"""
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

MAX_PAGES = 40
MAX_DEPTH = 3
MAX_CHARS = 120_000
REQUEST_TIMEOUT = 10
# Politeness delay between sequential requests to the target site — without
# it the crawl hits a customer's site as fast as the network allows,
# back-to-back for dozens of pages, which is exactly the pattern shared hosts
# rate-limit or flag as abusive. Applied to every request after the first.
REQUEST_DELAY_SECONDS = 0.4
# A sitemap index can chain to many sub-sitemaps; cap how many we'll follow so
# a pathological one can't turn "read the sitemap" into its own crawl.
MAX_SITEMAPS = 5
USER_AGENT = "WelcoChatBot/1.0 (+https://welcochat.com)"

_STRIP_TAGS = ("script", "style", "nav", "footer", "header", "noscript")
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class _PacedFetcher:
    """Wraps session.get() with the politeness delay above, applied uniformly
    across every HTTP request this crawl makes (start page, sitemap, and
    every followed link) — not just the link-following loop, since a burst of
    unpaced requests during sitemap discovery defeats the point just as much."""

    def __init__(self, session: requests.Session):
        self._session = session
        self._made_a_request = False

    def get(self, url: str, **kwargs) -> requests.Response:
        if self._made_a_request:
            time.sleep(REQUEST_DELAY_SECONDS)
        self._made_a_request = True
        return self._session.get(url, **kwargs)


def _load_robots(base_url: str) -> urllib.robotparser.RobotFileParser:
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(urljoin(base_url, "/robots.txt"))
        rp.read()
    except Exception:
        rp.disallow_all = False
    return rp


def _extract_page(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())

    links = []
    for a in soup.find_all("a", href=True):
        links.append(a["href"])

    return text, links


def _discover_sitemap_urls(fetcher: _PacedFetcher, base_url: str, domain: str) -> list[str]:
    """Best-effort: reads /sitemap.xml (following one level of sitemap-index
    chaining) and returns same-domain page URLs it lists. Link-following alone
    can miss pages a site never links to from anywhere the crawl reaches — the
    sitemap is the site's own authoritative page list. Never raises: a
    missing or malformed sitemap just means link-following is all we get,
    same as before this existed."""

    def same_domain_locs(el) -> list[str]:
        out = []
        for loc in el.findall(f"{_SITEMAP_NS}url/{_SITEMAP_NS}loc"):
            url = (loc.text or "").strip()
            if url and urlparse(url).netloc == domain:
                out.append(url)
        return out

    try:
        resp = fetcher.get(urljoin(base_url, "/sitemap.xml"), timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            return []
        # Parse whatever came back regardless of the declared Content-Type —
        # sitemap.xml is commonly served as text/plain or text/html by
        # misconfigured hosts, and ET.fromstring fails cleanly below if it
        # isn't actually XML.
        root = ET.fromstring(resp.content)
    except Exception:
        return []

    tag = root.tag.rsplit("}", 1)[-1]
    if tag == "urlset":
        # A large sitemap has no reason to hand back more entries than the
        # crawl could ever fetch — cap it here rather than growing the queue
        # with thousands of URLs that page_count/MAX_PAGES would prune anyway.
        return same_domain_locs(root)[:MAX_PAGES]

    if tag != "sitemapindex":
        return []

    urls: list[str] = []
    sub_sitemaps = [
        (loc.text or "").strip()
        for loc in root.findall(f"{_SITEMAP_NS}sitemap/{_SITEMAP_NS}loc")
        if loc.text
    ][:MAX_SITEMAPS]
    for sub_url in sub_sitemaps:
        try:
            sub_resp = fetcher.get(sub_url, timeout=REQUEST_TIMEOUT)
            if not sub_resp.ok:
                continue
            sub_root = ET.fromstring(sub_resp.content)
            urls.extend(same_domain_locs(sub_root))
        except Exception:
            continue
        if len(urls) >= MAX_PAGES:
            break
    return urls


def crawl_site(start_url: str) -> tuple[str, int]:
    """BFS-crawl `start_url` and same-domain pages reachable from it, seeded
    with any pages the site's own sitemap.xml lists.

    Returns (concatenated_text, page_count). Raises requests.RequestException
    if the start URL itself can't be fetched; individual follow-up pages that
    fail are skipped rather than aborting the whole crawl.
    """
    parsed_start = urlparse(start_url)
    if not parsed_start.scheme:
        start_url = f"https://{start_url}"
        parsed_start = urlparse(start_url)
    domain = parsed_start.netloc

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    fetcher = _PacedFetcher(session)

    robots = _load_robots(start_url)

    # Fetch the start page first — if this fails, the crawl is invalid.
    resp = fetcher.get(start_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    visited: set[str] = {start_url}
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])

    for sitemap_url in _discover_sitemap_urls(fetcher, start_url, domain):
        if sitemap_url not in visited:
            visited.add(sitemap_url)
            # depth=1, not 0: these are known real pages, so they're worth
            # visiting, but we still only follow shallow link-discovery from
            # them rather than treating them as a second starting point.
            queue.append((sitemap_url, 1))

    chunks: list[str] = []
    total_chars = 0
    page_count = 0
    first_response = resp

    while queue and page_count < MAX_PAGES and total_chars < MAX_CHARS:
        url, depth = queue.popleft()

        if url == start_url and first_response is not None:
            html = first_response.text
            first_response = None
        else:
            if not robots.can_fetch(USER_AGENT, url):
                continue
            try:
                page_resp = fetcher.get(url, timeout=REQUEST_TIMEOUT)
                page_resp.raise_for_status()
            except requests.RequestException:
                continue
            content_type = page_resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                continue
            html = page_resp.text

        text, links = _extract_page(html)
        if text:
            piece = f"\n\n=== {url} ===\n{text}"
            remaining = MAX_CHARS - total_chars
            if remaining <= 0:
                break
            chunks.append(piece[:remaining])
            total_chars += len(piece)
            page_count += 1

        if depth < MAX_DEPTH:
            for href in links:
                absolute = urljoin(url, href).split("#")[0]
                link_parsed = urlparse(absolute)
                if link_parsed.netloc != domain:
                    continue
                if absolute not in visited:
                    visited.add(absolute)
                    queue.append((absolute, depth + 1))

    return "".join(chunks).strip(), page_count
