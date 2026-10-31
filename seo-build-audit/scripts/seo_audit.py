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
        self.text_parts = []
        self.script_count = 0
        self.ext_scripts = 0
        self._skip_text = 0

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
            self.script_count += 1
            if a.get("src"):
                self.ext_scripts += 1
            if (a.get("type") or "").lower() == "application/ld+json":
                self._in_ld = True
                self._ld_buf = []
            else:
                self._skip_text += 1
        elif tag == "style":
            self._skip_text += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if self._in_ld:
                self._in_ld = False
                self.ldjson.append("".join(self._ld_buf).strip())
                self._ld_buf = []
            else:
                self._skip_text = max(0, self._skip_text - 1)
        elif tag == "style":
            self._skip_text = max(0, self._skip_text - 1)

    @property
    def body_text(self):
        t = " ".join(self.text_parts)
        return re.sub(r"\s+", " ", t).strip()

    def handle_data(self, data):
        if self._in_ld:
            self._ld_buf.append(data)
            return
        if self._in_title and self.title is not None:
            self.title += data
            return
        if self._skip_text:
            return
        self.text_parts.append(data)


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
    parts = urlsplit(url)
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path


def null_reader(url):
    return Response(url, 0, b"", {})


def image_size(data):
    """Return (width, height) for PNG, GIF, JPEG, or WebP, else None."""
    b = data
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    if b[:6] in (b"GIF87a", b"GIF89a") and len(b) >= 10:
        return (int.from_bytes(b[6:8], "little"),
                int.from_bytes(b[8:10], "little"))
    if b[:2] == b"\xff\xd8":
        i = 2
        sofs = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            marker = b[i + 1]
            if marker in sofs:
                return (int.from_bytes(b[i + 7:i + 9], "big"),
                        int.from_bytes(b[i + 5:i + 7], "big"))
            seglen = int.from_bytes(b[i + 2:i + 4], "big")
            i += 2 + max(seglen, 2)
        return None
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and len(b) >= 30:
        chunk = b[12:16]
        if chunk == b"VP8X":
            return (int.from_bytes(b[24:27], "little") + 1,
                    int.from_bytes(b[27:30], "little") + 1)
        if chunk == b"VP8 ":
            return (int.from_bytes(b[26:28], "little") & 0x3FFF,
                    int.from_bytes(b[28:30], "little") & 0x3FFF)
        if chunk == b"VP8L":
            bits = int.from_bytes(b[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def http_json(url, timeout=90):
    try:
        r = subprocess.run(
            ["curl", "-sS", "-L", "-m", str(timeout), "-A", UA, url],
            capture_output=True, timeout=timeout + 15)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return None


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
        self.max_link_checks = 30
        self.status_cache = {}
        self.discovered = 0
        self.limit_hit = False
        # Hosts we treat as internal. The seed's host is added up front; the host it
        # redirects to is added as soon as we see it, so a bare domain that redirects
        # to www does not reject its own sitemap.
        self.allowed_hosts = {urlsplit(self.base).netloc}

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
                 "hreflangs": p.hreflangs, "ldjson": p.ldjson, "h1": p.h1,
                 "text": p.body_text, "words": len(p.body_text.split()),
                 "links": p.links, "og_image": p.og.get("og:image", ""),
                 "scripts": p.script_count}
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

        words = len(p.body_text.split())
        if words < 50 and p.ext_scripts:
            self.add(WARN, "js-dependent-content", L,
                     f"only {words} words in the served HTML, but {p.ext_scripts} external script(s)",
                     "Confirm with `curl` and URL Inspection's rendered HTML. If the body appears "
                     "only after hydration, Google may index an empty shell.")

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

    def check_soft_404(self):
        """A catch-all route makes every missing URL indexable as a duplicate."""
        if not self.seed or not self.seed.startswith(("http://", "https://")):
            return
        probe = f"{self.base}/seo-audit-nonexistent-{os.urandom(5).hex()}"
        r = self.get(probe)
        if r.status == 200:
            self.add(ERROR, "soft-404", loc(probe),
                     "unknown URLs return 200 instead of 404",
                     "A catch-all route makes every missing page indexable as a duplicate. "
                     "Return 404 for unmatched paths.")

    def check_internal_links(self, host):
        if not self.max_link_checks:
            return
        checked, seen = 0, set()
        for p in self.pages:
            if p.get("excluded") or p["status"] != 200:
                continue
            base = p.get("final") or p["url"]
            for href in p.get("links", []):
                if checked >= self.max_link_checks:
                    return
                if href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
                    continue
                u = urljoin(base, href).split("#")[0].rstrip("/")
                if urlsplit(u).netloc != host or u in seen:
                    continue
                seen.add(u)
                if u in self.status_cache:
                    st = self.status_cache[u]
                else:
                    st = self.get(u).status
                    self.status_cache[u] = st
                checked += 1
                if st == 0 or st >= 400:
                    self.add(WARN, "internal-link-broken", loc(p["url"]),
                             f"internal link returns {st or 'no response'}: {u}",
                             "Fix or remove it; broken links waste crawl budget and lose users.")

    def check_duplicate_content(self):
        def shingles(text):
            w = re.findall(r"[a-z0-9']+", text.lower())
            if len(w) < 100:
                return None
            return {" ".join(w[i:i + 5]) for i in range(len(w) - 4)}

        sigs = []
        for p in self.pages:
            if p.get("excluded") or p["status"] != 200 or p.get("words", 0) < 100:
                continue
            s = shingles(p.get("text", ""))
            if s:
                sigs.append((p, s))

        n = len(sigs)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(n):
            for j in range(i + 1, n):
                inter = len(sigs[i][1] & sigs[j][1])
                if not inter:
                    continue
                if inter / len(sigs[i][1] | sigs[j][1]) >= 0.8:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[rj] = ri

        # One finding per cluster, not one per pair: five similar pages would
        # otherwise produce ten findings that all describe the same problem.
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)
        for idxs in groups.values():
            if len(idxs) < 2:
                continue
            first = sigs[idxs[0]][0]
            members = [loc(sigs[k][0]["url"]) for k in idxs]
            self.add(WARN, "duplicate-content", loc(first["url"]),
                     f"{len(idxs)} near-identical pages: {members[:6]}",
                     "Consolidate with a canonical or differentiate. Filtered variants of a listing "
                     "usually need rel=canonical to the unfiltered page, or noindex.")

    def check_og_images(self):
        seen = set()
        for p in self.pages:
            if p.get("excluded"):
                continue
            src = p.get("og_image")
            if not src or src in seen:
                continue
            seen.add(src)
            if len(seen) > 10:
                return
            u = urljoin(p.get("final") or p["url"], src)
            r = self.get(u)
            if r.status == 0 or r.status >= 400:
                self.add(WARN, "og-image-unreachable", loc(p["url"]),
                         f"og:image does not resolve ({r.status or 'no response'}): {u}",
                         "Link previews and the result thumbnail fall back to nothing.")
                continue
            dims = image_size(r.body)
            if dims and (dims[0] < 600 or dims[1] < 315):
                self.add(INFO, "og-image-small", loc(p["url"]),
                         f"og:image is {dims[0]}x{dims[1]}",
                         "Aim for at least 1200x630 so previews render large.")

    def check_sitemap_coverage(self, sitemap_urls, audited):
        """Pages reached by crawling but absent from the sitemap."""
        if not sitemap_urls:
            return
        listed = {(urlsplit(u).path.rstrip("/") or "/") for u in sitemap_urls}
        for p in self.pages:
            if p.get("excluded") or p["status"] != 200:
                continue
            parts = urlsplit(p.get("final") or p["url"])
            if parts.query:
                continue  # filter/parameter URLs don't belong in a sitemap
            path = parts.path.rstrip("/") or "/"
            if path not in listed:
                self.add(INFO, "page-not-in-sitemap", path,
                         "indexable and linked, but not listed in the sitemap",
                         "Add it if it should be indexed. A sitemap is a hint, not a requirement.")

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
        self.check_soft_404()
        sitemap_urls = self.check_sitemap(self.base)
        queue = [self.seed] if self.seed else []
        # Sitemap entries come from our own sitemap; take them as-is rather than
        # filtering by the seed's host, which fails whenever the site canonicalises
        # to www (or any other host) and the sitemap lists that canonical host.
        for u in sitemap_urls:
            if u not in queue:
                queue.append(u)
        if not queue:
            queue = self.discover([])

        # max_pages == 0 means "everything discovered". The limit counts pages that
        # were actually audited, not queue slots — otherwise an alias or a redirect
        # silently consumes budget and a real page is never reached.
        limit = self.max_pages if self.max_pages > 0 else None
        queued = set(queue)
        audited = {}
        idx = 0
        while idx < len(queue) and (limit is None or len(audited) < limit):
            u = queue[idx]
            idx += 1
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
            self.allowed_hosts.add(urlsplit(key).netloc)

            # Follow internal links found on the page, so pages missing from the
            # sitemap are still reached. Costs no extra requests: the HTML is cached
            # from the fetch that just happened.
            base = entry.get("final") or u
            for href in entry.get("links", []):
                if href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
                    continue
                try:
                    n = urljoin(base, href).split("#")[0].rstrip("/")
                except Exception:
                    continue
                if urlsplit(n).netloc not in self.allowed_hosts:
                    continue
                if n in queued or n in audited:
                    continue
                queued.add(n)
                queue.append(n)

        self.discovered = len(queue)
        self.limit_hit = bool(limit is not None and idx < len(queue))
        self.check_canonical_targets(audited)
        self.check_sitemap_coverage(sitemap_urls, audited)
        self.check_internal_links(urlsplit(self.base).netloc)
        self.check_duplicate_content()
        self.check_og_images()
        self.check_duplicates()
        self.check_hreflang_reciprocity()
        return self.findings

    def discover(self, sitemap_urls):
        """Fallback only. Link-following happens in run() using already-fetched pages."""
        return [u for u in sitemap_urls
                if urlsplit(u).netloc == urlsplit(self.base).netloc]


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
def report(findings, pages, out_json=None, discovered=None, limit_hit=False):
    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings = sorted(findings, key=lambda f: (order[f.severity], f.rule, f.page))
    counts = Counter(f.severity for f in findings)
    errors, warns = counts.get(ERROR, 0), counts.get(WARN, 0)
    score = max(0, 100 - 8 * errors - 2 * warns)

    if limit_hit and discovered:
        print(f"\npages audited: {len(pages)} of {discovered} discovered "
              f"(--max-pages stopped the crawl; use --max-pages 0 for everything)")
    else:
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
                   "discovered": discovered or len(pages),
                   "counts": dict(counts),
                   "findings": [f.as_dict() for f in findings],
                   "page_details": pages},
                  open(out_json, "w"), indent=1)
        print(f"\nwrote {out_json}")

    print()
    return 1 if errors else 0


