---
name: google-search-docs
description: Ground SEO and Search answers in Google's own Search documentation rather than SEO folklore. Use when the user asks what Google actually says about ranking, indexing, crawling, robots.txt, sitemaps, canonicalization, duplicate content, structured data, rich results, Core Web Vitals, spam policies, hreflang, site moves, traffic drops, or AI Overviews/AEO/GEO — or asks whether a widely repeated SEO claim is still true. Also use when a rich result disappeared or a structured-data type was retired, even if the user never mentions Google's docs.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Google Search documentation

Google publishes the rules. Most SEO content on the web is a paraphrase of a paraphrase, and a
large share of it describes features Google retired years ago. This skill is the correction
layer: answer from the docs, quote them, and say plainly when the popular advice is wrong.

## Answer from the docs, not from memory

Your training data is unreliable specifically here. Several of the most repeated SEO "facts" are
either retired or were never true, and those are exactly the ones that get asserted confidently.
Before stating any rule about eligibility, limits, or ranking, check it in `references/`.

When the user's premise is wrong, say so directly and give the doc's wording. "Google's spam
policies page says X, which is why Y doesn't apply here" is more useful than a hedged summary.

## Claims that are wrong or stale — check here first

Each row is a claim you will otherwise repeat. The right column is what the documentation says.

| Common claim | What the docs say |
| --- | --- |
| "FAQ rich results need `FAQPage` markup" | Retired. The FAQ rich result was removed; the doc now redirects to the news page. |
| "Add `HowTo` schema for step lists" | Retired. Same — `HowTo` rich results were removed. |
| "Set a 155-character meta description" | "There's no limit on how long a meta description can be." Truncation is visual, to fit the device. |
| "Meta keywords help ranking" | "has no effect on indexing and ranking at all." |
| "Duplicate content gets a penalty" | "Some duplicate content on a site is normal and it's not a violation of Google's spam policies." |
| "`rel=canonical` tells Google which URL to use" | It is "a hint, not a rule." Google may pick a different canonical. |
| "`rel=next`/`rel=prev` for pagination" | "Google no longer uses these HTML `<link>` tags, and they have no effect on indexing." |
| "`priority` and `changefreq` in sitemaps matter" | "Google ignores `<priority>` and `<changefreq>` values." |
| "Use `noindex` to manage crawl budget" | Backfires — "Google will still request, but then drop the page." |
| "robots.txt removes a page from Google" | "it is not a mechanism for keeping a web page out of Google." A disallowed URL can still be indexed. |
| "410 removes a page faster than 404" | No documented difference — "All `4xx` errors, except `429`, are treated the same." |
| "`crawl-delay` in robots.txt throttles Google" | "not processed by Google's crawlers." Use `500`/`503`/`429` with `Retry-After`. |
| "`llms.txt` / AI text files improve AI visibility" | "Google Search ignores them." No special file, markup, or schema is needed. |
| "Chunk content so AI can parse it" | "There's no requirement to break your content into tiny pieces." No ideal page length. |
| "Target every long-tail variant for AEO" | Generating pages per query variation "violates Google's scaled content abuse spam policy." |
| "E-E-A-T is a ranking factor" | "E-E-A-T itself isn't a specific ranking factor." Raters "have no control over how pages rank." |
| "Page experience is a single score" | "There is no single signal." Beyond Core Web Vitals, other aspects "don't directly help your website rank higher." |
| "301 redirects leak PageRank" | "`301` and other permanent redirects don't cause a loss in PageRank." |
| "You can set your own title link / snippet" | Fully automated — "we can't manually change title links for individual sites." |
| "You can mark a page as a featured snippet" | "How can I mark my page as a featured snippet? You can't." |
| "Sitelinks are configurable / have markup" | "At the moment, sitelinks are automated." No markup exists. |
| "Place robots meta only in `<head>`" | Placement "is not enforced"; Google "will respect robots meta tags in the body section." |
| "Freshness: keep the date updated" | Content "is rated by quality, regardless of age." Trivial date bumps do nothing. |
| "A core update penalty needs a fix" | Updates "don't target specific sites or individual web pages." A 2→4 drop needs no action at all. |
| "Deleting weak content recovers rankings" | "Deleting content is a last resort." Mass deletion signals search-first content. |
| "Blocked pages free up crawl budget elsewhere" | Budget shifts "only if Google is already hitting your site's crawl capacity limit." |
| "`lang` attribute sets page language" | Google infers language from text; it "doesn't rely on code annotations such as the `lang`." |
| "Dynamic rendering is the fix for JS SEO" | "a workaround and not a long-term solution" — docs now call it deprecated. |
| "Sign up for signed exchanges / AMP cache" | Retired July 2026. AMP content "will continue to rank just like any other web page." |

If a claim isn't in that table but sounds like folklore, grep the references before repeating it.

## Hard numbers worth knowing

