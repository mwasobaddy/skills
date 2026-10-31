#!/usr/bin/env python3
"""Audit technical SEO on a live URL or a local build directory.

    python3 seo_audit.py https://example.com
    python3 seo_audit.py ./dist --base-url https://example.com
    python3 seo_audit.py https://example.com --max-pages 50 --json report.json
    python3 seo_audit.py --selftest

Checks the things that actually decide whether a page can be indexed and how it
appears: status, indexability, title, description, canonical, headings, lang,
JSON-LD, hreflang reciprocity, image alt text, robots.txt, and the sitemap.

Exit code is 1 when any error-severity finding exists, so this drops into CI.
Warnings alone exit 0.

Requires python3 and curl. In --dir mode no network access is used.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")

ERROR, WARN, INFO = "error", "warn", "info"

# Structured data types Google has retired. Markup for these renders no rich result,
# so finding it is more useful than finding nothing.
RETIRED_TYPES = {
    "FAQPage", "HowTo", "CourseInfo", "CriticReview", "EstimatedSalary",
    "HomeActivities", "JobTraining", "LearningVideo", "PracticeProblems",
    "SitelinksSearchBox", "SpecialAnnouncement", "VehicleListing",
}

# Required properties per type, from each feature's own documentation page. Types not
# listed here are either overview pages that delegate, or have no required properties.
REQUIRED_PROPS = {
    "BreadcrumbList": ["itemListElement"],
    "Product": ["name"],
    "ProductGroup": ["name"],
    "Recipe": ["name"],
    "Event": ["startDate"],
    "JobPosting": ["datePosted", "description", "hiringOrganization", "jobLocation", "title"],
    "LocalBusiness": ["address", "name"],
    "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
    "Review": ["author"],
    "WebSite": ["name", "url"],
    "Organization": [],
    "Article": [],
}

# Region codes that look plausible but are not assigned in ISO 3166-1 Alpha 2.
BAD_REGIONS = {"uk", "eu", "un", "dd", "zr", "an", "cs", "su"}


# --------------------------------------------------------------------------- fetch
class Response:
    def __init__(self, url, status, body, headers, redirects=0, effective=None):
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers
        self.redirects = redirects
        self.effective = effective or url

    @property
    def x_robots(self):
        return self.headers.get("x-robots-tag", "")


def http_get(url, timeout=25):
    """curl, because python's CA bundle is unreliable on many machines."""
    with tempfile.TemporaryDirectory() as td:
        body_p = os.path.join(td, "body")
        head_p = os.path.join(td, "head")
        fmt = "%{http_code}\\n%{num_redirects}\\n%{url_effective}"
        try:
            r = subprocess.run(
                ["curl", "-sS", "-L", "-m", str(timeout), "--compressed",
                 "-A", UA, "-D", head_p, "-o", body_p, "-w", fmt, url],
                capture_output=True, timeout=timeout + 15)
        except Exception as e:
            return Response(url, 0, b"", {}, 0, url)
        if r.returncode != 0:
            return Response(url, 0, b"", {}, 0, url)
        out = r.stdout.decode("utf-8", "replace").strip().split("\n")
        try:
            status = int(out[0])
            redirects = int(out[1]) if len(out) > 1 else 0
            effective = out[2] if len(out) > 2 else url
        except (ValueError, IndexError):
            status, redirects, effective = 0, 0, url
        headers = {}
        try:
            raw = open(head_p, "rb").read().decode("iso-8859-1", "replace")
            # keep only the final response block
            blocks = re.split(r"\r?\n\r?\n", raw)
            for line in (blocks[-2] if len(blocks) > 1 else raw).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
        except OSError:
            pass
        try:
            body = open(body_p, "rb").read()
        except OSError:
            body = b""
        return Response(url, status, body, headers, redirects, effective)


