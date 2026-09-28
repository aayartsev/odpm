#!/usr/bin/env python3
"""Crawl odpm stable docs on GitHub Pages; report broken internal links."""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict, deque
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://aayartsev.github.io/odpm/stable/"
USER_AGENT = "odpm-docs-link-check/1.0"


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)


def normalize_url(url: str) -> str:
    url, _frag = urldefrag(url)
    parsed = urlparse(url)
    path = parsed.path or "/"
    if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path += "/"
    return parsed._replace(path=path, params="", query="").geturl()


def is_internal_docs_link(url: str, site_root: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", ""):
        return False
    if parsed.netloc and parsed.netloc != urlparse(site_root).netloc:
        return False
    root_path = urlparse(site_root).path.rstrip("/")
    path = parsed.path or "/"
    return path == root_path or path.startswith(root_path + "/")


def fetch_page(url: str, timeout: float) -> tuple[int | None, str | None, str | None]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, None, resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, str(exc), None
    except URLError as exc:
        return None, str(exc), None


def head_status(url: str, timeout: float) -> tuple[int | None, str | None]:
    req = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status in (403, 405):
                code, err, _ = fetch_page(url, timeout)
                return code, err
            return resp.status, None
    except HTTPError as exc:
        if exc.code in (403, 405):
            return fetch_page(url, timeout)[:2]
        return exc.code, str(exc)
    except URLError as exc:
        return None, str(exc)


def crawl(base_url: str, timeout: float, delay: float) -> tuple[set[str], dict[str, list[str]], dict[str, dict]]:
    site_root = base_url if base_url.endswith("/") else base_url + "/"
    queue: deque[str] = deque([site_root])
    seen_pages: set[str] = set()
    link_sources: dict[str, set[str]] = defaultdict(set)

    while queue:
        page_url = queue.popleft()
        norm_page = normalize_url(page_url)
        if norm_page in seen_pages:
            continue
        seen_pages.add(norm_page)

        status, err, html = fetch_page(norm_page, timeout)
        if status is None or status >= 400 or html is None:
            continue

        parser = LinkExtractor()
        parser.feed(html)
        for href in parser.links:
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            absolute = normalize_url(urljoin(norm_page, href))
            if not is_internal_docs_link(absolute, site_root):
                continue
            link_sources[absolute].add(norm_page)
            if absolute not in seen_pages:
                queue.append(absolute)
        time.sleep(delay)

    broken: dict[str, dict] = {}
    for target, sources in sorted(link_sources.items()):
        status, err = head_status(target, timeout)
        if status is None or status >= 400:
            broken[target] = {
                "url": target,
                "status": status,
                "error": err,
                "found_on": sorted(sources),
            }
        time.sleep(delay)

    return seen_pages, {k: sorted(v) for k, v in link_sources.items()}, broken


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE, help="Docs root URL")
    parser.add_argument("--output", required=True, help="Markdown report path")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--delay", type=float, default=0.02)
    args = parser.parse_args()

    pages, _all_links, broken_map = crawl(args.base, args.timeout, args.delay)
    broken = list(broken_map.values())

    lines = [
        "# Broken links in stable docs crawl",
        "",
        f"- Base: `{args.base}`",
        f"- Pages visited: **{len(pages)}**",
        f"- Broken internal links: **{len(broken)}**",
        "- Checked at: crawl run from repo script `scripts/crawl_stable_docs_links.py`",
        "",
    ]
    if broken:
        lines.append("| Status | URL | Found on (sample) |")
        lines.append("|--------|-----|-------------------|")
        for item in sorted(broken, key=lambda x: x["url"]):
            status = item.get("status")
            status_s = str(status) if status is not None else "ERR"
            found = "; ".join(f"`{u}`" for u in item["found_on"][:3])
            if len(item["found_on"]) > 3:
                found += f" (+{len(item['found_on']) - 3} more)"
            lines.append(f"| {status_s} | `{item['url']}` | {found} |")
    else:
        lines.append("_No broken internal links found._")

    lines.extend(["", "## Visited pages", ""])
    for page in sorted(pages):
        lines.append(f"- `{page}`")

    output = "\n".join(lines) + "\n"
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(output)

    print(f"Visited {len(pages)} pages; broken {len(broken)}; report -> {args.output}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
