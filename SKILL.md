---
name: nextjs-i18n
description: Architect and implement internationalization for Next.js App Router apps — folder structure, locale-prefixed routing, typed message files, ICU plurals, and localized SEO with hreflang. Use when adding or fixing multiple languages or translations on a Next.js site or app, choosing between next-intl, Lingui and next-i18next, wiring a [locale] segment with proxy or middleware, or migrating an English-only app to localized URLs. Triggers on i18n, localization, multi-language, translations, locale routing, lang attribute, hreflang, next-intl.
license: MIT
metadata:
  author: hiikey7
  version: "1.0"
---

# Next.js i18n

Structural guidance for putting a Next.js app into multiple languages: what the folder
layout must be, what breaks when it's wrong, and what to avoid.

## Pick the library first

Default to **next-intl** for anything new on the App Router. It needs no build plugin, no
macro step, and no per-locale instance juggling; messages are plain JSON typed off your
source locale.

| Library | Reach for it when | Cost |
| --- | --- | --- |
| **next-intl** *(default)* | New App Router work, any team size | None — plain JSON, no codegen |
| **@lingui/react** | You want compile-time extraction and a tiny runtime, or one i18n layer across React/Vue/Astro | SWC or Babel macro plugin, pinned exactly |
| **next-i18next** | The team already knows i18next, or you migrate Pages Router code | Per-request instance, `getT`/`useT` split |
| **Next.js built-in `i18n`** | **Pages Router only.** Never App Router | Not applicable |

Next.js's `i18n: { locales, defaultLocale }` config is **Pages Router only**. In the App
Router it does nothing — locale routing there means a `[locale]` segment plus a proxy.
Do not let the agent "enable" built-in i18n for an App Router project.

Full comparison, including bundle cost and per-library tradeoffs:
`references/library-comparison.md`.

## Canonical architecture

Keep static dictionaries **outside `src/`** so bundling and import paths stay obvious, and
keep all locale machinery in one folder.

```
messages/                      # pure static dictionaries — keep out of /src
├── en.json                     # source of truth; every other locale mirrors it
├── de.json
└── ja.json
src/
├── i18n/
│   ├── routing.ts              # defineRouting: locales + defaultLocale
│   ├── request.ts              # getRequestConfig: resolve locale, load messages
│   └── navigation.ts           # createNavigation: locale-aware Link/redirect
├── proxy.ts                    # locale detection + redirect (Next 16; was middleware.ts)
└── app/
    ├── [locale]/               # wraps the entire localized app
    │   ├── layout.tsx          # validate locale, <html lang>, generateStaticParams
    │   └── page.tsx
    └── not-found.tsx           # global 404 lives OUTSIDE [locale]
```

Rules that make this shape work:

- **`[locale]` is a root dynamic segment.** Everything localized lives under it. Root-level
  routes (`not-found.tsx`, `error.tsx`, `api/`) stay outside and must not call i18n hooks
  unconditionally, or they crash at runtime.
- **One source locale.** `messages/en.json` is the master. Every other file must mirror its
  shape exactly.
- **All locale knowledge in `src/i18n/`.** Components import `Link` from
  `@/i18n/navigation`, never from `next/link`. One place to add a language.

## Setup (greenfield)

Run in this order. The order matters — `proxy.ts` depends on `routing.ts`, and the layout
depends on `request.ts`.

1. Install `next-intl`, wrap `next.config.ts` with `createNextIntlPlugin()`.
2. Create `src/i18n/routing.ts` with `defineRouting`.
3. Create `src/proxy.ts` exporting `createMiddleware(routing)` plus the default matcher.
4. Create `src/i18n/request.ts` with `getRequestConfig` resolving the locale.
5. Move `app/**` under `app/[locale]/**`; add `generateStaticParams` and validate the param.
6. Create `src/i18n/navigation.ts` with `createNavigation(routing)`.
7. Create `messages/en.json` and replace hardcoded strings with `useTranslations`.
8. Set `<html lang>` and add localized metadata + hreflang.

Exact file contents for every step: `references/next-intl-setup.md`.

## Gotchas

Read this section before writing any i18n code. These are the failures that cost hours.

- **`setRequestLocale` is legacy.** On Next.js 16.3+, read the locale with
  `next/root-params` inside `getRequestConfig` instead. Most guides, tutorials, and LLM
  training data still teach `setRequestLocale(params.locale)`. It still works and is
  documented as backwards-compatible — but it is the old API. Use it only on Next < 16.3.
  `generateStaticParams` is still required either way.
- **`params` is a Promise on Next 15+.** `const {locale} = await params`. Treat
  `params.locale` as a type error, not a runtime one.
- **Validate the locale or unknown values render.** Use `hasLocale(routing.locales, locale)`
  and `notFound()`. Without it, `/xx/about` renders your English page at a fake URL.
- **`proxy.ts`, not `middleware.ts`, on Next 16.** `middleware.ts` is deprecated. The proxy
  runs on **Node.js only — the Edge runtime is not supported**. Lingui and next-i18next
  advertise Edge-safe proxies; if you need Edge, you have a real trade-off, not a free win.
