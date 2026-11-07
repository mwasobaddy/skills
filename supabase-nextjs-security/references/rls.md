# RLS, scoping and storage policies

Everything here assumes the publishable key is in the browser, which it is. A policy is the only thing
deciding who reads a row.

## Default deny, then grant

```sql
alter table public.notes enable row level security;
```

RLS on with zero policies = nobody can read or write. That is the state every new table should start
in. Then add only what the app needs.

| Operation | Clause | Meaning |
| --- | --- | --- |
| `select` | `using` | which existing rows are visible |
| `update` | `using` + `with check` | which rows may be targeted, and what they may become |
| `delete` | `using` | which rows may be removed |
| `insert` | `with check` | what a new row must look like |

`with check` on update is the one people forget:

```sql
-- Without `with check`, an owner can PATCH their row and change user_id to
-- someone else's, moving it out of (or into) another account.
create policy "owner updates own notes"
  on public.notes for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
```

Use `(select auth.uid())`, not bare `auth.uid()`. The subquery is evaluated once per statement instead
of once per row — Supabase's own performance guidance, and it matters on any table with a few thousand
rows.

## Insert-then-select needs both policies

```ts
const { data } = await supabase.from('notes').insert({ body }).select();
```

`.select()` after `.insert()` returns the row, which requires a **select** policy as well. Without one
the insert succeeds and `data` is `null` with no error — a bug that looks like a broken insert.

## Multi-tenant scoping

Do not trust a tenant id from the client. The policy derives it from the user.

```sql
create table public.memberships (
  org_id uuid not null references public.organizations(id),
  user_id uuid not null references auth.users(id),
  role text not null default 'member',
  primary key (org_id, user_id)
);

alter table public.memberships enable row level security;

-- A policy on `memberships` that queries `memberships` recurses infinitely.
-- Break the cycle with a SECURITY DEFINER function.
create or replace function public.is_org_member(target_org uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.memberships
    where org_id = target_org and user_id = (select auth.uid())
  );
$$;

revoke execute on function public.is_org_member(uuid) from public, anon;
grant execute on function public.is_org_member(uuid) to authenticated;

create policy "members read their org rows"
  on public.documents for select
  to authenticated
  using (public.is_org_member(org_id));
```

Notes that matter:

- `security definer` runs as the function's owner (`postgres`), which **bypasses RLS**. It exists here
  only to read the membership table outside the policy that would otherwise recurse.
- `revoke execute ... from public, anon` is required. By default any role can call it, including
  `anon`, and the function returns whether an arbitrary org has *some* member — a membership oracle.
- `set search_path = ''` and fully-qualified names stop a caller-controlled search path from
  redirecting the function at another schema.
- **Do not** let the function take a `user_id` argument. If the caller can pass one, they can pass
  someone else's. Derive the user inside.
- Never write a `security definer` function that returns rows from a table without repeating the
  ownership filter in its body. The execute grant limits *who can call it*, not *what they get back*.

## Views

A view in `public` runs with its owner's privileges, so it **bypasses RLS** on the tables underneath.

```sql
create view public.tenant_documents
with (security_invoker = true)   -- Postgres 15+, which Supabase runs
as select * from public.documents;
```

Without `security_invoker`, a view is a hole: the table is locked and the view serves everything.
Audit views as well as tables.

## The secret key, precisely

The secret/service-role key bypasses RLS **only when the request carries no user access token**. If a
user JWT is attached, the query runs as that user.

```ts
import 'server-only';
import { createClient } from '@supabase/supabase-js';

// Admin client: bypasses RLS. Keep it in a server-only module so a client
// import fails the build instead of shipping the key.
export const admin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SECRET_KEY!,
);
```

Use it for jobs, webhooks, and admin screens — and check the caller's permission yourself, because the
database will not.

## Storage

Buckets have their own policies on `storage.objects`; table policies do not cover files.

- **Public bucket** → any object is served to anyone with the URL, no policy involved. Use only for
  genuinely public assets.
- **Private bucket** → access requires a policy on `storage.objects`. None means denied, including for
  your app.
- **Scope the path.** Store as `{org_id}/{file}` and match the first folder segment, otherwise one
  policy grants every tenant every file:

```sql
create policy "org members read own folder"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'documents'
    and public.is_org_member(((storage.foldername(name))[1])::uuid)
  );
```

Uploads need `insert` with a matching `with check`; deletes need `delete`.

## Testing a policy

Run as a real user inside SQL, which is faster than clicking through the app:

```sql
begin;
set local role authenticated;
set local request.jwt.claims = '{"sub":"<user-uuid>","role":"authenticated"}';

select count(*) from public.documents;        -- expect only their rows
update public.documents set org_id = '<other-org>' where id = '<id>';  -- expect 0 rows

rollback;
```

Then repeat with `anon` and no claims: every protected table should return zero rows.

## Checklist

- [ ] `pg_tables` shows no `public` table with `rowsecurity = false`
- [ ] Each table has policies per operation, not one `for all`
- [ ] Every update policy has a `with check`
- [ ] Insert-then-select tables also have a select policy
- [ ] Membership checks go through a `security definer` function with `execute` revoked from `anon`
- [ ] Views use `security_invoker = true`
- [ ] Storage buckets are private unless they hold public assets
- [ ] Object policies are scoped by the first path segment