# --------------------------------------------------------------------------- parse
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self.descriptions = []
        self.robots = []
        self.canonicals = []
        self.hreflangs = []
        self.h1 = 0
        self.h2 = 0
        self.lang = None
        self.charset = False
        self.has_favicon = False
        self.twitter = {}
        self.og = {}
        self.ldjson = []
        self._in_ld = False
        self._ld_buf = []
        self.images = 0
        self.images_no_alt = 0
        self.alt_empty = 0
        self.links = []
        self.meta_keywords = False
        self.rel_next_prev = False
        self.has_viewport = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang") or self.lang
        elif tag == "title":
            self._in_title = True
            if self.title is None:
                self.title = ""
        elif tag == "meta":
            if a.get("charset"):
                self.charset = True
            if (a.get("http-equiv") or "").lower() == "content-type" \
                    and "charset" in (a.get("content") or "").lower():
                self.charset = True
            name = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content") or ""
            if name == "description":
                self.descriptions.append(content)
            elif name in ("robots", "googlebot"):
                self.robots.append(content)
            elif name == "keywords":
                self.meta_keywords = True
            elif name == "viewport":
                self.has_viewport = True
            elif name.startswith("og:"):
                self.og[name] = content
            elif name.startswith("twitter:"):
                self.twitter[name] = content
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "canonical" in rel:
                self.canonicals.append(a.get("href") or "")
            if "icon" in rel:
                self.has_favicon = True
            if "alternate" in rel and a.get("hreflang"):
                self.hreflangs.append((a["hreflang"], a.get("href") or ""))
            if rel in ("next", "prev"):
                self.rel_next_prev = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "h2":
            self.h2 += 1
        elif tag == "img":
            self.images += 1
            if "alt" not in a:
                self.images_no_alt += 1
            elif not (a.get("alt") or "").strip():
                self.alt_empty += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json":
                self._in_ld = True
                self._ld_buf = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False
            self.ldjson.append("".join(self._ld_buf).strip())
            self._ld_buf = []

    def handle_data(self, data):
        if self._in_title and self.title is not None:
            self.title += data
        elif self._in_ld:
            self._ld_buf.append(data)


def parse_html(body_bytes, encoding_hint=""):
    m = re.search(rb'charset=["\']?([\w-]+)', body_bytes[:2048], re.I)
    enc = (m.group(1).decode() if m else "") or encoding_hint or "utf-8"
    try:
        text = body_bytes.decode(enc, "replace")
    except LookupError:
        text = body_bytes.decode("utf-8", "replace")
    p = PageParser()
    try:
        p.feed(text)
    except Exception:
        pass
    return p


# --------------------------------------------------------------------------- model
class Finding:
    __slots__ = ("severity", "rule", "page", "message", "fix")

    def __init__(self, severity, rule, page, message, fix=""):
        self.severity = severity
        self.rule = rule
        self.page = page
        self.message = message
        self.fix = fix

    def as_dict(self):
        return {"severity": self.severity, "rule": self.rule, "page": self.page,
                "message": self.message, "fix": self.fix}


def loc(url):
    return urlsplit(url).path or "/"


def null_reader(url):
    return Response(url, 0, b"", {})