- **Never concatenate translated strings.** `"You have " + count + " items"` is ungrammatical
  in Japanese and Arabic. Use ICU: `"{count, plural, =1 {One item} other {# items}}"`.
- **Never interpolate with `+` or template literals inside a message.** Use named
  placeholders — `{name}` — so word order can move.
- **Dates and numbers cause hydration mismatches.** `new Date()` on the server and in the
  browser differ by timezone and clock. Set `timeZone` in `getRequestConfig`, or render
  client-only for relative times. Symptom: "Text content does not match server-rendered HTML".
- **Formatting is locale-dependent.** `toLocaleString()` without an explicit locale formats
  by *runtime* locale, not the *requested* locale. Use `useFormatter()` / `getFormatter()`.
- **`getRequestConfig` runs per request and is cached by React.** Do not put request-varying
  state (cart, user prefs) in there. Only locale-varying config.
- **Server Actions and Route Handlers have no root params.** `await locale()` works in
  Server Components only. Pass the locale explicitly as an argument in actions and handlers.

## Retrofitting an existing app

Treat this as a migration with URL impact, not a config change. Every existing URL changes
shape when you add a `[locale]` prefix.

Plan in this order:

1. **Inventory strings** — run `scripts/find-untranslated.sh` to find hardcoded JSX text.
2. **Choose the routing strategy before coding.** Locale-prefix-always (`/en/about`,
   `/de/about`) is the default; it is unambiguous and hreflang-clean. `localePrefix: 'as-needed'`
   serves the default locale at the bare path — better URLs, weaker SEO signal. Decide now;
   switching later is a full re-migration.
3. **Stand up routing before touching any component.** Get `proxy.ts` + `[locale]` working
   with English-only messages.
4. **Move routes under `[locale]/`** — this is a large mechanical `git mv`. Do it in one
   commit so `git log --follow` stays useful.
5. **Replace strings** namespace by namespace, not file by file. Translate one namespace
   end-to-end so the key shape is proven before it multiplies.
6. **Add redirects for every URL that changed.** `/about` → `/en/about` (or 307 to detected
   locale). Without this you drop all existing rankings. Non-negotiable.
7. **Add hreflang + localized metadata only after** every locale has the route, or you emit
   alternates pointing at 404s.

Full migration sequence with the redirect and rollback notes: `references/migration.md`.

## What to avoid

- **Don't put `messages/` inside `src/`.** Server-only dicts in the source tree blur what
  ships to the client.
- **Don't import `Link` from `next/link`** in localized routes. It drops the locale prefix
  and silently links to the wrong language.
- **Don't hand-write locale prefixes in hrefs** (`href={`/${locale}/about`}`). Use
  `Link` from `@/i18n/navigation`, which handles prefixed, as-needed, and domain routing.
- **Don't use one flat key namespace.** Group by feature/page. Flat keys collide and are
  unsearchable.
- **Don't auto-translate at build time as the source of truth.** Machine output is a draft;
  committing it unreviewed makes errors permanent and untraceable.
- **Don't add a locale to `routing.locales` and call it done.** Without a translated
  `messages/xx.json`, every page renders keys or falls back silently.
- **Don't mix routing strategies.** `as-needed` plus a `hreflang` pointing at prefixed URLs
  is a self-inflicted SEO bug.

## References

Read these on demand, not upfront:

- `references/library-comparison.md` — choosing between next-intl, Lingui, next-i18next;
  bundle cost, migration triggers, per-library setup shape.
- `references/next-intl-setup.md` — every file in the canonical setup, copy-paste ready.
- `references/messages-and-keys.md` — namespace structure, key naming, ICU syntax,
  date/number/list formatting, typed messages.
- `references/seo.md` — hreflang, `<html lang>`, localized `generateMetadata`, canonical,
  sitemap alternates, locale-switcher SEO rules.
- `references/migration.md` — retrofitting an existing app, redirects, rollback.

## Scripts

- `scripts/find-untranslated.sh` — flags likely-hardcoded user-facing strings in a project so
  you can size the work before starting. Run it as step 1 of a retrofit.
- `scripts/run-trigger-eval.sh` — measures whether this skill's `description` fires on the
  right prompts. Use it when changing the description.

### Testing the description

The `description` is the only thing the agent sees before deciding to load this skill. If it
fails to fire, nothing below matters.

```bash
bash scripts/run-trigger-eval.sh --dry-run          # show the plan, no API calls
bash scripts/run-trigger-eval.sh --split train     # 12 queries x 3 runs
bash scripts/run-trigger-eval.sh --split validation --out report.json
```

Query set: `evals/trigger-queries.json` — 12 should-trigger, 8 should-not-trigger, split
60/40 into a fixed train and validation set.

When editing the description:

- Fix failures using the **train** set only. Touch the validation set once at the end to check
  the change generalizes — if train improves and validation drops, you overfit.
- Should-trigger failures mean the description is too narrow: add the *concept* the query
  represents, never the query's keywords.
- Should-not-trigger failures mean it is too broad: say what the skill does not cover.
- Re-run before editing. Triggering is nondeterministic, and one run proves nothing.

Do not add keywords from a failing query — that is how descriptions end up looking like a
keyword list and stop matching real prompts.
