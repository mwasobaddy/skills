# Search Essentials — eligibility and spam policies

Source: `search/docs/essentials/technical`, `search/docs/essentials/spam-policies`.

## Minimum technical requirements

Three conditions, all required, none sufficient. Quoted:

> As long as your page meets the minimum technical requirements, it's eligible to be indexed by
> Google Search: Googlebot isn't blocked. The page works, meaning that Google receives an HTTP
> `200 (success)` status code. The page has indexable content.

> Just because a page meets these requirements doesn't mean that a page will be indexed; indexing
> isn't guaranteed.

- **Not blocked** — not behind a login, not disallowed by robots.txt or a `noindex` rule.
- **Returns `2xx`** — client and server error pages are not indexed.
- **Indexable content** — present in the rendered HTML, in a supported file type (see below).

Language is inferred from the page text; Google "doesn't rely on code annotations such as the `lang`".

### Indexable file types

- **Parsed directly:** HTML, `.csv`, `.kml`/`.kmz`, `.gpx`, `.svg`, `.tex`, `.txt`, `.wml`/`.wap`, `.xml`,
  and source code (`.c`, `.cc`, `.cpp`, `.cs`, `.h`, `.java`, `.py`, `.pl`, `.bas`).
- **Converted:** `.pdf`, `.ps`, `.epub`, `.rtf`, `.hwp`, and Office formats (`.doc[x]`, `.xls[x]`,
  `.ppt[x]`, `.odt`, `.ods`, `.odp`).
- **Images:** BMP, GIF, JPEG, PNG, WebP, SVG, AVIF.
- **Video:** 3GP, 3G2, ASF, AVI, DivX, M2V, M3U, M3U8, M4V, MKV, MOV, MP4, MPEG, OGV, QVT, RAM, RM,
  VOB, WebM, WMV, XAP.

Type is read from `Content-Type`; a missing or wrong header can cause a re-parse or a wrong parser.

### Sizes

- Googlebot reads the first **2 MB** of a file, and the first **64 MB** of a PDF. Each CSS/JS
  subresource is fetched separately and bound by the same limit. Applied to uncompressed data —
  beyond it Googlebot "stops the fetch and only sends the already downloaded part".
- Crawler-wide default is **15 MB** per file.

## Spam policies

These apply to all web search results, "including those from Google's own properties". Detected by
automated systems and, as needed, human review. Consequence: "may rank lower in results or not appear
in results at all", plus manual actions.

The policies are non-exhaustive: "Google may act against any type of spam practices we detect."

### Cloaking

Presenting different content to users and search engines to manipulate rankings and mislead users.
Examples: a travel page served to crawlers but discount-drug content to users; keywords injected only
for search-engine user agents. Being hacked often involves cloaking, which hides the hack from owners.

Paywalls are **not** cloaking if Google can see the full content exactly as a subscriber would, and you
follow the Flexible Sampling guidance.

### Doorway abuse

Sites or pages built to rank for specific similar queries that funnel users through intermediate pages
less useful than the destination. Examples: near-duplicate sites with slight URL/homepage variations;
many domains or city pages funnelling to one page; pages closer to a search-results list than a
browsable hierarchy.

### Expired domain abuse

Buying an expired domain and repurposing it primarily to manipulate rankings with low-value content.
Examples: affiliate content on a former government site; medical products on a former charity site;
casino content on a former school site.

### Hacked content

Content placed without permission due to security flaws. Four documented patterns: code injection
(malicious JS/iframes), page injection (new spammy pages), content injection (hidden links/text via CSS,
or cloaking), and redirects (often conditional on referrer, user agent, or device).

### Hidden text and link abuse

Content placed solely to manipulate engines and not viewable by humans: white-on-white text, text behind
an image, off-screen CSS positioning, `font-size:0` or `opacity:0`, a link hidden on a single character.

Explicitly **not** violations: accordions and tabs, slideshows, tooltips, and screen-reader-only text.

### Keyword stuffing

Filling a page with keywords or numbers to manipulate rankings — phone-number lists without added value,
city/region blocks aimed at queries, unnatural repetition.

### Link spam

Links created primarily to manipulate rankings. Documented examples:

- Buying or selling links for ranking, including exchanging goods/services, or sending a product in
  exchange for a review that includes a link.
