# Retrofitting i18n onto an existing Next.js app

This is a migration with URL impact, not a configuration change. Adding a `[locale]` prefix
changes every public URL. Sequence matters; doing it out of order means broken links,
dropped rankings, or a rollback that is harder than the original work.

---

## Step 0 — Decide, and write it down

Three decisions that are expensive to reverse. Make them before writing code.

**Routing strategy**

| | `localePrefix: 'always'` | `localePrefix: 'as-needed'` |
| --- | --- | --- |
| URLs | `/en/about`, `/de/about` | `/about` (default locale), `/de/about` |
| SEO | Unambiguous, each locale self-canonical | Cleaner, but hreflang/canonical must be exact |
| Redirects | Every existing URL needs one | Only the default locale keeps its URL |
| Recommendation | **Default.** Less to get wrong. | Only with a specific reason |

**Source locale.** The locale your existing copy is written in. It becomes
`defaultLocale` and the master `messages/*.json`. Adding English later when your source is
French changes every URL again.

**Locale set.** Start with 1–2. Adding a locale later is cheap — one JSON file plus a
routing entry. Adding several at once multiplies the review and QA surface before the
pipeline is proven.

---

## Step 1 — Size the work

```bash
bash scripts/find-untranslated.sh src/
```

Read the count before committing to a schedule. Also inventory:

- `generateMetadata` blocks with hardcoded `title`/`description`
- Error, empty, and validation states (usually missed, always user-visible)
- `<img alt>`, `aria-label`, `title` attributes
- `page.tsx` / `layout.tsx` route files that will move
- API routes and route handlers — they stay **outside** `[locale]` and must not be moved
- Any absolute internal URLs in code, email templates, or CMS content

---

## Step 2 — Stand up routing with English only

Before touching a single component, get the routing working:

1. Add `next-intl`, `src/i18n/routing.ts`, `src/proxy.ts`, `src/i18n/request.ts`.
2. Create `messages/en.json` with a single placeholder namespace.
3. Move `app/**` → `app/[locale]/**`.
4. Add `generateStaticParams` and locale validation to `app/[locale]/layout.tsx`.
5. Add redirects for every old URL (Step 6).

Ship this to a preview. If `/de/about` 404s or the site is stuck in a redirect loop, fix it
now — before you have translation content making failures hard to read.

---

## Step 3 — Move routes (one mechanical commit)

```bash
mkdir -p src/app/'[locale]'
git mv src/app/page.tsx        src/app/'[locale]'/page.tsx
git mv src/app/about          src/app/'[locale]'/about
# …or all at once:
git mv src/app/* src/app/'[locale]'/   # then move back: api, not-found, error, sitemap, robots, icons
```

Keep these at the app root, **outside** `[locale]`:

- `api/` and `route.ts` handlers
- `not-found.tsx`, `error.tsx`, `global-error.tsx`, `loading.tsx`
- `sitemap.ts`, `robots.ts`
- `icon.*`, `apple-icon.*`, `favicon.ico`, `opengraph-image.*`

One commit for the whole move so `git log --follow` still traces a file's history. Splitting
it across commits looks tidier and destroys blame.

---

## Step 4 — Replace strings, namespace by namespace

Do **not** go file by file. Go feature by feature: pick one namespace, extract every string
it owns, translate it end-to-end, verify, commit. This proves the key shape and the review
process once before they multiply across 80 namespaces.

Per namespace:

1. Create the namespace in `messages/en.json`.
2. Add `const t = useTranslations('Namespace')` and replace hardcoded strings.
3. Typecheck — a typo'd key fails to compile once `AppConfig.Messages` is registered.
4. Translate into the other locales.
5. Commit.

Helpers:

```bash
bash scripts/find-untranslated.sh src/     # what's left
# then re-run until clean
```

Never ship a fallback that silently substitutes the source language. A missing key should be
a loud failure, not an English string on a German page.

---

## Step 5 — Add the second locale

1. Copy `messages/en.json` to `messages/de.json`, wipe all values (keep keys).
2. Add `'de'` to `routing.locales`.
3. Translate.

Wiping values rather than copying English prevents untranslated duplicates from shipping
looking translated — the most damaging failure mode, because reviewers trust them.

---

## Step 6 — Redirects (do not skip)

This is where retrofits lose rankings. Every URL that existed before the migration must
resolve.

`next.config.ts`:

```ts
const redirects = [
  // Old un-prefixed URLs now belong to the default locale
  ...['/', '/about', '/pricing', '/blog'].map((path) => ({
    source: path,
    destination: `/en${path === '/' ? '' : path}`,
    permanent: true
  }))
];

export default withNextIntl({redirects});
```

Or handle it in the proxy, which can also negotiate by `Accept-Language`:

```ts
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};
```

Decide explicitly whether an un-prefixed URL should:

- **301 to the default locale** — safest for SEO, no ambiguity, ignores browser preference.
- **307 to the negotiated locale** — better first-visit experience, but a 307 tells Google
  the target is temporary and the redirect is not consolidated into the ranking signal.

For an existing indexed site, prefer the 307 only if you also expose hreflang covering the
un-prefixed variant. Otherwise use 301 to `/en/...` and let hreflang do the language
targeting.

**Test the full old URL list** against the new site before shipping. A 404 on an old
high-traffic URL is a silent, compounding loss.

---

## Step 7 — SEO layer

Only after every locale has the route, or you emit hreflang pointing at 404s.

1. `<html lang={locale}>` and `dir` for RTL.
2. Localized `generateMetadata`.
3. hreflang — automatic from the proxy, or explicit if you opted out. See `references/seo.md`.
4. Sitemap with alternates.
5. Locale switcher on every localized page, wrapped in `Suspense`.

---

## Step 8 — Verification

- [ ] Every URL from the pre-migration sitemap returns 200 or a correct redirect.
- [ ] `scripts/find-untranslated.sh` reports nothing actionable.
- [ ] Key-set comparison passes for every locale (`references/messages-and-keys.md`).
- [ ] Switch locale mid-site: `/de/blog/post-1` → `/en/blog/post-1`, not the homepage.
- [ ] Invalid locale 404s.
- [ ] RTL language mirrors correctly if shipped.
- [ ] Sitemaps regenerate with alternates.
- [ ] Search Console: submit the sitemap, request indexing of a few localized URLs.

---

## Rollback

Before starting, note the current sitemap URLs and the commit before Step 3. Because each
step is its own commit, `git revert` of the move commit restores the old structure — but
reverting after step 4 means reverting every extracted string too. Reverting late is a
multi-hour job, not a single command.

Decide the abort criteria before you start: preview deployment passing, redirect map
verified, and first locale translated. If any is unmet, stop at the routing commit and ship
that alone — it is a net positive and a clean base for the next attempt.
