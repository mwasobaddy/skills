# Overlay policy: sheets for create, edit and view; a modal for delete

Records are handled in a **sheet** — a panel from the right on large screens, from the bottom on
phones — for all three of create, edit and view. The one exception is a delete confirmation, which is
a **centred modal**. Everything is URL-based.

| Job | Surface |
| --- | --- |
| **Create** | Sheet |
| **Edit** | Sheet |
| **View** | Sheet |
| **Delete** — confirmation | Centred modal, with password |

Two rules sit above the table:

- **Every one of these is URL-based.** Opening, closing and deep-linking are URL changes, not
  `useState` flips.
- **One overlay at a time.** Stacking a sheet on a sheet fights over the focus trap and double-dims
  the page.

## Why one surface for all three

The three record operations are the same interaction with different verbs. Using one surface means
the user learns the overlay once and it behaves identically whether they are adding, changing or
reading — same position, same close affordance, same keyboard handling, same back-button behaviour.

It also keeps the list on screen behind the panel. The user keeps their place, their filters and
their scroll, which is the whole reason not to navigate to a dedicated page.

**Do not use a full page for a record.** A page loses the list, needs its own route and breadcrumb,
and the back button leaves the record instead of closing it. The only thing that legitimately needs a
page is a genuine multi-step wizard, which is not CRUD.

**Do not use a centred modal for a form.** A modal is small by design and centres attention, which is
right for a destructive confirmation and wrong for a form the user has to fill in. The delete modal is
the only modal.

## Create

A sheet with the form in it, opened at `/users/create` (or `?create=1` where the app already uses
query params). The list stays behind it.

- Keep it to one screen where you can. A form that scrolls is still usable in a sheet — the body
  scrolls inside the panel — but if it has repeated groups (assign ten properties, add line items),
  group them and consider whether it is really two operations.
- A sheet does not need a footer button per field. One primary action, one Cancel.

## Edit

Identical to create, at `/users/123/edit`. Shareable ("look at what I changed here") and safe to
refresh mid-form.

This is the operation sheets are best at: the user can compare the row they are editing with the
other rows behind the panel, which a page or a modal both prevent.

## View

The same sheet, at `/users/123`, showing the record read-only: the fields, the related records, and
the actions (Edit, Delete, and any record-specific action such as a contract or a history).

- **The sheet is the record's view, not a peek.** There is no separate page behind it. The URL is the
  address to send someone; opening it opens the sheet over the list.
- **Keep it to what fits.** If a record grows genuine sub-navigation — tabs of related tables, an
  activity log, several sections — that is the point at which a page is the honest answer, and it
  should be a deliberate exception rather than the default.
- **Link from the row.** The card or table cell opens the sheet through the URL, not local state.

## Delete

**Always a centred Modal, never a Sheet.** The backdrop blocks the rest of the interface and forces
attention on a destructive action; a sheet reads as "just another panel" and invites a click-through.

The modal carries a **password field**, and the password is verified **server-side**. The modal is not
the gate — the `current_password` rule is. The route's permission middleware is the actual
authorization; the password only confirms the actor.

- **No password is needed when** the app has already confirmed it in this session (a recent
  `password.confirm`) or the record does not exist yet.
- **URL-based**, like everything else: `/items/123/delete` or `?mode=delete&item=123`.
- **On wrong password, keep the modal open** and clear the field. Closing it would hide the error.
- **Carry the record's id in the URL** beside the mode — the modal needs it to build the `DELETE` URL.

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

### The record URL must not shadow `/create`

`GET /occupants/{occupant}` and `GET /occupants/create` have the same shape. If the record route is
registered first and `{occupant}` is unconstrained, it swallows the create URL: the model binding
fails and the form 404s with nothing explaining why.

Constrain the id rather than relying on route order — the create route usually lives in a different
permission group, so the order is not yours to keep stable.

```php
Route::get('/{property:slug}/occupants/{occupant}', ...)
    ->whereNumber('occupant');
```

## Component contract

- **Create / edit / view** → `ResponsiveOverlay` (`components/responsive-overlay.tsx`): bottom
  `Drawer` under `useIsMobile()`, right `Sheet` with `sm:max-w-lg` above it. One component for both
  breakpoints, and one component for all three operations.
- **Delete** → `ConfirmDeleteOverlay` (`components/confirm-delete-overlay.tsx`): a `Dialog` with a
  password field that `DELETE`s to the given URL. Add a `Destroy*Request` with `current_password` on
  the server — the modal is not the gate.
- **URL helper** → `useOverlayParam()` (`hooks/use-overlay-param.ts`): returns `query` and
  `setOverlayParam(key, value, { replace, keep, only })`, and reads `page.url` rather than
  `window.location` for the reason above.

Do not build a second sheet component per operation, and do not add a modal for forms.

## What this looks like in a resource

```
routes:      GET  /users                     -> users/index
             GET  /users/create             -> users/index + create sheet
             GET  /users/{user}/edit        -> users/index + edit sheet
             GET  /users/{user}             -> users/index + view sheet
             GET  /users/{user}/delete      -> users/index + delete modal
             POST /users                    -> redirect users/index
             PATCH /users/{user}            -> redirect users/index
             DELETE /users/{user}           -> redirect users/index
```

A record the list cannot supply — a row from another page of a paginated table — is passed as a
`focused*` prop and used when the id is not in the current rows:

```php
'focusedOccupant' => $this->focusedOccupant($request, $property),
```

## Checklist before you call an overlay done

- [ ] Create, edit and view all use the sheet, not a page and not a modal
- [ ] Delete uses the modal, asks for a password, and the server verifies it
- [ ] Every overlay opens from a URL and closes back to the list URL
- [ ] The back button closes the overlay instead of leaving the page
- [ ] A refresh at an overlay URL reopens the overlay
- [ ] A save redirects to the index, so the overlay closes itself
- [ ] The record URL is constrained so it cannot shadow `/create`
