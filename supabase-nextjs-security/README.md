# supabase-nextjs-security

A security posture for **Next.js + Supabase**, built around the thing that actually decides who reads
a row: Postgres Row Level Security. Not a generic hardening checklist, and deliberately not a
restatement of Supabase's docs.

The publishable key is in the browser by design. That means the client is not the boundary, and no
amount of client-side care substitutes for a policy. Most Supabase incidents are a table that was
created and never secured.

## The problem it solves

Ask an agent to "add Supabase auth and save this to the database" and you get a working app where every
new table is world-readable with the publishable key, the service-role key sits in a `NEXT_PUBLIC_`
variable, and the SSR client drops the cache headers that stop a CDN serving one session to another.
Nothing errors. It works in dev, with one user.

This skill turns that into an ordered procedure: RLS first, then key discipline, then storage, then
auth settings, then server code — and it says how to verify each, because "it works when I'm logged in"
is not a test.

## What it does

- **RLS as the model** — default deny, a policy per operation, `with check` on update (the bug that
  lets a user move a row into another tenant), and the `pg_tables` query that finds every unprotected
  table in one line.
- **Multi-tenant scoping** — membership checks through a `security definer` function, the recursion it
  exists to break, and the `revoke execute` that keeps it from being a membership oracle.
- **Key discipline** — publishable vs secret, the `server-only` guard, and the detail most people miss:
  the secret key bypasses RLS *only when no user token is attached*.
- **Storage** — bucket visibility and path-scoped `storage.objects` policies, which table policies do
  not cover.
- **Auth settings you can actually change** — leaked-password protection, enumeration, rate limits,
  the per-account backoff hook, and re-authentication before destructive actions.
- **SSR correctness** — `getUser()` over `getSession()`, the cookie refresh, and the cache-header rule
  that silently leaks sessions when skipped.
- **Myth correction** — Argon2id, pepper, hand-rolled CSRF tokens and HttpOnly-only sessions are not
  available in this stack, with the reason and the equivalent control for each.

## When to use it

Adding Supabase Auth or the first table; writing or reviewing RLS; wiring `@supabase/ssr`; anything
touching the service-role key; multi-tenant scoping; investigating "the API returns other people's
data"; or when someone hands you a hardening checklist written for an app that stores its own
credentials.

## What it does not do

No CSP, no dependency auditing, no security-headers checklist, no penetration testing. It covers the
Supabase boundary: who can read a row, and how the session that decides that reaches the server intact.

## Files

- `SKILL.md` — the five rules, the order of work, and how to verify
- `references/rls.md` — policies, `with check`, multi-tenant functions, views, storage, SQL testing
- `references/auth-config.md` — bcrypt reality, password settings, rate limits, reauth, MFA
- `references/ssr-nextjs.md` — `@supabase/ssr` clients, proxy/middleware, Server Actions, cache headers
- `references/leaks-and-myths.md` — what actually leaks, and verdicts on advice that does not apply

## Install

```bash
npx skills add mwasobaddy/skills --skill supabase-nextjs-security
```

## Scope

Targets Supabase's hosted platform, `@supabase/ssr`, and the Next.js App Router (Next 15/16 — the
proxy file is `middleware.ts` before 16 and `proxy.ts` after). Self-hosted Supabase and Pages Router
differ in places that are called out where they matter.

## License

MIT