class Auditor:
    def __init__(self, base, fetch=null_reader, max_pages=25, seed=None):
        # base must be an origin (scheme://host). Passing a full page URL makes every
        # site-level probe resolve under that path — /admin/users/robots.txt — which
        # reports a missing robots.txt and sitemap on a site that has both.
        self.base = base.rstrip("/")
        self._fetch = fetch
        self.max_pages = max_pages
        self.seed = seed or self.base
        self.findings = []
        self.pages = []

    def get(self, url):
        return self._fetch(url)

    def add(self, sev, rule, page, msg, fix=""):
        self.findings.append(Finding(sev, rule, page, msg, fix))

    # ---- site level
    def check_robots(self):
        r = self.get(self.base + "/robots.txt")
        if r.status == 0:
            self.add(WARN, "robots-unreachable", "/robots.txt",
                     "robots.txt could not be fetched",
                     "Confirm the site is serving /robots.txt at the host root.")
            return
        if r.status >= 500:
            self.add(ERROR, "robots-5xx", "/robots.txt",
                     f"robots.txt returned {r.status}",
                     "A 5xx on robots.txt stalls crawling. Serve a 200 file.")
            return
        if r.status == 404:
            self.add(WARN, "robots-missing", "/robots.txt",
                     "No robots.txt found",
                     "Not fatal, but add one so you control crawl and point to the sitemap.")
            return
        body = r.body.decode("utf-8", "replace")
        if len(body.encode()) > 500 * 1024:
            self.add(ERROR, "robots-too-large", "/robots.txt",
                     "robots.txt exceeds 500 KiB",
                     "Google ignores everything past 500 KiB.")
        if re.search(r"(?im)^\s*crawl-delay\s*:", body):
            self.add(INFO, "robots-crawl-delay", "/robots.txt",
                     "crawl-delay present",
                     "Google does not process crawl-delay. Use 503/429 with Retry-After.")
        if re.search(r"(?im)^\s*host\s*:", body):
            self.add(INFO, "robots-host-directive", "/robots.txt",
                     "Host directive present",
                     "Yandex-specific. Google ignores it; sitemap and canonical cover this.")
        groups = re.split(r"(?im)^\s*user-agent\s*:", body)
        for g in groups[1:]:
            ua = g.split("\n", 1)[0].strip().lower()
            if ua in ("*", ""):
                if re.search(r"(?im)^\s*disallow\s*:\s*/\s*$", g):
                    self.add(ERROR, "robots-blocks-all", "/robots.txt",
                             "robots.txt disallows / for user-agent *",
                             "This blocks the entire site. If intentional, serve 503 instead.")
                break

    def check_sitemap(self, robots_url):
        candidates = []
        r = self.get(self.base + "/robots.txt")
        if r.status == 200:
            for m in re.finditer(r"(?im)^\s*sitemap\s*:\s*(\S+)", r.body.decode("utf-8", "replace")):
                candidates.append(m.group(1))
        if not candidates:
            candidates = [self.base + "/sitemap.xml"]
        urls = []
        for sm in candidates[:3]:
            r = self.get(sm)
            if r.status != 200:
                continue
            body = r.body.decode("utf-8", "replace")
            if "<sitemapindex" in body:
                subs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
                for sub in subs[:3]:
                    r2 = self.get(sub)
                    if r2.status == 200:
                        urls.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>",
                                               r2.body.decode("utf-8", "replace")))
            else:
                urls.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body))
            if re.search(r"<priority>|<changefreq>", body):
                self.add(INFO, "sitemap-ignored-tags", sm,
                         "sitemap contains <priority> or <changefreq>",
                         "Google ignores both. Removing them reduces noise.")
        if not urls:
            self.add(WARN, "sitemap-missing", "/sitemap.xml",
                     "No sitemap found via robots.txt or /sitemap.xml",
                     "Add sitemap.xml and reference it from robots.txt.")
            return []
        bad = [u for u in urls if not u.startswith(("http://", "https://"))]
        if bad:
            self.add(ERROR, "sitemap-relative-urls", "/sitemap.xml",
                     f"{len(bad)} sitemap entries are not absolute URLs",
                     "Use absolute https URLs in <loc>.")
        if len(urls) > 50000:
            self.add(ERROR, "sitemap-too-large", "/sitemap.xml",
                     f"sitemap lists {len(urls)} URLs",
                     "Split at 50,000 URLs / 50 MB per file using a sitemap index.")
        return urls

    def check_https(self):
        if self.base.startswith("http://"):
            self.add(WARN, "http-not-https", "/",
                     "Auditing over plain HTTP",
                     "Serve HTTPS; it is a canonicalization signal and required for most features.")

    # ---- page level
    @staticmethod
    def _nodes(data):
        """Flatten a JSON-LD document into its top-level nodes, including @graph."""
        out = []
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            out.append(it)
            graph = it.get("@graph")
            if isinstance(graph, list):
                out.extend(x for x in graph if isinstance(x, dict))
        return out

    def _check_ldjson(self, L, p):
        for i, block in enumerate(p.ldjson):
            if not block:
                continue
            try:
                data = json.loads(block)
            except json.JSONDecodeError as e:
                self.add(ERROR, "ldjson-invalid", L,
                         f"JSON-LD block {i + 1} is not valid JSON ({e.msg} at char {e.pos})",
                         "Validate with the Rich Results Test; broken JSON is discarded entirely.")
                continue
            for item in self._nodes(data):
                t = item.get("@type")
                if not t:
                    self.add(WARN, "ldjson-no-type", L,
                             "JSON-LD block has no @type",
                             "Every structured data node needs @type.")
                    continue
                for ty in (t if isinstance(t, list) else [t]):
                    if not isinstance(ty, str):
                        continue
                    if ty in RETIRED_TYPES:
                        self.add(WARN, "ldjson-retired-type", L,
                                 f"{ty} markup present, but that rich result was retired",
                                 "No markup will bring it back. Keep it only for other consumers, "
                                 "or remove it.")
                    req = REQUIRED_PROPS.get(ty)
                    if req:
                        missing = [k for k in req if k not in item]
                        if missing:
                            self.add(WARN, "ldjson-missing-required", L,
                                     f"{ty} missing required: {', '.join(missing)}",
                                     "A missing required property makes the item ineligible.")

    def _check_hreflang_code(self, L, code):
        c = code.strip()
        if c.lower() == "x-default":
            return
        parts = [x for x in c.split("-") if x]
        if not parts or not re.fullmatch(r"[A-Za-z]{2}", parts[0]):
            self.add(WARN, "hreflang-invalid-code", L,
                     f"hreflang={code} has no two-letter language subtag",
                     "The first subtag must be an ISO 639-1 language code.")
            return
        if len(parts) > 1:
            second = parts[1]
            if re.fullmatch(r"[A-Za-z]{4}", second):
                return  # ISO 15924 script subtag, e.g. zh-Hant
            if not re.fullmatch(r"[A-Za-z]{2}", second):
                self.add(WARN, "hreflang-invalid-code", L,
                         f"hreflang={code} has an invalid second subtag",
                         "Use a two-letter ISO 3166-1 Alpha 2 region, or a script subtag.")
            elif second.lower() in BAD_REGIONS:
                self.add(WARN, "hreflang-invalid-code", L,
                         f"hreflang={code}: '{second}' is not an assigned region code",
                         "UK/EU/UN are unassigned and silently ignored. Use GB for the UK.")

    def audit_page(self, url):
        r = self.get(url)
        p = parse_html(r.body, r.headers.get("content-type", ""))
        # Identity after redirects. Comparing against the requested URL makes every
        # canonical look wrong when the audit starts on a host that redirects.
        final_url = (r.effective or url).rstrip("/")
        entry = {"url": url, "final": final_url, "status": r.status, "redirects": r.redirects,
                 "title": (p.title or "").strip(),
                 "desc": next((d.strip() for d in p.descriptions if d.strip()), ""),
                 "canonicals": p.canonicals,
                 "hreflangs": p.hreflangs, "ldjson": p.ldjson, "h1": p.h1}
        self.pages.append(entry)
        L = loc(url)

        if r.status != 200:
            self.add(ERROR, "status-not-200", L, f"returned HTTP {r.status}",
                     "Only 2xx pages are indexable. Fix or redirect.")
            return entry
        if r.redirects > 1:
            self.add(WARN, "redirect-chain", L,
                     f"took {r.redirects} hops to resolve",
                     "Keep chains under 3 hops; point links at the final URL.")

        robots = " ".join(p.robots).lower() + " " + r.x_robots.lower()
        excluded = "noindex" in robots or "none" in robots.split()
        entry["excluded"] = excluded

        # Head hygiene applies to every page, excluded ones included: encoding and mobile
        # rendering are technical requirements, not ranking concerns.
        if not p.charset:
            self.add(WARN, "charset-missing", L, "no <meta charset> in the head",
                     "Declare it within the first 1024 bytes, or parsers guess the encoding "
                     "and may garble the rest of the document.")
        if not p.has_viewport:
            self.add(WARN, "viewport-missing", L, "no viewport meta tag",
                     "Its presence is what signals to Google that the page is designed for mobile.")

        if excluded:
            # An excluded page is a deliberate decision. Missing description, canonical, h1,
            # Open Graph tags and word count are not defects here — flagging them is the single
            # biggest source of false positives in SEO audits.
            self._check_ldjson(L, p)
            self.add(INFO, "page-excluded", L,
                     "excluded from indexing by design (noindex)",
                     "Only technical head hygiene is checked. Confirm the exclusion is intentional.")
            if p.canonicals:
                self.add(INFO, "canonical-on-noindex", L,
                         "canonical present on a noindex page",
                         "Google ignores it here. Harmless, but it confuses audit tools.")
            return entry

        t = (p.title or "").strip()
        if not t:
            self.add(ERROR, "title-missing", L, "missing <title>",
                     "Every indexable page needs a unique, descriptive title.")
        elif len(t) > 60:
            self.add(WARN, "title-long", L, f"title is {len(t)} chars",
                     "Google truncates the title link around 60 characters. Front-load the topic.")

        desc = [d.strip() for d in p.descriptions if d.strip()]
        if not desc:
            self.add(WARN, "description-missing", L, "missing meta description",
                     "Not a ranking factor, but it is the snippet fallback. Add one.")
        elif len(desc[0]) > 160:
            self.add(INFO, "description-long", L, f"description is {len(desc[0])} chars",
                     "No hard limit exists, but the snippet truncates to the device width.")

        if len(p.canonicals) > 1:
            self.add(ERROR, "canonical-multiple", L,
                     f"{len(p.canonicals)} canonical tags",
                     "Keep exactly one canonical per page.")
        elif p.canonicals:
            c = p.canonicals[0]
            if not c.startswith(("http://", "https://")):
                self.add(WARN, "canonical-relative", L, "canonical is a relative URL",
                         "Use an absolute URL so it cannot be resolved against the wrong host.")
            elif c.rstrip("/") != final_url:
                self.add(INFO, "canonical-not-self", L, f"canonical points to {c}",
                         "Fine when intentional. Confirm it matches the URL you want indexed.")
        else:
            self.add(WARN, "canonical-missing", L, "no canonical tag",
                     "Add a self-referencing canonical to avoid duplicate-cluster ambiguity.")

        if p.h1 == 0:
            self.add(WARN, "h1-missing", L, "no <h1>",
                     "Add one visible h1 that matches the page topic.")
        elif p.h1 > 1:
            self.add(INFO, "h1-multiple", L, f"{p.h1} <h1> elements",
                     "Not an error. One dominant heading keeps the title link stable.")

        if not p.lang:
            self.add(WARN, "lang-missing", L, "<html> has no lang attribute",
                     "Add lang for accessibility. Google infers language from text, not this attribute.")

        self._check_ldjson(L, p)

        if p.images_no_alt:
            self.add(WARN, "img-alt-missing", L,
                     f"{p.images_no_alt} of {p.images} images have no alt attribute",
                     "Alt text is the strongest image signal; describe the image.")

        if p.meta_keywords:
            self.add(INFO, "meta-keywords", L, "meta keywords tag present",
                     "Google ignores it entirely. Safe to remove.")

        if p.rel_next_prev:
            self.add(INFO, "rel-next-prev", L, "rel=next/prev present",
                     "Google no longer uses these. Paginated pages need unique URLs and self-canonicals.")

        if p.hreflangs:
            for code, href in p.hreflangs:
                if not href.startswith(("http://", "https://")):
                    self.add(ERROR, "hreflang-relative", L,
                             f"hreflang={code} uses a relative URL",
                             "Alternate URLs must be fully qualified with the scheme.")
                self._check_hreflang_code(L, code)
            if not any(c.lower() == "x-default" for c, _ in p.hreflangs):
                self.add(INFO, "hreflang-no-x-default", L,
                         "hreflang set has no x-default",
                         "Add x-default so unmatched languages land somewhere sensible.")

        # ---- head completion: social and icons
        if not p.og.get("og:image"):
            self.add(INFO, "og-image-missing", L, "no og:image",
                     "Improves link previews. Google also reads og:image as a preferred "
                     "image signal for the result thumbnail.")
        if not p.og.get("og:title"):
            self.add(INFO, "og-title-missing", L, "no og:title",
                     "Google reads og:title as one of its title-link sources.")
        if not p.og.get("og:description"):
            self.add(INFO, "og-description-missing", L, "no og:description",
                     "Not used by Google; social platforms use it for link previews.")
        if not p.twitter.get("twitter:card"):
            self.add(INFO, "twitter-card-missing", L, "no twitter:card",
                     "Not used by Google. Affects X/Twitter previews only.")
        if not p.has_favicon:
            self.add(INFO, "favicon-missing", L, 'no <link rel="icon">',
                     "Google uses it for the favicon in results. Square, at least 8x8.")

        return entry

    def check_canonical_targets(self, audited):
        """A canonical pointing at a dead URL consolidates into nothing."""
        checked = set()
        for p in self.pages:
            if not p.get("canonicals") or p.get("excluded"):
                continue
            c = p["canonicals"][0].rstrip("/")
            if not c.startswith(("http://", "https://")) or c in checked:
                continue
            checked.add(c)
            if len(checked) > 10:
                break
            if c in audited or c == (p.get("final") or "").rstrip("/"):
                continue
            r = self.get(c)
            if r.status == 0 or r.status >= 400:
                self.add(ERROR, "canonical-target-error", loc(p["url"]),
                         f"canonical target is not reachable ({r.status or 'no response'}): {c}",
                         "Fix the target or the canonical. Consolidating into a broken URL loses the page.")

    # ---- cross-page
    def check_duplicates(self):
        titles = defaultdict(list)
        descs = defaultdict(list)
        for p in self.pages:
            if p["status"] != 200 or p.get("excluded"):
                continue
            if p["title"]:
                titles[p["title"].lower()].append(loc(p["url"]))
            if p.get("desc"):
                descs[p["desc"].lower()].append(loc(p["url"]))
        for title, pages in titles.items():
            if len(pages) > 1:
                self.add(ERROR, "title-duplicate", pages[0],
                         f"title shared by {len(pages)} pages: {pages[:5]}",
                         "Duplicate titles compete with each other. Make each page's title specific.")
        for d, pages in descs.items():
            if len(pages) > 1:
                self.add(WARN, "description-duplicate", pages[0],
                         f"meta description shared by {len(pages)} pages: {pages[:5]}",
                         "Write a distinct description per page.")

    def check_hreflang_reciprocity(self):
        sets = {}
        for p in self.pages:
            if not p.get("hreflangs"):
                continue
            mine = {c.lower(): h.rstrip("/") for c, h in p["hreflangs"]}
            sets[p["url"].rstrip("/")] = mine
        if not sets:
            return
        for url, mine in sets.items():
            for code, target in mine.items():
                if code == "x-default":
                    continue
                other = sets.get(target)
                if other is None:
                    continue  # not crawled; cannot judge
                if url not in other.values():
                    self.add(WARN, "hreflang-not-reciprocal", loc(url),
                             f"hreflang={code} -> {target} does not link back",
                             "hreflang is ignored unless both pages point at each other.")

    def run(self):
        self.check_https()
        self.check_robots()
        sitemap_urls = self.check_sitemap(self.base)
        targets = self.discover(sitemap_urls)
        # Always audit the URL the user actually asked about, even when the sitemap
        # doesn't list it or discovery started somewhere else. Directory mode sets
        # seed to None because it already enumerates every file itself.
        if self.seed and self.seed not in targets:
            targets.insert(0, self.seed)
        audited = {}
        for u in targets[: self.max_pages]:
            mark = len(self.findings)
            try:
                entry = self.audit_page(u)
            except Exception as e:  # never let one page kill the run
                self.add(WARN, "page-error", loc(u), f"could not audit: {e}", "")
                continue
            # The same page can be reachable at several hosts. Audit it once, by the
            # URL it actually resolves to, or every alias looks like a duplicate.
            key = entry.get("final") or u
            if key in audited:
                del self.findings[mark:]
                self.pages.pop()
                continue
            audited[key] = u
        self.check_canonical_targets(audited)
        self.check_duplicates()
        self.check_hreflang_reciprocity()
        return self.findings

    def discover(self, sitemap_urls):
        same_host = [u for u in sitemap_urls
                     if urlsplit(u).netloc == urlsplit(self.base).netloc]
        if same_host:
            return same_host
        # fall back to crawling internal links from the seed page
        seen, queue, out = {self.seed}, [self.seed], [self.seed]
        while queue and len(out) < self.max_pages:
            url = queue.pop(0)
            r = self.get(url)
            if r.status != 200:
                continue
            for href in parse_html(r.body).links:
                n = urljoin(url, href).split("#")[0]
                if urlsplit(n).netloc != urlsplit(self.base).netloc:
                    continue
                if n in seen or len(out) >= self.max_pages:
                    continue
                seen.add(n)
                out.append(n)
                queue.append(n)
        return out


