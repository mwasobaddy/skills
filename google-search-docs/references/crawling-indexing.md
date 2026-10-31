# Crawling and indexing

Source: `search/docs/crawling-indexing/**`, `crawling/docs/**`.

## robots.txt

Only at the host root. `https://example.com/folder/robots.txt` is "Not a valid robots.txt file.
Crawlers don't check for robots.txt files in subdirectories." A file applies "only to the host,
protocol, and port number where the robots.txt file is hosted" (HTTP, HTTPS, FTP).

- **Default:** "there are no restrictions for crawling for the designated crawlers."
- **Encoding:** UTF-8 plain text; lines separated by CR, CR/LF, or LF. A BOM and invalid lines are
  ignored. Non-UTF-8 characters may be dropped, "potentially rendering robots.txt rules invalid".
- **Size:** 500 KiB. "Content which is after the maximum file size is ignored."
- **Supported fields — exactly four:** `user-agent`, `allow`, `disallow`, `sitemap`.

### Syntax

`<field>:<value><#optional-comment>`. Field names are case-insensitive; **path values are
case-sensitive**; a path must start with `/` and rules without a path are ignored. Everything after `#`
is a comment.

### Wildcards

Supported in `allow`/`disallow` only (not `sitemap`):

- `*` — "0 or more instances of any valid character"
- `$` — "the end of the URL"

A trailing `*` is ignored, so `/*` is equivalent to `/` and `/fish*` to `/fish`.

Rules are compared in percent-encoded form, and Google "automatically canonicalize[s] raw UTF-8 rule
paths into percent-encoded forms".

### Group selection and precedence

- Only **one** group applies: "the group with the most specific user agent that matches". Version or
  wildcard suffixes are ignored — "both `googlebot/1.2` and `googlebot*` are equivalent to `googlebot`".
  Order in the file is irrelevant.
- Multiple groups for the same specific agent are merged. "User agent specific groups and global groups
  (`*`) are not combined."
- Because the rule parser ignores `sitemap`, a group containing only `user-agent` and `sitemap` merges
  with the following group.
- Precedence: "the most specific rule based on the length of the rule path. In case of conflicting rules,
  including those with wildcards, Google uses the least restrictive rule."
- `*` matches all crawlers **except** the various AdsBot crawlers, "which must be named explicitly".

### Status handling

| Response | Behaviour |
| --- | --- |
| `3xx` | Follows at least five redirect hops, then treats it as `404`. Frames, JS, and meta refresh redirects are not followed. |
| `4xx` (except `429`) | Treated "as if a valid robots.txt file didn't exist … no crawl restrictions." |
| `5xx` | Stops crawling but keeps trying for 12 hours; then uses "the last good version" for 30 days; after 30 days behaves as if none exists. |
| DNS/network failure | Treated as a server error. |

Caching: "up to 24 hours, but may cache it longer", adjustable by `max-age`; "The cached response may be
shared by different crawlers."

### What robots.txt is not

- Not a removal tool: "it is not a mechanism for keeping a web page out of Google." A disallowed URL "can
  still be indexed if linked to from other sites", and "the URL address and, potentially, other publicly
  available information such as anchor text … can still appear".
- Not enforcement: "The instructions in robots.txt files cannot enforce crawler behavior."
- Not private: it is publicly readable, "potentially disclosing the location of your private content."
- `crawl-delay` — "The non-standard "crawl-delay" robots.txt rule is not processed by Google's crawlers."
  Throttle with `500`/`503`/`429` and an optional `Retry-After`.

## Robots meta tag and `X-Robots-Tag`

- Supported `name` tokens: `googlebot` and `googlebot-news`; "other values are ignored". `robots`
  applies to all engines.
- Placement is not enforced — Google "will respect robots meta tags in the body section".
- `X-Robots-Tag` follows the same rules and supports an agent prefix (`X-Robots-Tag: googlebot: nofollow`)
  and comma-separated lists. Header, agent name, and values are case-insensitive.
- Conflicts: "the more restrictive rule applies" — so `max-snippet:50` plus `nosnippet` yields
  `nosnippet`. Mixed agent tags use "the sum of the negative rules".
- Non-HTML resources (PDF, video, images) need `X-Robots-Tag`; they cannot carry meta tags.
- `noindex` only works if the page is crawlable. If robots.txt blocks it, the rule is never seen.

### Directives

**Enforced — indexing/removal**

