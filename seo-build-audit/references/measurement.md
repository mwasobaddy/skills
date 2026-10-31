# Measuring what the auditor can't

Four things a crawl cannot settle: performance, Search Console state, the rendered DOM, and content
quality. Each has a concrete procedure. Do not guess at any of them.

---

## 1. Core Web Vitals

| Metric | Measures | Good |
| --- | --- | --- |
| LCP | Loading | ≤ 2.5 s |
| INP | Responsiveness | < 200 ms |
| CLS | Visual stability | < 0.1 |

**Field data is what matters.** Lab data is a simulation on one device; Google's ranking input comes
from real users (the Chrome UX Report). A site can pass lab and fail field.

### Getting it

```bash
# lab + field together, optional in the auditor
python3 scripts/seo_audit.py https://example.com --psi --psi-key "$PSI_API_KEY"
```

The API also works standalone:

```bash
curl -sS "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https%3A%2F%2Fexample.com&strategy=mobile&key=$PSI_API_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['lighthouseResult']['audits']['largest-contentful-paint']['displayValue'])"
```

| Source | Gives you | Needs |
| --- | --- | --- |
| Search Console → Core Web Vitals | Field, 28-day, grouped by URL pattern | Verified property |
| PageSpeed Insights | Lab (Lighthouse) + field (CrUX) | API key for volume |
| CrUX API / BigQuery | Field, by origin or URL | API key / GCP project |
| `web-vitals` JS library | Your own field data | Instrumentation |

Without a key the anonymous PSI quota is shared and frequently exhausted — a `429` is a quota
problem, not a site problem. The auditor reports it as info rather than failing.

### What usually causes each failure

- **LCP** — a hero image without `fetchpriority="high"`, a render-blocking font or CSS, a slow TTFB.
- **INP** — long tasks on the main thread from hydration or third-party scripts.
- **CLS** — images or embeds without `width`/`height`, or fonts swapping without `size-adjust`.

Do not chase a perfect score. Google's own documentation says page experience is not a single signal
and that "trying to get a perfect score just for SEO reasons may not be the best use of your time".

---

## 2. Search Console state

The auditor cannot see any of this, and none of it can be inferred from HTML:

| Report | Question |
| --- | --- |
| Performance | Which queries and pages earn clicks, impressions, and position |
| Page indexing | Which URLs are indexed, excluded, or errored, and the stated reason |
| Crawl stats | Fetch volume, response codes, file types, crawl purpose |
| Manual actions | Whether a human reviewer applied a penalty |
| Security issues | Malware or social engineering detected |
| Core Web Vitals | Field performance by URL group |
| Generative AI performance | Visibility inside AI features |
| Data anomalies | Whether the data itself was corrupted |

**URL Inspection is the authority for one URL.** It shows the crawled HTML, the rendered HTML, the
user-declared vs Google-selected canonical, and the indexing verdict. When the auditor and URL
Inspection disagree about indexability, URL Inspection wins — it is reading Google's own state.

For programmatic access use the Search Analytics API (performance data), the URL Inspection API
(single-URL status), or bulk export to BigQuery. All require OAuth; none can be faked.

**A clean audit means "eligible", not "indexed".** Only Search Console can tell you the latter.

---

## 3. The rendered DOM

Three different documents, and the differences are the diagnosis:

```bash
# 1. What the server sends (what the auditor reads)
curl -sS https://example.com/page | head -100

# 2. What a browser ends up with
#    open the page, then in the console:
#    document.querySelector('main').innerText.length

# 3. What Google received after rendering
#    Search Console → URL Inspection → Test live URL → View tested page → HTML
```

| Comparison | Meaning |
| --- | --- |
| curl ≈ browser | Server-rendered or static. Nothing to fix. |
| curl is thin, browser is full | **Client-rendered content.** The gate-4 failure. |
| curl is full, Google's HTML is thin | Rendering or resource blocking — check `robots.txt` for JS/CSS and WRS resource drops. |
| All three differ | Caching, cloaking, or A/B testing by user agent. |

The auditor flags the likely case as `js-dependent-content` when a page has fewer than 50 words but
loads external scripts. Treat that as a prompt to run the three-way comparison, not as proof.

---

## 4. Content quality

Not measurable by a crawler, and not a score. Use the documented rubric rather than inventing one.

### Who, How, Why

- **Who** created it — is authorship self-evident? Add real bylines where readers expect them.
  Never fabricate author profiles, credentials, or headshots.
- **How** it was created — was there first-hand experience, research, or testing? Describe it where
  it matters.
- **Why** it exists — to help a reader, or to capture a query? If the honest answer is the latter,
  the page is the problem.

### What the documentation actually says

- E-E-A-T is **not a specific ranking factor**. It is a useful lens, not a checklist score.
- Trust is the most important of the four; the others contribute to it.
- Search quality raters "have no control over how pages rank" and their data "is not used directly in
  our ranking algorithms".
- For topics affecting health, financial stability, or safety (YMYL), the systems give more weight to
  signals consistent with strong E-E-A-T.

### Practical self-assessment

1. Does the page demonstrate first-hand experience, or restate what already ranks?
2. Is there a clear author or organisation accountable for it?
3. Would a reader feel the page answered the question, or that it was padded to a word count?
4. Is anything on the page there only for search engines? Remove it.
5. Does the site have pages that exist only to capture query variants? That is scaled content abuse,
   not SEO.

---

## Verifying a fix

1. Deploy.
2. Re-run the auditor against the live URL, not the build.
3. Request a recrawl via URL Inspection for the specific URL.
4. Expect days to weeks for indexing changes. Metadata changes usually appear within days; canonical
   consolidation can take up to two weeks; `noindex` removal can take months if the page hasn't been
   recrawled.
5. Confirm in Search Console, not by searching for yourself — personalisation and location make your
   own results an unreliable signal.
