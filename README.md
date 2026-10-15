# nextjs-i18n

Structural guidance for putting a Next.js App Router app into multiple languages — folder
layout, locale routing, typed message files, ICU plurals, and localized SEO.

## What it does

- **Library selection** — next-intl (default) vs Lingui vs next-i18next, with the tradeoffs
  that actually decide it, and when *not* to migrate.
- **Canonical architecture** — the folder tree that keeps locale machinery in one place and
  dictionaries out of the source tree.
- **Setup from scratch** — every file, in dependency order, copy-paste ready.
- **Retrofitting an existing app** — a sequenced migration that treats the URL change as the
  real risk, including the redirects you cannot skip.
- **Localized SEO** — `<html lang>`, hreflang, canonical vs hreflang, sitemap alternates,
  locale switcher rules.
- **Gotchas** — the ones that cost hours, including a Next.js 16.3 change that makes the most
  widely copied setup pattern obsolete.

## When to use it

When adding or fixing multiple languages on a Next.js app, wiring a `[locale]` segment with
a proxy or middleware, structuring `messages/*.json`, debugging a hydration mismatch from
dates, or deciding whether the built-in Next.js `i18n` config applies (it does not, on the
App Router).

## Key detail worth knowing up front

On **Next.js 16.3+**, `next/root-params` lets Server Components read the `[locale]` param
directly, which makes `setRequestLocale` **legacy**. Most tutorials, blog posts, and model
training data still teach `setRequestLocale(params.locale)`. It still works, but it is the
old API, and this skill documents the current one while keeping the legacy path for older
projects.

## Install

```bash
# Symlink into place on this machine
../../scripts/install.sh nextjs-i18n

# Or clone directly
git clone <repo-url> ~/.claude/skills/nextjs-i18n
```

Requires `bash` and the usual POSIX tools. `scripts/find-untranslated.sh` needs nothing
extra.

## Contents

- `SKILL.md` — library choice, canonical architecture, gotchas, retrofit checklist
- `references/library-comparison.md` — choosing and migrating between i18n libraries
- `references/next-intl-setup.md` — every file in the canonical setup
- `references/messages-and-keys.md` — namespaces, ICU, formatting, keeping locales in sync
- `references/seo.md` — hreflang, canonical, sitemap, locale switcher, verification
- `references/migration.md` — the retrofit sequence, redirects, rollback
- `scripts/find-untranslated.sh` — size a retrofit before starting
- `evals/trigger-queries.json` + `scripts/run-trigger-eval.sh` — measure whether this skill
  fires on the right prompts

## Script usage

```bash
bash scripts/find-untranslated.sh src/          # report candidates
bash scripts/find-untranslated.sh --json src/   # machine-readable
```

Exits non-zero while candidates remain, so it drops into CI or a pre-commit hook. Heuristic,
not a compiler — it errs toward recall and expects a human pass.

### Trigger eval

```bash
bash scripts/run-trigger-eval.sh --dry-run                 # plan only, no API calls
bash scripts/run-trigger-eval.sh --split train            # 12 queries x 3 runs
bash scripts/run-trigger-eval.sh --split validation --out report.json
```

Requires `jq` and the agent CLI under test (`claude` by default, or `--client opencode`).
Any other client works via `--detector-cmd`, which receives raw agent output on stdin and
exits 0 when the skill was consulted.

Run it whenever you change the `description`. The query set is split 60/40 into a fixed
train/validation pair — optimize on train, then check validation for overfitting.

## Versions

Written against **next-intl v4.14** and **Next.js 16.3+**. Notes the legacy path for
Next < 16.3 and Next < 15.

## License

MIT