| Directive | Effect |
| --- | --- |
| `noindex` | Do not show in results. |
| `none` | "Equivalent to `noindex, nofollow`." |
| `indexifembedded` | Permits indexing when embedded via iframe despite `noindex`. "only has an effect if it's accompanied by `noindex`." |

**Enforced — presentation limits**

| Directive | Effect |
| --- | --- |
| `nosnippet` | No snippet or video preview; a static thumbnail may remain. Applies to web search, Images, Discover, AI Overviews, AI Mode, and "will also prevent the content from being used as a direct input for AI Overviews and AI Mode". |
| `max-snippet:[n]` | Max characters. `0` equals `nosnippet`; `-1` lets Google choose. "ignored if no parseable [number] is specified." Does not affect image/video previews. |
| `max-image-preview:[none\|standard\|large]` | `large` allows up to viewport width. |
| `max-video-preview:[n]` | Seconds. `0` = static image only; `-1` = no limit. |
| `noimageindex` | Do not index images on the page. |
| `notranslate` | No translated title link or snippet. |
| `unavailable_after:[date]` | Drop after a date (RFC 822 / RFC 850 / ISO 8601). "Googlebot will decrease the crawl rate of the URL considerably after the specified date and time." |

`all` is "the default value and has no effect if explicitly listed". Defaults are `index, follow`.

