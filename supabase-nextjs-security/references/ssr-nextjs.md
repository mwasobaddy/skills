# @supabase/ssr in Next.js App Router

The session lives in a cookie named `sb-<project-ref>-auth-token`. The SSR package reads, refreshes and
rewrites it. Almost every "randomly signed out" bug is a response that dropped the rewritten cookie or
its cache headers.

## Two clients, never one

```ts
// lib/supabase/client.ts — browser only
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}
```

```ts
// lib/supabase/server.ts — server only
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Components cannot set cookies. The proxy refreshes the
            // session; ignoring here is the documented pattern, not a swallow.
          }
        },
      },
    },
  );
}
```

- Never import the server client into a client component. Add `import 'server-only'` to the module so
  a mistake fails the build.
- The browser client carries only the publishable key. It is public by design; RLS is what protects it.

## The cache-header rule

`setAll` receives a second argument: `headers` with `cache-control`, `expires` and `pragma`. They must
go on the HTTP response. If they are dropped, a CDN can cache a response containing **another user's
session cookie** and serve it to the next visitor.

When you build a response instead of returning `supabaseResponse`, copy both the cookies and the
headers:

```ts
const response = NextResponse.next({ request });

response.cookies.setAll(supabaseResponse.cookies.getAll());
for (const header of ['cache-control', 'expires', 'pragma']) {
  const value = supabaseResponse.headers.get(header);
  if (value) response.headers.set(header, value);
}

return response;
```

This is the single most dangerous line to skip in the whole setup, because nothing fails visibly — the
app works until traffic hits a cache.

## Proxy / middleware

Next 16 calls it `proxy.ts`; earlier versions use `middleware.ts`. Same job: refresh the session on
every request that can touch it.

```ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // Nothing between createServerClient and getUser: the docs are explicit that
  // inserting code here can cause random logout.
  const { data: { user } } = await supabase.auth.getUser();

  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|webp)$).*)'],
};
```

- Returning a **new** `NextResponse` after `setAll` ran is fine only if that response is the one you
  return — the cookies were written onto it.
- A matcher that misses a route means the session silently stops refreshing there.
- Do not do authorization here alone. The proxy is a redirect convenience; the Server Action, Route
  Handler and RLS are the actual gates.

## getUser(), not getSession()

```ts
// yes — verified against the auth server
const { data: { user } } = await supabase.auth.getUser();

// no — reads the token from storage without verifying it
const { data: { session } } = await supabase.auth.getSession();
```

Server code that authorizes must use `getUser()`. Supabase's docs say not to trust `getSession()` in a
server environment, because it does not revalidate the token.

## Server Actions

```ts
'use server';

import { createClient } from '@/lib/supabase/server';

export async function deleteDocument(id: string) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) return { error: 'Unauthorized' };

  // The id comes from the client — scope by the verified user, never by a
  // user_id or org_id the client also sent.
  const { error } = await supabase
    .from('documents')
    .delete()
    .eq('id', id)
    .eq('owner_id', user.id);

  return { error: error?.message ?? null };
}
```

- The `.eq('owner_id', user.id)` is defence in depth; the RLS delete policy must also enforce it.
- A Server Action is a public HTTP endpoint. Hiding the button changes nothing.
- Next protects actions against cross-site requests with an origin check; do not hand-roll a CSRF
  token on top of it.

## Route Handlers

Same rule: `getUser()` first, then scope the query. If the handler streams a file from a private
bucket, generate a short-lived signed URL rather than making the bucket public.

## Common failures

| Symptom | Cause |
| --- | --- |
| Randomly signed out after a custom response | cookies or cache headers were not copied |
| Session never refreshes | proxy/middleware matcher excludes the route |
| `Auth session missing` in a Server Component | server client built on `request` cookies but response never persisted them |
| Works locally, users collide in production | CDN cached a response with a session cookie |
| RLS returns more rows than expected | the server used the secret key, which bypasses RLS |
| Delete succeeds but select returns null | no select policy alongside the delete return |