def psi_findings(url, key=None):
    """Core Web Vitals from the public PageSpeed Insights API.

    Optional on purpose: it needs network access, is rate limited, and field data
    only exists for origins with enough real traffic. Pass --psi-key or set
    PSI_API_KEY; the anonymous quota is shared and usually exhausted.
    """
    from urllib.parse import quote
    api = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
           f"?url={quote(url, safe='')}&strategy=mobile&category=performance")
    if key:
        api += f"&key={quote(key, safe='')}"
    d = http_json(api)
    if not d:
        return [Finding(INFO, "cwv-unavailable", "/",
                        "PageSpeed Insights unreachable", "")]
    err = d.get("error")
    if err:
        code = err.get("code")
        msg = "PageSpeed Insights unavailable"
        if code == 429:
            msg = ("PageSpeed Insights quota exceeded — pass --psi-key or set PSI_API_KEY. "
                   "The anonymous quota is shared and usually exhausted.")
        return [Finding(INFO, "cwv-unavailable", "/", msg, "")]

    audits = (d.get("lighthouseResult") or {}).get("audits") or {}

    def num(key):
        return (audits.get(key) or {}).get("numericValue")

    field = (d.get("loadingExperience") or {}).get("metrics") or {}
    lcp, cls = num("largest-contentful-paint"), num("cumulative-layout-shift")
    flcp = (field.get("LARGEST_CONTENTFUL_PAINT_MS") or {}).get("percentile")
    finp = (field.get("INTERACTION_TO_NEXT_PAINT") or {}).get("percentile")
    fcls = (field.get("CUMULATIVE_LAYOUT_SHIFT_SCORE") or {}).get("percentile")

    bad = []
    if lcp and lcp > 2500:
        bad.append(f"lab LCP {lcp / 1000:.1f}s")
    if cls and cls > 0.1:
        bad.append(f"lab CLS {cls:.2f}")
    if flcp and flcp > 2500:
        bad.append(f"field LCP {flcp / 1000:.1f}s")
    if finp and finp > 200:
        bad.append(f"field INP {finp}ms")
    if fcls and fcls / 100 > 0.1:
        bad.append(f"field CLS {fcls / 100:.2f}")

    if bad:
        return [Finding(WARN, "cwv-poor", "/", ", ".join(bad),
                        "Thresholds are LCP 2.5s, INP 200ms, CLS 0.1. Lab data is a proxy; "
                        "field data is what ranking systems see.")]
    return [Finding(INFO, "cwv-pass", "/", "Core Web Vitals within thresholds", "")]


