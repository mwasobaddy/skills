# Leaks and myths

Two purposes: what actually leaks in Supabase apps, and how to answer hardening advice that was written
for apps that build their own auth.

## What actually leaks, in order of frequency

1. **RLS disabled or missing on a new table.** One `create table` without `enable row level security`
   and the publishable key reads it from any browser. This is the incident, not a stolen database.
2. **A policy that says `using (true)`** — often added to "fix" a permission error and never removed.
3. **The secret key in the client bundle**, usually via a `NEXT_PUBLIC_` prefix or an import that
   crossed the server/client boundary.
4. **Storage buckets with no policies, or a public bucket** holding invoices and IDs.
5. **A `security definer` function** owned by `postgres`, executable by `anon`, returning rows it never
   filtered.
6. **A view** without `security_invoker`, which bypasses the RLS on its base tables.
7. **A CDN-cached response** carrying someone's session cookie, caused by dropping the cache headers
   the SSR package hands you.

None of these are cryptographic. All of them are configuration or one missing clause.

## Advice that does not apply

| Advice | Verdict for Supabase |
| --- | --- |
| Argon2id with tuned time, memory and threads | **Not available.** New passwords are bcrypt + per-hash salt. Argon2 is accepted only as an import format. No cost/algorithm setting exists. |
| Pepper held outside the database | **Not available.** You do not run the hash; there is nowhere to inject it. |
| Add a unique salt per password | **Already done**, automatically. Adding one is impossible and pointless. |
| Check passwords against breach lists via k-anonymity | **Exists, as a setting.** "Prevent use of leaked passwords" uses HIBP Pwned Passwords. **Pro plan and above.** |
| Parameterized queries to stop SQLi | **Correct but not the risk here.** Use `.eq()`/`.rpc()` with arguments, but the equivalent exposure is a mis-scoped policy or a `security definer` function. Review those first. |
| Signed CSRF token per state-changing request | **Not the model.** Next's Server Actions already check the request origin. The real transport risk is cache headers leaking a session. |
| HttpOnly session cookie | **Not the default and not a toggle.** The browser client reads the session from `document.cookie`; HttpOnly breaks it. A server-only session is an architecture choice, not a setting. |
| Sudo-mode interceptor middleware | **No built-in.** Use `reauthenticate()` + nonce, or require the password on the destructive route, verified server-side. |
| IP leaky bucket + per-account token bucket | **Partly built in.** Project-wide auth rate limits are configured per project; per-account backoff needs the password verification hook returning 429. |
| Uniform error responses to prevent enumeration | **Sign-in is uniform already.** The leak is sign-up; enable email enumeration protection, and make password reset always report success. |

## Why the list feels right

It is a correct checklist for an application that stores credentials itself: it owns hashing, session
storage, CSRF and throttling, so every item applies. Supabase moves hashing and session issuance into a
managed service. The checklist still names the same goals — protect credentials, verify the session,
resist brute force — but the controls have moved from *code you write* to *settings you choose plus
RLS you author*.

The mistake is treating "the database is public" as "so the hashes must survive a dump". Your hashes
live in `auth.users`, which the API never exposes and where RLS does not even apply to API traffic. The
rows that leak are the ones in your `public` schema.

## How to respond

1. Name the item and say plainly whether the stack supports it.
2. Say what the equivalent control is here, if one exists.
3. Point at the thing that is actually unprotected. A hardening request is a good moment to run the
   `pg_tables` audit.

Do not implement a shadow of the control to satisfy the request. A pepper column filled with the same
global secret for every user, or a home-made CSRF token on top of Server Actions, adds code and no
security — and hides the real gap.

## If the user insists

Sometimes they want it anyway. Then be explicit about what is and is not achieved:

- A "pepper" concatenated in the app before calling `signUp` is a **password transform**. It protects
  nothing against a dump of `auth.users`, because the transformed value is what the provider hashes,
  and it breaks password reset and email-link flows that expect the real password.
- A custom CSRF token on a Server Action is redundant with Next's origin check and does not cover the
  cache-header failure.
- Custom hashing means running your own auth. If the requirement is genuinely "credentials must
  survive a full database compromise", that is a self-hosted auth decision, not a Supabase setting — and
  it should be stated as a migration, not a tweak.
