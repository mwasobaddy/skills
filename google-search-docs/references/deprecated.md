# Retired features, systems, and documentation URLs

Source: crawled `search/docs/**` and `crawling/docs/**`. A page that redirects to
`developers.google.com/search/updates` (the "Latest Google Search Documentation Updates" page) has been
removed — that
redirect is the signal that a feature is gone.

## Structured data features removed

These no longer produce rich results. Their pages redirect to the news page. Most SEO guides still
recommend them.

| Retired | Was |
| --- | --- |
| `FAQPage` | FAQ rich results |
| `HowTo` | Step-by-step rich results |
| `CourseInfo` | Course info carousel |
| `CriticReview` | Critic reviews |
| `EstimatedSalary` | Salary estimates |
| `HomeActivities` | Home activities markup |
| `JobTraining` | Job training markup |
| `LearningVideo` | Educational video markup |
| `PracticeProblems` | Practice problems |
| `SitelinksSearchBox` | Sitelinks search box |
| `SpecialAnnouncement` | COVID-era special announcements |
| `VehicleListing` | Vehicle listings |

`Logo` was folded into `Organization` rather than removed — use `Organization.logo`.

## Retired ranking signals and systems

Retired as standalone systems, now part of core ranking:

| System | Status |
| --- | --- |
| Helpful content system | Launched 2022; "In March 2024, it evolved and became part of our core ranking systems." |
| Hummingbird | "made in August 2013"; superseded |
| Panda | "became part of our core ranking systems in 2015" |
| Penguin | "integrated into our core ranking systems in 2016" |
| FID (First Input Delay) | "INP replaces FID as a Core Web Vital" |

Consequence for advice: there is no longer a "helpful content update" to recover from specifically, and no
separate Panda or Penguin penalty to check. Treat these as core-update dynamics.

Also note: MUM is **not** a general ranking system — "It's not currently used for general ranking in Search
but rather for some specific applications."

## Retired directives and markup

| Item | Status |
| --- | --- |
| `noarchive` | Cached link "feature no longer exists" |
| `nocache` | "isn't used by Google Search" |
| `nositelinkssearchbox` | Sitelinks search box "feature no longer exists" |
| `<link rel="next">` / `rel="prev"` | "Google no longer uses these HTML `<link>` tags, and they have no effect on indexing." |
| `<meta name="keywords">` | "has no effect on indexing and ranking at all" |
| `lang` attribute (for language detection) | Google infers language from text |
| AJAX crawling (`#!`) scheme | "deprecated since 2015" |
| `crawl-delay` in robots.txt | "not processed by Google's crawlers" |
| Dynamic rendering | "a workaround and not a long-term solution"; documented as deprecated |
| Sitemap `<priority>` / `<changefreq>` | "Google ignores `<priority>` and `<changefreq>` values." |

### Removed sitemap tags

- **Video:** `<video:category>`, `<video:gallery_loc>`, `autoplay` and `allow_embed` attributes of
  `<video:player_loc>`, `<video:price>`, `<video:tvshow>`.
- **Image:** `<image:caption>`, `<image:geo_location>`, `<image:title>`, `<image:license>`.

Use the structured-data or image-license-metadata equivalents instead of the sitemap extensions.

## Retired products and programs

| Item | Status |
| --- | --- |
| Signed Exchanges (SXG) | Retired. Guidance removed **1 July 2026**, along with AMP viewer and AMP Cache instructions. AMP content "will continue to rank just like any other web page." |
| AMP cache configuration | No longer required — publishers "no longer need to update the AMP cache or configure signed exchanges." |
| Web Light (`googleweblight`) | Crawler retired; docs removed. It also ignored robots.txt rules. |
| Notes and your website | Page returns 404 |
| Package tracking (Early Adopters) | "no longer accepting new partners" |
| Duplex on the web | Retired |
| AdsBot Mobile Web (`AdsBot-Google-Mobile`) | Retired |
| `Google-NotebookLM` | Renamed `Google-GeminiNotebook`; old agent supported until August 2026 |
| `google-speakr` | Renamed `Google-Read-Aloud` |

## Documentation URL moves

Old paths still redirect, so citing them is not fatal — but the canonical location is the new one, and older
paths sometimes still describe retired behaviour.

| Old path | Current path |
| --- | --- |
| `/search/docs/advanced/structured-data/*` | `/search/docs/appearance/structured-data/*` |
| `/search/docs/guides/intro-structured-data` | `/search/docs/appearance/structured-data/intro-structured-data` |
| `/search/docs/guides/javascript-seo-basics` | `/search/docs/crawling-indexing/javascript/javascript-seo-basics` |
| `/search/docs/guides/fix-search-javascript` | `/search/docs/crawling-indexing/javascript/fix-search-javascript` |
| `/search/docs/guides/lazy-loading` | `/search/docs/crawling-indexing/javascript/lazy-loading` |
| `/search/docs/guides/enable-web-stories` | `/search/docs/appearance/enable-web-stories` |
| `/search/docs/guides/search-gallery` | `/search/docs/appearance/structured-data/search-gallery` |
| `/search/docs/advanced/robots/robots_meta_tag` | `/search/docs/crawling-indexing/robots-meta-tag` |
| `/search/docs/advanced/crawling/special-tags` | `/search/docs/crawling-indexing/special-tags` |
| `/search/docs/advanced/guidelines/valid-html` | `/search/docs/crawling-indexing/valid-page-metadata` |
| `/search/docs/advanced/guidelines/qualify-outbound-links` | `/search/docs/crawling-indexing/qualify-outbound-links` |
| `/search/docs/advanced/mobile/google-discover` | `/search/docs/appearance/google-discover` |
| `/search/docs/beginner/get-started` | `/search/docs/fundamentals/seo-starter-guide` |
| `/search/docs/basics/get-started` | `/search/docs/fundamentals/seo-starter-guide` |
| `/search/docs/beginner/search-console` | `/search/docs/monitor-debug/search-console-start` |
| `/crawling/docs/robots-txt/robots-txt-spec` | `/search/docs/crawling-indexing/robots/robots_txt` (content now lives under `/crawling/docs/`) |
| `/crawling/docs/troubleshooting/http-status-codes` | `/search/docs/crawling-indexing/http-network-errors` |

Crawler documentation moved to a separate site (`developers.google.com/crawling/docs/`). IP ranges moved to
`/crawling/ipranges` — "The old location will continue to work."

`consolidation-of-duplicate-urls` now returns a 404; the content was folded into
`consolidate-duplicate-urls`.

## Still live but program-gated

These are documented but require application, interest forms, or are region-limited. Don't recommend them as
generally available:

- Aggregator unit, supplier unit, ecosystem carousel (EEA)
- Job sites features, places sites features (EEA / Türkiye)
- South Africa badge and refinement chip
- UGC Fresh Data Program (application, 6–8 week response; OAuth 2.0 plus validated JSON-LD)
- Carousels (beta)
- Package tracking, if it ever reopens

## How to check

Before implementing anything from a third-party guide:

1. Find the feature page under `developers.google.com/search/docs/appearance/structured-data/`.
2. If it redirects to `/search/updates`, the feature is retired.
3. If it loads, read the required-properties table on that page — not a summary of it.
4. Run `python3 scripts/crawl-google-docs.py --diff` to detect what changed since this file was written.
