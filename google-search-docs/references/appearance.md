# Ranking and search appearance

Source: `search/docs/appearance/**` (excluding structured data, which is in `structured-data.md`).

## Title links

"Google's generation of title links on the Google Search results page is completely automated and takes
into account both the content of a page and references to it that appear on the web." There is no manual
override: "While we can't manually change title links for individual sites…"

`<title>` is **one input among nine**, not the output. Sources used automatically:

1. `<title>` content
2. The main visual title on the page
3. Heading elements (`<h1>`)
4. `og:title` meta tag
5. Other large or prominent styled text
6. Other text on the page
7. Anchor text on the page
8. Text in links pointing to the page
9. `WebSite` structured data

No length limit: "the title link is truncated in Google Search results as needed, typically to fit the
device width."

### Documented reasons Google rewrites a title

| Named issue | What triggers it |
| --- | --- |
| Half-empty title | `<title>| Site Name</title>` → rebuilt from headers or prominent text |
| Obsolete title | Title year contradicts visible content → the visible date wins |
| Inaccurate title | Keyword padding that misrepresents the page → trimmed |
| Micro-boilerplate | Identical titles across sibling pages (e.g. TV seasons) → distinguishing text injected |
| No clear main title | Several equally prominent headings → "it may use the first heading" |
| Writing-system mismatch | Script of title doesn't match the page language |
| Site-name duplication | At domain level, Google "may omit the site name from the title link" |

Flight prices in `<title>` are likely not shown, because "pricing for flights can change so fast".

**To improve:** unique descriptive title per page; concise brand via a delimiter (`-`, `:`, `|`); one
visually dominant `<h1>`; no keyword stuffing; no boilerplate; title language must match page language.
Changes take "a few days to a few weeks" to appear.

If a page can't be crawled at all, Google will "rely on off-page content to generate the title link".

## Snippets

"Google primarily uses the content on the page to automatically determine the appropriate snippet."

The meta description is a **fallback competitor**, not a directive — used "if it describes the page better
than other parts of the content". Snippets are query-dependent, and "we can't manually change snippets for
individual sites."

### Controls

- `nosnippet` — blocks snippets entirely for the page.
- `max-snippet:[n]` — "specify the maximum length for your snippets."
- `data-nosnippet` — excludes specific regions.

`nosnippet` beats `data-nosnippet`: "`nosnippet` takes priority, and snippets won't be shown for the page."
`data-nosnippet` regions also won't appear in featured snippets.

Length: "There's no limit on how long a meta description can be, but the snippet is truncated… typically to
fit the device width." There is no 155- or 160-character rule anywhere.

Keyword-string descriptions are penalised in selection: "meta descriptions comprised of long strings of
keywords … are less likely to be displayed as a snippet." Programmatic generation is acceptable —
"can be appropriate and are encouraged" — if "human-readable and diverse".

A meta description can carry facts the body wouldn't surface in a snippet: author, date, price, page count.

"Read more" deep links require visible content (no tabs or expanders), no JS-forced scroll position on
load, and no stripping of the URL hash.

## Ranking systems

The doc describes "some of our more notable ranking systems" — explicitly a partial list. **No weights, no
percentages, no ordering, and no combination formula are disclosed.**

> "Our ranking systems are designed to work on the page level, using a variety of signals and systems to
> understand how to rank individual pages. Site-wide signals and classifiers are also used… Having some
> good site-wide signals does not mean that all content from a site will always rank highly, just as having
> some poor site-wide signals does not mean all the content from a site will rank poorly."

There is **no single "algorithm"** in the documentation. It consistently uses plural "ranking systems" and
"core ranking systems".

### Active systems

| System | Function |
| --- | --- |
| BERT | Understands "how combinations of words express different meanings and intent." |
| Crisis information systems | Crisis hotlines and trusted content; SOS Alerts for disasters. |
| Deduplication systems | Shows "only the most relevant results to avoid unhelpful duplication"; also suppresses the duplicate listing when a page becomes a featured snippet. |
| Exact match domain system | Removes excess credit for domains built to match queries. |
| Freshness systems | "Query deserves freshness" — fresher content where expected. |
| Link analysis and PageRank | PageRank "continues to be part of our core ranking systems." |
| Local news systems | Surfaces local sources in Top stories and Local news. |
| MUM | "It's not currently used for general ranking in Search but rather for some specific applications." |
| Neural matching | Matches representations of concepts in queries and pages. |
| Original content systems | Ranks original reporting ahead of those who merely cite it. |
| Removal-based demotion | Site-wide demotion after significant volumes of valid copyright, defamation, counterfeit, or court-order removals; CSAM sites are demoted. Personal-information removals demote sites with exploitative practices. |
| Passage ranking | Identifies individual sections/passages to judge relevance. |
| RankBrain | Understands word↔concept relations, so pages needn't contain the exact query words. |
| Reliable information systems | Surface authoritative pages, demote low quality, elevate quality journalism; content advisories when confidence is low. |
| Reviews system | Rewards "insightful analysis and original research … written by experts or enthusiasts." |
| Site diversity | "generally won't show more than two web page listings from the same site in our top results"; subdomains count as the root domain, with exceptions. |
| Spam detection | Includes SpamBrain; enforces spam policies. |

