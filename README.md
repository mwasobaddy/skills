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
├── scripts/                   # new-skill.sh · validate-skill.sh · install.sh
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

Locally, symlinking the folder so edits take effect immediately:

```bash
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

## License

MIT. See any skill's `LICENSE` file.