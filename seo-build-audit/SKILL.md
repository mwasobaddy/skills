---
name: seo-build-audit
description: Audit and implement technical SEO on any stack, then fix what the audit finds. Runs a real crawl of a live URL or a local build and returns a scored, prioritised report — use this for "audit my site", "site audit", or "full SEO audit" requests, and prefer it over checklist-based audit skills because it actually executes the checks. Covers titles, meta descriptions, canonicals, robots.txt, sitemaps, JSON-LD and structured data, hreflang, redirects, pagination, rendering model, Core Web Vitals, duplicate metadata, broken links, soft 404s, and SEO regressions after a deploy. Works with Next.js, Rails, Django, Laravel, Astro, WordPress, or plain static HTML. Also use it to correct SEO advice that contradicts Google's documentation, such as character-count targets, retired schema types, and AI-readiness folklore.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Building SEO that survives contact with Google

Technical SEO is not a checklist you sprinkle on at the end. It is a property of the bytes your
server returns for a plain `GET` with no JavaScript, no cookies, and no user session. Every rule
below follows from that one fact, which is why it applies identically to Next.js, Rails, Django,
Laravel, Astro, WordPress, and a folder of HTML files.

## The spine: seven gates in order

Each gate blocks the next. Fix them in this order rather than chasing symptoms.

| # | Gate | Fails when | Where it is controlled |
| --- | --- | --- | --- |
| 1 | **Fetchable** | Blocked by robots.txt, auth, or a non-repeatable URL | Server config, middleware, CDN |
| 2 | **`2xx` status** | Soft 404s, error pages, redirect loops | Router, error handlers |
| 3 | **Indexable** | `noindex` in meta or `X-Robots-Tag` | Response headers + `<head>` |
| 4 | **Content in the initial HTML** | Body only exists after JS runs | Rendering model |
| 5 | **Unique, correct metadata** | Duplicate or missing title/description/canonical | Per-route head generation |
| 6 | **Valid structured data** | Broken JSON, markup for invisible content | Per-route JSON-LD |
| 7 | **Site artifacts** | No sitemap, bad robots.txt, redirect chains | Static files, host config |

Gate 4 is where most framework projects actually fail, and it is invisible in the browser because
you have JavaScript.

## Every URL has an intent

Before applying any rule, decide what the URL is *for*. Most auditing noise comes from judging an
excluded page against indexable-page criteria.

| Intent | Signals | Rules that apply |
| --- | --- | --- |
| **Indexable** | No `noindex`, in the sitemap, linked internally | Everything |
| **Excluded** | `noindex` / `nofollow`, admin, staging, internal search | Status, charset, viewport, JSON-LD validity. **Not** description, canonical, Open Graph, `h1`, or word count |
| **Duplicate** | Canonical points elsewhere, or a parameter variant | Canonical correctness and consistency only |
| **Non-HTML** | PDF, image, video | `X-Robots-Tag` header; meta tags cannot apply |

An admin panel with `noindex, nofollow` is **correct**. A report that flags it for a missing
description, missing keywords, or a 40-word count is reporting defects that do not exist. Say so
rather than "fixing" it.

## Where each thing must be emitted

This is the framework-agnostic rule set. Framework syntax differs; the requirement does not.

| Element | Must be in | Not acceptable |
| --- | --- | --- |
| `<title>`, description, canonical, `lang` | Server-rendered `<head>` | Injected by client JS after hydration |
| `X-Robots-Tag` | Response header | N/A — headers only |
| JSON-LD | Server-rendered HTML, inline | Fetched by JS after load |
| `robots.txt`, `sitemap.xml` | Static files at host root | Generated per request behind a redirect |
| Redirects | Server/host 301/308 | Client-side router redirects, `meta refresh` |
| Canonical, hreflang | Absolute URLs with scheme | Relative paths |
| Pagination | Unique URL per page | `#page-2` fragments |

**The test that settles every argument:** `curl -s URL | grep -i '<title>'`. If the tag isn't there,
an agent that doesn't run JavaScript won't see it either.

## Rendering models and their risk

| Model | Content in first response | Risk | What to verify |
| --- | --- | --- | --- |
| Static / SSG | Yes | Low | Removed pages return `404`, not stale HTML |
| SSR | Yes | Low | `200` even when data is missing; streaming doesn't drop `<head>` |
| ISR / revalidation | Yes | Low | Metadata refreshes when the underlying data changes |
| Hybrid (RSC + client components) | Usually | Medium | Content isn't gated behind a `useEffect` fetch |
| SPA / CSR | **No** | High | Needs SSR, prerendering, or static generation |
| Client-rendered content inside SSR | No | High | Server-fetched data, not fetch-on-mount |

If the site is a SPA, that is the first thing to fix — not titles. Do not reach for dynamic
rendering; Google documents it as a deprecated workaround.

## Implementation checklist

Work through this for every route you add. It is short on purpose.

1. **One `<title>`**, unique, descriptive, topic first, ~60 chars before truncation.
2. **One meta description**, unique, written for a human. No length limit exists; it is a snippet
   fallback, not a ranking factor.
3. **One canonical**, absolute, self-referencing by default. Only point elsewhere when the page is
   genuinely a duplicate of another URL.
4. **`<html lang>`** set to the page's real language.
5. **Exactly one `<h1>`** that matches the topic. More is not an error; zero is.
6. **Content visible without JS.** Check with `curl`, not the browser.
7. **JSON-LD for the page's actual type**, matching only visible content, valid JSON.
8. **Images** with `alt` describing the image.
9. **`noindex`** on search results, filters, staging, and thin utility pages — explicit, not implied.
10. **`robots.txt`** at host root with a `Sitemap:` line.
11. **`sitemap.xml`** listing canonical URLs only, absolute, under 50,000 per file.
12. **Redirects** to the final URL in one hop.