class DirAuditor(Auditor):
    """Same checks, reading a local build directory instead of the network."""

    def __init__(self, root, base_url, max_pages=25):
        super().__init__(base_url, max_pages=max_pages)
        self.root = os.path.abspath(root)
        self.seed = None  # discover() walks the tree; no seed page to force

    def _path(self, url):
        path = urlsplit(url).path or "/"
        if path.endswith("/"):
            path += "index.html"
        p = os.path.join(self.root, path.lstrip("/"))
        if not os.path.exists(p) and os.path.exists(p + ".html"):
            p += ".html"
        if os.path.isdir(p):
            p = os.path.join(p, "index.html")
        return p

    def get(self, url):
        p = self._path(url)
        if not os.path.exists(p):
            return Response(url, 404, b"", {})
        body = open(p, "rb").read()
        return Response(url, 200, body, {"content-type": "text/html"})

    def discover(self, sitemap_urls):
        if sitemap_urls:
            return sitemap_urls
        out = []
        for dirpath, _, files in os.walk(self.root):
            for f in sorted(files):
                if f.endswith((".html", ".htm")):
                    rel = os.path.relpath(os.path.join(dirpath, f), self.root)
                    path = "/" + rel.replace(os.sep, "/")
                    if path.endswith("/index.html"):
                        path = path[: -len("index.html")]
                    out.append(self.base + path)
        return sorted(out)

    def check_https(self):
        pass