| Limit | Value | Scope |
| --- | --- | --- |
| robots.txt size | 500 KiB; content beyond is ignored | Per host, root only |
| Sitemap | 50 MB uncompressed / 50,000 URLs | Per file |
| Sitemap index | 50,000 `loc`, 500 index files per site | Per site |
| Googlebot file read | 2 MB (HTML/assets), 64 MB (PDF) | Uncompressed |
| Crawlers generally | 15 MB default | Crawler-wide |
| Redirect hops followed | 10 | Recommend ≤3 in a chain |
| Keep redirects live | ≥1 year | Site moves |
| `503`/`429` before URL drop | ~2 days | Site pause only |
| LCP / INP / CLS | 2.5 s / 200 ms / 0.1 | Core Web Vitals |
| Same-site results in top results | ~2 listings | Site diversity system |
| Favicon | Square, ≥8×8 px (≥48×48 recommended) | One per hostname |
| Discover image | ≥1200 px wide, >300,000 px, 16:9 | Discover eligibility |
| Video thumbnail | ≥60×30 px, fetcher: Googlebot + Googlebot-Images | Video indexing |
| Web Stories poster | 640×853, 3:4; logo ≥96×96, 1:1 | Web Stories |
| Paywall free quota | 6–10 articles/user/month; ~10 per month to start | Flexible sampling |

## Decision procedures

### "Why isn't my page indexed?"

Work in this order — each step gates the next:

1. **Not blocked.** robots.txt allows the path, and the page isn't behind auth. A `noindex` inside a
   robots-blocked page is never seen, so the page can still be indexed via external links.
2. **Returns `2xx`.** Error pages are not indexed. `noindex` is honoured only on a crawlable page.
3. **Content is in the rendered HTML.** Google indexes the mobile rendering. If it appears only after
   a user gesture, it "won't be able to index it." Check with URL Inspection's rendered HTML.
4. **`noindex` / `X-Robots-Tag` absent** — and remember it's enforced on the *response*, so check headers
   on the final URL, not just the DOM.
5. **Canonicalization.** Google may have consolidated the URL into a cluster and chosen a different
   canonical. "Google might hold pages in a duplicate cluster for up to two weeks."

Indexing is never guaranteed, even when all of the above pass. Say that rather than inventing a cause.

### "Remove this from Google" — pick the method by intent

| Intent | Method | Note |
| --- | --- | --- |
| Content should be gone everywhere | Delete it, then serve `404`/`410` | "the best way to ensure that it won't appear" |
| Page must stay live for users | `noindex` | Needs the page crawlable to work |
| Private/confidential | Password or auth | Blocks crawler and users |
| Only images/videos | robots.txt | URL may still be listed |
| Urgent, temporary | Removals tool | ~6 months, then expires |

Never recommend robots.txt for deindexing, and never the Removals tool for canonicalization
("It hides all versions of a URL from Search").

### "Traffic dropped" — diagnose in this order

1. Widen the date range to 16 months. Confirm the drop isn't yearly seasonality.
2. Compare against the previous period, then split by Search type (Web/Images/Video/News), then by
   country, device, and page. A site-wide drop and a one-page drop have different causes.
3. Check the Search Console reports for a signal: Page indexing (technical), Crawl stats (technical),
   Manual actions (spam), Security issues (malware/phishing), Data anomalies (data error).
4. If impressions held and only clicks fell, the issue is title/snippet appeal, not ranking.
5. If nothing is flagged, it may be a core update. Wait "at least a full week after a core update
   completes" before drawing conclusions. A 2→4 move needs no action.

Recovery from a core update is content work at the site level, not a checklist. "Deleting content is a
last resort." No guarantee is ever given that changes will have a visible effect.

### "Which structured data should I add?"

Check `references/structured-data.md` for the live feature list and required properties. Defaults that
survive most of the noise:

- `Article`/`BlogPosting` for editorial, `BreadcrumbList` for hierarchy, `Organization`/`WebSite` on the
  home page, `Product` + `Offer` for commerce, `Recipe`, `Event`, `VideoObject`, `JobPosting`.
- Required properties only get you **eligibility**, never a guarantee of display.
- Structured data is not required for AI features and there is "no special schema.org structured data
  that you need to add" for them.

## Reference map

Read on demand — do not load all of these.

| File | Read it when |
| --- | --- |
| `references/essentials.md` | Any question about eligibility, spam policies, manual actions, or why a site is suppressed |
| `references/crawling-indexing.md` | robots.txt/X-Robots-Tag, canonicalization, sitemaps, JS rendering, redirects, site moves, removals |
| `references/appearance.md` | Title links, snippets, ranking systems, Core Web Vitals, images/video, Discover, AI features, paywalls |
| `references/structured-data.md` | Choosing or debugging a rich result; required vs recommended properties |
| `references/monitoring.md` | Traffic-drop triage, Search Console reports, search operators, hacked-site recovery |
| `references/specialty.md` | hreflang and internationalization, ecommerce structure/pagination, explicit content |
| `references/deprecated.md` | "Is X still supported?" — retired features, systems, crawlers, and doc URLs |

## Refreshing the corpus

The references were distilled from a crawl of `developers.google.com/search/docs` — 277 URLs, 191
distinct live documents, plus 15 retired features that redirect. Google edits these pages
continuously, so verify a load-bearing claim before relying on it in high-stakes work:

```bash
python3 scripts/crawl-google-docs.py --out /tmp/gdocs     # fetch + extract
python3 scripts/crawl-google-docs.py --out /tmp/gdocs --diff   # show pages changed since last run
```

The script is resumable and caches HTML, so re-running is cheap. When a claim is contradicted by a
fresh crawl, **trust the crawl** and note the change rather than deferring to this file.

## Scope

Covers `developers.google.com/search/docs` and the linked `crawling/docs` pages. It does not cover
Search Console's UI in depth, Ads, Merchant Center policy, or the Search Quality Rater Guidelines
beyond how the docs reference them.

Content is derived from Google Search Central documentation, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Quotations remain Google's.
