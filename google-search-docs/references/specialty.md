# Specialty guides — international, ecommerce, explicit content

Source: `search/docs/specialty/**`.

## International and multilingual sites

### What `hreflang` is for

It tells Google that several URLs are localized variants of the same content, so Search can return the
right one per user. It is **not** a language detector:

> "Google doesn't use `hreflang` or the HTML `lang` attribute to detect the language of a page; instead, we
> use algorithms to determine the language."

Localized pages are duplicates "only if the main content of the page remains untranslated" — so a
translated page is a distinct page, not a duplicate needing a canonical.

### Three equivalent methods

HTML `<link>`, HTTP `Link:` headers, or the XML sitemap. "The three methods are equivalent from Google's
perspective." Using all three gives "no benefit in Search".

### Rules that decide whether annotations are honoured

- "Each language version must list itself as well as all other language versions."
- "Alternate URLs must be fully-qualified, including the transport method (http/https)" — `https://example.com/foo`,
  not `//example.com/foo` or `/foo`.
- "Alternate URLs do not need to be in the same domain."
- **Reciprocity is mandatory:** "If two pages don't both point to each other, the tags will be ignored."
  The reason given: "so that someone on another site can't arbitrarily create a tag naming itself as an
  alternative version of one of your pages."
- Partial sets are tolerated: "you can omit some languages on some pages; Google will still process the
  ones that point to each other." New language pages should be linked bidirectionally to the originating or
  dominant language rather than to each other.
- Add a catch-all for unmatched languages, especially on language selectors and auto-redirecting home pages,
  using `x-default`.

### HTML form

Identical `<link>` set in the `<head>` of every variant, including a self-reference:

```html
<head>
  <title>Widgets, Inc</title>
  <link rel="alternate" hreflang="en-GB" href="https://en-gb.example.com/page.html" />
  <link rel="alternate" hreflang="en-US" href="https://en-us.example.com/page.html" />
  <link rel="alternate" hreflang="en"    href="https://en.example.com/page.html" />
  <link rel="alternate" hreflang="de"    href="https://de.example.com/page.html" />
  <link rel="alternate" hreflang="x-default" href="https://www.example.com/" />
</head>
```

- Must be inside a **well-formed** `<head>`; validate the rendered page, not the template.
- Don't combine `hreflang` with other attributes such as `media` on the same `<link>`.

Subdomains like `en-gb.` are not interpreted: "the language-specific subdomains … are not used by Google to
determine the target audience for the page; you must explicitly map the target audience."

### HTTP header form

Useful for non-HTML files such as PDFs:

```
Link: <https://example.com/file.pdf>; rel="alternate"; hreflang="en",
      <https://de-ch.example.com/file.pdf>; rel="alternate"; hreflang="de-CH",
      <https://de.example.com/file.pdf>; rel="alternate"; hreflang="de"
```

URLs need surrounding `<>`. The header returned must be identical for every version.

### Sitemap form

Declare `xmlns:xhtml="http://www.w3.org/1999/xhtml"`. Each `<url>` carries `<loc>` plus one
`<xhtml:link rel="alternate" hreflang="…">` per variant, including itself. Child links "don't count towards
the URL limit for sitemaps."

### Codes

- Language: **ISO 639-1**. Region: **ISO 3166-1 Alpha 2**. Only codes in those standards work — "other codes
  that aren't listed in those standards, such as es-419, aren't supported."
- Case-insensitive, but uppercase regions follow convention (`en-GB`).
- **You cannot specify a country alone.** "The first code stands for the language and Google doesn't
  automatically derive the language from a country code." So `be` means Belarusian, not Belgium — use
  `de-BE`, `nl-BE`, `fr-BE`.
- Script variants: the script is derived from the region (`zh-TW` → Traditional), or set explicitly with
  ISO 15924 (`zh-Hant`, `zh-Hans`, and optionally `zh-Hans-US`).
- Reserved codes with **no effect**: `EU`, `UN`, `UK` — "Google Search ignores that part of the annotation."

`x-default` matches any language not otherwise listed. "There's no need to specify a language code for the
`x-default` value." It was "designed for language selector pages".

### Documented common mistakes

1. **Missing return links** — the top cause of ignored annotations.
2. **Incorrect language codes** — using a region where a language belongs.
3. **Incorrect region codes** — reserved or unofficial codes silently ignored.

### Multi-regional guidance

For content in one language with regional variations, or fully translated sites, use `hreflang` plus a
consistent URL scheme (ccTLD, subdomain, or subdirectory). Do not auto-redirect by IP or browser language on
the canonical entry point — keep a selector page and let users choose, and use `x-default`.

Google warns that auto-redirecting locale-adaptive pages can prevent crawling of other versions; see
`locale-adaptive-pages` before implementing IP-based redirection.

## Ecommerce

### URL structure

- "Minimize the number of alternative URLs that return the same content" — Google "may not realize that two
  URLs return the same page until after both are retrieved."
- Descriptive over numeric: `/product/black-t-shirt-with-a-white-collar`, not `/product/3243`.
- Query parameters are fine when used consistently: `/photo-frames?page=2`, `/t-shirt?color=green`.

### Pagination and incremental loading

- "Give each page a unique URL" — paginated pages "are treated as separate pages by Google."
- "Don't use the first page of a paginated sequence as the canonical page. Instead, give each page its own
  canonical URL."
- **Never paginate with fragment identifiers** — "Google ignores fragment identifiers", so Googlebot may
  treat `#page-2` as the page it already fetched.
- `rel="next"` / `rel="prev"`: "Google no longer uses these tags, although these links may still be used by
  other search engines."
- `preload`, `preconnect`, and `prefetch` can smooth navigation.
- Block filter and sort-order variants (`?order=price`) with `noindex` or robots.txt rules so they don't
  compete with the canonical listing.
- For "load more" and infinite scroll, content must be reachable without user interaction — see the
  lazy-loading rules in `crawling-indexing.md`.

### Site structure

- Keep a browseable hierarchy; avoid pages closer to a search-result list than a category structure (this is
  also the doorway-abuse line).
- Link to important products from category pages and the home page rather than relying on the sitemap alone.
- Use `BreadcrumbList` to express hierarchy, and `ItemList` for category pages.

### Product data

Three distinct surfaces, and they need different data: `Product` snippet (rich result), Merchant listing
(purchasable), and product variants (`ProductGroup`). Merchant Center feeds and Business Profiles feed AI
responses and other Search surfaces.

## Explicit content

### How SafeSearch works

SafeSearch filters results leading to visual depictions of explicit material. It is automated, and can
recognize "educational, documentary, scientific, or artistic (EDSA) value", which is preserved.

- Pages violating the main spam/content policies are removed "regardless of your SafeSearch setting."
- Automated classifiers flag potentially explicit content, making a page ineligible when filtering is on.
- A single explicit page can cause the **entire site** to be filtered "even if some pages" are not explicit.
- Sites can self-declare with the `rating` meta tag (`<meta name="rating" content="adult">`).

### If incorrectly flagged

1. Confirm the cause — check whether the `rating` meta tag is present on pages that aren't adult.
2. Remove the `rating` meta tag where it doesn't belong.
3. Make the non-explicit nature evident in visible content, not just metadata.
4. **Wait at least 2–3 months before requesting a review.** "requesting a review" earlier than that is
   unproductive; the classifiers need time to re-evaluate.
5. Request a review, then recheck.

Explicit flagging also removes eligibility for rich results, featured snippets, and video previews,
independent of SafeSearch.