# --------------------------------------------------------------------------- report
def report(findings, pages, out_json=None):
    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings = sorted(findings, key=lambda f: (order[f.severity], f.rule, f.page))
    counts = Counter(f.severity for f in findings)
    errors, warns = counts.get(ERROR, 0), counts.get(WARN, 0)
    score = max(0, 100 - 8 * errors - 2 * warns)

    print(f"\npages audited: {len(pages)}")
    print(f"score: {score}/100   errors: {errors}   warnings: {warns}   info: {counts.get(INFO, 0)}")

    if not findings:
        print("\nno findings\n")

    icons = {ERROR: "ERR ", WARN: "WARN", INFO: "info"}
    current = None
    for f in findings:
        if f.severity != current:
            current = f.severity
            print(f"\n{f.severity.upper()}S")
        print(f"  [{icons[f.severity]}] {f.rule:24} {f.page}")
        print(f"         {f.message}")
        if f.fix:
            print(f"         fix: {f.fix}")

    if out_json:
        json.dump({"score": score, "pages": len(pages),
                   "counts": dict(counts),
                   "findings": [f.as_dict() for f in findings],
                   "page_details": pages},
                  open(out_json, "w"), indent=1)
        print(f"\nwrote {out_json}")

    print()
    return 1 if errors else 0


