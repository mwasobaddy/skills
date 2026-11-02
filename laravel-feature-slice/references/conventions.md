# Author conventions

These are the preferences of the person who maintains this skill. They are **portable defaults**, not
universal best practice — the reasoning is included so you can tell when one does not apply. A project
rule that contradicts one of these wins; say so rather than silently following either.

## Page naming

A resource gets one lowercase-plural folder, and its list page is always `index`.

```
resources/js/pages/users/
├── index.tsx      # the list — always called index, never users-table.tsx / list.tsx / -page.tsx
├── chat.tsx       # another page under the same namespace
└── chat/          # only once chat becomes several pages
    ├── index.tsx
    └── history.tsx
```

Rules that make this predictable:

- **`index.tsx` inside a folder is the page for that folder's own path.** `pages/users/index.tsx` is the
  page for `/users`; `pages/users/chat/index.tsx` is the page for `/users/chat`.
- **A folder is a namespace for sibling pages, not a wrapper around one page.** `pages/users/` holds
  `index.tsx` and its sibling pages; `pages/users/chat/` holds the chat pages.
- **One page, one file.** A single page does not get its own folder. `users/chat.tsx` is correct;
  `users/chat/index.tsx` with nothing else in it is a folder that earns nothing.
- **Switch to a folder when the page gains a second page or co-located components.** The moment chat
  grows `history` and `conversation`, move it to `chat/index.tsx` + `chat/history.tsx`. Moving is a
  `git mv` and one `Inertia::render` string.
- **Never `users/chat/chat.tsx`.** The folder is the namespace; the page inside it is `index.tsx`.

Inertia resolves `Inertia::render('users/chat')` to **either** `users/chat.tsx` **or**
`users/chat/index.tsx`, so both work — which is exactly why you need one rule. Having both on disk is a
silent duplicate: one of them is dead code and nothing warns you.

`Inertia::render('users/index')` must match the folder and file exactly. A mismatch is a blank screen,
not an error.

## Create, edit and view use a URL-based overlay

Which surface to use — modal, sheet, full page — is decided by the job, not by the CRUD verb. The
matrix, the URL mechanics and the component contract all live in `references/overlays.md`.

The one thing to remember without opening it: **the overlay's open state comes from the URL, never
from `useState`.** Local state means the sheet cannot be linked to, cannot be refreshed, and the back
button leaves the page instead of closing it.

## Permission-first, never role-first

Check what the user may **do**, not what they are called.

```php
// yes
$request->user()->hasPermissionTo(RoleDelete->value);
$request->user()->hasSubPermission($organization, SubPermissionKey::PropertyDelete);

// no
$request->user()->hasRole('admin');
```

A role is a bundle of permissions. A permission is the thing you actually mean. Checking a role means
every future role that should have that access needs a code change in the check; checking a permission
means it just works.

- Roles exist to **assign** permissions in the UI.
- Code checks permissions.
- The one legitimate role check is a platform-operator gate where the role *is* the concept (for
  example "may impersonate"), and even then prefer a named permission that the admin role happens to
  hold.

## Editing migrations during development

While a project is unreleased, prefer **editing the existing migration** over adding a new one that
only adds columns. A chain of `add_column_to_x` migrations for a table nobody has deployed is noise in
the schema history.

**But ask before you edit an existing migration.** Editing one that has already run somewhere destroys
data or leaves environments inconsistent, and it cannot be undone by a rollback.

Before touching any existing migration file, establish whether the project is live:

> "Is this app deployed anywhere with data that can't be lost — a production URL, real users, or a
> managed database? If so I'll add a new migration instead of editing the existing one."

Signals it is live, and you must add a new migration instead:

- a production or staging URL that is not local
- real users or real records (not seed data)
- a managed database, or backups configured
- deploys on merge to a main branch
- `APP_ENV=production` anywhere

Signals it is safe to edit:

- the migration has never left this machine
- the only data is seeded or factory data
- the branch is unreleased and no one else has pulled it

When in doubt, ask. The cost of asking is one message; the cost of guessing wrong is a schema change
applied to data you cannot reconstruct.
