# Inertia starter kits (React, Vue, Svelte)

React is Inertia 3 + React 19 + TypeScript + shadcn/ui. Vue is Inertia 3 + Vue 3 + shadcn-vue.
Svelte is Inertia 3 + Svelte 5 + shadcn-svelte. All use Fortify, Tailwind 4, and Wayfinder.
Detect with `references/starter-kits.md`.

## Where files go

```
resources/js/
├── components/     # reusable; shadcn primitives in components/ui
├── hooks/          # client-side behaviour
├── layouts/        # shell, nav
├── lib/            # utility functions (cn and friends)
├── pages/          # one file per Inertia page
└── types/          # page props and DTO mirrors

resources/js/wayfinder/   # generated — gitignored
resources/js/actions/     # generated — gitignored
resources/js/routes/      # generated — gitignored
```

The generated directories are build output. Never edit them; fix the PHP route or controller and let
Wayfinder regenerate.

## Page and route

A page with server data gets a controller and an Inertia response:

```php
Route::get('onboarding', [OnboardingController::class, 'create'])->name('onboarding.create');

return Inertia::render('onboarding/wizard', [
    'steps' => OnboardingStep::cases(),
    'profile' => new OnboardingProfileResource($profile),
]);
```

A page with no server data can skip the controller:

```php
Route::inertia('dashboard', 'dashboard')->name('dashboard');
```

The `Inertia::render()` / `Route::inertia()` string is the path under `resources/js/pages`, minus the
extension: `onboarding/wizard` → `pages/onboarding/wizard.tsx`. A mismatch is a blank screen, not an
error.

## Write path

Controller → Form Request → Action, as in the build order. The controller validates nothing, writes
nothing, and returns `Inertia::render()` or `to_route()`.

## Forms

The kits use Inertia 3's `<Form>` component with Wayfinder's `form()` variant:

```tsx
import { Form } from '@inertiajs/react';
import ProfileController from '@/actions/App/Http/Controllers/Settings/ProfileController';

<Form {...ProfileController.update.form()} options={{ preserveScroll: true }}>
    {({ processing, errors }) => (
        <>
            <Input name="name" defaultValue={auth.user.name} />
            <InputError message={errors.name} />
            <Button disabled={processing}>Save</Button>
        </>
    )}
</Form>
```

- `form()` returns `action` and `method`, including method spoofing. The Vite plugin must enable
  `formVariants` — the kits do.
- A 422 response populates `errors`. Do not hand-roll error state.
- `useForm()` still exists, and older pages use it. Use it only where the project already does, or
  when the form needs client state beyond submission. Do not mix both styles in one feature.

## Types

Type props at the page boundary and mirror the **DTO**, not the database row:

```tsx
type Props = { profile: OnboardingProfileData };

export default function Wizard({ profile }: Props) { … }
```

## Tests

One HTTP feature test per controller action: route, validation, authorization, redirect. A
`Route::inertia()` page needs a smoke test when it is part of the feature.

## Rules

- Never `fetch()` data the page needs — pass it as props from the controller.
- Use Wayfinder imports instead of hardcoded URLs.
- Never put business validation in JavaScript; mirror the server rules for UX only.
- One page component per `Inertia::render()` target.

Vue and Svelte share this structure with `.vue` / `.svelte` files. The form idiom differs — check the
kit's own pages before writing one.
