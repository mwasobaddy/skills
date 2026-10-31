# Debugging playbooks

Each playbook follows the same shape: confirm the symptom, isolate the cause, fix, verify. Start at
the top of the seven-gate spine and don't skip gates — a metadata fix on an unindexable page is
wasted work.

Useful primitives throughout:

```bash
curl -sS https://example.com/page | head -60                    # what the crawler receives
curl -sS -o /dev/null -w '%{http_code}\n' https://example.com/x  # status only
curl -sS -o /dev/null -w '%{num_redirects} %{url_effective}\n' https://example.com/old
curl -sS https://example.com/robots.txt                          # crawl rules
```

---

## 1. Page is not indexed

**Confirm:** Search Console → URL Inspection → "URL is not on Google". Read the reason it gives.

**Isolate, in order:**

1. **Blocked?** `robots.txt` allows the path? URL Inspection shows "Crawled: blocked by robots.txt".
2. **Status?** Must be `2xx`. A `302` to a login, a `503`, or a soft `200` error page all block it.
3. **`noindex`?** Check the meta tag **and** the response header. `curl -I` for `X-Robots-Tag`.
4. **Canonicalised away?** URL Inspection's "Google-selected canonical" may differ from yours. That
   is a duplicate-clustering decision, not a bug in the tag.
5. **Content present without JS?** Compare `curl` output to the rendered HTML in URL Inspection.
   If the body only exists after hydration, this is the cause.
6. **Discovered?** Is it in the sitemap, and linked from an indexed page? Orphan pages get found
   slowly or never.
7. **Too new?** Newly created URLs can take days to weeks. There is no way to force it.

**Fix:** whatever the earliest failing gate is. Then request a recrawl via URL Inspection.

**Verify:** the inspection result changes to "URL is on Google". Recheck after a few days; `noindex`
can take weeks to clear if Google crawled the page long ago.

---

## 2. "Indexed, not selected" / indexed but never ranks

**Confirm:** URL Inspection reports "URL is on Google" but the page doesn't appear for its own
target query.

**This is not an indexing bug — the page is eligible and losing on relevance.** Do not chase
technical fixes.

**Isolate:**

- Does a *different* URL from your site rank for the query? → cannibalization. Consolidate.
- Does the page appear for a more specific query? → it ranks, just not where you expect.
- Is the page thin relative to the results that do rank? → content problem.
- Does `site:example.com/exact-page` return it? → confirms indexation, nothing more.

**Fix:** merge or differentiate competing pages, improve the page's coverage of the query intent, or
repoint internal links. This is the one playbook where the answer is editorial.

---

## 3. Wrong URL appears in results

**Confirm:** you expect `/products/widget` and Google shows `/products/widget?ref=home` or the
`www` variant.

**Isolate:** URL Inspection on both URLs → compare "Google-selected canonical". If Google picked a
different URL than your tag, your signals conflict or the tag isn't seen.

**Causes:**

- Canonical only set in JS, so the initial HTML has none.
- Contradictory signals: canonical says A, sitemap says B, internal links say C.
- A tracking parameter URL is linked internally and has more inbound links.
- `rel=canonical` combined with `media`, `hreflang`, or `lang` on the same tag — ignored entirely.

**Fix:** one canonical, absolute, in the initial HTML; sitemap lists the same URL; internal links
point at it. Consistency matters more than tag strength.

**Note:** duplicates can stay clustered for up to two weeks after a fix.

---

## 4. Empty or wrong content in the cached snapshot

**Confirm:** the indexed page shows a shell, spinner, or "enable JavaScript" text.

**Isolate:** `curl -sS URL | grep -c '<your main heading>'`. Zero means the body is client-rendered.

**Causes, in order of likelihood:**

1. Data fetched in `useEffect` / `componentDidMount`.
2. Content behind an interaction (tab, accordion, "load more") that isn't in the DOM at all.
3. Content lazy-loaded only when scrolled into view, including above the fold.
4. A client-only router path that renders nothing on first paint.

**Fix:** server-fetch the content, or statically generate it. Dynamic rendering is a documented
deprecated workaround — don't reach for it.

---

## 5. Traffic dropped

**Confirm first that it's real:** widen the date range to 16 months. Yearly seasonality looks
identical to a penalty.

**Isolate by blast radius:**

| Pattern | Likely cause |
| --- | --- |
| Whole site, sudden | robots.txt, `noindex` deploy, `503`, DNS/TLS, redirect loop |
| Whole site, gradual | Core update, or a spam/manual action |
| One section | Template change, canonical regression, section-wide `noindex` |
| One page | Lost relevance, canonicalised into another page |
| Impressions flat, clicks down | Title/snippet appeal, not ranking |

