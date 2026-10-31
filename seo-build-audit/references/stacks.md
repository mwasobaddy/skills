# Emitting SEO per stack

Each section answers one question: **where does this stack emit the `<head>`, the status code, and
the redirect?** That is the only thing that differs between frameworks.

If your framework isn't listed, find the equivalent of "server-rendered head template" and "route
handler that can set a status code". The rules in `implementation.md` are unchanged.

---

## Next.js — App Router

Metadata is exported from the route segment; it is rendered server-side.

```ts
// app/products/[slug]/page.tsx
import type { Metadata } from "next";

export async function generateMetadata({ params }): Promise<Metadata> {
  const p = await getProduct(params.slug);
  return {
    title: `${p.name} | Acme`,
    description: p.summary,
    alternates: { canonical: `https://acme.com/products/${p.slug}` },
    openGraph: { images: [p.image] },
  };
}
```

- Set `metadataBase` once in the root layout, otherwise canonical/OG URLs render relative.
- `export const metadata` for static values; `generateMetadata` when they depend on data.
- Not-found content must call `notFound()` so the response is a real `404`.
- Redirects in `next.config` (host-level) or `redirect()` in server code. Never `router.push()` for
  SEO redirects — that is a client navigation with a `200`.
- `robots.ts` and `sitemap.ts` generate the root artifacts at build time.
- Watch: a client component that fetches content in `useEffect` produces an empty initial HTML body.

## Next.js — Pages Router

- `<Head>` from `next/head` inside the page component, or `_document.tsx` for site-wide tags.
- `getStaticProps` / `getServerSideProps` for data, so the HTML arrives populated.
- `next.config.js` → `redirects()` for permanent moves.

## Rails

- `content_for :head` in the layout, populated by `content_for` blocks in views.
- `render status: :not_found` for real 404s — do not render a 200 template.
- `redirect_to` with `status: :moved_permanently` (301) or `:permanent_redirect` (308).
- Route slugs with a database-backed permalink, not `/:id`.
- Gems like `meta-tags` help, but a plain `content_for` is enough and easier to audit.

## Django

- Base template `<head>` with blocks; each view template overrides `{% block title %}` etc.
- Context processor for site-wide canonical host.
- `HttpResponseGone` / `HttpResponseNotFound` for removals.
- `RedirectView(permanent=True)` or `redirect()` with `permanent=True`.
- `django.contrib.sitemaps` and a plain `robots.txt` view or static file at the root.
- `APPEND_SLASH` decides whether `/page` redirects to `/page/` — pick one and be consistent.

## Laravel

- `@yield('head')` in the layout; `@section('head')` per view.
- `abort(404)` for missing content — it sets the status correctly.
- `Route::redirect('/old', '/new', 301)` or `Redirect::route(...)->withStatus(301)`.
- Inertia/Vue/React: the initial HTML only contains what the controller passes as props. Don't fetch
  the primary content in a component mount hook.
- Blade-heavy sites: put canonical and Open Graph in the layout, not in partials that may not render.

## Astro

- Frontmatter exports on the page/layout, rendered at build time:

```astro
---
const { title, description, canonical } = Astro.props;
---
<html lang="en">
  <head>
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonical} />
  </head>
```

- Content is static by default — the lowest-risk model. Verify that any `client:only` island isn't
  the source of primary content.
- `astro-sitemap` (or a manual `sitemap.xml` route) and a static `robots.txt` in `public/`.

## WordPress

- Most sites delegate to a plugin (Yoast, Rank Math, SEOPress). Verify what it emits rather than
  adding a second source — duplicate canonical tags from a theme plus a plugin is the classic bug.
- **Disable indexing of** `/search`, author archives (unless real), tag archives (usually), and
  attachment pages.
- Check `wp_head()` is present in `header.php`; a stripped theme loses all plugin metadata.
- Pagination: WordPress emits `?paged=` URLs — keep them indexable or canonical deliberately.
- Static `robots.txt` in the web root overrides the virtual one WordPress serves.

## Express / Node / any SSR

```js
app.get("/products/:slug", async (req, res) => {
  const p = await db.product(req.params.slug);
  if (!p) return res.status(404).render("404");
  res.render("product", { product: p });
});
app.get("/old", (req, res) => res.redirect(301, "/new"));
```

- `res.redirect(301, ...)` not `res.redirect(...)` (defaults to 302).
- Set `X-Robots-Tag` on the response for gated content.
- Render `<head>` from the server template, never from a client hydration step.

## Static HTML / JAMstack

- Lowest risk model: the file *is* the response.
- Redirects live in host config (`_redirects` on Netlify, `vercel.json`, `amplify.yml`, S3 routing
  rules), not in client JS.
- Generate `sitemap.xml` at build time from the same page list that generates the pages, so they
  cannot drift.
- Watch for a SPA fallback that serves `index.html` with `200` for unknown paths — that is a
  site-wide soft 404.

---

## The cross-stack check

Regardless of framework, these two commands tell you the truth:

```bash
curl -sS https://example.com/page | grep -iE '<title>|canonical|robots' | head
curl -sS -o /dev/null -w '%{http_code}\n' https://example.com/missing-page   # expect 404
```

If the first shows nothing useful, the content is client-rendered. If the second returns `200`, the
site has a soft-404 problem that no amount of metadata will fix.
