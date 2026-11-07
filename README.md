# Skills

Personal collection of **Agent Skills**. All skills live in this one repository and can be
installed individually.

Skills follow the open [Agent Skills](https://agentskills.io/specification) standard, so
they load in Claude Code, opencode, Codex, Cursor, and 20+ other clients via the
`npx skills` CLI.

## Layout

```
skills/
├── AGENTS.md                  # rules for agents working in this folder
├── PITFALLS.md                # error classes we've hit, and how to avoid repeating them
├── README.md                  # this file + skill registry
├── templates/skill-template/  # scaffolding source
├── scripts/                   # new-skill.sh · validate-skill.sh · install.sh · update.sh
└── <skill-name>/              # one folder per skill, committed here
```

Skills sit at the repo root — that is the layout the `npx skills` CLI discovers, so don't
move them into a subfolder without re-testing `npx skills add ./ --list`.

## Install

From GitHub, one skill:

```bash
npx skills add mwasobaddy/skills --skill nextjs-i18n
```

Everything at once, or browse first:

```bash
npx skills add mwasobaddy/skills --list
npx skills add mwasobaddy/skills --skill '*'
```

Add `-g` for a global install, or `-a claude-code` to target specific agents.

## Update

How you update depends on how you installed, because the two mechanisms differ:

| Installed with | Update with | Notes |
| --- | --- | --- |
| `install.sh` (symlinks) | `git pull` | Live immediately. Nothing else to do. |
| `npx skills add` (copies) | `npx skills update -g -y` | Copies do not track repo edits. |
| Project `.ai/skills/` (Boost) | re-copy, then `php artisan boost:update` | See the skill's `install-to-project.sh`. |

One command for this machine — pulls, re-links every skill into the detected agents,
validates each, and runs the self-tests:

```bash
~/Desktop/skills/scripts/update.sh            # pull + relink + validate + selftest
~/Desktop/skills/scripts/update.sh --check    # is there anything new? changes nothing
~/Desktop/skills/scripts/update.sh --relink   # refresh symlinks after installing a new agent
```

Absolute paths work from any directory, because the scripts resolve their own location.
`./scripts/…` works **only** if you are already inside the repo — the scripts therefore
never document themselves that way.

It warns you if a skill is also tracked by the `npx skills` lockfile, because
`npx skills update -g` installs **copies** and would silently replace the symlink — after
which repo edits stop reaching the agent.

Locally, symlinking the folder so edits take effect immediately:

```bash
cd ~/Desktop/skills                   # the commands below are repo-relative
./scripts/install.sh                  # interactive picker, detected agents pre-checked
./scripts/install.sh nextjs-i18n      # a specific skill
./scripts/install.sh --all            # every skill, same agents
./scripts/install.sh --list           # agents this machine has, and where they read skills
./scripts/install.sh --agents claude-code,opencode   # non-interactive
```

`install.sh` links straight at this repo, so edits are live with no reinstall. Paths are
transcribed from the `npx skills` CLI so both installers agree. Use `npx … -g` to verify the
public install path; use `install.sh` for development — the two write different targets and
will overwrite each other.

## Create a skill

```bash
./scripts/new-skill.sh my-skill-name "What it does. Use when ..."
```

Edit the generated `SKILL.md`, validate, then commit:

```bash
./scripts/validate-skill.sh my-skill-name --strict
git add -A && git commit -m "feat(my-skill-name): initial release"
```

Full conventions — naming, frontmatter, description writing, content rules — are in
[AGENTS.md](AGENTS.md). Known failure modes are in [PITFALLS.md](PITFALLS.md); read it
before writing scripts, because most of those mistakes were made here.

## Registry

| Skill | What it does | Install |
| --- | --- | --- |
| [nextjs-i18n](nextjs-i18n) | Next.js App Router internationalization — library choice, locale routing, message catalogs, ICU plurals, hreflang, and retrofitting an existing app | `npx skills add mwasobaddy/skills --skill nextjs-i18n` |
| [google-search-docs](google-search-docs) | Grounds SEO and Search answers in Google's own documentation — corrects retired features and stale advice, with crawler, indexing, structured-data, hreflang, and traffic-drop procedures | `npx skills add mwasobaddy/skills --skill google-search-docs` |
| [seo-build-audit](seo-build-audit) | Implements and verifies technical SEO on any stack — seven-gate checklist, per-framework emission points, a crawl auditor that runs on a live URL or local build, and 11 debugging playbooks | `npx skills add mwasobaddy/skills --skill seo-build-audit` |
| [laravel-feature-slice](laravel-feature-slice) | Prescriptive Laravel feature architecture — the file manifest per feature, thin controllers, Form Requests, Actions, DTOs, dual validation across Inertia/Livewire, and a checker for architectural drift | `npx skills add mwasobaddy/skills --skill laravel-feature-slice` |
| [supabase-nextjs-security](supabase-nextjs-security) | Next.js + Supabase security posture — RLS-first data access, multi-tenant policies, key discipline, storage buckets, auth settings, SSR session/cache traps, and corrections for hardening advice that does not apply to Supabase | `npx skills add mwasobaddy/skills --skill supabase-nextjs-security` |

## License

MIT. See any skill's `LICENSE` file.