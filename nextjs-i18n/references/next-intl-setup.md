# Canonical next-intl setup (Next.js 16.3+)

Every file, in dependency order. Adapt paths to your `@/*` alias.

---

## 0. Install

```bash
npm i next-intl
```

`next.config.ts` — the plugin wires message loading for the bundler:

```ts
import type {NextConfig} from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin();

export default withNextIntl({});
```

---

## 1. `src/i18n/routing.ts`

Single source of truth for which languages exist. Everything else imports from here.

```ts
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'de', 'ja'],
  defaultLocale: 'en'

  // Optional — the two strategies that affect URLs:
  // localePrefix: 'always'      -> /en/about, /de/about  (default)
  // localePrefix: 'as-needed'  -> /about (en), /de/about
  // localePrefix: 'never'       -> language by cookie only (weak for SEO)
  // domains: [...]              -> fr.example.com style host-based routing
});
```

---

## 2. `src/proxy.ts`

Locale detection and redirect. On Next.js 16 this file replaces `middleware.ts`.
`proxy` runs on **Node.js only** — Edge is not supported.

```ts
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // Skip API routes, internals, and anything with a file extension
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};
```

The matcher must exclude `api`, `_next`, `_vercel`, and dot-containing paths. A missing
exclusion here causes redirect loops on static assets and 500s on API routes.

---

## 3. `src/i18n/request.ts`

Resolves the active locale and loads its messages. This is the single place locale is
determined, for Server Components and Server Actions.

**Next.js 16.3+** — read the root param directly:

```ts
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import * as rootParams from 'next/root-params';
import {notFound} from 'next/navigation';
import {routing} from './routing';

export default getRequestConfig(async ({locale}) => {
  // An explicit locale argument wins (used by Server Actions)
  if (!locale) {
    const requested = await rootParams.locale();

    if (hasLocale(routing.locales, requested)) {
      locale = requested;
    } else {
      notFound();
    }
  }

  return {
    locale,
    // Pin the server timezone or dates drift between server and client
    timeZone: 'UTC',
    messages: (await import(`../../messages/${locale}.json`)).default
  };
});
```

**Next.js < 16.3** — the legacy shape, still supported:

```ts
export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default
  };
});
```

Add global formats here so presets are defined once:

```ts
export const formats = {
  dateTime: {
    short: {day: 'numeric', month: 'short', year: 'numeric'}
  },
  number: {
    precise: {maximumFractionDigits: 5}
  },
  list: {
    enumeration: {style: 'long', type: 'conjunction'}
  },
  displayName: {
    region: {type: 'region'}
  }
} as const;
```

---

## 4. `src/i18n/navigation.ts`

Locale-aware replacements for the Next.js navigation APIs. Import these instead of
`next/link` and `next/navigation` in localized code.

```ts
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
```

Usage:

```tsx
import {Link} from '@/i18n/navigation';

// On /en/about, renders href="/de/about"
<Link href="/about">About</Link>

// Search params via the query prop, not a string
<Link href={{pathname: '/users', query: {sortBy: 'name'}}}>Users</Link>

// Language switch — also sets hreflang on the anchor
<Link href="/" locale="de">Deutsch</Link>
```

---

## 5. `src/app/[locale]/layout.tsx`

The locale lives here for the whole tree. Validate it, and generate the static params.

```tsx
import type {ReactNode} from 'react';
import {notFound} from 'next/navigation';
import {hasLocale, NextIntlClientProvider} from 'next-intl';
import {getMessages, getTranslations} from 'next-intl/server';
import {routing} from '@/i18n/routing';

type Props = {
  children: ReactNode;
  params: Promise<{locale: string}>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

export async function generateMetadata({params}: Omit<Props, 'children'>) {
  const {locale} = await params;
  const t = await getTranslations({locale, namespace: 'Metadata'});

  return {
    title: t('title'),
    description: t('description')
    // alternates: see references/seo.md
  };
}

export default async function LocaleLayout({children, params}: Props) {
  const {locale} = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} dir={locale === 'ar' || locale === 'he' ? 'rtl' : 'ltr'}>
      <body>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

`generateStaticParams` is **required** on Next 16.3 as well — root params make static
rendering possible, they do not opt you in automatically.

`NextIntlClientProvider` is only needed if client components call `useTranslations`,
`useFormatter`, or `useLocale`. Without any of those, omit it and skip the message fetch.

---

## 6. `src/app/[locale]/page.tsx`

```tsx
import {useTranslations} from 'next-intl';

export default function HomePage() {
  const t = useTranslations('HomePage');

  return (
    <>
      <h1>{t('heroTitle', {username: 'Ada'})}</h1>
      <p>{t('heroSubtitle')}</p>
    </>
  );
}
```

No `params`, no `setRequestLocale` on 16.3+. If you maintain a Next < 16.3 project, the
page needs `setRequestLocale(locale)` before any hook call.

---

## 7. Root-level routes

`not-found.tsx` and `error.tsx` sit outside `[locale]`, so no locale param exists there.
Reading `await locale()` returns undefined — fall back explicitly:

```tsx
import {locale} from 'next/root-params';

export default async function NotFound() {
  const current = (await locale()) ?? 'en';
  // render current-language copy
}
```

Forcing `notFound()` from inside `getRequestConfig` covers unknown locale segments. The
root `not-found.tsx` is a separate concern — it handles missing *content*.

---

## 8. Types

Make the source locale the type source of truth so a missing key is a compile error:

```ts
// global.ts
import {formats} from '@/i18n/request';
import en from './messages/en.json';
import {routing} from '@/i18n/routing';

declare module 'next-intl' {
  interface AppConfig {
    Messages: typeof en;
    Formats: typeof formats;
    Locale: (typeof routing.locales)[number];
  }
}
```

Requires `compilerOptions.paths` to map your alias, and the file included in `tsconfig.json`.
Keep it a `.ts` module and import it once from `next.config.ts` or a layout so it is not
tree-shaken before the compiler reads it.

---

## Versions

Developed against **next-intl v4.14** and **Next.js 16.3+**. On Next < 16.3 use the legacy
`setRequestLocale` path. On Next < 15 `params` is a plain object, not a Promise — remove the
`await`.
