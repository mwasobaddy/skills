# Monitoring and debugging

Source: `search/docs/monitor-debug/**`, plus the Search Console pages they reference.

## Traffic-drop triage

### Step 1 — Rule out seasonality and demand

Change the date range to **Last 16 months**. "This will help you analyze the traffic drop in context and
make sure it's not a drop that happens every year due to a festivity or a trend." Beyond 16 months, pull
data via the Search Analytics API or bulk exports.

If traffic fell but impressions held, the cause is title/snippet appeal, not ranking — check title links
and snippets (see `appearance.md`). If both fell, continue.

### Step 2 — Compare against a matching period

Use the Compare tab: "Compare last 3 months to previous period" or "year over year". Then click every
dimension tab — queries, URLs, countries, devices, search appearance — to find what actually changed.

### Step 3 — Split by search type

Use the Search type filter for Web, Images, Video, and News separately. A drop confined to one type has a
different cause than a whole-site drop.

### Step 4 — Check the reports for a signal

| Suspected cause | Where to look |
| --- | --- |
| Technical (crawl, index, serving errors) | Page indexing report, Crawl stats report |
| Manual action / spam | Manual Actions report; re-read the spam policies |
| Security (malware, phishing) | Security Issues report — interstitials suppress traffic |
| Data or logging error | Search Console Data Anomalies page |
| Site move / migration | Site move troubleshooting; see `crawling-indexing.md` |
| Demand shift | Google Trends, per query |

Technical issues can be site-wide (the site is down) or page-level (a misplaced `noindex`, which produces a
slower decline because it depends on Google re-crawling the page).

### Step 5 — Classify the position change

- **Small drop** (e.g. position 2 → 4): "a noticeable drop in traffic without a big change in
  impressions." "Small fluctuations in position can happen at any time (including moving back up in
  position, without you needing to do anything)." The doc's advice: "we recommend avoiding making radical
  changes if your page is already performing well."
- **Large drop** (e.g. top 10 → position 29 across a wide range of terms): "self-assess your whole website
  overall (not just individual pages) to make sure it's helpful, reliable and people-first."

### Step 6 — If it's a core update

Confirm the rollout finished, then "wait at least a full week after a core update completes" and compare
that week to the week before rollout. "some changes can take effect in a few days, while others could take
several months." "there's no guarantee that changes you make to your website will result in noticeable
impact in search results."

### Step 7 — Find the affected pages

In the Pages table, select **Clicks Difference** to rank pages by traffic lost. That separates
- a site-wide issue → check the Page indexing report;
- a group of pages → find the shared pattern;
- one important page → inspect that URL directly.

### Step 8 — Check industry context

Compare the dropped queries in Google Trends to see whether interest fell web-wide (changing interests) or
only for your site (seasonality is also a factor — diets in January, turkeys in November).

## Search Console reports

| Report | Question it answers |
| --- | --- |
| Performance | Which queries, pages, countries, devices, and search types produced clicks and impressions |
| Page indexing | Which URLs are indexed, excluded, or errored, and why |
| Crawl stats | How much Googlebot fetched, response codes, file types, purpose |
| Manual actions | Whether a human reviewer applied a penalty, and of what kind |
| Security issues | Malware, phishing, or other threats Google detected |
| Core Web Vitals | Field performance against LCP/INP/CLS thresholds |
| Generative AI performance | Visibility inside AI features |
| Data anomalies | Whether the data itself was affected by a processing error |

URL Inspection is the authority for a single URL: it shows the crawled vs rendered HTML, the canonical
Google selected, indexing status, and lets you request a recrawl.

## Search operators

Documented operators for debugging: `site:`, `filetype:`, `imagesize:` (Images only), `src:` (Images only).

The limitation matters more than the operators:

> "Because search operators are bound by indexing and retrieval limits, the URL Inspection tool in Search
> Console is more reliable for debugging purposes."

Consequences to state plainly:

- `site:` returning fewer results than expected is **not** proof of a penalty or deindexing. Use URL
  Inspection.
- `site:https://www.example.com` "doesn't return the same results as" `site:https://example.com/` — the
  operator follows URLs, prefixes, and domains differently.
- Presence in `site:` results is not guaranteed even for indexed URLs.

## Security and abuse

Three documented threat categories, each with its own report and recovery path:

**Malware / unwanted software** — harmful executables, or software that changes browser settings or leaks
data without disclosure. Site owners sometimes host malware unknowingly through user uploads.

**Social engineering (phishing and deceptive sites)** — impersonation that tricks users into disclosing
credentials or paying the wrong party.

**Hacked site** — content injected without permission: code injection, page injection, content injection
(hidden links/text, cloaking), and conditional redirects (varying by referrer, user agent, or device) —
the last is what makes hacks hard for owners to spot.

### Recovery order

1. Identify and remove the injected content or malicious code.
2. Fix the vulnerability that allowed it — otherwise reinfection is immediate.
3. Verify the fix.
4. Request a review in Search Console.
5. Recheck the Security Issues report.

**Safe Browsing Repeat Offenders Policy:** "Sites that repeatedly switch between compliant and noncompliant
behavior within a short window of time will be classified as Repeat Offenders." Owners are notified by
email, cannot request additional reviews via Search Console while flagged, and the status "persists for 30
days" before review is available again.

## Preventing user-generated spam

"Even simple deterrents such as an unusual challenge users have to complete before interacting with your
property may discourage spammers."

Documented measures:

- **Publish an abuse policy** and communicate it at signup; let trusted users report spam.
- **Build a reputation signal** from signup and interaction patterns: form completion time, requests per IP
  range, user agents, submitted values.
- **`noindex` posts from new users** until they gain reputation — "This will greatly demotivate spammers
  from interacting with your platform."
- **`nofollow` or `ugc`** on all links in untrusted content.
- **Only index content meant for Search.** Pages created for direct sharing, collaboration, or utility
  should get `noindex` or be blocked in robots.txt.

## Measurement caveats

- Client-side analytics under-report Googlebot: WRS "may not fetch such resources" and "Client-side
  analytics may not provide a full or accurate representation of Googlebot and WRS activity." Use Crawl
  stats.
- Ranking is query- and user-dependent (location, language, device), so a rank tracker's number is one
  sample, not a position.
- No third-party tool "has access to our internal ranking or AI systems." Any claim otherwise is false.
