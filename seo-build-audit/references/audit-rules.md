# Audit rule reference

Every finding `scripts/seo_audit.py` can emit (59 rules), what it means, and when it is safe to
ignore.

**Scoring:** `100 - (8 × errors) - (2 × warnings)`, floored at 0. Info findings never affect the
score. Exit code is `1` when at least one **error** exists, so CI fails on real problems only.

**Page intent changes the ruleset.** If a page carries `noindex`, it is treated as deliberately
excluded: only technical head hygiene is checked, and the content/social rules are skipped. That is
intentional — flagging a missing description or Open Graph tag on an admin panel is the largest
source of false positives in SEO tooling.

**Severity policy:** an error means the page cannot be indexed correctly or is sending contradictory
signals. A warning means it works but is leaving something on the table. Info is an observation —
several info rules fire because the thing is *ignored by Google*, so don't "fix" them by adding more.

---

## Errors

| Rule | Meaning | When it's fine |
| --- | --- | --- |
| `status-not-200` | Page didn't return `2xx` | Never for a page you want indexed |
| `title-missing` | No `<title>` at all | Never — Google invents one from page text |
| `title-duplicate` | Identical title on multiple crawled pages | Rarely; only for deliberately equivalent pages |
| `canonical-multiple` | More than one canonical tag | Never — multiple tags are ambiguous |
| `ldjson-invalid` | A JSON-LD block doesn't parse | Never — the entire block is discarded |
| `hreflang-relative` | `hreflang` uses a relative URL | Never — must be fully qualified |
| `robots-blocks-all` | `Disallow: /` under `User-agent: *` | Only during an intentional hard block |
| `robots-5xx` | robots.txt returns a server error | Never — stalls crawling while it persists |
| `robots-too-large` | robots.txt exceeds 500 KiB | Never — content past the cap is ignored |
| `sitemap-relative-urls` | `<loc>` entries aren't absolute | Never |
| `sitemap-too-large` | More than 50,000 URLs in one file | Never — split with a sitemap index |
| `canonical-target-error` | The canonical URL itself returns `4xx`/`5xx` | Never — you are consolidating into nothing |
| `soft-404` | Unknown URLs return `200` instead of `404` | Never — a catch-all route makes every missing page indexable |

## Warnings

| Rule | Meaning | When it's fine |
| --- | --- | --- |
| `charset-missing` | No `<meta charset>` | Never — parsers guess the encoding and garble the page |
| `viewport-missing` | No viewport meta tag | Never — its presence is what signals a mobile-built page |
| `canonical-missing` | No canonical tag | Low-risk sites with no parameterised URLs; still worth adding |
| `canonical-relative` | Canonical is a relative path | Resolves correctly *if* the host is right — fragile, so fix it |
| `description-missing` | No meta description | Fine on utility pages; bad on pages you want clicked |
| `description-duplicate` | Same description on several pages | Rarely |
| `h1-missing` | No `<h1>` | Fine when the page has a visible title in other markup |
| `title-long` | Title over ~60 chars | If the important words are front-loaded anyway |
| `img-alt-missing` | Images without `alt` | Decorative images — but use `alt=""` deliberately |
| `lang-missing` | `<html>` has no `lang` | Never really; accessibility first, SEO second |
| `hreflang-not-reciprocal` | A variant doesn't link back | Only if the target wasn't crawled — unknown targets are skipped |
| `ldjson-no-type` | JSON-LD node has no `@type` | Never |
| `ldjson-retired-type` | Markup for a rich result Google retired (`FAQPage`, `HowTo`, `SitelinksSearchBox`, …) | Harmless but earns nothing — remove it or keep it for other consumers |
| `ldjson-missing-required` | A required property is missing for that type | Never — the item becomes ineligible |
| `hreflang-invalid-code` | Language or region subtag isn't valid ISO 639-1 / 3166-1 | Never — Google silently ignores that subtag |
| `internal-link-broken` | An internal link returns `4xx`/`5xx` or no response | If the target is intentionally gone — then remove the link |
| `duplicate-content` | Two pages share ≥80% of their 5-word shingles | Syndicated or regional variants where a canonical handles it |
| `js-dependent-content` | Under 50 words served, with external scripts | A genuinely short page that isn't JS-rendered — verify with `curl` |
| `og-image-unreachable` | `og:image` doesn't resolve | Never — previews fall back to nothing |
| `cwv-poor` | Lab or field Core Web Vitals exceed thresholds | Never, but weigh it against relevance — it is one signal among many |
| `redirect-chain` | More than one hop to resolve | Behind a host-level redirect you don't control |
| `robots-missing` | No robots.txt | Acceptable on tiny sites; you lose crawl control and sitemap discovery |
| `robots-unreachable` | robots.txt couldn't be fetched | Network blip — re-run before acting |
| `sitemap-missing` | No sitemap via robots.txt or `/sitemap.xml` | Sites under ~500 pages that are fully interlinked |
| `http-not-https` | Audited over plain HTTP | Local builds |
| `page-error` | The auditor crashed on one page | Investigate — usually malformed HTML |