# --------------------------------------------------------------------------- selftest
BAD_PAGE = """<!doctype html><html><head>
<title>A Page About Widgets And Shipping And Many Other Things Besides Widgets For Everyone</title>
<meta name="keywords" content="a,b">
<link rel="canonical" href="/page">
<link rel="alternate" hreflang="de-CH" href="/de">
<script type="application/ld+json">{ "name": "broken" </script>
</head><body><h1>x</h1><h1>y</h1><img src="a.png"><img src="b.png">
<a href="/clean">c</a> <a href="/does-not-exist">broken</a></body></html>"""

LONG_PARAGRAPH = ("Our programme works with schools across the county to identify girls who have "
                  "dropped out and to support their return to a classroom with a mentor, a uniform "
                  "and the materials they need for the term ahead. Each mentor meets the family at "
                  "home, agrees a plan with the school, and checks in weekly for the first three "
                  "months so that problems are caught early rather than after another absence. The "
                  "approach is deliberately slow and personal because re-entry fails when it is "
                  "treated as a placement rather than a relationship that has to be rebuilt with "
                  "teachers, caregivers and the girls themselves.")

DUP_A = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Programme A</title>
<meta name="description" content="Programme A page.">
<link rel="canonical" href="https://example.com/dup-a"></head>
<body><h1>Programme A</h1><p>{LONG_PARAGRAPH}</p><p>{LONG_PARAGRAPH}</p></body></html>"""

DUP_B = DUP_A.replace("Programme A", "Programme B").replace("dup-a", "dup-b")

SPARSE_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Sparse app</title>
<script src="/app.js"></script></head><body><div id="root"></div></body></html>"""

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
        open(os.path.join(td, "dup-a.html"), "w").write(DUP_A)
        open(os.path.join(td, "dup-b.html"), "w").write(DUP_B)
        open(os.path.join(td, "sparse.html"), "w").write(SPARSE_PAGE)
        a = DirAuditor(td, "https://example.com", 10)
        findings = a.run()

        rules = {f.rule for f in findings}
        must_fire = {"title-long", "canonical-relative", "ldjson-invalid",
                     "hreflang-relative", "img-alt-missing", "meta-keywords",
                     "h1-multiple", "description-missing", "lang-missing",
                     "charset-missing", "viewport-missing"}
        # status-not-200 is excluded here: the fixture deliberately links to /broken,
        # and link-following is expected to reach it and report it.
        must_not = {"title-missing", "canonical-multiple"}

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

        # Broader checks: broken internal link, near-duplicate body, JS-only shell.
        extra = {"internal-link-broken", "duplicate-content", "js-dependent-content"}
        if extra - rules:
            print(f"FAIL: checks did not fire: {sorted(extra - rules)}")
            ok = False

        # Soft 404: a catch-all that answers 200 for any path must be flagged.
        class CatchAll(DirAuditor):
            def __init__(self, root, base_url, n=10):
                super().__init__(root, base_url, n)
                self.seed = base_url + "/"

            def get(self, url):
                if "seo-audit-nonexistent" in url:
                    return Response(url, 200, b"", {})
                return super().get(url)

        if not any(f.rule == "soft-404" for f in CatchAll(td, "https://example.com", 5).run()):
            print("FAIL: soft-404 not detected")
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
    ap.add_argument("--max-pages", type=int, default=25,
                    help="pages to audit; 0 audits every page discovered")
    ap.add_argument("--max-link-checks", type=int, default=30,
                    help="internal links to verify; 0 disables")
    ap.add_argument("--psi", action="store_true",
                    help="also fetch Core Web Vitals from PageSpeed Insights")
    ap.add_argument("--psi-key", default=os.environ.get("PSI_API_KEY", ""),
                    help="PageSpeed Insights API key (or set PSI_API_KEY)")
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

    auditor.max_link_checks = args.max_link_checks

    try:
        subprocess.run(["curl", "--version"], capture_output=True, check=True)
    except Exception:
        if not isinstance(auditor, DirAuditor):
            print("error: curl is required for URL audits", file=sys.stderr)
            return 2

    findings = auditor.run()
    if args.psi and isinstance(auditor, Auditor) and not isinstance(auditor, DirAuditor):
        findings.extend(psi_findings(auditor.seed or auditor.base, args.psi_key))
    return report(findings, auditor.pages, args.json,
                  auditor.discovered, auditor.limit_hit)


if __name__ == "__main__":
    sys.exit(main())
