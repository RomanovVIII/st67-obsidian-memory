# ST67 Obsidian Memory

ST67 Obsidian Memory is an Agent Skill for organizing and maintaining project-specific Obsidian and Markdown knowledge bases. It can guide a beginner through safe initial setup while keeping an existing project's local schema authoritative.

Russian documentation: [README.ru.md](README.ru.md)

## Status

The repository is in `Unreleased` state. The first planned version is `0.1.0`; no release or Git tag exists yet.

## Capabilities

- separates four operating modes: onboarding, maintenance, read-only query, and read-only audit;
- inventories a new or unstructured project without changing it;
- asks a short adaptive questionnaire, proposes a project code and explained wiki structure, and waits for approval before writing;
- provides ready adaptive templates for project instructions, metadata, the main index, current tasks, decisions, logs, incidents, entities, both base rules, and the preliminary setup proposal;
- provides a beginner standard with one main index, current tasks, accumulated decisions, monthly logs, incidents, entities, inbox, and base rules;
- discovers and follows the local `AGENTS.md`, entry point, and rules;
- maintains one canonical owner for each durable fact;
- keeps Wikilinks inside the current vault;
- audits the onboarding structure, required object types, names, numbering, metadata, index coverage, and current monthly log;
- audits Wikilinks, headings, block references, binary embeds, Markdown links and attachments, weak incoming links, and unresolved `TBD_` references;
- handles Unicode NFC/NFD paths;
- supports nested managed wiki roots inside a larger vault.

Both auditors read the target project without modifying it. Runtime code uses Python 3.9+ and the standard library only. It does not access the network or start external processes. Supported target systems are macOS, Linux, and Windows.

Onboarding never installs Obsidian, changes its settings, or reorganizes existing material without separate approval. Obsidian is optional; the resulting Markdown wiki remains usable without it.

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
└── repository and runtime regression tests
```

The layout is plugin-ready, but a plugin manifest is intentionally not included.

## Use

Install or link the `skills/obsidian-memory` directory using the skill-discovery rules of your agent environment. Invoke the skill as `$obsidian-memory`.

Inventory a project before onboarding:

```bash
python3 skills/obsidian-memory/scripts/structure_audit.py /path/to/project
```

Validate a confirmed onboarding layout:

```bash
python3 skills/obsidian-memory/scripts/structure_audit.py /path/to/project \
  --wiki-root /path/to/project/wiki_example \
  --code EXAMPLE \
  --strict-exit
```

`--wiki-root` and `--code` are optional for inventory and must be supplied together for full validation. Structure-audit exit codes are `0` for success, `1` for strict structural findings, and `2` for invalid input. Findings contain relative paths and categories; suspected secret values and unrecognized index-line contents are never printed.

Run the link auditor:

```bash
python3 skills/obsidian-memory/scripts/link_audit.py /path/to/managed-wiki \
  --vault-root /path/to/current-vault \
  --strict-exit
```

Its stable CLI inputs are `memory_root`, `--index`, `--vault-root`, repeatable `--index-exclude`, and `--strict-exit`. Exit codes are `0` for success, `1` for strict audit findings, and `2` for invalid input.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills tests
```

The future CI matrix is configured for Ubuntu, macOS, and Windows with Python 3.9 and 3.14. It is not considered executed until the repository is published and the workflow runs on GitHub.

## Attribution

- Developer: Studio 67
- Author and copyright holder: Master V
- Technical co-developer: MacMaster.

This is original work created for Studio 67 and is licensed under the MIT License. See [LICENSE](LICENSE).

Obsidian is a trademark of Dynalist Inc. This project is independent and is not affiliated with, endorsed by, or sponsored by Obsidian or Dynalist Inc.