**Ignored or retired:** `noarchive` (cached link "feature no longer exists"), `nocache` ("isn't used by
Google Search"), `nositelinkssearchbox` ("feature no longer exists").

`nofollow` is a hint: it can be "join[ed] with a `noindex` rule", and pages linked with it "may still be
crawled".

### `data-nosnippet`

Text-level and boolean, valid only on `span`, `div`, `section`. "any value specified is ignored" —
including `"false"`. An unclosed element swallows all following content. Custom elements must be wrapped.
Do not toggle it with JavaScript: extraction "may happen both before and after rendering".

Robots meta does **not** limit structured data use — except `article.description` and other creative-work
`description` values. Structured data inside `data-nosnippet` "remains usable".

## Canonicalization

Google selects "the representative –canonical– URL of a piece of content" by clustering near-duplicates
and choosing "the page that … is objectively the most complete and useful". The canonical is crawled most;
duplicates less often, "in order to reduce the crawling load on sites".

Signal strength, in the doc's order:

1. **Redirects** — "A strong signal that the target of the redirect should become canonical."
2. **`rel="canonical"`** — "A strong signal".
3. **Sitemap inclusion** — "A weak signal".

Methods stack: "when you use two or more of the methods, that will increase the chance".

### `rel="canonical"` specifics

- Not a directive: "indicating a canonical preference is a hint, not a rule." Google "may choose a
  different page as canonical than you do".
- Only accepted inside `<head>`. Use absolute URLs (relative paths work but are discouraged). Add a
  self-referential canonical.
- Ignored variants: annotations carrying `hreflang`, `lang`, `media`, or `type` "are not used for
  canonicalization".
- Available as an HTTP header for non-HTML, including PDFs — "Google supports this method for web search
  results only".
- HTTPS is preferred over HTTP. That preference is broken by an invalid SSL cert, insecure dependencies
  (other than images), HTTPS→HTTP redirects, or an HTTPS page canonicalising to HTTP. "Implementing HSTS
  cannot override this strong preference."

### Duplicate content

"Some duplicate content on a site is normal and it's not a violation of Google's spam policies."

Localized variants are duplicates "only if the primary content is in the same language". A search result
may point to a non-canonical duplicate when it suits the user (e.g. the mobile page for a mobile user).

Documented failure modes: missing localized annotations; bad canonical elements injected by CMS or
plugins; servers returning another domain's content or identical soft-404s; hacking that injects 3xx or
cross-domain canonicals; syndicated content ("The canonical link element is not recommended for those who
want to avoid duplication by syndication partners"); copycat sites.

Anti-patterns named by the doc:

- Don't use robots.txt for canonicalization — "Google may still index URLs that are disallowed."
- Don't use the Removals tool — "It hides all versions".
- Don't signal different canonicals through different methods.
- Don't use URL fragments.
- "We don't recommend using `noindex` to prevent selection of a canonical page within a single site."

Clusters are sticky: "Google might hold pages in a duplicate cluster for up to two weeks."

## Sitemaps

"A sitemap helps search engines discover URLs on your site, but it doesn't guarantee that all the items
in your sitemap will be crawled and indexed." Submission "is merely a hint".

Not needed for sites of "about 500 pages or fewer" that are comprehensively interlinked.

- **Limits:** 50 MB uncompressed or 50,000 URLs per file; must be UTF-8.
- **Scope:** "unless you submit your sitemap through Search Console, a sitemap affects only descendants of
  the parent directory" — host at the root.
- **URLs:** absolute. "Google will attempt to crawl your URLs exactly as listed."
- **Order:** "doesn't matter to Google."

### Elements

- `<priority>` and `<changefreq>`: "Google ignores `<priority>` and `<changefreq>` values."
- `<lastmod>`: used only "if it's consistently and verifiably … accurate". Must reflect the "last
  significant update" — main content, structured data, or links. "an update to the copyright date is not".
- All URLs in a sitemap "are suggested as canonicals". For mobile+desktop, "we recommend pointing to only
  one version in a sitemap".
- Don't resubmit unchanged sitemaps repeatedly — "Submitting the same, unchanged sitemap multiple times
  per day" is listed under Avoid.

### Sitemap index

Referenced sitemaps must be on the same site, and "must be in the same directory as the sitemap index
file, or lower". Up to 50,000 `loc` tags; up to 500 index files per site in Search Console.

In robots.txt, `sitemap:` lines are unlimited, "The URL doesn't have to be on the same host", and the
field "isn't tied to any specific user agent".

### Extension caps

- Image: up to 1,000 `<image:image>` per `<url>`.
- News: up to 1,000 `news:news` tags; only articles "created in the last two days".
- Video: max 32 tags per video; files must be reachable over "HTTP and FTP (streaming protocols are not
  supported)".

## JavaScript SEO

Three phases — "Crawling, Rendering, Indexing". Googlebot queues pages for both, and "It is not
immediately obvious when a page is waiting for crawling and when it is waiting for rendering."

- Renderer: "an evergreen version of Chromium", run headless in the Web Rendering Service (WRS).
- Queue latency: "The page may stay on this queue for a few seconds, but it can take longer than that."
- **No documented render timeout.** Any "Googlebot renders for N seconds" figure is unsourced.
- All `200` pages are queued: "All pages with a `200` HTTP status code are sent to the rendering queue, no
  matter whether JavaScript is present." Non-`200` skips rendering.
- Blocked means no render: "Google Search won't render JavaScript from blocked files or on blocked pages."
- WRS does not persist state — "Local Storage and Session Storage data are cleared across page loads" and
  "HTTP Cookies are cleared across page loads."
- Transport: HTTP only. No "`WebSockets` or `WebRTC`".
- Caching: "WRS may ignore caching headers" — fingerprint asset filenames (`main.2bb85551.js`).
- Permissions: "Expect Googlebot to decline user permission requests". WebGL is not supported.
- Shadow DOM: Google "flattens the shadow DOM and light DOM content"; unrendered content is not indexed.
- Feature detection is required.
- WRS "continuously analyze[s] and identify[ies] resources that don't contribute to essential page
  content and may not fetch such resources" — so "Client-side analytics may not provide a full or accurate
  representation of Googlebot and WRS activity."

### Links and navigation

"Google can only discover your links if they are `<a>` HTML elements with an `href` attribute." Fragments
are unusable — "The AJAX-crawling scheme has been deprecated since 2015." Use the History API.

### Lazy loading

"make sure that your lazy-loading implementation loads all relevant content whenever it is visible in the
viewport". Methods "don't rely on user actions… which is important as Google Search does not interact with
your page." Never lazy-load above-the-fold content.

Infinite scroll requires: "each chunk its own persistent, unique URL", absolute not relative parameters
(`?page=12`, not `?date=yesterday`), sequential links, and History API URL updates.

### Canonical and `noindex` under JS

- Set the canonical in the initial HTML. Don't use JavaScript to change it, and "make sure that this is
  the only `rel="canonical"` link tag on the page."
- "When Google encounters the `noindex` tag, it may skip rendering and JavaScript execution" — removing it
  via JS may not work.
- Soft 404s in SPAs: redirect via JS to a URL the server answers `404`, or inject `noindex`.
- Paywalls: shipping full content then hiding it with JS "isn't a reliable way to limit access".

### Dynamic rendering

"Dynamic rendering was a workaround and not a long-term solution." It "creates additional complexities and
resource requirements". Preferred: server-side rendering, static rendering, or hydration.

It is not cloaking "As long as your dynamic rendering produces similar content". Serving materially
different content is cloaking.

## Meta tags and page metadata

Supported `name` values: `description`, `robots`, `googlebot`, `google-site-verification`, `rating`,
`nopagereadaloud`, `viewport`. Plus `http-equiv` `Content-Type`, `charset`, `refresh`.

- `description`: "In some situations, this description is used in the snippet shown in search results."
  No length limit and no ranking claim.
- `<meta name="keywords">`: "The meta-keyword tag is not used by Google Search, and it has no effect on
  indexing and ranking at all."
- `<link rel="next">` / `prev`: "Google no longer uses these HTML `<link>` tags, and they have no effect on
  indexing."
- `meta refresh`: supported but "not supported by all browsers and can be confusing to the user. We
  recommend using a server-side `301` redirect instead."
- Case matters only for `google-site-verification`.
- "Google will ignore `meta` tags that it doesn't support."
- Avoid injecting meta tags with JavaScript.

`<head>` must be structurally valid: "If you use an invalid element in the `<head>` element, Google
ignores any elements that appear after the invalid element." Valid children: `title`, `meta`, `link`,
`script`, `style`, `base`, `noscript`, `template`.

## Redirects and site moves

| Type | Codes | Behaviour |
| --- | --- | --- |
| Permanent | `301`, `308`, instant meta refresh (0 s), HTTP refresh (0 s), JS `location` | "the indexing pipeline uses the redirect as a signal that the redirect target should be canonical" |
| Temporary | `302`, `303`, `307`, meta refresh > 0 s, HTTP refresh > 0 s | "The indexing pipeline doesn't use the redirect as a signal"; target may still be indexed via other signals |

`301` is "a strong signal"; `302` is "a weak signal".

- Hop limit: crawlers follow up to 10; site-move guidance is "no more than 3 and fewer than 5".
- Content at the redirecting URL "is ignored, and the final target URL's content is processed instead."
- "`301` and other permanent redirects don't cause a loss in PageRank."
- Old URLs persist: Google "will continue to occasionally show the old URLs in the results… This is
  normal."
- Timing: "for medium-sized websites, it can take a few weeks or more" and longer for larger sites. "The
  move takes place on a per-URL basis"; Googlebot must visit every old and new URL at least once.
- Keep redirects "generally at least 1 year".
- Expect heavier crawling post-move and temporary ranking fluctuation.

Do:

- Server-side permanent redirects.
- Update self-referencing canonicals, `hreflang`, internal links, and sitemaps.
- Submit Change of Address only for domain or subdomain changes. "You don't need it for HTTP to HTTPS
  moves, switching between www and non-www on the same domain, or moving paths within the same domain."

Don't:

- Redirect many URLs to one irrelevant page — "might be treated as a `soft 404`".
- Chain redirects.
- Rely on crypto redirects ("like the Loch Ness monster, its existence may be disputed").

For hosting-only moves, lower DNS TTL "to a conservative low value (for example, a few hours) at least a
week in advance" and expect "a temporary drop in Googlebot's crawl rate immediately after the launch".

## Removals

| Method | Effect | Use when |
| --- | --- | --- |
| Delete content | Gone everywhere | "the best way to ensure that it won't appear in Google Search and anywhere else" |
| Password-protect | Blocks crawler and users | Private/confidential |
| `noindex` | Out of Search, still reachable | Page stays live for users |
| robots.txt | Crawl blocked, URL may still be indexed | Images/video only, or crawl-load control |
| `404`/`410` | URL dropped over time | Content permanently gone |
| Removals tool | ~6 months, then expires | Urgent, temporary |

- `404` vs `410`: no documented difference. "All `4xx` errors, except `429`, are treated the same."
- robots.txt is explicitly wrong for removal: "Don't use robots.txt as a way to block your page." And
  "Don't use the URL removal tool for canonicalization. It hides all versions of a URL from Search."
- `noindex` timing: "it may take months for Googlebot to revisit a page." Request a recrawl via URL
  Inspection.
- Blocked URLs linger: "Blocked URLs, however, will stay part of your crawl queue much longer, and will be
  recrawled when the block is removed."
- Emergency pause: return `503` or `429`, but "returning `503` or `429` for more than 2 days will cause
  Google to drop those URLs from the index". Never serve `503` for robots.txt. For longer outages serve an
  indexable `200` placeholder.
- Site-wide removal is hard to reverse: "there's no mechanism to speed that up."
