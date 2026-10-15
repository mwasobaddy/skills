# Skills

Personal collection of **independent Agent Skills**. Each subfolder is its own Git
repository, installable on its own, without this folder.

Skills follow the open [Agent Skills](https://agentskills.io/specification) standard, so
they load in Claude Code, opencode, Codex, Cursor, and any compatible client.

## Layout

```
skills/
├── AGENTS.md                  # rules for agents working in this folder
├── README.md                  # this file + skill registry
├── templates/skill-template/  # scaffolding source
└── scripts/                   # new-skill.sh · validate-skill.sh · install.sh
```

Only the meta files above are tracked by the root repo. Every skill folder is its own
repo — this folder is a container, not a monorepo.

## Create a skill

```bash
./scripts/new-skill.sh my-skill-name "What it does. Use when ..."
```

Edit the generated `SKILL.md`, then validate and commit:

```bash
./scripts/validate-skill.sh my-skill-name
git -C my-skill-name add -A
git -C my-skill-name commit -m "feat(my-skill-name): initial release"
```

Full conventions — naming, frontmatter, description writing, content rules, git rules —
are in [AGENTS.md](AGENTS.md).

## Install locally

```bash
./scripts/install.sh my-skill-name    # symlink for one skill
./scripts/install.sh --all            # symlink every skill
```

This symlinks into `~/.claude/skills` and `~/.config/opencode/skill`, so edits take
effect immediately without reinstalling.

## Registry

| Skill | What it does | Install |
| --- | --- | --- |
| _(none yet)_ | | |

Add a row here in the root repo when you add a skill — the registry is the only place
that tracks skills across repos.

## License

MIT. See any skill's `LICENSE` file.
