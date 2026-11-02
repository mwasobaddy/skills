# Author conventions

These are the preferences of the person who maintains this skill. They are **portable defaults**, not
universal best practice — the reasoning is included so you can tell when one does not apply. A project
rule that contradicts one of these wins; say so rather than silently following either.

## Page naming

A resource gets one lowercase-plural folder, and its list page is always `index`.

```
resources/js/pages/users/
├── index.tsx      # the list — always called index, never users-table.tsx / list.tsx / -page.tsx
├── create.tsx     # only if create needs its own URL
├── edit.tsx       # only if edit needs its own URL
└── show.tsx       # only if the record needs its own URL
```

- `index.tsx` is the default list name in every resource. Do not invent `users-table`, `users-list`, or
  `users-index-page`.
- `Inertia::render('users/index')` must match the folder and file exactly. A mismatch is a blank
  screen, not an error — so get the name right the first time.
- Sub-views that are only reachable from the list (a detail panel, a tab) live beside `index` with the
  action name: `history.tsx`, `settings.tsx`.

## Create, edit and view open in an overlay

Do not send the user to a separate page to create, edit or view a record that belongs to a list. Use a
**responsive overlay**: a `Drawer` rising from the bottom on phones, a `Sheet` sliding from the right
on `sm` and up.

The component is `ResponsiveOverlay` (`resources/js/components/responsive-overlay.tsx`). Copy it into a
new project once, then use it everywhere:

```tsx
<ResponsiveOverlay
    open={open}
    onOpenChange={setOpen}
    title="Edit user"
    description="Changes apply immediately."
    footer={<Button form="user-form" type="submit">Save</Button>}
>
    <UserForm user={user} />
</ResponsiveOverlay>
```

It already handles the breakpoint with `useIsMobile()` — bottom `Drawer` under it, right `Sheet` with
`sm:max-w-lg` above it. Do not build a second overlay or hand-roll the breakpoint.

Why an overlay rather than a page:

- the list stays in view, so the user keeps their place
- no route change, so no back-button ambiguity and no lost filters
- one component serves both breakpoints instead of two screens to maintain

A **full page** is the right call when the view needs its own URL: shareable, deep-linkable, printable,
or reached from a notification. Those are the exceptions, and they should be deliberate.

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