# --------------------------------------------------------------------------- selftest
BAD_PAGE = """<!doctype html><html><head>
<title>A Page About Widgets And Shipping And Many Other Things Besides Widgets For Everyone</title>
<meta name="keywords" content="a,b">
<link rel="canonical" href="/page">
<link rel="alternate" hreflang="de-CH" href="/de">
<script type="application/ld+json">{ "name": "broken" </script>
</head><body><h1>x</h1><h1>y</h1><img src="a.png"><img src="b.png">
<a href="/clean">c</a></body></html>"""

# A page carrying markup Google has retired, plus an unassigned region code.
RETIRED_PAGE = """<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Frequently asked questions</title>
<meta name="description" content="Answers to common questions.">
<link rel="canonical" href="https://example.com/retired">
<link rel="alternate" hreflang="en-UK" href="https://example.com/retired">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Recipe"}]}
</script>
</head><body><h1>Questions</h1></body></html>"""

CLEAN_PAGE = """<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<title>Shipping a Widget</title>
<meta name="description" content="How to ship a widget safely.">
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="https://example.com/clean">
<meta property="og:image" content="https://example.com/a.png">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Shipping a Widget"}</script>
</head><body><h1>Shipping a Widget</h1><img src="a.png" alt="A widget">
<a href="/broken">b</a></body></html>"""

