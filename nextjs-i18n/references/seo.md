# Localized SEO

Adding a locale prefix changes every URL on the site. Search engines treat the un-prefixed
page and each locale as **separate pages**, so the wrong setup here costs rankings, not
just polish.

---

## 1. `<html lang>`

The single highest-value attribute. Screen readers use it to pick a voice, and search
engines use it to target a locale.

```tsx
<html lang={locale} dir={locale === 'ar' || locale === 'he' ? 'he' : 'ltr'}>
```

`dir="rtl"` for RTL languages (`ar`, `he`, `fa`, `ur`) — otherwise the whole layout mirrors
wrong. Prefer Next's built-in dir inference by setting `dir` on `<html>` from the locale.

Keep `<html>` inside `app/[locale]/layout.tsx`. There must be exactly one root layout, and
it is the localized one. Do not add a second root layout outside `[locale]` to serve
`not-found.tsx` — that produces two `<html>` tags.

---

## 2. Localized metadata

`generateMetadata` runs for every locale. Translate title and description per locale —
a page whose `<title>` is English on `/de/` ranks poorly and looks broken.

```tsx
// src/app/[locale]/layout.tsx
export async function generateMetadata({params}: Omit<Props, 'children'>) {
  const {locale} = await params;
  const t = await getTranslations({locale, namespace: 'Metadata'});

  return {
    title: t('title'),
    description: t('description')
  };
}
```

Page-level metadata overrides layout metadata; use the same pattern per route with that
route's namespace.

---

## 3. hreflang

### Automatic

next-intl's proxy sets the `Link` header with `hreflang` alternates and an `x-default`
entry pointing at the negotiating redirect, based on your routing config. This covers most
projects. It reflects `locales`, `localePrefix`, `domains`, and `basePath` automatically.

### When you must set it yourself

- Some pages exist in only certain locales.
- Pathnames come from a CMS or locale-dependent slugs (`/news/[articleSlug]`), so the
  proxy cannot know the mapping.
- You use `localePrefix: 'as-needed'` and want explicit prefixed URLs.

Opt out of the automatic behavior, then supply your own:

```ts
// src/i18n/routing.ts
export const routing = defineRouting({
  locales: ['en', 'de', 'ja'],
  defaultLocale: 'en',
  alternateLinks: false
});
```

```tsx
import {getPathname} from '@/i18n/navigation';

export async function generateMetadata({params}) {
  const {locale} = await params;

  return {
    alternates: {
      canonical: `https://acme.com${(await getPathname({locale, href: '/'})).replace(/^\/(en)(?=\/|$)/, '')}`,
      languages: {
        en: 'https://acme.com',
        de: 'https://acme.com/de',
        ja: 'https://acme.com/ja',
        'x-default': 'https://acme.com'
      }
    }
  };
}
```

Rules:

- **Reciprocal.** Every page must list every other language version, and each must list the
  original. One-directional hreflang is ignored.
- **Absolute URLs**, including protocol and domain. Relative hreflang is dropped.
- **`x-default`** points at the negotiating redirect or the default locale — not a
  translated page.
- **Self-reference required.** Each page must include its own URL in the list.

---

## 4. Canonical vs hreflang — do not confuse them

They solve opposite problems:

| | Tells | Use |
| --- | --- | --- |
| `canonical` | Which URL is the *authoritative* one | Duplicate content |
| `hreflang` | Which page is *this language's* version | Regional targeting |

With `localePrefix: 'always'`, each locale is its own canonical page. With
`localePrefix: 'as-needed'`, `/about` (en) and `/de/about` must both be self-canonical —
**not** both canonical to `/about`, or the German page drops out of the index.

A common self-inflicted bug: canonical pointing at the default locale while hreflang lists
the localized versions. That tells Google to index the English page and ignore the
translations entirely.

---

## 5. Sitemap alternates

Default sitemaps list only the default-locale URLs. Add alternates or the other locales are
discovered only via hreflang.

```tsx
// src/app/sitemap.ts
import type {MetadataRoute} from 'next';
import {getPathname} from '@/i18n/navigation';
import {routing} from '@/i18n/routing';

const host = 'https://acme.com';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticHrefs = ['/', '/about', '/pricing'];

  return Promise.all(
    staticHrefs.map(async (href) => {
      const languages = Object.fromEntries(
        await Promise.all(
          routing.locales.map(async (locale) => [
            locale,
            host + (await getPathname({locale, href}))
          ])
        )
      );

      return {
        url: host + (await getPathname({locale: routing.defaultLocale, href})),
        lastModified: new Date(),
        alternates: {languages}
      };
    })
  );
}
```

Sitemap files live at the **app root**, outside `[locale]` — one sitemap, not one per
locale.

---

## 6. Locale switcher

Build it from the localized `Link`, which sets `hreflang` on the anchor:

```tsx
'use client';
import {useLocale, useTranslations} from 'next-intl';
import {useParams, useSearchParams} from 'next/navigation';
import {Link} from '@/i18n/navigation';
import {routing} from '@/i18n/routing';

export function LocaleSwitcher() {
  const activeLocale = useLocale();
  const t = useTranslations('Navigation');
  const params = useParams();
  const searchParams = useSearchParams();

  return (
    <nav aria-label={t('languageSelector')} className="flex gap-2">
      {routing.locales.map((locale) => (
        <Link
          key={locale}
          href={{pathname: '/', params}}
          locale={locale}
          className={locale === activeLocale ? 'font-bold' : ''}
        >
          {t('languages', {locale})}
        </Link>
      ))}
    </nav>
  );
}
```

`useSearchParams` in a client component requires a `<Suspense>` boundary, or the whole route
opts out of static rendering. Wrap the switcher.

Keep the switcher on **every** localized page. A selector reachable only from the homepage
means most visitors never change language and search engines see a monolingual experience.

---

## 7. Open Graph and social

Translated pages sharing one OG image and one `og:title` look broken in a feed. Generate
locale-specific OG images with the image convention, which receives params:

```tsx
// src/app/[locale]/opengraph-image.tsx
export default async function Image({params}: {params: Promise<{locale: string}>}) {
  const {locale} = await params;
  const t = await getTranslations({locale, namespace: 'Metadata'});

  return new Response(/* render with t('ogTitle') */);
}
```

Always set `og:locale` and `og:locale:alternate` per locale, and point `og:url` at that
locale's canonical URL.

---

## 8. Post-launch verification

Check these before declaring the migration done:

- [ ] `/de/about` renders German copy, with `<html lang="de">`.
- [ ] `/xx/about` returns 404, not English at a fake URL.
- [ ] Every page's `Link` header lists all locales **and** itself.
- [ ] Canonical on `/de/about` is `/de/about`, not `/about`.
- [ ] Old URLs 301/307 to the right locale — this is the biggest ranking risk in a retrofit.
- [ ] Sitemap contains alternates.
- [ ] Switching locale preserves the current path, not the homepage.
- [ ] Google Search Console shows no "Alternate page with proper canonical" conflicts after
      crawling.
