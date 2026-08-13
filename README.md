**English** | [Русский](README.ru.md)

[![GitHub stars](https://img.shields.io/github/stars/RomanovVIII/st67-obsidian-memory?style=social)](https://github.com/RomanovVIII/st67-obsidian-memory/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

# 🧠 ST67 Obsidian Memory

## Turn a pile of Markdown files into a knowledge base your AI can actually understand.

**Structure. Links. Decisions. Memory. Audits. Without forcing your project into someone else's folder scheme.**

![ST67 Obsidian Memory](assets/st67-obsidian-memory-hero.png)

ST67 Obsidian Memory is an Agent Skill for OpenAI Codex that helps create, organize, maintain, query, and audit project knowledge bases in Obsidian and Markdown.

### ⚡ Built for real projects

- messy existing vaults;
- long-running AI projects;
- multiple agents and contributors;
- Markdown + Obsidian workflows;
- projects where the **source of truth** actually matters.

The skill follows your project's existing rules first. It can inspect before writing, detect structural problems, preserve local conventions, and keep an AI agent from turning a knowledge base into a second pile of duplicated notes.

⭐ **If this helps your AI understand the project instead of just reading files, star the repository.** It helps other people building agent-managed knowledge bases discover it.

## Why it exists

Without a stable structure, a project knowledge base gradually becomes a collection of disconnected files:

- the same facts live in several places;
- decisions and tasks get lost among notes;
- links stop working;
- new contributors do not know where to begin;
- an agent cannot tell which document is the source of truth.

ST67 Obsidian Memory helps turn that material into a managed knowledge base while preserving source data and requiring approval before changes.

The skill works for both beginners with a chaotic collection of notes and projects with an established structure. It does not impose a universal schema: existing `AGENTS.md` files, indexes, and local rules always take priority.

## Four operating modes

### Onboarding

For a new or chaotic knowledge base.

The skill:

1. inspects the project in read-only mode;
2. finds Markdown files, existing rules, indexes, and possible vaults;
3. identifies duplicate topics and sensitive-data candidates;
4. asks only questions whose answers cannot be determined automatically;
5. proposes a short project code and an explained structure;
6. shows an exact setup proposal;
7. stops and waits for explicit approval before writing.

### Maintenance

For maintaining, migrating, and reorganizing an existing knowledge base.

The skill follows the accepted local schema, updates the canonical owners of knowledge, and does not create duplicate documents or parallel wikis.

### Query

For searching and answering without changing files.

The skill starts from the project's entry point and distinguishes confirmed current state from history, assumptions, and unverified material.

### Audit

For a standard or full read-only knowledge-base audit.

The audit covers structure, metadata, index coverage, Wikilinks, headings, block references, attachments, and vault boundaries.

## What a beginner gets

After inspection, the skill can propose this baseline:

```text
<project>/
├── AGENTS.md
└── wiki_<project_slug>/
    ├── decisions_<CODE>.md
    ├── entities/
    ├── inbox/
    ├── incidents/
    ├── index_<CODE>.md
    ├── logs/
    │   └── 0001_LOG-<CODE>_YYYY-MM.md
    ├── rules/
    │   ├── 0001_RUL-<CODE>-database-maintenance.md
    │   └── 0002_RUL-<CODE>-link-workflow.md
    └── todo_<CODE>.md
```

Every object has an explained purpose:

- the single index covers all permanent Markdown files and folders;
- TODO contains only current unresolved items;
- decisions accumulate in one document with new entries at the top;
- logs are split by month with new events at the top;
- every significant incident gets a separate card;
- entity cards are updated in place;
- `inbox/` holds unverified material and is never cleared automatically;
- two required rules define knowledge-base maintenance and link handling.

Additional folders are created only when a confirmed need exists.

## Onboarding safety

Without separate approval, onboarding does not:

- install or configure Obsidian;
- replace an existing `AGENTS.md`;
- move, merge, or delete ambiguous material;
- delete duplicates;
- create a Git repository or backup;
- change source documents;
- write secrets into the wiki.

An existing `AGENTS.md` is preserved. The skill may only propose exact compatible additions and show them before writing.

## Structure auditor

Inventory a project:

```bash
python3 skills/obsidian-memory/scripts/structure_audit.py /path/to/project
```

Fully validate an approved structure:

```bash
python3 skills/obsidian-memory/scripts/structure_audit.py /path/to/project \
  --wiki-root /path/to/project/wiki_example \
  --code EXAMPLE \
  --strict-exit
```

The auditor checks:

- required files and folders, including their object type;
- naming and numbering;
- YAML frontmatter;
- index uniqueness;
- index completeness and ordering;
- the current month's log;
- Unicode NFC/NFD;
- sensitive-data candidates.

The audit does not modify the project. Suspected secret values and unrecognized index-line contents are never printed. A discovered symlink whose resolved target leaves the project is rejected as invalid input.

Exit codes:

- `0` — successful check;
- `1` — strict mode found violations;
- `2` — invalid input.

## Link auditor

```bash
python3 skills/obsidian-memory/scripts/link_audit.py /path/to/managed-wiki \
  --vault-root /path/to/current-vault \
  --strict-exit
```

Supported forms include:

- `[[page]]`;
- `[[folder/page]]`;
- aliases;
- heading links;
- block references;
- `![[note]]`;
- binary embeds;
- Markdown links and attachments;
- Unicode NFC/NFD;
- a nested managed wiki inside a larger vault.

The auditor detects broken and ambiguous links, missing targets, targets outside the vault, incomplete index coverage, and documents without sufficient incoming links. Symlinks and index paths that resolve outside the confirmed boundary are rejected. Unsafe Markdown targets are counted as broken without accessing the external path.

Diagnostic details contain only a safe relative source path, a finding category, and a line number. Raw link and stale-index target values are not printed.

It is read-only, does not use the network, and does not start external processes.

## Install in Codex

### With Skill Installer

Open Codex and ask `$skill-installer` to install the skill from this repository:

```text
Install obsidian-memory from:
https://github.com/RomanovVIII/st67-obsidian-memory/tree/v0.1.0/skills/obsidian-memory
```

Restart Codex if the new skill does not appear immediately.

### Manually

Copy:

```text
skills/obsidian-memory
```

to your user skills directory:

```text
$HOME/.agents/skills/obsidian-memory
```

Codex also supports a symlink to the skill directory.

After installation, invoke the skill explicitly:

```text
$obsidian-memory
```

You can also describe the task in ordinary language and let Codex select the skill from its description.

## Quick start

For a chaotic knowledge base:

```text
$obsidian-memory inspect this project and propose a safe knowledge-base organization. Do not change anything before my approval.
```

For maintenance:

```text
$obsidian-memory read the local rules and update the knowledge base with the results of the current work.
```

For a query:

```text
$obsidian-memory find the confirmed decisions on this topic. Do not modify files.
```

For a full audit:

```text
$obsidian-memory run a full structure and link audit of this wiki.
```

## Requirements

- Python 3.9 or newer;
- OpenAI Codex for the primary use case;
- macOS, Linux, or Windows;
- no third-party runtime dependencies;
- Obsidian is optional.

The Markdown rules, templates, and Python auditors can be adapted to other agent environments that support Agent Skills or a compatible instruction format. Compatibility must be verified separately in each environment.

## Repository layout

```text
skills/obsidian-memory/
├── SKILL.md
├── agents/openai.yaml
├── references/onboarding.md
└── scripts/
    ├── link_audit.py
    └── structure_audit.py
tests/
└── contract and runtime tests
```

## Development

```bash
python3 -B -m unittest discover -s tests -v
python3 -m compileall -q skills tests
```

CI checks the project on Ubuntu, macOS, and Windows with Python 3.9 and 3.14.

## Contributing

Bug reports, Pull Requests, ideas, and feedback are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before making changes.

Do not publish vulnerability details in ordinary Issues. Use private vulnerability reporting as described in [SECURITY.md](SECURITY.md).

## Support the project

If ST67 Obsidian Memory helps you keep an AI-managed knowledge base structured, linked, and maintainable, **give the repository a ⭐**.

## Attribution

- Developer: Studio 67
- Author and copyright holder: Master V
- Technical co-developer: MacMaster

The project is available under the [MIT License](LICENSE).

## Independent project

Obsidian is a trademark of Dynalist Inc.

ST67 Obsidian Memory is an independent Studio 67 project. It is not affiliated with, endorsed by, or sponsored by Obsidian, Dynalist Inc., or OpenAI.
