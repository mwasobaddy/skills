# google-search-docs

Answers SEO and Search questions from Google's own documentation, and corrects the advice that
survives in blogs long after Google retires the feature.

## What it does

- **A correction table** — 29 claims that are repeated constantly and are wrong or stale, each
  with the doc's own wording: `FAQPage` markup, 155-character meta descriptions, `rel=canonical`
  as a directive, "duplicate content penalty", `llms.txt`, E-E-A-T as a ranking factor, and more.
- **Decision procedures** — why a page isn't indexed, which removal method fits which intent, how
  to triage a traffic drop, and which structured data to add.
- **Hard numbers** — robots.txt 500 KiB, sitemaps 50 MB / 50,000 URLs, 10 redirect hops, LCP 2.5 s
  / INP 200 ms / CLS 0.1, and the rest.
- **Structured data that actually exists** — the live feature inventory with each page's required
  properties, plus the twelve types Google has retired.
- **hreflang done properly** — the reciprocity rule, `x-default`, and the three codes that are
  silently ignored.
- **A refresh path** — a resumable crawler that reports what changed since the references were
  written.

## When to use it

When the question is "what does Google actually say", not "what do people claim". Ranking,
indexing, crawling, robots.txt, canonicalization, sitemaps, JavaScript rendering, structured data,
rich results, Core Web Vitals, spam policies, hreflang, site moves, traffic drops, AI
Overviews/AEO/GEO, or whether a specific SEO tactic is still supported.

## Why it exists

The SEO advice most likely to be repeated confidently is the advice most likely to be out of date.
FAQ rich results, `HowTo` markup, sitelinks search box, `rel=next`/`prev`, dynamic rendering, signed
exchanges, and the `noarchive` directive have all been retired — some as recently as July 2026 —
while still appearing in current-looking guides and in model training data.

This skill's job is to make the agent check rather than recall.

## Install

```bash
# From GitHub
npx skills add mwasobaddy/skills --skill google-search-docs

# Symlink into place on this machine, for live editing
../scripts/install.sh google-search-docs
```

## Contents

- `SKILL.md` — the correction table, hard numbers, decision procedures, reference map
- `references/essentials.md` — technical requirements and every spam policy, exhaustively
- `references/crawling-indexing.md` — robots.txt, robots meta, canonicalization, sitemaps, JS, redirects, removals
- `references/appearance.md` — title links, snippets, ranking systems, Core Web Vitals, AI features, images/video, Discover, paywalls
- `references/structured-data.md` — general guidelines, live feature inventory, required properties
- `references/monitoring.md` — traffic-drop triage, Search Console reports, search operators, hacked-site recovery
- `references/specialty.md` — international/hreflang, ecommerce structure and pagination, explicit content
- `references/deprecated.md` — retired features, systems, directives, crawlers, and doc URL moves
- `scripts/crawl-google-docs.py` — resumable crawler with change detection

## Script usage

```bash
python3 scripts/crawl-google-docs.py --out /tmp/gdocs            # full crawl (~5 min)
python3 scripts/crawl-google-docs.py --out /tmp/gdocs --diff     # what changed since last run
python3 scripts/crawl-google-docs.py --out /tmp/gdocs --seed URL --max-hops 0   # one page
```

Needs `python3` and `curl`. HTML is cached in `<out>/html/`, so re-runs only refetch what failed.
Pages that Google has retired are flagged automatically — they redirect to
`developers.google.com/search/updates`, which is the signal this skill uses to keep
`references/deprecated.md` honest.

Output is `<out>/pages/*.txt` (clean article text) plus `<out>/manifest.json` with per-page hashes.

## Scope

`developers.google.com/search/docs` and the `crawling/docs` pages it links to — 277 URLs, of which
262 are live and 191 are distinct documents after de-duplicating aliases. The other 15 are retired
features that redirect to the docs-updates page. Not covered: Search Console's UI in depth, Ads,
Merchant Center policy, or the Search Quality Rater Guidelines beyond how the docs reference them.

## Attribution

Distilled from [Google Search Central](https://developers.google.com/search/docs) documentation,
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Quotations remain Google's.
Google is not affiliated with and does not endorse this skill.

## License

MIT for the skill's own text and code.
