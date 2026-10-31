# Implementing SEO per concern

Framework-neutral. Every snippet below belongs in the **server-rendered** response. If your
framework can only emit it client-side, that is the bug to fix first.

For the complete `<head>` in canonical order, with a per-tag table of what Google actually reads
versus ignores, see `head-template.md`. This file covers each concern in depth.

## Titles

```html
<title>Primary topic | Brand</title>
```

- Unique per URL. Duplicates actively compete with each other.
- Front-load the topic; brand last. Delimiter `|`, `-`, or `:` — no preference exists.
- ~60 characters before truncation; not a hard limit, just what survives.
- Don't stuff variants (`Foobar, foo bar, foobars`). Google rewrites padded titles.
- Never leave it half-empty (`<title>| Brand</title>`) — Google rebuilds from page text.
- Match the script and language of the page content.

## Meta descriptions

```html
<meta name="description" content="One specific sentence about what this page covers.">
```

- Unique per URL, written for a human.
- No length limit exists. Truncation is visual, to the device width. Target ~150–160 to be safe,
  not because a limit exists.
- Not a ranking factor. It is the snippet fallback when the body doesn't answer the query better.
- Description text can surface facts the body buries — price, author, date, count.
- Keyword strings are *less* likely to be selected, not more.

## Charset and viewport

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
```

- `charset` must appear within the **first 1024 bytes**. Later, parsers guess.
- `viewport` is a technical requirement, not a nicety: its presence is what indicates to Google that
  the page is built for mobile, and indexing is mobile-first.

## Social and Open Graph

```html
<meta property="og:type" content="website">
<meta property="og:site_name" content="Acme">
<meta property="og:title" content="Shipping a Widget | Acme">
<meta property="og:description" content="How to ship a widget safely.">
<meta property="og:url" content="https://acme.com/widgets/shipping">
<meta property="og:image" content="https://acme.com/img/shipping-1200x630.jpg">
<meta property="og:image:alt" content="A widget in a shipping box">
<meta name="twitter:card" content="summary_large_image">
```

- **Google reads `og:title`, `og:site_name`, and `og:image`.** Not for ranking, but as inputs: a
  title-link source, a site-name source, and a preferred image for the result thumbnail. Keep them
  consistent with `<title>` and your `WebSite` structured data, or you hand Google three competing
  candidates.
- Google ignores `og:description`, `og:url`, `og:type`, `og:locale`, and all `twitter:*` tags. Keep
  them for social previews, not for Search.
- Image at least 1200×630 for wide previews. Supply `og:image:alt`.

## Canonical

```html
<link rel="canonical" href="https://example.com/absolute/path">
```

- Absolute, with scheme and host. Relative works but breaks across hosts.
- Self-referencing by default on every indexable page.
- Exactly one per page.
- Only point elsewhere when the URL is genuinely a duplicate variant (sort order, tracking param,
  print view, paginated duplicate).
- Not a directive: Google may pick a different canonical. Repeating it in sitemap and redirect adds
  weight.
- Must appear in the initial HTML. Setting it from JavaScript is unreliable.

## Robots meta and `X-Robots-Tag`

```html
<meta name="robots" content="noindex">
```

```
X-Robots-Tag: noindex
```

- Use the header for non-HTML (PDF, images, video). Meta tags cannot apply there.
- `noindex` needs the page crawlable. If robots.txt blocks it, the rule is never seen and the URL
  can still be indexed from external links.
- Placement in `<head>` is not enforced — Google honours it in `<body>` too — but put it in `<head>`.

Use `noindex` for: internal search results, faceted/filter URLs, staging, thin utility pages,
thank-you pages, and paginated duplicates you don't want indexed.

## Redirects

| From → to | Use | Notes |
| --- | --- | --- |
| Permanent move | `301` or `308` | One hop. Never chain. |
| Temporary | `302` or `307` | Keeps the original canonical |
| Host/protocol change | `301` at the edge | Plus Change of Address for domain moves |

- Point internal links at the **final** URL so crawlers never take the hop.
- Keep permanent redirects live for at least a year.
- Don't redirect many unrelated URLs to one page — Google treats that as a soft 404.
- Don't implement redirects in the client router. The server must answer with the status code.

## Pagination

- Every page gets its own URL (`?page=2`) and its own self-canonical. Do not canonical page 2 to
  page 1.
- `rel=next`/`rel=prev` are ignored by Google. Keep them only for other engines, if at all.
- Never paginate with `#` fragments — Google ignores fragments and may treat page 2 as page 1.

