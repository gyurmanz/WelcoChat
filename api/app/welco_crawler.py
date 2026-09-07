# app/welco_crawler.py
"""Same-domain website crawler that builds the raw-text knowledge base for a
Kaptila Welco agent. v1 has no embeddings/vector search — the crawled text is
small enough (bounded below) to paste directly into the LLM's context window
on every chat call, see welco_engine.py.
"""
import urllib.robotparser
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

MAX_PAGES = 40
MAX_DEPTH = 3
MAX_CHARS = 120_000
REQUEST_TIMEOUT = 10
USER_AGENT = "KaptilaWelcoBot/1.0 (+https://kaptila.com/welco)"

_STRIP_TAGS = ("script", "style", "nav", "footer", "header", "noscript")


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


def crawl_site(start_url: str) -> tuple[str, int]:
    """BFS-crawl `start_url` and same-domain pages reachable from it.

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

    robots = _load_robots(start_url)

    # Fetch the start page first — if this fails, the crawl is invalid.
    resp = session.get(start_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    visited: set[str] = {start_url}
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
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
                page_resp = session.get(url, timeout=REQUEST_TIMEOUT)
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