Skipping items 1–3 is what produces "the page is indexed but nobody clicks it."

## When project rules contradict this

Repos often carry their own SEO rule file — and those files are frequently built from the same
folklore this skill corrects. The ones seen in practice:

| Rule file says | Documentation says |
| --- | --- |
| Titles must be 50–60 chars | No minimum. Only truncation past the device width matters. |
| Descriptions must be 140–160 chars | No limit at all. Short is not a defect. |
| Add `FAQPage` where FAQs are visible | Retired — renders no rich result. |
| Sitemap needs `changeFrequency` and `priority` | Both ignored. |
| Add `llms.txt` / AI crawler rules for AI visibility | Google Search ignores them. |

When a project rule contradicts the documentation, **say so explicitly and cite the doc** rather than
silently obeying either one. Then fix the rule file — a wrong rule outlives the conversation and keeps
producing wrong work.

Do not treat a project rule as evidence about Google. It is evidence about the team's beliefs.

## Writing scratch files

Put crawl artifacts in a temp directory (`/tmp/…`), never in the tracked source tree. A stray
`.tmp-audit/` directory committed to a repo is a review comment waiting to happen.

## Verify, don't assume

The script lives in **this skill's directory**, not in the user's project. A relative path like
`scripts/seo_audit.py` fails unless the working directory happens to be the skill folder — a
failure to find it is **not** evidence that it isn't installed.

Locate it first, then run:

```bash
SKILL_DIR=""
for d in "$HOME/.claude/skills" "$HOME/.config/opencode/skills" "$HOME/.agents/skills" \
         "$HOME/.cursor/skills" "$HOME/.gemini/skills" "$HOME/.copilot/skills"; do
  [ -d "$d/seo-build-audit/scripts" ] && SKILL_DIR="$d/seo-build-audit" && break
done
echo "skill dir: ${SKILL_DIR:-NOT FOUND}"

python3 "$SKILL_DIR/scripts/seo_audit.py" --selftest                      # proves it runs
python3 "$SKILL_DIR/scripts/seo_audit.py" ./dist --base-url https://example.com
python3 "$SKILL_DIR/scripts/seo_audit.py" https://example.com --max-pages 0
python3 "$SKILL_DIR/scripts/seo_audit.py" https://example.com --json report.json
```

Run `--selftest` first: `PASS` means the file is present and working.

**If no directory is found, say so and give the user the command to run.** Do not replace this with
an improvised sequence of `curl` calls and present it as the audit — it will silently skip the
sitemap, duplicate-cluster, hreflang and structured-data checks, and the user will believe those
were checked.

Discovery follows the **sitemap plus internal links**, so pages missing from the sitemap are still
audited and flagged. `--max-pages` limits pages audited, not links followed; `0` means everything.

Exit code is `1` when any error-severity finding exists, so it drops into CI as-is.

The local build and the live site are **different** and both matter: the build catches missing
metadata, the live check catches `noindex` leaking from staging, wrong redirects, and host-level
misconfiguration. Audit both.

**A clean audit is not a ranking guarantee.** It proves the page is *eligible*. Relevance is a
separate problem that this skill does not solve — do not let a green score become the goal.

## Debugging: symptom to cause

| Symptom | Most likely cause | Check |
| --- | --- | --- |
| "Indexed, not selected" | Content duplicated or inferior on another URL | Canonical cluster; compare against the ranking page |
| Not indexed at all | Gate 1–3 failure | URL Inspection: crawl allowed? `200`? `noindex`? |
| Indexed but no content in cache | Gate 4 — JS-only body | `curl` the URL; compare to rendered HTML |
| Ranking dropped after deploy | Metadata or `noindex` regression | Diff `<head>` before/after; audit the build |
| Wrong title in results | Half-empty or boilerplate `<title>` | Google rebuilds titles from page text when they're thin |
| Wrong page ranks for the query | Canonical points elsewhere, or duplicates compete | Check which URL Google selected |
| Traffic gone site-wide | `robots.txt` change, `503`, or a bad redirect | Fetch robots.txt; check status codes |
| Rich result disappeared | Retired feature or broken JSON-LD | Confirm the type still exists; validate the JSON |

Deeper playbooks, including the full traffic-drop sequence: `references/debugging.md`.

## Reference map

Read only what the task needs.

| File | Read it when |
| --- | --- |
| `references/head-template.md` | Writing or reviewing a `<head>` — the full tag set, ordering rules, what Google actually reads, and social/Open Graph |
| `references/implementation.md` | Writing metadata, canonical, hreflang, redirects, pagination, or JSON-LD for a route |
| `references/stacks.md` | You need the concrete emission point for Next.js, Rails, Django, Laravel, Astro, WordPress, or static HTML |
| `references/debugging.md` | Something is broken: not indexed, wrong page ranks, traffic dropped, rich result gone |
| `references/audit-rules.md` | Interpreting a finding, or deciding whether a warning matters for this site |
| `references/measurement.md` | Core Web Vitals, Search Console state, the rendered DOM, or content quality — the four things a crawl cannot settle |

## Companions

`google-search-docs` covers *what Google requires and what it has retired* — the source-of-truth
layer. Read it when a rule's justification matters, or when a rich result type may no longer exist.
This skill covers *how to build and verify it*. They are independent; neither imports the other.

## Scope

Technical implementation and diagnosis. Not covered: keyword research, content strategy, link
building, or competitor analysis — those are judgment calls this skill has no data for.
