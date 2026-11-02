# Overlay policy: create, edit, view and delete

The surface follows the **job**, not the CRUD verb. A create with eight fields is a page; an edit
with three fields is a sheet. Decide by asking what the user needs to see while doing it.

| Job | Surface | Why |
| --- | --- | --- |
| **Create**, 3–5 fields | **Modal** | Small enough that the list behind it is still useful context |
| **Create**, extensive config, multi-step, or heavy validation | **Full page** | Needs room; a modal that scrolls is worse than a page |
| **Edit** | **Sheet** (right) / **Drawer** (bottom) | Standard. The list stays visible on the left while fields change on the right |
| **Edit** whose schema mirrors a complex create | **Full page** | Same form, same reason for room |
| **View** — the primary way to see the record | **Full page** | Needs canvas: activity logs, sub-navigation, related records |
| **View** — a "Quick View" peek from a table | **Sheet** | Preview without losing the table; the full page still exists |
| **Delete** — confirmation | **Modal, always, with password** | A security gate, not a convenience |

Two rules sit above the table:

- **Every one of these is URL-based.** Opening, closing and deep-linking are URL changes, not
  `useState` flips. See "URL mechanics" below.
- **One overlay at a time.** Stacking a sheet on a sheet fights over the focus trap and double-dims
  the page. Reach for a different surface instead of a second overlay.

## Create

Ask two questions in order:

1. **How many fields?** Four or fewer → Modal. Six or more → Full page. Five is the boundary;
   decide by question 2.
2. **Is it one screen?** A repeated group (assign properties, add line items), a step sequence, or
   validation that only reveals itself section by section → Full page, whatever the field count.
   An eight-checkbox property picker is "extensive configuration" even though it is one field.

A create becomes a URL like `/users/create` (or `?create=1` where the app already does that), so a
user can send someone the form, reload it, and return to it with the back button.

## Edit

**The sheet is the default.** A sheet keeps the table visible, so the user can compare rows while
editing one — which is exactly what editing from a list is for.

Escalate to a full page in one case only: the edit form is structurally the same as a create that
already needed a full page. It is the same form; it gets the same room. Do not make create a page
and edit a sheet when the two schemas match, because the user sees one form shrink on save.

The URL is `/items/123/edit`. It is shareable ("look at what I changed here"), and a refresh mid-form
does not lose the user's place.

A three-field record can therefore be **created in a modal and edited in a sheet**. That is deliberate,
not an inconsistency: creating has no row to compare against, so the modal is enough; editing happens
while the user is scanning the list, so the sheet keeps it readable beside the fields.

## View

**The full page is the real view.** `/items/123` is where the record lives: its detail, its history,
its related records, its sub-navigation. That is the address you send someone.

**A sheet is only a Quick View** — a peek from a table row, so the user can check a status or a phone
number without navigating away. A Quick View is additive:

- the table row still links to the full page
- the sheet does not become the only way to see the data
- if a record has more than about six facts, it is not a Quick View, it is the page

Never let a table's Sheet replace the record's page. The moment someone needs to link to a record,
they need `/items/123` to exist.

### Routing the record page

`GET /occupants/{occupant}` and `GET /occupants/create` have the same shape. If the show route is
registered first and `{occupant}` is unconstrained, it swallows `/occupants/create`: the model binding
fails and the create form 404s with no error explaining why.

```php
Route::get('/{property:slug}/occupants/{occupant}', [OccupantController::class, 'show'])
    ->whereNumber('occupant')
    ->name('tenant.occupants.show');
```

Constrain the id rather than relying on route order. The overlay's `create` route usually lives in a
different permission group, so the order is not yours to keep stable.

## Delete

**Always a Modal, never a Sheet, never a page.** A centered modal with a backdrop blur blocks the
rest of the interface and forces attention on a destructive action; a sheet reads as "just another
panel" and invites a click-through.

The modal carries a **password field**, and the password is verified **server-side**. The modal is
not the gate — the `current_password` rule is. The route's permission middleware is the actual
authorization; the password only confirms the actor.

- **No password is needed when** the app has already confirmed it in this session (a recent
  `password.confirm`) or the record does not exist yet.
- **URL-based**, like everything else: `/items/123/delete` or `?mode=delete&item=123`. It is
  shareable and the back button closes it.
