# Library comparison

Pick one. Do not mix two in a single app.

---

## Decision table

| | **next-intl** | **@lingui/react** | **next-i18next** |
| --- | --- | --- | --- |
| App Router (RSC) | Native, first-class | Native since v4.10 | Native since v16 |
| Build step | **None** | SWC or Babel macro plugin | None |
| Message storage | Plain JSON, typed | Compiled catalogs | JSON or backend |
| Extraction | Manual keys | Automatic at compile time | Manual keys or CLI |
| Runtime size | Moderate | ~2 kB gzipped | Largest of the three |
| Per-locale instance | Not needed | Required (one per locale) | Required |
| Client bundle | Messages only | Compiled catalogs | Resources + instance |
| Built-in ICU | Yes | Yes | Yes (via i18next-icu) |
| Formatting API | `useFormatter` | Via i18n | Via i18n |
| Pages Router | Supported | Supported | Supported |
| Next 16 `proxy.ts` | Yes | Yes | Yes (`createProxy`) |

---

## next-intl — the default

Choose it when starting new App Router work with no i18n legacy.

Why it wins on adoption: zero configuration beyond four small files, messages stay as
readable JSON checked into the repo (diffable, reviewable, editable by non-developers), and
TypeScript reads the source locale directly. No plugin to pin against the host bundler's
SWC version.

Cost: no automatic extraction, so a renamed key is caught only by TypeScript — which is
exactly why `AppConfig.Messages` augmentation matters.

---

## @lingui/react — when compile-time extraction earns its keep

Choose it when:

- You want keys auto-extracted at build time, so dead keys never reach the catalog.
- The runtime budget is tight and ~2 kB matters.
- The same catalog must be shared across React, Vue, Astro, React Native, or Node.

Cost that bites hardest in Next.js: the macro plugin must be **pinned to an exact version**
compatible with the Next.js version's bundled SWC. A caret range resolves to a plugin built
against a newer `swc_core` than the host accepts, and the failure surfaces at build time,
not install time. If no plugin major fits your Next version, upgrade Next or use the Babel
path.

Server-side shape differs from next-intl materially:

```ts
// src/initLingui.ts — one instance per locale, stored in React cache
import {setI18n} from '@lingui/react/server';
import {getI18nInstance} from './appRouterI18n';
import {locale} from 'next/root-params';

export async function initLingui() {
  const i18n = getI18nInstance((await locale()) as string);
  setI18n(i18n);
  return i18n;
}
```

Two traps specific to Lingui here:

- **Never use a global `@lingui/core` i18n singleton on the server.** Two concurrent
  requests for different locales race over `activate()`, and users see each other's language.
  One instance per locale, created once at module scope.
- **Call `initLingui(locale)` in every layout *and* every page that renders translations.**
  Next renders segments independently; on client-side navigation only the page re-renders, so
  a page relying on its layout's call breaks on soft navigation.
- `generateMetadata` runs outside component rendering, so it takes the instance explicitly
  rather than relying on the request cache.

---

## next-i18next — when the team already speaks i18next

Choose it when you are migrating an existing i18next codebase, or the team already knows
`useTranslation`/`initReactI18next` and the ecosystem (locize, locize-editor) matters.

`next-i18next` v16 is a thin Next-specific layer over i18next: `getT()` in Server
Components, `useT()` in client components, `createProxy()` for detection and routing. The
App Router `Trans` component needs the no-context variant with both `t` and `i18n` passed
explicitly:

```tsx
import {Trans} from 'react-i18next/TransWithoutContext';
import {getT} from 'next-i18next/server';

export default async function Page() {
  const {t, i18n} = await getT();
  return <Trans t={t} i18n={i18n} i18nKey="welcome">Welcome</Trans>;
}
```

Cost: more wiring (config file, server init, provider), a heavier client bundle, and an
instance per request. Backend loaders are the one thing it does that the others do not.

---

## Next.js built-in `i18n` config

```js
module_modules.config.js
module.exports = {
  i18n: {locales: ['en', 'fr'], defaultLocale: 'en'}
};
```

**Pages Router only.** The App Router ignores it entirely — App Router locale routing is a
`[locale]` dynamic segment plus a proxy. If a plan proposes this config for an App Router
app, it will appear to work (the app builds and runs) while serving English to every URL.

Limits if you are on Pages Router: 100 locales, 100 locale-domain entries.

---

## Migration triggers

| Signal | Move to |
| --- | --- |
| Starting new App Router work | next-intl |
| Existing i18next install | next-i18next (stay, don't churn) |
| Cross-framework catalog sharing | Lingui |
| Bundle budget is the binding constraint | Lingui |
| Need CMS/remote translation backend | next-i18next |
| Need `localePrefix: 'as-needed'` + domain routing | any — all three support it |

Do not migrate libraries mid-project for tidiness. The cost is a full catalog conversion
plus a routing rewrite, and the benefit is cosmetic.
