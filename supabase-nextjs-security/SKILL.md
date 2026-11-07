---
name: supabase-nextjs-security
description: Harden Next.js + Supabase apps against the failures that actually leak data — tables without RLS, a service-role key that reached the client, permissive storage buckets, SSR session cookies cached by a CDN, and auth settings left at defaults. Use when adding Supabase Auth, writing or reviewing RLS policies, wiring @supabase/ssr, handling the publishable vs secret key boundary, building multi-tenant scoping, or investigating "everyone can read this table" — even if the user never says security. Also use to reject advice that does not apply to Supabase, such as configuring Argon2id or a pepper.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Supabase + Next.js security

The security boundary in a Supabase app is **Postgres, not the client**. The publishable key ships to
the browser by design, so the only thing standing between a signed-out visitor and your rows is Row
Level Security. A table in the `public` schema with RLS disabled is readable by anyone who views source.

That single fact explains most real Supabase incidents. They are almost never a broken hash function;
they are a table that was created and never secured.

## When to use this

- Setting up Supabase Auth, or a signed-up user's first row (a profile, a workspace).
- Writing, reviewing, or debugging RLS policies.
- Anything involving the service-role/secret key.
- Wiring `@supabase/ssr` in App Router, Route Handlers, Server Actions, or a proxy/middleware.
- Multi-tenant scoping — organizations, teams, workspaces.
- Someone reports "the API returns other people's data".
- Someone proposes Argon2id, a pepper, or hand-rolled CSRF tokens. See
  `references/leaks-and-myths.md` before agreeing.

## The five rules

### 1. Every exposed table has RLS and explicit policies

```sql
alter table public.notes enable row level security;
```

RLS enabled with **no** policy is deny-all — the correct default. Add one policy per operation you
actually need, not one policy to rule them all.

```sql
create policy "owner reads own notes"
  on public.notes for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy "owner writes own notes"
  on public.notes for insert
  to authenticated
  with check ((select auth.uid()) = user_id);
```

`using` filters which rows a statement can see or touch; `with check` validates the row being written.
**An update policy without `with check` lets a user move a row to another tenant** — the classic RLS
bug. See `references/rls.md`.

Audit in one query:

```sql
select schemaname, tablename
from pg_tables
where schemaname = 'public' and not rowsecurity;
```

Anything in the result is world-readable with the publishable key.

### 2. The secret key never reaches the client

| Key | Where it may live | What it does |
| --- | --- | --- |
| publishable / anon | anywhere, including the browser | subject to RLS |
| secret / service_role | server only | **bypasses RLS** |

- Never give it a `NEXT_PUBLIC_` prefix. That is the whole rule.
- Put the admin client in its own module with `import 'server-only';` at the top, so importing it from
  a client component fails the build instead of shipping the key.
- The bypass is conditional: the secret key ignores RLS **only when the request carries no user
  access token**. If you pass a user's JWT, it runs as that user. "I use the service key" is not a
  blanket excuse.
- A service-role query inside a Server Action still runs as the key, not the caller. Check the caller
  yourself before using it.

### 3. Storage policies are separate from table policies

Buckets are governed by policies on `storage.objects`. Securing `public.documents` does nothing for
the files.

- A **public** bucket serves any object to anyone with the URL, with no policy involved. Make buckets
  private unless the files are genuinely public assets.
- A private bucket with no policies denies everything — including your own app.
- Scope object paths by tenant (`{org_id}/{file}`) and write the policy against the first path segment,
  otherwise one policy grants every tenant every file.

### 4. Configure auth; do not implement it

Supabase Auth owns hashing, salting, session issuance and token rotation. What you own is settings and
authorization.

- Passwords are hashed with **bcrypt plus a per-hash salt**. Argon2 is accepted only as an import
  format. There is no algorithm, cost, or pepper setting — do not add one, and do not tell the user you
  can.
- Turn on **leaked password protection** (HaveIBeenPwned, Pro plan and above).
- Keep the project's auth rate limits on, and add the password-verification hook if you need
  per-account backoff.
- Re-authenticate before destructive actions (`supabase.auth.reauthenticate()` plus a nonce).
- Never build your own password hashing, JWT issuance, or session store. See
  `references/auth-config.md`.

### 5. Server-side authorization reads the verified user, never the request body

```ts
const { data: { user } } = await supabase.auth.getUser();

if (!user) {
  return new Response('Unauthorized', { status: 401 });
}
```

- **`getUser()` on the server, not `getSession()`.** `getSession()` reads the token from storage
  without verifying it; the docs say not to trust it for authorization.
- Never take a `user_id`, `org_id`, or `role` from a form field or query string. Derive it from
  `user`, then scope the query.
- Hiding a button is not authorization. The Server Action, Route Handler, and RLS policy each have to
  hold on their own.
- With `@supabase/ssr`, copy the refreshed cookies **and** the `cache-control` / `expires` / `pragma`
  headers onto any response you build yourself, or a CDN can serve one user's session to another. See
  `references/ssr-nextjs.md`.

## Order of work

1. **RLS** — enable on every `public` table, write policies per operation, add `with check`.
2. **Keys** — find the secret key, confirm it is not client-reachable, add `server-only`.
3. **Storage** — private buckets, path-scoped policies.
4. **Auth settings** — leaked passwords, rate limits, enumeration, reauth.
5. **Server code** — `getUser()` everywhere, no client-supplied identity, cookie headers preserved.

Doing 4 before 1 is wasted effort: a perfect auth config with an unsecured table leaks everything.

## Verify, don't assume

- Query `pg_tables` for `rowsecurity = false` — the fastest audit, and it catches the table someone
  added last week.
- Test with the **publishable key and no session**: every protected table must return zero rows, not
  an error you interpreted as blocked.
- Test with a second user's token: they must not see the first user's rows. A single-user test passes
  with a broken policy.
- Test the update path, not just select — `with check` bugs only show on write.
- Check the browser bundle for the secret key after a production build, not before.

## What to tell the user when the advice is wrong

The most common bad request is a generic hardening checklist written for apps that build their own
auth. Supabase is not that app. Argon2id, pepper, hand-rolled CSRF tokens, HttpOnly-only sessions and
dual rate-limit buckets either do not exist here or break the supported flow.

`references/leaks-and-myths.md` gives the verdict, the evidence, and what to do instead for each.
Read it before implementing anything from such a list.

## Reference map

| File | Read it when |
| --- | --- |
| `references/rls.md` | Writing policies, multi-tenant scoping, views, functions, service-key edge cases |
| `references/auth-config.md` | Password/login settings, rate limits, reauth, MFA, enumeration |
| `references/ssr-nextjs.md` | `@supabase/ssr` in App Router, cookies, proxy/middleware, Server Actions, cache headers |
| `references/leaks-and-myths.md` | Someone proposes a control that does not apply to Supabase |

## What this skill is not

It is not a general Next.js security guide — no CSP, no dependency auditing, no headers checklist. It
is the Supabase-specific boundary: who can read a row, and how the session that decides that gets to
the server intact.
