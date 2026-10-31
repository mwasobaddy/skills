# The `<head>` block: canonical format

Every page needs a head. Two things decide whether yours works: **what is in it**, and **what order
it is in**.

## Ordering rules that actually matter

1. **`<meta charset>` first**, within the first 1024 bytes. After that, parsers guess and can
   mis-decode the rest of the document.
2. **`<meta name="viewport">` early.** Its presence is what tells Google the page is built for
   mobile.
3. **If an invalid element appears in `<head>`, Google ignores every element after it.** A stray
   `<div>`, a comment that isn't closed properly, or a `<script>` that emits markup can silently
   kill your canonical and robots tags. Validate the rendered head, not the template.
4. **One `<title>` and at most one canonical.** Duplicates are ambiguous, not additive.

## Indexable page

```html
<!doctype html>
<html lang="en-KE">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <title>Girls' school re-entry programme | Imarisha Dada</title>
  <meta name="description" content="How Imarisha Dada helps girls in Kibera return to school, with safe spaces and economic empowerment for young mothers.">

  <link rel="canonical" href="https://www.imarishadada.org/programmes/school-re-entry">

  <!-- Google-specific: allowed previews, and explicit indexability -->
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">

  <!-- Social and messaging apps -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Imarisha Dada">
  <meta property="og:title" content="Girls' school re-entry programme | Imarisha Dada">
  <meta property="og:description" content="How Imarisha Dada helps girls in Kibera return to school.">
  <meta property="og:url" content="https://www.imarishadada.org/programmes/school-re-entry">
  <meta property="og:image" content="https://www.imarishadada.org/img/re-entry-1200x630.jpg">
  <meta property="og:image:alt" content="Students in a classroom in Kibera">
  <meta property="og:locale" content="en_KE">
  <meta name="twitter:card" content="summary_large_image">

  <!-- Only when real alternates exist -->
  <link rel="alternate" hreflang="en-KE" href="https://www.imarishadada.org/programmes/school-re-entry">
  <link rel="alternate" hreflang="x-default" href="https://www.imarishadada.org/programmes/school-re-entry">

  <link rel="icon" href="/favicon.ico" sizes="48x48">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">

  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"NGO",
   "name":"Imarisha Dada",
   "url":"https://www.imarishadada.org",
   "logo":"https://www.imarishadada.org/img/logo.png"}
  </script>
</head>
```

## Excluded page (admin, staging, internal search)

```html
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Users · Admin</title>
  <meta name="robots" content="noindex, nofollow">
</head>
```

That is the **whole** required head. A deliberately excluded page does not need a description, a
canonical, Open Graph tags, an `h1`, or a word count. Do not "fix" those.

For non-HTML resources (PDF, images, video), meta tags cannot apply — use the header:

```
X-Robots-Tag: noindex
```

## Per-tag table: who consumes what

| Tag | Google Search | Other consumers | Notes |
| --- | --- | --- | --- |
| `<meta charset>` | Required | Browsers | First 1024 bytes |
| `<meta name="viewport">` | Read — signals mobile design | Browsers | Required for mobile-first |
| `<title>` | **Used** — one of 9 title-link inputs | Browsers, social | Never a guarantee |
| `<meta name="description">` | Read — snippet fallback | — | Not a ranking factor, no length limit |
| `<link rel="canonical">` | **Hint**, not a directive | — | Absolute, one per page |
| `<meta name="robots">` | **Enforced** | Other engines | `noindex` wins over `index` |
| `X-Robots-Tag` header | **Enforced** | Other engines | Only option for non-HTML |
| `og:title` | **Read** as a title-link source | Facebook, Slack, LinkedIn | Non-obvious |
| `og:site_name` | **Read** as a site-name source | Social | Below `WebSite` structured data in priority |
| `og:image` | **Read** — preferred image for Google Images | Social | 1200×630 is the social convention |
| `og:description` | **Not used** by Google | Social | Duplicate the description if convenient |
| `og:url`, `og:type`, `og:locale` | **Not used** by Google | Social | Harmless |
| `<meta name="twitter:*">` | **Not used** by Google | X/Twitter | Optional |
| `<link rel="icon">` | **Used** for the favicon in results | Browsers | Square, ≥8×8, one per hostname |
| `hreflang` alternates | **Used** for localization | — | Not language detection |
| JSON-LD `<script>` | **Used** for rich results | — | Must match visible content |
| `<meta name="keywords">` | **Ignored entirely** | Nothing | Delete it |
| `<meta name="theme-color">` | **Not used** | Browsers | Fine to keep |
| `<meta name="author">` | **Not used** | Nothing | Authorship comes from structured data |
| `<link rel="next"|"prev">` | **Ignored** | Some engines | Delete it |
| `<meta name="noarchive">` | **Ignored** — feature retired | — | Delete it |

## Social tags: the minimum that matters

Google reads three Open Graph tags and ignores the rest. Keep them anyway — they are what makes a
link look correct when someone shares it, which is a real distribution channel.

- `og:title`, `og:description`, `og:url`, `og:image` (≥1200×630), `og:image:alt`.
- `og:type` — `website` for pages, `article` for posts.
- `og:site_name` — the brand name. Also a Google site-name input, so set it deliberately.
- `twitter:card` — `summary_large_image` if you have a wide image, else `summary`.

Because `og:title` and `og:site_name` feed Google, keep them **consistent with** `<title>` and your
`WebSite` structured data. Contradictory values give Google three candidates and no clear
preference.

## Common head mistakes

| Mistake | Effect |
| --- | --- |
| Invalid element in `<head>` | Everything after it is ignored — canonical and robots included |
| Canonical injected by JavaScript | Often unseen; Google may pick a different URL |
| Two canonical tags (theme + plugin) | Ignored as ambiguous |
| Relative canonical | Resolves against the wrong host on some routes |
| `noindex` on a robots.txt-blocked page | Never seen; the URL can still be indexed |
| `Disallow: /` in robots.txt by accident | Whole site deindexed |
| Description duplicated across pages | Candidates for rewriting, and usually not selected |
| `hreflang` pointing one way only | Ignored entirely |
| Title left half-empty (`<title>| Brand</title>`) | Google rebuilds it from page text |
| JSON-LD describing content not on the page | Loses eligibility; possible manual action |

## Checking it

```bash
curl -sS https://example.com/page | sed -n '/<head>/,/<\/head>/p'
```

That is the head a crawler receives. If a tag you expected isn't in that output, it does not exist as
far as Google is concerned — regardless of what the browser's inspector shows after hydration.