**Retired, folded into core:** Helpful content system (2022 → core, March 2024), Hummingbird (2013), Panda
(2011 → core 2015), Penguin (2012 → core 2016).

## Core updates and spam updates

Core updates: "Several times a year, Google makes significant, broad changes to our search algorithms and
systems." Crucially, "These changes are broad in nature, and don't target specific sites or individual web
pages."

Ranking moves are not quality verdicts — the doc's restaurant analogy: restaurants that move down "aren't
necessarily 'bad'; there are just other restaurants that make your top 20."

**Prescribed diagnostic procedure:**

1. Confirm the rollout finished (Search Status Dashboard).
2. Wait "at least a full week after a core update completes".
3. Compare that week to the week before rollout started.
4. Review top pages and queries.
5. Analyse search types separately (Web, Images, Video, News).

Small drop (2→4): "There's no need to take drastic action (in fact, we recommend avoiding making changes to
content that's already performing well)." Large drop (4→29): assess the site as a whole.

Advice: apply the self-assessment to the site, not individual pages; get an unaffiliated third party to
assess; "Avoid doing 'quick fix' changes (like removing some page element because you heard it was bad for
SEO)"; "Deleting content is a last resort" — and wanting to delete whole sections is "likely a sign those
sections were created for search engines first, and not people."

Timeline: "some changes can take effect in a few days, but it could take several months"; otherwise "waiting
until the next core update." Smaller core updates are also shipped unannounced.

Explicit non-claims: "there's no guarantee that changes you make to your website will result in noticeable
impact in search results"; positions "aren't static or fixed in place."

Spam updates are improvements to spam detection. Affected sites "should review our spam policies";
violators "may rank lower in results or not appear in results at all"; recovery is possible if "our
automated systems learn over a period of months that the site complies." The link spam update is the
exception — link benefits "cannot be regained".

## Page experience and Core Web Vitals

| Metric | Measures | Threshold |
| --- | --- | --- |
| LCP | Loading performance | Within the first **2.5 s** of load starting |
| INP | Responsiveness | **< 200 ms** |
| CLS | Visual stability | **< 0.1** |

What role it plays, in the doc's words:

> "There is no single signal. Our core ranking systems look at a variety of signals that align with overall
> page experience."

> "Core Web Vitals are used by our ranking systems. We recommend site owners achieve good Core Web Vitals
> for success with Search…"

> "Keep in mind that getting good results in reports like Search Console's Core Web Vitals report or
> third-party tools doesn't guarantee that your pages will rank at the top of Google Search results… trying
> to get a perfect score just for SEO reasons may not be the best use of your time."

> "Beyond Core Web Vitals, other page experience aspects don't directly help your website rank higher in
> search results. However, they can make your website more satisfying to use, which is generally aligned
> with what our ranking systems seek to reward."

> "Google Search always seeks to show the most relevant content, even if the page experience is sub-par."

Evaluation is page-specific in general, with "some site-wide assessments".

## Intrusive interstitials

"Interstitials are overlays on the whole page and dialogs are overlays only on a part of the page" — both
"obstruct users' view of the content, usually for promotional purposes." They "make it hard for Google and
other search engines to understand your content, which may lead to poor search performance."

Two prohibited patterns, "Unless they're legally mandatory":

1. "Don't obscure the entire page with interstitials."
2. "Don't redirect the user to a separate page for their consent or input."

Preferred: banners "that take up only a small fraction of the screen" — Smart App Banners, Chrome's in-app
install experience, small HTML banners.