**Check in order:**

1. `curl -sS https://site/robots.txt` — unchanged? Not `Disallow: /`?
2. `curl -sS -o /dev/null -w '%{http_code}' https://site/` — `200`?
3. `curl -sS https://site/page | grep -i 'noindex'` — empty?
4. Search Console: Manual Actions, Security Issues, Page indexing, Crawl stats.
5. Search Console: compare periods, then split by search type, country, device, page.
6. If nothing is flagged and it aligns with a rollout date, it is likely a core update. Wait at
   least a full week after the rollout completes before judging.

**Fix:** depends entirely on which row above matched. For a core update there is no fix list —
assess the site as a whole, and don't make quick speculative changes.

---

## 6. Rich result disappeared

**Confirm:** the result lost its stars, breadcrumb, or carousel.

**Isolate:**

1. **Does the type still exist?** Several were retired (`FAQPage`, `HowTo`, `SitelinksSearchBox`,
   and others). If the doc page now redirects to the docs-updates page, the feature is gone and no
   markup will bring it back.
2. **Is the JSON still valid?** One syntax error discards the entire block. Validate the rendered
   HTML, not the template.
3. **Is the page still indexable?** A `noindex` elsewhere removes eligibility.
4. **Does the markup match visible content?** Marking up content that isn't on the page loses
   eligibility and can trigger a structured-data manual action.
5. **Did required properties change?** Google adds and removes them.

**Fix:** correct or remove the markup. Never add more markup hoping it compensates — an ineligible
type stays ineligible.

---

## 7. Soft 404s

**Symptom:** Crawl stats or the Page indexing report shows "Soft 404", or thousands of junk URLs
are indexed.

**Confirm:** `curl -sS -o /dev/null -w '%{http_code}' https://site/definitely-missing` returns `200`.

**Causes:**

- SPA fallback serves `index.html` with `200` for every unknown path.
- A "not found" template rendered without `status: 404`.
- Redirecting unknown URLs to the home page.
- Empty search results pages returning `200`.

**Fix:** return a real `404`. For a SPA, the host must serve `404` for unmatched paths while still
routing known client routes. Then remove the junk URLs from the index.

---

## 8. Redirect problems

**Confirm:** `curl -sS -o /dev/null -w '%{num_redirects} %{url_effective}\n' https://site/old`.

- `0` hops → not a redirect at all; the page returns `200` with old content.
- `> 1` hop → chain. Collapse it.
- Points at the wrong host/scheme → mixed canonical signals.

**Fix:** one hop to the final destination, absolute, `301`/`308`. Update internal links to point
directly at the target so crawlers never traverse the hop.

---

## 9. Sitemap not being used

**Confirm:** Search Console → Sitemaps shows the file as read, or errors.

**Isolate:**

- Is it at the host root, absolute URLs, UTF-8, under 50 MB?
- Does it list only canonical `200` URLs? Redirects and `noindex` URLs in a sitemap are noise and
  erode trust in the file.
- Does robots.txt reference it with a `Sitemap:` line?
- Index file: are children in the same directory or below?

**Fix:** regenerate from the canonical URL list. A sitemap is a hint, not a control — it never
guarantees crawling.

---

## 10. Ranking dropped immediately after a deploy

Treat this as a regression, and diff it.

```bash
# before deploy, snapshot the head of your top pages
for u in / /products /pricing; do curl -sS "https://site$u" | sed -n '1,80p' > "before$(echo $u|tr / _).html"; done
# after deploy, diff
diff before_.html after_.html
```

**Look for:** a new `noindex`, a changed canonical, a title template that broke, a robots.txt
change, a redirect added to a previously `200` URL, or a `<head>` element reordered after an invalid
element (Google ignores everything after an invalid `<head>` child).

**Fix and verify:** audit the live site, not just the build. The build can pass while the edge adds
a header.

---

## 11. Keyword cannibalization

**Symptom:** several pages alternate for the same query, and none performs well.

**Confirm:** Search Console → Performance → filter by query → look at which URLs received
impressions.

**Fix:** pick the strongest URL as the target, merge the others into it with a `301`, and repoint
internal links. Do not leave near-identical pages competing with different titles — differentiation
must be real, not cosmetic.

---

## When to stop

If all seven gates pass, the page is **eligible** and this skill has done its job. Ranking is a
relevance judgment made from signals this skill cannot inspect. Saying "the page is eligible and
the rest is a relevance question" is a correct and useful answer — inventing a technical cause is
not.
