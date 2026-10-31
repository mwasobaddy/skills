#!/usr/bin/env python3
"""Crawl Google Search documentation into clean text, and report what changed.

    python3 crawl-google-docs.py --out /tmp/gdocs
    python3 crawl-google-docs.py --out /tmp/gdocs --diff
    python3 crawl-google-docs.py --out /tmp/gdocs --seed URL --max-hops 1

The corpus is 190+ pages, so a full crawl takes a few minutes. HTML is cached, so
re-running only refetches pages that failed. --diff compares against the hashes
recorded by the previous run and prints added, removed, and changed URLs.

Extraction keeps only the article body. Google's devsite wraps content in
`devsite-article` and marks navigation with `nocontent`; without those filters the
output is mostly site chrome.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
SEED = "https://developers.google.com/search/docs"
ALLOW = re.compile(r"^https://developers\.google\.com/(search/docs|crawling/docs)/")

SKIP_CLASS = {
    "nocontent", "devsite-nav", "devsite-sidebar-content", "devsite-footer-linkboxes",
    "devsite-footer-promos", "devsite-footer-utility", "devsite-article-meta",
    "devsite-toc", "devsite-book-nav", "devsite-tabs-content", "devsite-content-data",
}


def fetch(url, tries=3):
    """curl, not urllib: python's CA store is frequently broken on macOS."""
    for i in range(tries):
        try:
            r = subprocess.run(
                ["curl", "-sS", "-L", "-m", "40", "--compressed", "-A", UA, url],
                capture_output=True, timeout=70)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", "replace")
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(1.5 * (i + 1))
    return None


