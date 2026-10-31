# seo-build-audit

Implement technical SEO on any stack, then prove it with a crawl audit that works on a local build
or a live URL.

## What it does

- **The seven gates** — fetchable → `2xx` → indexable → content in the initial HTML → unique
  metadata → valid structured data → site artifacts. Fix them in that order instead of chasing
  symptoms.
- **Where each thing must be emitted** — the framework-agnostic table that settles most arguments:
  `<head>` tags in the server response, `X-Robots-Tag` in headers, redirects at the server, never
  from client JS.
- **Stack notes** — the concrete emission point for Next.js (App and Pages), Rails, Django, Laravel,
  Astro, WordPress, Express, and static hosts.
- **A real auditor** — crawls a URL or a build directory and reports ranked findings with fixes,
  plus JSON output and a non-zero exit code for CI.
- **Page intent** — indexable vs excluded vs duplicate vs non-HTML, so an admin panel with `noindex` is recognised as correct instead of flagged
- **Debugging playbooks** — not indexed, indexed but not ranking, wrong URL ranking, empty cached
  snapshot, traffic drop, lost rich result, soft 404s, redirect chains, sitemap not used,
  post-deploy regression, cannibalization.

## When to use it

While building: "where does the canonical go", "what should the title template be", "should this
be noindex", "does my SPA render content Google can see", "how do I paginate this".

While debugging: "why isn't this page indexed", "why did traffic drop after deploy", "why does the
wrong URL rank", "where did my rich result go".

## Why a separate skill from `google-search-docs`

They answer different questions and should not be merged:

| Skill | Question |
| --- | --- |
| `google-search-docs` | *What does Google require, and what has it retired?* |
| **`seo-build-audit`** | *How do I build and verify it on my stack?* |

This skill is self-contained — it does not import the other's files, so either installs alone.

## Install

```bash
npx skills add mwasobaddy/skills --skill seo-build-audit

# live editing
../scripts/install.sh seo-build-audit
```

## Audit

> Run these from this skill's directory — that is where `scripts/` lives. If you are
> elsewhere, substitute the resolved path shown in `SKILL.md`.

```bash
# local build, before deploy
python3 scripts/seo_audit.py ./dist --base-url https://example.com

# live site, after deploy
python3 scripts/seo_audit.py https://example.com --max-pages 50

# add Core Web Vitals (needs an API key; the anonymous quota is shared)
python3 scripts/seo_audit.py https://example.com --psi --psi-key "$PSI_API_KEY"

# machine-readable, for CI
python3 scripts/seo_audit.py https://example.com --json report.json

# prove the checks work
python3 scripts/seo_audit.py --selftest
```

Requires `python3` and `curl`. Directory mode uses no network at all.

**What it crawls.** Discovery is the union of the sitemap and internal links: every
`sitemap.xml` URL, plus every internal link found on the pages it fetches, followed breadth-first.
That second half matters — pages missing from the sitemap still get audited, and they are reported
as `page-not-in-sitemap`. Link-following costs no extra requests because the HTML is already
cached from the audit fetch.

`--max-pages` caps *pages actually audited* (default 25). Aliases and redirects don't consume the
budget, so the cap means what it says. Use `--max-pages 0` to audit everything discovered.

Checks status codes, `noindex` (meta and header), titles, descriptions, canonicals, `h1` and `lang`,
charset, viewport, Open Graph and Twitter tags, favicons, JSON-LD validity, hreflang reciprocity,
image alt text, robots.txt, and the sitemap. Duplicate titles and descriptions are detected across
the crawled set, and pages that are deliberately `noindex` are classified as excluded rather than
nagged for metadata they don't need.

Beyond metadata it also catches:

- **soft 404s** — probes a nonexistent path and fails if the site answers `200`
- **broken internal links** — verifies up to `--max-link-checks` targets
- **near-duplicate pages** — ≥80% shared 5-word shingles
- **JS-only shells** — under 50 words served alongside external scripts
- **retired schema types** — `FAQPage`, `HowTo`, and ten others Google no longer renders
- **missing required properties** for the structured data type you used
- **canonical URLs that don't resolve**
- **`og:image`** reachability and dimensions (PNG, GIF, JPEG, WebP)
- **invalid hreflang subtags** — including the `UK`/`EU`/`UN` trap

Exit code is `1` when an error exists, `0` otherwise, so it works directly in CI.

**A clean audit means the page is eligible, not that it will rank.** Core Web Vitals need `--psi`;
Search Console state and content quality cannot be automated at all — see
`references/measurement.md` for those, and don't let a green score imply otherwise.

## Contents

- `SKILL.md` — the seven gates, emission rules, checklist, symptom table
- `references/implementation.md` — per-concern implementation with code
- `references/stacks.md` — where each framework emits head/status/redirect
- `references/debugging.md` — 11 symptom-driven playbooks
- `references/head-template.md` — the complete `<head>`, ordering rules, and who consumes each tag
- `references/audit-rules.md` — all 59 rules, severity, and when to ignore each
- `references/measurement.md` — Core Web Vitals, Search Console, rendered DOM, content quality
- `scripts/seo_audit.py` — the auditor, with `--selftest`
- `evals/trigger-queries.json` — trigger evaluation set

## Testing

`--selftest` builds a deliberately broken page and a clean one in a temp directory, then asserts
the expected rules fire and that the clean page produces no errors. It is the check that the checker
can fail — without it, a passing audit is indistinguishable from a broken one.

Verified against: a local multi-page fixture (duplicate titles, unreciprocated hreflang, missing
artifacts), `example.com`, and `www.iana.org` (sitemap-driven, 5 pages).

## Scope

Technical implementation and diagnosis. Not covered: keyword research, content strategy, link
building, or competitor analysis.

## License

MIT