## hreflang

```html
<link rel="alternate" hreflang="en-GB" href="https://example.com/en-gb/page">
<link rel="alternate" hreflang="de" href="https://example.com/de/page">
<link rel="alternate" hreflang="x-default" href="https://example.com/page">
```

- Every page lists **itself and all alternates** — identical stack on each variant.
- Absolute URLs only.
- **Reciprocal or ignored.** If A points to B, B must point to A.
- `x-default` for unmatched languages.
- ISO 639-1 language, optional ISO 3166-1 region. Region alone is invalid. `UK`, `EU`, `UN` are
  silently ignored.
- Don't combine `hreflang` with `media` or other attributes on the same `<link>`.
- For PDFs, use the `Link:` response header instead.

## Structured data (JSON-LD)

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Article",
 "headline":"Shipping a Widget","datePublished":"2026-01-14"}
</script>
```

- JSON-LD is the recommended format. Microdata and RDFa work; JSON-LD is easier to validate.
- Must be valid JSON. One syntax error discards the whole block.
- Mark up only content visible on the page.
- Required properties come from each type's own documentation — not from blog checklists. `Recipe`
  requires only `name`; `Event` only `startDate`.
- Must be crawlable: don't block the page, don't gate it behind `noindex`.
- Put it on duplicate URLs too, not just the canonical.

## Images

```html
<img src="/widget.jpg" alt="A blue widget on a workbench" width="800" height="450" loading="lazy">
```

- `alt` describing the image. Keyword stuffing here is a spam signal.
- Explicit `width`/`height` prevent layout shift (CLS).
- `loading="lazy"` only below the fold. Never lazy-load the hero image.
- Images must be real `<img>` tags. CSS background images are not indexed.
- Formats: JPEG, PNG, WebP, AVIF, GIF, SVG.

## 404s and gone pages

- Return an actual `404` status. A "not found" page with a `200` is a soft 404 and gets indexed.
- `410` is not faster than `404`; both are treated the same.
- For removed content, return `404`/`410` — not `noindex`, not a redirect to the home page.
- During maintenance, return `503` with `Retry-After`. Never `503` for longer than about two days,
  and never `503` your robots.txt.

## robots.txt

```
User-agent: *
Allow: /

Disallow: /search
Disallow: /*?sort=

Sitemap: https://example.com/sitemap.xml
```

- At the **host root only**. Subdirectory robots.txt files are never read.
- Fields Google supports: `user-agent`, `allow`, `disallow`, `sitemap`. `crawl-delay` is ignored.
- 500 KiB cap; everything after is discarded.
- `Disallow: /` for `*` with no `Allow` blocks the whole site — the most common catastrophic typo.
- robots.txt is not a removal tool. A blocked URL can still appear in results.

## Sitemap

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page</loc></url>
</urlset>
```

- Absolute URLs only. Canonical URLs only — not redirects, not `noindex` pages, not 404s.
- 50,000 URLs / 50 MB per file; use a sitemap index beyond that.
- `priority` and `changefreq` are ignored. Omit them.
- `lastmod` only helps when it's genuinely accurate.
- Reference it from robots.txt.

## Staging protection

The single most common production incident: staging `noindex` shipped to prod, or prod `noindex`
left in from a launch freeze.

- Gate the directive on an environment variable, and make the default *indexable*.
- Assert it in CI: audit the built output and fail if production pages carry `noindex`.
- Audit the live site after deploy, not just the build — headers can differ at the edge.