- Excessive link exchanges, or partner pages existing only for cross-linking.
- Automated programs or services that create links.
- Requiring a link by ToS or contract without letting the other party qualify it.
- Text ads or text links that don't block ranking credit.
- Advertorials/native ads with links that pass credit or carry optimized anchor text.
- Low-quality directory or bookmark links.
- Keyword-rich, hidden, or low-quality links in widely distributed widgets.
- Widely distributed footer or template links.
- Forum comments or signatures with optimized links.
- Creating low-value content primarily to manipulate linking signals.

Buying and selling links **is** acceptable for advertising and sponsorship **if qualified** with
`rel="nofollow"` or `rel="sponsored"`.

### Machine-generated traffic

Sending automated queries to Google — including scraping results for rank checking — without express
permission. Violates both spam policies and the Google Terms of Service.

### Malicious practices

A mismatch between expectation and outcome. Covers **malware**, **unwanted software** (hijacking
settings, leaking data without disclosure), and **back button hijacking** (manipulating browser history
so the back button can't return the user).

### Misleading functionality

Sites that promise a capability they don't deliver — a fake generator that provides nothing, or a "PDF
merge" / "countdown timer" / "online dictionary" page that funnels users to deceptive ads.

### Scaled content abuse

Many pages generated primarily to manipulate rankings rather than help users, "no matter how it's
created". Examples: generating many pages with AI without added value; scraping feeds or search results
and transforming them (synonymizing, translating, obfuscating); stitching content from different pages;
multiple sites to hide the scaled nature; many pages that are keyword-bearing but nonsensical to a reader.

### Scraping

Taking content from other sites, often automatically, to manipulate rankings. Examples: republishing
without original content or value (even without citing); copying and lightly modifying (synonyms,
automation); reproducing feeds without unique benefit; sites that only embed or compile others' media.

### Site reputation policy

Third-party content published on a host mainly **because of** that host's established ranking signals.
Third-party content alone is fine — it's only inconsistent when published *to borrow* the host's signals.

Inconsistent: an education site hosting third-party payday-loan reviews distributed across many sites; a
medical site hosting an unrelated low-quality "best casinos" page.

**Not** inconsistent: wire services and press-release sites; news syndication; UGC sites (forums,
comments); columns and opinion pieces; advertorials intended to reach readers directly rather than to
manipulate rankings; affiliate links treated properly or third-party ad units.

Enforcement differs by region:

- **Outside the EEA** — the relevant pages may receive a manual action.
- **Within the EEA** — pages may be "categorized as separate from the main domain", ranking on their own
  merits, and are *not* subject to a manual action's impact.

Human review (rare) weighs: how the content is presented (design/format/UX consistency), content quality
relative to the main domain, stated or implied authorship, and whether near-identical content appears on
multiple other sites. "Not one of these factors is either necessary or sufficient on its own."

### Sneaky redirects

Redirecting maliciously to show users and engines different content, or unexpected content that doesn't
fulfil the original need. Examples: search engines see one thing, users get something materially
different; desktop users get a normal page while mobile users are sent to a spam domain.

Legitimate redirects include site moves, consolidating pages, and post-login redirects. The test is
intent to deceive.

### Thin affiliation

Affiliate content whose product descriptions and reviews are copied from the merchant with no original
value — typically cookie-cutter templates replicated across domains or languages.

Good affiliate pages add value: pricing detail, original reviews, testing and ratings, category
navigation, comparisons.

### User-generated spam

Spam added by users through channels meant for user content: spam accounts on open hosting, forum posts,
blog comments, uploaded files.

## Other practices that cause demotion or removal

### Legal removals

A significant volume of valid copyright removal requests leads to demotion of other content from the
site. Similar demotion applies to defamation, counterfeit goods, and court-ordered removals. CSAM is
always removed, and sites with a significant proportion are demoted.

### Personal information removals

Sites with exploitative removal practices get other content demoted, and the pattern is checked across
other sites. Similar demotion for doxxing, non-consensual explicit imagery, and non-consensual fake
explicit content.

### Policy circumvention

Continuing to bypass policies — including via new subdomains, subdirectories, or sites — can restrict or
remove eligibility for features (Top Stories, Discover) and remove more sections of a site from results.

### Scam and fraud

Impersonating an official business or service, displaying false business information, or attracting users
under false pretences. Detected by automated systems.

## Recovery

- Spam violations may resolve as "our automated systems learn over a period of months that the site
  complies."
- The link spam update is an exception: "making changes might not generate an improvement… Any potential
  ranking benefits generated by those links cannot be regained."
- Site reputation actions can be addressed or appealed via a reconsideration request; EEA sites can also
  use alternative dispute resolution.
