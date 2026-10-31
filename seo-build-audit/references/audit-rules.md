# Audit rule reference

Every finding `scripts/seo_audit.py` can emit, what it means, and when it is safe to ignore.

**Scoring:** `100 - (8 × errors) - (2 × warnings)`, floored at 0. Info findings never affect the
score. Exit code is `1` when at least one **error** exists, so CI fails on real problems only.

**Severity policy:** an error means the page cannot be indexed correctly or is actively sending
contradictory signals. A warning means it works but is leaving something on the table. Info means
"this is present and here is what it does" — several info rules fire specifically because the thing
is *ignored by Google*, so don't "fix" them by adding more.

---

## Errors

| Rule | Meaning | When it's fine |
| --- | --- | --- |
| `status-not-200` | Page didn't return `2xx` | Never for a page you want indexed |
| `noindex` | `noindex` or `none` in robots meta or `X-Robots-Tag` | Intentional gating (staging, search results, filters) |
| `title-missing` | No `<title>` at all | Never — Google will invent one from page text |
| `title-duplicate` | Identical title on multiple crawled pages | Rarely; only for deliberately equivalent pages |
| `canonical-multiple` | More than one canonical tag | Never — multiple tags are ambiguous |
| `ldjson-invalid` | A JSON-LD block doesn't parse | Never — the entire block is discarded |
| `hreflang-relative` | `hreflang` uses a relative URL | Never — must be fully qualified |
| `robots-blocks-all` | `Disallow: /` under `User-agent: *` | Only during an intentional hard block |
| `robots-5xx` | robots.txt returns a server error | Never — stalls crawling while it persists |
| `robots-too-large` | robots.txt exceeds 500 KiB | Never — content past the cap is ignored |
| `sitemap-relative-urls` | `<loc>` entries aren't absolute | Never |
| `sitemap-too-large` | More than 50,000 URLs in one file | Never — split with a sitemap index |

## Warnings

| Rule | Meaning | When it's fine |
| --- | --- | --- |
| `canonical-missing` | No canonical tag | Low-risk sites with no parameterised URLs; still worth adding |
| `canonical-relative` | Canonical is a relative path | It resolves correctly *if* the host is right — fragile, so fix it |
| `description-missing` | No meta description | Fine on utility pages; bad on pages you want clicked |
| `description-duplicate` | Same description on multiple pages | Rarely |
| `title-long` | Title over ~60 chars | If the important words are front-loaded anyway |
| `img-alt-missing` | Images without `alt` | Decorative images — but use `alt=""` deliberately |
| `lang-missing` | `<html>` has no `lang` | Never really; it's an accessibility issue before an SEO one |
| `hreflang-not-reciprocal` | A variant doesn't link back | Only if the target wasn't crawled — the rule skips unknown targets |
| `ldjson-no-type` | JSON-LD node has no `@type` | Never |
| `redirect-chain` | More than one hop to resolve | Behind a host-level redirect you don't control |
| `robots-missing` | No robots.txt | Acceptable on tiny sites; you lose crawl control and sitemap discovery |
| `robots-unreachable` | robots.txt couldn't be fetched | Network blip — re-run before acting |
| `sitemap-missing` | No sitemap found via robots.txt or `/sitemap.xml` | Sites under ~500 pages that are fully interlinked |
| `http-not-https` | Audited over plain HTTP | Local builds |
| `page-error` | The auditor crashed on one page | Investigate — usually malformed HTML |

## Info

These are *observations*, not defects. Several exist to stop you adding things that do nothing.

| Rule | Meaning | Action |
| --- | --- | --- |
| `canonical-not-self` | Canonical points at a different URL | Confirm it's intentional — this is a consolidation decision |
| `description-long` | Description over 160 chars | None required — no length limit exists; truncation is visual |
| `h1-multiple` | More than one `<h1>` | None — not an error |
| `meta-keywords` | `meta keywords` present | Safe to delete; Google ignores it entirely |
| `rel-next-prev` | `rel=next`/`prev` present | Safe to delete; Google ignores them |
| `robots-crawl-delay` | `crawl-delay` in robots.txt | Delete it; Google does not process it |
| `sitemap-ignored-tags` | `<priority>`/`<changefreq>` in sitemap | Delete them; both are ignored |
| `hreflang-no-x-default` | hreflang set has no `x-default` | Add one if you have a language selector or fallback |
| `og-image-missing` | No `og:image` | Add one for link previews; no ranking impact |

---

## Reading a report

1. **Fix every error on a page before touching its warnings.** A perfect description on a `noindex`
   page is wasted work.
2. **Sort by page, not by rule.** One template usually causes all instances of a rule; fix the
   template, not 200 pages.
3. **Treat info rules as a license to delete markup.** If `meta-keywords` or `<priority>` fired,
   removing them is an improvement, not a regression.
4. **Don't optimise the score.** A 100 is reachable while the site still ranks badly, because
   relevance is not measured here. The score measures hygiene.

## Known limits of the auditor

State these when reporting, so a clean run isn't over-trusted:

- It checks **extraction of the served HTML**, not Google's rendered result. Use URL Inspection for
  the rendered view.
- `hreflang-not-reciprocal` only fires between pages it actually crawled. Missing targets are
  skipped rather than guessed.
- It cannot see Search Console data: indexation status, manual actions, crawl stats, or
  impressions. A clean audit means "eligible", not "indexed".
- It does not evaluate content quality, relevance, or intent match.
- The crawl is capped by `--max-pages` (default 25), so duplicate detection only sees the sampled
  set. Raise it for a full run: `--max-pages 200`.
- It does not execute JavaScript, which is exactly why it's a good proxy for what a crawler sees.