Legally mandatory gates are exempt but should overlay rather than replace content ("This will ensure that
Google can still at least index some of the content") and must not redirect all URLs to one consent page,
since "Googlebot can only fetch that page".

## AI features (AI Overviews, AI Mode)

**Nothing special is required:**

> "The best practices for SEO remain relevant for AI features in Google Search… There are no additional
> requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary."

> "To be eligible to be shown as a supporting link in AI Overviews or AI Mode, a page must be indexed and
> eligible to be shown in Google Search with a snippet, fulfilling the Search technical requirements. There
> are no additional technical requirements."

> "You don't need to create new machine readable files, AI text files, or markup to appear in these
> features. There's also no special schema.org structured data that you need to add."

So: no `llms.txt`, no AI-specific file, no AI-specific schema. One additional gating condition — a site
must be included in *Search generative AI features* in Search Console to be eligible for display there.

**Explicitly discouraged** (from the generative-AI guide):

- `LLMS.txt` and similar files — Google Search "ignores them". Harmless, but no effect either way.
- "Chunking" content — "There's no requirement to break your content into tiny pieces." "There's no ideal
  page length."
- Rewriting content for machines — AI systems handle synonyms and paraphrase, so chasing every long-tail
  variant is wasted work.
- Inauthentic "mentions" — core ranking systems reward quality, and other systems block spam.
- Over-focusing on structured data — not required for AI features, though still worth keeping for rich
  results.

**Mechanics:** both features "may use a 'query fan-out' technique — issuing multiple related searches across
subtopics and data sources", and "may use different models and techniques, so the set of responses and links
they show will vary". "AI Overviews are only shown when our systems determine that it is additive to classic
Search."

**Control surface:** "AI is built into Search and integral to how Search functions, which is why robots.txt
directives for Googlebot is the control for site owners to manage access to how their sites are crawled for
Search." Presentation limits: `nosnippet`, `data-nosnippet`, `max-snippet`, `noindex`. AI training and
grounding in *other* Google systems is controlled by `Google-Extended`.

**Measurement:** AI-feature traffic sits inside normal Search Console Performance data, "within the 'Web'
search type", plus the Generative AI performance report. No third-party tool has access to internal ranking
or AI systems.

## Images

- Must be embedded as `<img src>` (including inside `<picture>`). "Google doesn't index CSS images" —
  `background-image` is the documented failure case.
- Formats: BMP, GIF, JPEG, PNG, WebP, SVG, AVIF. Data URIs work. Extension should match the type.
- Always include a `src` fallback alongside `srcset`.
- Image sitemaps may contain `<image:loc>` from other domains (a CDN); verify ownership in Search Console.
- Alt text is "The most important attribute", used "along with computer vision algorithms and the contents
  of the page." Keyword-stuffed alt text "may cause your site to be seen as spam."
- Preferred-image signals: `primaryImageOfPage`, `image` on the main entity via `mainEntity` /
  `mainEntityOfPage`, or `og:image`. Avoid logos, text-in-image, extreme aspect ratios.
- Reference the same image URL everywhere so it can be cached.
- To opt out of inline linking: on a request with a Google referrer, return `200` or `204`. Googlebot still
  crawls the page and shows a crawl-time thumbnail; "This behavior isn't considered image cloaking and won't
  result in manual actions."

## Video

- Discovery via `<video>`, `<embed>`, `<iframe>`, `<object>` only. No fragment identifiers, no
  user-action-gated loading, container must exist even if the media API fails.
- **Indexing gate (all four required):** the watch page must be indexed; **"The indexed watch page must be
  performing well in Search before its video can be considered for indexing"**; the video must be embedded
  on a watch page and can't be hidden behind other elements; it needs "a valid thumbnail that's available
  at a stable URL."
- "Just because the watch page is indexed doesn't mean that the video will also be indexed."
- Data URLs are unsupported.
- Thumbnail: BMP/GIF/JPEG/PNG/WebP/SVG/AVIF, **minimum 60×30 px**, fetchable by Googlebot *and*
  Googlebot-Images, stable URL. "At least 80% of the thumbnail's pixels must have an alpha (transparency)
  value greater than 250."
- A watch page is one whose main purpose is watching a single video; a blog post reviewing an embedded video
  is not.
- Feature markup: previews (cap with `max-video-preview`), key moments (`Clip`, or `SeekToAction` —
  language-limited — or YouTube description timestamps), Live Badge (`BroadcastEvent`). `nosnippet` opts out
  of key moments.
- "Google doesn't guarantee that adding markup will result in a specific video feature."

## Discover

- "Content is automatically eligible to appear in Discover if it is indexed by Google and meets Discover's
  content policies. **No special tags or structured data are required.**" Eligibility is not a guarantee.
- Image specs: **at least 1200 px wide**, **more than 300,000 total pixels**, **16:9**; enabled via
  `max-image-preview:large`.
- Filtered out: "job applications, petitions, forms, code repositories, or satirical content without any
  context", plus SafeSearch and shocking content.
- "Traffic from Discover is less predictable or dependable … consider traffic from Discover as supplemental
  to your keyword-driven search traffic."
- Reporting: Discover performance report, 16 months of data, includes Chrome traffic.

## Web Stories

- Must be valid AMP.
- Required metadata on every story: `publisher-logo-src`, `poster-portrait-src`, `title`, `publisher`.
- "All Web Stories must be canonical" — self-referencing `link rel="canonical"`.
- Poster: "at least 640x853px and use an aspect ratio of 3:4". Logo: "at least 96x96 px and aspect ratio of
  1:1".
- Desktop Search requires landscape support.
- Content policy caps: ineligible "if the majority of pages have more than 180 characters of text"; video
  "less than 60 seconds per page"; titles "shorter than 90 characters"; roughly 280 characters per page.
- Must have a narrative, must not require clicks to other sites for essential information, and must not be
  solely advertising.

## Site names, sitelinks, favicons

### Site names

- Automated, but `WebSite` structured data "is most important, if you want to specify a preference". Other
  sources: `og:site_name`, `<title>`, headings, home-page text.
- Mark up the **home page only** (domain or subdomain root). Required: `name`, `url`. Recommended:
  `alternateName` as a preference-ordered list.
- "Google Search only supports one site name per site, where a site is defined by the domain or subdomain.
  Google Search does not support site names at the subdirectory level." `www` and `m` are "generally
  considered as being equivalent".
- Duplicate home pages (HTTP/HTTPS, www/non-www) need identical structured data on every copy.
- "Site names aren't supported in the Rich Results Test" — use the Schema Markup Validator.

### Sitelinks

- "At the moment, sitelinks are automated… we may incorporate site owner input in the future." No markup.
- "We only show sitelinks for results when we think they'll be useful to the user."
- Levers: clear titles and headings, logical structure, links to important pages, concise descriptive
  anchor text.
- To remove one: "consider removing the page from your site or using `noindex`."

### Favicons

- One `<link rel="icon">` (or `shortcut icon`, `apple-touch-icon`, `apple-touch-icon-precomposed`) in the
  home page `<head>`. `href` may be relative, absolute, or off-site/CDN.
- **Square (1:1), at least 8×8 px**; "we recommend using a favicon that's larger than 48x48px". Formats:
  BMP, GIF, ICO, PNG, JPEG, PPM, TIFF. Stable URL.
- One favicon per **hostname**; subdirectories can't have their own.
- Googlebot must crawl the home page and follow redirects to the favicon; **Googlebot-Image** must fetch it.
- "A favicon isn't guaranteed to appear … even if all guidelines are met."

## Byline dates

- "A byline date is the date that Google estimates that the web page was updated or published." Not
  guaranteed to be shown.
- Requires a **user-visible** date, prominent, and labelled ("Posted Feb 4, 2019"), plus structured data —
  a `CreativeWork` subtype (`Article`, `BlogPosting`, `VideoObject`) with `datePublished` and/or
  `dateModified`.
- "The date is required; the time is not." Visible and structured dates must agree.
- "Don't specify future dates, or the date of the action described on the page" — use `Event` markup for
  events.
- If the wrong date is chosen, "consider removing some or all other dates that appear on the page."

## Featured snippets

- No opt-in: "How can I mark my page as a featured snippet? You can't."
- Two opt-outs: `nosnippet` (blocks all snippets) or a lower `max-snippet` (suppresses featured snippets only,
  probabilistically).
- "In general, the shorter your `max-snippet` rule setting, the less likely the page will appear as a featured
  snippet… If you need a guaranteed solution, use the `nosnippet` rule."
- No published minimum length — "the minimum length is variable".
- A page elevated to a featured snippet is not repeated later on the first page.

## Flexible sampling (paywalls)

- Two sanctioned models: **metering** (quota before paywall) and **lead-in** (partial article visible).
- "monthly, rather than daily metering provides more flexibility and a safer environment for testing."
- "for most daily news publishers, we expect the value to fall between **6 and 10 articles per user per
  month**"; "we encourage you to provide **10 articles per month** to Google search users and iterate".
- "general user satisfaction starts to degrade significantly when paywalls are shown more than **10% of the
  time**."
- Restricted access can "unintentionally impact article ranking in Google Search".
- Mark paywalled content with structured data to avoid being treated as cloaking, and don't ship paywalled
  content to the browser when it shouldn't be accessible.
