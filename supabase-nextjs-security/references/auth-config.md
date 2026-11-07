# Auth configuration

Supabase Auth owns password hashing, session issuance and token rotation. The work here is choosing
settings and gating sensitive actions — never reimplementing the cryptography.

## What the provider actually does

- New passwords are hashed with **bcrypt** and a randomly generated per-hash salt, stored in
  `auth.users.encrypted_password`. The column name is legacy; it holds a hash, not ciphertext.
- **Argon2 is accepted only as an import format** when migrating users in. It is not selectable for
  passwords your users set.
- There is **no pepper**, and no exposed cost/parameter setting for the hash.

Practical consequence: "configure Argon2id with high cost" and "add a pepper in the HSM" are not
available in this stack. Do not spend a task on them. See `references/leaks-and-myths.md`.

## Settings worth turning on

In the dashboard, under Authentication:

1. **Minimum password length** — 8 is a floor, not a target. Set what your risk profile wants.
2. **Required characters** — the strongest option requires digits, upper, lower and symbols.
3. **Leaked password protection** — rejects passwords present in HaveIBeenPwned, via k-anonymity
   (the password never leaves the server in clear). **Pro plan and above.**
4. **Email enumeration protection** — otherwise sign-up tells an attacker whether an address already
   has an account.
5. **Confirm email** — decide deliberately. Off reduces friction and increases abuse.
6. **Session timebox / JWT expiry** and **refresh token rotation** — shorter lives shrink the window
   for a stolen token; rotation makes reuse detectable.
7. **MFA (TOTP)** — enable the provider, then enforce AAL in the app (below).

These are configuration, not code. Check them before writing anything.

## Rate limiting

Project-wide limits for sign-in, sign-up, token refresh and email sends are configured per project and
apply by default. Do not disable them to fix a flaky test.

Project-wide limits are coarse. For **per-account** backoff — the thing that stops credential stuffing
across rotating IPs — use the password verification hook:

```sql
create table public.password_failed_attempts (
  user_id uuid primary key,
  last_failed_at timestamptz not null
);

create function public.hook_password_verification_attempt(event jsonb)
returns jsonb
language plpgsql
as $$
declare
  last_failed_at timestamptz;
begin
  if event->'valid' is true then
    return jsonb_build_object('decision', 'continue');
  end if;

  select a.last_failed_at into last_failed_at
  from public.password_failed_attempts a
  where a.user_id = (event->>'user_id')::uuid;

  if last_failed_at is not null and now() - last_failed_at < interval '10 seconds' then
    return jsonb_build_object(
      'error', jsonb_build_object(
        'http_code', 429,
        'message', 'Please wait a moment before trying again.'
      )
    );
  end if;

  insert into public.password_failed_attempts (user_id, last_failed_at)
  values ((event->>'user_id')::uuid, now())
  on conflict (user_id) do update set last_failed_at = now();

  return jsonb_build_object('decision', 'continue');
end;
$$;

grant all on table public.password_failed_attempts to supabase_auth_admin;
revoke all on table public.password_failed_attempts from authenticated, anon;
```

Two things that break this quietly:

- Without the `grant` to `supabase_auth_admin`, the hook fails and auth falls back to default behavior.
- Without the `revoke`, the table of failed-attempt timestamps is readable through the API.

Register the function as the password verification hook in the dashboard, then test a wrong password
twice in a row and confirm the second returns 429.

## Re-authentication for destructive actions

A long-lived session should not be enough to delete an account, change an email, or export everything.

- Enable **require reauthentication** for the sensitive operations the dashboard offers (password
  change is gated this way: sessions older than 24 hours must reauthenticate).
- For your own destructive routes, require a recent proof before acting. `reauthenticate()` requests a
  nonce; the user supplies it and you submit it with the change.

```ts
// Ask the provider for a nonce (sent by email), then require it alongside the action.
const { error: nonceError } = await supabase.auth.reauthenticate();

// Later, with the nonce the user supplied:
const { error } = await supabase.auth.updateUser({ password: next, nonce });
```

For a delete confirmation, the honest pattern is a centred modal that requires the password, checked
server-side before the row is touched — not a session-age check alone.

## Enforcing MFA

Enrolling TOTP is not enforcement. Read the assurance level and refuse the sensitive path when it is
below what you require:

```ts
const { data } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();

if (data?.currentLevel !== 'aal2' && data?.nextLevel === 'aal2') {
  redirect('/mfa');
}
```

Check this in the server component or action that performs the sensitive operation, not only in the
UI that links to it.

## Non-enumeration

Sign-in already answers `Invalid login credentials` for both a wrong password and a missing account.
The leaks are on the edges:

- **Sign-up** without email enumeration protection reveals which addresses exist.
- **Password reset** should always report success, whether or not the address is registered.
- Timing: do not add a fast path that returns early for unknown emails.

## Do not

- Do not hash passwords yourself, add a pepper column, or store a second credential.
- Do not mint your own JWTs; RLS reads `auth.uid()` from the provider's token.
- Do not put `role` in a client-editable profile column and trust it. Roles for authorization belong
  in a table the user cannot write, read through RLS.
- Do not disable rate limits, email confirmation, or leaked-password checks to make a test pass.
