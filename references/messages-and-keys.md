# Messages, keys, and formatting

---

## Structure

Namespace by feature, not by page file. One namespace per route or per shared component
group. Never one flat keyspace.

```json
{
  "Navigation": {
    "home": "Home",
    "about": "About us",
    "contact": "Contact"
  },
  "HomePage": {
    "heroTitle": "Welcome back, {username}!",
    "heroSubtitle": "Manage your dashboard effectively."
  },
  "Errors": {
    "serverError": "Something went wrong. Please try again later.",
    "notFound": "The page you are looking for does not exist."
  }
}
```

Why namespaces: flat keys collide the moment two features want `title`; namespaced keys make
`grep '"contact"' messages/en.json` return exactly the strings for one feature, and let a
translator be handed one namespace instead of a 900-line file.

Naming rules:

- `camelCase` keys. Match the component or feature: `HomePage.heroTitle`.
- Name the string by its **role**, not its English text. `submitButton` survives a
  reword; `clickHere` becomes a lie the moment marketing changes the copy.
- Keep punctuation inside the message, including the trailing period and the space before a
  colon in French — target languages have their own conventions and you cannot fix them by
  concatenating.
- Do not include a placeholder's *name* in the value: `"{count} items"` is fine,
  `"{count} number of items in your cart"` is redundant for translators.

---

## ICU message syntax

Never concatenate. Word order, gender, and number agreement change per language.

### Plurals

```json
{
  "Cart": {
    "itemsCount": "{count, plural, =0 {Your cart is empty} =1 {You have 1 item} other {You have {count} items}}"
  }
}
```

`=0`, `=1` are exact matches. `other` is the required fallback. Languages with more plural
forms (Polish: `one`, `few`, `many`; Russian, Arabic) add them inside the same message:

```json
{
  "itemsCount": "{count, plural, one {# plik} few {# pliki} many {# plików} other {# pliku}}"
}
```

Getting this wrong is not cosmetic — a Polish user seeing "1 plików" (wrong: should be
"1 plik") reads it as broken.

### Select (gender, tense, formality)

```json
{
  "Profile": {
    "invite": "{gender, select, male {He invited you} female {She invited you} other {They invited you}}"
  }
}
```

### Rich text

```json
{
  "Terms": {
    "body": "By continuing you accept our <link>terms of service</link>."
  }
}
```

```tsx
const t = useTranslations('Terms');

t.rich('body', {
  link: (chunks) => <a href="/terms">{chunks}</a>
});
```

Only use `rich` when the **translated** string must contain markup. Adding markup for
styling is a component concern — style it with CSS, not with tags in the message.

### Escaping

A literal `{` or `}` in a message needs quoting: `"{'{'}"`. This bites with JSON payloads,
CSS-in-class-names, and template-literal examples inside help text.

---

## Placeholders

Always named, never positional, never concatenated outside the message:

```tsx
// Wrong
t('greeting') + ' ' + name
`${t('greeting')} ${name}`

// Right
{ t('greeting', {name}) }
```

Named placeholders let the translator reorder freely: `{name} 님, 환영합니다` is grammatical;
`{0} 님` is not.

For values that are themselves sentences, use `select` or restructure the message so the
variable stays a noun.

---

## Formatting dates, numbers, and lists

`Intl` output is locale-dependent. Formatting by **runtime** locale instead of **requested**
locale shows a German user US formatting on a page they explicitly requested in German.

### Client components

```tsx
'use client';
import {useFormatter} from 'next-intl';

function Price() {
  const format = useFormatter();
  return <span>{format.number(1234.5, 'precise')}</span>;
}
```

### Server components

```tsx
import {getFormatter} from 'next-intl/server';

export default async function Price() {
  const format = await getFormatter();
  return <span>{format.number(1234.5, 'precise')}</span>;
}
```

Define presets once in `getRequestConfig` and reference them by name (`'short'`,
`'precise'`, `'enumeration'`, `'region'`) rather than passing raw `Intl` options at call
sites — see `references/next-intl-setup.md` §3.

### Currency

Do not hand-roll: `"$" + amount` ignores locale symbol position, separators, and the fact
that some locales put the symbol after the number. Use a currency format preset and pass the
currency **code**:

```json
{
  "number": {
    "EUR": {style: 'currency', currency: 'EUR'}
  }
}
```

```tsx
format.amount(1234.5, 'EUR')
```

### Lists

```tsx
format.list(['HTML', 'CSS', 'JS'], 'enumeration');
```

Produces "HTML, CSS, and JS" in English and the correct localized conjunction elsewhere.
Hand-rolled `items.join(', ')` always gets the "and" wrong.

### Dates, relative times, and hydration

`new Date()` evaluated on the server and in the browser produces different strings whenever
the timezone or clock differs — the classic "Text content does not match server-rendered
HTML" error.

Three options, in order of preference:

1. **Pin `timeZone`** in `getRequestConfig` and format absolute dates. Server and client then
   agree by construction.
2. **Pass a fixed `now`.** For deterministic tests and SSG output, set `now` from a build
   timestamp rather than `Date.now()`.
3. **Render relative time client-only** when it must be live ("2 hours ago"). Accept the
   server rendering an absolute date and swap after mount, or suppress the warning
   deliberately — do not leave it unhandled and hope.

---

## Keeping locales in sync

A missing key is the most common i18n bug. Three defenses, use all three:

1. **TypeScript.** With `AppConfig.Messages = typeof en`, `t('typo')` fails to compile.
2. **Structural test.** Compare key sets, not values — languages legitimately differ in
   which plural forms they need.

```ts
function keyPaths(obj: unknown, prefix = ''): string[] {
  if (typeof obj !== 'object' || obj === null) return [prefix];
  return Object.entries(obj).flatMap(([k, v]) =>
    keyPaths(v, prefix ? `${prefix}.${k}` : k)
  );
}

const enKeys = keyPaths(en).sort();
for (const locale of routing.locales.filter((l) => l !== routing.defaultLocale)) {
  const missing = enKeys.filter((k) => !keyPaths(messages[locale]).includes(k));
  const extra = keyPaths(messages[locale]).filter((k) => !enKeys.includes(k));
  if (missing.length || extra.length) {
    throw new Error(`${locale}: missing ${missing.join(', ') || '-'}; extra ${extra.join(', ') || '-'}`);
  }
}
```

3. **Build-time check.** Run the comparison in CI. A missing key that ships is a blank
   button on a live page.

Do not "fix" a missing key by falling back at runtime in production — a silent fallback
hides the gap from users while shipping English to a German page. Fail the build instead.

---

## Translation workflow

- Machine translation is a **draft**, not a source. Never commit unreviewed output as the
  canonical text for a locale; the errors become permanent and unattributable.
- Keep the source locale's string stable across versions. Every edit to `en.json`
  invalidates every translation for that key.
- Record context. A bare key `"cta"` is untranslatable; `"cta.buyNow"` on a pricing table
  column is.
- Pseudo-localization (`en-XA` with expanded strings) catches layout that breaks when text
  grows 30–50% — German routinely does this to buttons that fit in English.