- **On wrong password, keep the modal open** and clear the field. Closing it would hide the error.
- **Do not derive the target from client state.** The modal needs the record's identity to build the
  `DELETE` URL, so carry the id in the URL alongside the mode.

## URL mechanics

Two shapes are acceptable. Pick the one the app already uses; do not introduce a second.

**A `modal` prop** — the overlay route renders the list component with an extra prop:

```php
Route::get('/users/{user}/edit', [UserController::class, 'edit'])->name('users.edit');

public function edit(User $user): Response
{
    return Inertia::render('users/index', [
        'users' => UserResource::collection(User::paginate()),
        'modal' => ['type' => 'edit', 'user' => new UserResource($user)],
    ]);
}
```

**A query parameter** — the overlay route redirects to the list with a param the page reads:

```php
Route::get('platform/users/create', fn () => redirect()
    ->route('platform.users.index', ['create' => 1]));
```

Both are URL-based. The `modal` prop costs one request instead of two and keeps a clean address; the
query param is what an app already using it should keep. The compatibility rule from
`conventions.md` applies: keep old links working, render directly for new ones.

What matters in the client either way:

```tsx
// open state from the URL
const { query, setOverlayParam } = useOverlayParam();
const isEditOpen = query.get('mode') === 'edit';

// closing returns to the list URL
setOverlayParam('mode', null, { replace: true });
```

- **`preserveScroll: true`** — without it the page jumps to the top behind the overlay.
- **`preserveState: true`** — without it, opening create and cancelling resets filters and paging.
- **`only: [...]`** — a partial reload, so opening an overlay does not re-run every query on the page.
- **Open pushes history, close replaces it** — so Back closes an overlay rather than walking back
  through each one the user opened.
- **After a successful write, redirect to the index**, never back to the edit URL. Redirecting to the
  edit URL re-opens the overlay you just saved and closed.

### Read the URL from `page.url`, not `window.location`

Inertia pushes history *after* React renders, so `window.location` is stale during render and
nothing re-renders on the change afterwards. The overlay would not open until a full page load.

```tsx
const query = useMemo(() => {
    const index = page.url.indexOf('?');

    return new URLSearchParams(index === -1 ? '' : page.url.slice(index));
}, [page.url]);
```

`page.url` is part of the reactive page object, so it is both correct and a dependency.

## Component contract

- **Modal** → `FormModal` (`components/form-modal.tsx`): `Dialog` + title/description + a body that
  scrolls inside `max-h-[60vh]` + footer. Use it for short creates.
- **Sheet** → `ResponsiveOverlay` (`components/responsive-overlay.tsx`): bottom `Drawer` under
  `useIsMobile()`, right `Sheet` with `sm:max-w-lg` above it. One component for both breakpoints.
- **Delete** → `ConfirmDeleteOverlay` (`components/confirm-delete-overlay.tsx`): a `Dialog` with a
  password field that `DELETE`s to the given URL. Add a `Destroy*Request` with
  `current_password` on the server — the modal is not the gate.
- **URL helper** → `useOverlayParam()` (`hooks/use-overlay-param.ts`): returns `query` and
  `setOverlayParam(key, value, { replace, keep, only })`, and reads `page.url` rather than
  `window.location` for the reason above.

Do not build a second overlay component for each surface. If a surface needs behaviour the shared
component does not have, add it to the component.

## What this looks like in a resource

```
routes:      GET  /users                     -> users/index
             GET  /users/create             -> users/index + modal create
             GET  /users/{user}/edit        -> users/index + modal edit
             GET  /users/{user}             -> users/show        (full page)
             GET  /users/{user}/delete      -> users/index + modal delete
             POST /users                    -> redirect users/index
             PATCH /users/{user}            -> redirect users/index
             DELETE /users/{user}           -> redirect users/index
```

## Checklist before you call an overlay done

- [ ] The surface matches the table above, and you can say which row and why
- [ ] Every overlay opens from a URL and closes back to the list URL
- [ ] The back button closes the overlay instead of leaving the page
- [ ] A refresh at an overlay URL reopens the overlay
- [ ] A save redirects to the index, so the overlay closes itself
- [ ] Delete asks for a password and the server verifies it