## Info

Observations, not defects. Several exist precisely to stop you adding markup that does nothing.

| Rule | Meaning | Action |
| --- | --- | --- |
| `page-excluded` | Page is `noindex` by design | None — confirm the exclusion is intentional |
| `canonical-on-noindex` | Canonical present on a `noindex` page | Harmless; Google ignores it there |
| `canonical-not-self` | Canonical points at a different URL | Confirm — this is a consolidation decision |
| `description-long` | Description over 160 chars | None — no length limit exists; truncation is visual |
| `h1-multiple` | More than one `<h1>` | None — not an error |
| `meta-keywords` | `meta keywords` present | Safe to delete; Google ignores it entirely |
| `rel-next-prev` | `rel=next`/`prev` present | Safe to delete; Google ignores them |
| `robots-crawl-delay` | `crawl-delay` in robots.txt | Delete it; Google does not process it |
| `robots-host-directive` | `Host:` in robots.txt | Delete it or ignore it; Yandex-only, Google ignores it |
| `sitemap-ignored-tags` | `<priority>`/`<changefreq>` in sitemap | Delete them; both are ignored |
| `og-title-missing` | No `og:title` | Add it — Google reads it as a title-link source |
| `og-image-missing` | No `og:image` | Add one — link previews, and a Google image signal |
| `og-description-missing` | No `og:description` | Optional — Google ignores it, social platforms use it |
| `twitter-card-missing` | No `twitter:card` | Optional — X/Twitter previews only |
| `favicon-missing` | No `<link rel="icon">` | Add one — used as the favicon in search results |
| `hreflang-no-x-default` | hreflang set has no `x-default` | Add one if you have a language selector or fallback |
| `og-image-small` | `og:image` is below 600×315 | Use ≥1200×630 for large previews |
| `page-not-in-sitemap` | Indexable page reached by crawling, absent from the sitemap | Intentionally unlisted pages |
| `cwv-pass` | Core Web Vitals within thresholds | None — this is the good outcome |
| `cwv-unavailable` | PageSpeed Insights unreachable or quota exceeded | Add `--psi-key`; the anonymous quota is shared |

---

## Reading a report

1. **Fix every error on a page before touching its warnings.** A perfect description on a page that
   returns `500` is wasted work.
2. **Sort by page, not by rule.** One template usually causes every instance of a rule; fix the
   template, not 200 pages.
3. **Check intent before "fixing" anything.** A `page-excluded` finding means the page is
   deliberately out of the index — a report that lists missing descriptions there is noise.
4. **Treat info rules as a licence to delete markup.** If `meta-keywords` or `sitemap-ignored-tags`
   fired, removing them is an improvement.
5. **Don't optimise the score.** 100 is reachable while the site still ranks badly, because
   relevance is not measured here. The score measures hygiene.

## Known limits of the auditor

State these when reporting, so a clean run isn't over-trusted:

- It checks the **served HTML**, not Google's rendered result. `js-dependent-content` is a heuristic;
  confirm with the three-way comparison in `measurement.md`.
- It does not execute JavaScript — which is why it is a faithful proxy for what a crawler receives.
- **Core Web Vitals only with `--psi`**, and only if the PSI API answers. It needs `--psi-key` for
  reliable volume; the anonymous quota is shared and often exhausted. Without it, use Search Console
  or CrUX.
- **It cannot see Search Console state**: indexation, manual actions, crawl stats, impressions. A
  clean audit means "eligible", not "indexed".
- `hreflang-not-reciprocal` only fires between pages it actually crawled; missing targets are
  skipped rather than guessed.
- Link checking is capped at `--max-link-checks` (default 30) and covers **internal links only**.
  External links are not verified.
- `duplicate-content` compares 5-word shingles within the crawled sample. It catches near-identical
  bodies, not paraphrases.
- It does not evaluate content quality, relevance, or intent match — see the rubric in
  `measurement.md`.
- `og:image` dimensions are read for PNG, GIF, JPEG, and WebP only; SVG and AVIF report presence
  without size.
- The crawl is capped by `--max-pages` (default 25), so every cross-page check only sees the sample.
  Raise it for a full run: `--max-pages 200`.