# The shape of the admin panel in the wild: correctly excluded, and therefore
# legitimately missing everything a marketing page needs.
ADMIN_PAGE = """<!doctype html><html lang="en-KE"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Users · Admin</title>
<meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="https://example.com/">
</head><body><h1>Users</h1><img src="x.png"><a href="/">home</a></body></html>"""


def selftest():
    """Prove the checks fire on a bad page and stay quiet on a good one."""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "index.html"), "w").write(BAD_PAGE)
        open(os.path.join(td, "clean.html"), "w").write(CLEAN_PAGE)
        open(os.path.join(td, "admin.html"), "w").write(ADMIN_PAGE)
        open(os.path.join(td, "retired.html"), "w").write(RETIRED_PAGE)
        a = DirAuditor(td, "https://example.com", 10)
        findings = a.run()

        rules = {f.rule for f in findings}
        must_fire = {"title-long", "canonical-relative", "ldjson-invalid",
                     "hreflang-relative", "img-alt-missing", "meta-keywords",
                     "h1-multiple", "description-missing", "lang-missing",
                     "charset-missing", "viewport-missing"}
        must_not = {"title-missing", "status-not-200", "canonical-multiple"}

        # The excluded page must be recognised as intentional, not nagged for a
        # missing description, canonical, Open Graph tags, or favicon.
        admin_rules = {f.rule for f in findings if f.page == "/admin.html"}
        must_fire_admin = {"page-excluded", "canonical-on-noindex"}
        must_not_admin = {"description-missing", "og-title-missing",
                          "twitter-card-missing", "favicon-missing",
                          "canonical-missing", "h1-missing"}

        missing = must_fire - rules
        bad_positive = must_not & rules
        ok = True
        if missing:
            print(f"FAIL: checks did not fire: {sorted(missing)}")
            ok = False

        # Retired-type detection, required-property gaps, and unassigned region codes.
        retired_rules = {f.rule for f in findings if f.page == "/retired.html"}
        must_fire_retired = {"ldjson-retired-type", "ldjson-missing-required",
                             "hreflang-invalid-code"}
        if must_fire_retired - retired_rules:
            print(f"FAIL: retired/invalid markup not caught: "
                  f"{sorted(must_fire_retired - retired_rules)}")
            ok = False
        if bad_positive:
            print(f"FAIL: false positive on clean page: {sorted(bad_positive)}")
            ok = False
        if must_fire_admin - admin_rules:
            print(f"FAIL: excluded page not recognised: {sorted(must_fire_admin - admin_rules)}")
            ok = False
        if must_not_admin & admin_rules:
            print(f"FAIL: nagged an excluded page about: {sorted(must_not_admin & admin_rules)}")
            ok = False

        # the clean page alone must be silent for page-level errors
        b = DirAuditor(td, "https://example.com", 10)
        b.discover = lambda _s: ["https://example.com/clean"]
        clean = [f for f in b.run() if f.page == "/clean" and f.severity == ERROR]
        if clean:
            print(f"FAIL: clean page produced errors: {[f.rule for f in clean]}")
            ok = False

        print(f"selftest: {len(findings)} findings, {len(rules)} rules fired")
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="site URL or local directory")
    ap.add_argument("--base-url", help="site URL to use for a local directory")
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--json", help="write a machine-readable report")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.target:
        ap.error("give a URL or a directory, or use --selftest")

    t = args.target
    if t.startswith(("http://", "https://")):
        parts = urlsplit(t)
        origin = f"{parts.scheme}://{parts.netloc}"
        auditor = Auditor(origin, http_get, args.max_pages, seed=t)
    else:
        if not os.path.isdir(t):
            ap.error(f"not a directory: {t}")
        auditor = DirAuditor(t, args.base_url or "https://example.com", args.max_pages)

    try:
        subprocess.run(["curl", "--version"], capture_output=True, check=True)
    except Exception:
        if not isinstance(auditor, DirAuditor):
            print("error: curl is required for URL audits", file=sys.stderr)
            return 2

    findings = auditor.run()
    return report(findings, auditor.pages, args.json)


if __name__ == "__main__":
    sys.exit(main())