class Article(HTMLParser):
    """Extract the article body, preserving headings, lists, tables, and code."""

    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
             "table", "section", "article", "pre", "blockquote", "dt", "dd",
             "ul", "ol", "thead", "tbody", "figcaption", "aside", "main"}
    VOID = {"br", "img", "input", "meta", "link", "hr", "source", "col",
            "area", "base", "embed", "param", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.out = []
        self.started = False
        self.pre = 0

    def _skipping(self):
        return any(skip for _, skip in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        skip = bool(set(cls) & SKIP_CLASS) or tag in ("script", "style", "noscript", "svg")
        if tag not in self.VOID:
            self.stack.append((tag, skip))
        if tag == "article" or "devsite-article" in cls or "devsite-article-body" in cls:
            self.started = True
        if self._skipping():
            return
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag in ("h1", "h2", "h3", "h4", "h5") and self.started:
            self.out.append("\n" + "#" * int(tag[1]) + " ")
        if tag == "li":
            self.out.append("- ")
        if tag in ("td", "th"):
            self.out.append(" | ")
        if tag == "pre":
            self.pre += 1
            self.out.append("\n```\n")
        if tag == "code" and not self.pre:
            self.out.append("`")

    def handle_endtag(self, tag):
        if not self._skipping():
            if tag in self.BLOCK:
                self.out.append("\n")
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
                self.out.append("\n```\n")
            if tag == "code" and not self.pre:
                self.out.append("`")
        if tag != "VOID" and tag not in self.VOID:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    def handle_data(self, data):
        if self._skipping() or not self.started:
            return
        self.out.append(data)


def clean(text):
    text = text.replace("\u200b", "").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    out = []
    for line in (l.strip() for l in text.split("\n")):
        if line in ("", "|", "-", "#", "##") and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out).strip()


def slug(url):
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[?#].*$", "", s)
    return re.sub(r"[^A-Za-z0-9._-]+", "__", s.strip("/")) or "index"


def norm(href, base):
    from urllib.parse import urljoin, urlsplit
    u = urljoin(base, href)
    parts = urlsplit(u)
    # Pages contain unescaped template fragments in attributes (e.g. `<var translate=`),
    # which urljoin happily accepts. Reject anything that isn't a plain http(s) URL.
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(f"not a fetchable URL: {href!r}")
    if re.search(r"[<>\"'`\s]", u):
        raise ValueError(f"invalid characters in URL: {href!r}")
    return parts._replace(query="", fragment="").geturl().rstrip("/")


def discover(seed, max_hops, workers):
    seen, queue, hop = set(), [seed], {seed: 0}
    while queue:
        batch = [u for u in queue[:workers] if u not in seen]
        queue = queue[workers:]
        seen.update(batch)
        with ThreadPoolExecutor(workers) as ex:
            results = list(ex.map(fetch, batch))
        for url, html in zip(batch, results):
            if not html:
                continue
            links = re.findall(r'href="([^"#]+)"', html)
            for href in links:
                try:
                    n = norm(href, url)
                except Exception:
                    continue
                if not ALLOW.match(n) or n in seen or n in hop:
                    continue
                if hop[url] + 1 > max_hops:
                    continue
                hop[n] = hop[url] + 1
                queue.append(n)
    return sorted(seen)


def extract_all(urls, out, workers, force):
    os.makedirs(f"{out}/html", exist_ok=True)
    os.makedirs(f"{out}/pages", exist_ok=True)

    def one(url):
        hp = f"{out}/html/{slug(url)}.html"
        if force or not os.path.exists(hp) or os.path.getsize(hp) < 2000:
            html = fetch(url)
            if html:
                open(hp, "w", encoding="utf-8").write(html)
        if not os.path.exists(hp):
            return {"url": url, "ok": False}
        html = open(hp, encoding="utf-8", errors="replace").read()
        parser = Article()
        try:
            parser.feed(html)
        except Exception:
            pass
        text = clean("".join(parser.out))
        pp = f"{out}/pages/{slug(url)}.txt"
        open(pp, "w", encoding="utf-8").write(text)
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        title = ""
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        # A removed feature page redirects to the docs-updates index. Check the
        # canonical and the title; the canonical has appeared as both /search/news
        # and /search/updates, so match the prefix rather than one exact URL.
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        retired = bool(canon and re.match(
            r"https://developers\.google\.com/search/(news|updates)/?$", canon.group(1)))
        if not retired:
            retired = "Latest Google Search Documentation Updates" in html[:4000]
        return {"url": url, "ok": True, "chars": len(text), "hash": digest,
                "title": title, "retired": retired}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, urls))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="corpus directory")
    ap.add_argument("--seed", default=SEED)
    ap.add_argument("--max-hops", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="refetch cached HTML")
    ap.add_argument("--diff", action="store_true", help="compare with the previous run and exit")
    args = ap.parse_args()

    manifest_path = f"{args.out}/manifest.json"
    previous = {}
    if os.path.exists(manifest_path):
        previous = {r["url"]: r for r in json.load(open(manifest_path)) if r.get("ok")}

    if args.diff:
        if not previous:
            sys.exit(f"error: no previous manifest at {manifest_path} — run without --diff first")
        print(f"refetching {len(previous)} known pages...")
        rows = extract_all(sorted(previous), args.out, args.workers, force=True)
    else:
        print(f"discovering from {args.seed} (max hops {args.max_hops})...")
        urls = discover(args.seed, args.max_hops, args.workers)
        print(f"discovered {len(urls)} URLs; extracting...")
        rows = extract_all(urls, args.out, args.workers, force=args.force)

    json.dump(rows, open(manifest_path, "w"), indent=1)

    ok = [r for r in rows if r.get("ok")]
    retired = [r for r in ok if r.get("retired")]
    print(f"\npages: {len(ok)} ok, {len(rows) - len(ok)} failed, {len(retired)} retired")
    print(f"characters: {sum(r['chars'] for r in ok):,}")

    if args.diff:
        now = {r["url"]: r for r in ok}
        added = sorted(set(now) - set(previous))
        removed = sorted(set(previous) - set(now))
        changed = sorted(u for u in set(now) & set(previous)
                         if now[u].get("hash") != previous[u].get("hash"))
        for label, items in (("ADDED", added), ("REMOVED", removed), ("CHANGED", changed)):
            print(f"\n{label} ({len(items)}):")
            for u in items:
                print(f"  {u}")
        if not (added or removed or changed):
            print("\nno changes")

    failed = [r["url"] for r in rows if not r.get("ok")]
    if failed:
        print("\nfailed:")
        for u in failed:
            print(f"  {u}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
