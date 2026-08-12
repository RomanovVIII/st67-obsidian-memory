---
name: obsidian-memory
description: Use when the user asks to set up, organize, migrate, reorganize, maintain, query, or audit a project-specific Obsidian or Markdown knowledge base, especially when its files are unstructured or local instructions require updating its durable wiki. Do not trigger for ordinary project work merely because Markdown or Obsidian is present.
license: MIT
---

# Obsidian Memory

Maintain project knowledge without inventing a universal structure; the project owns its model.

## Choose The Mode

- **Onboarding:** The user wants a first knowledge base, has unstructured material, or has no coherent local schema. Read `references/onboarding.md` and follow its discovery, interview, proposal, approval, and validation gates.
- **Maintenance:** Maintain, migrate, or reorganize an existing wiki. Follow its current `AGENTS.md`, index, and local rules, and obtain approval before changing its schema or moving material.
- **Query:** Search and answer read-only from the current wiki. Start from its entry point and distinguish confirmed current state from archived or unverified claims.
- **Audit:** Inspect read-only at the requested scope. Use the local validation workflow for a managed wiki; use the onboarding structural auditor only for that standard or an explicitly approved adoption.

Never apply the onboarding structure merely because it is available. Do not retrofit the onboarding schema onto an existing managed wiki unless the user approves a migration plan.

## Resolve The Local Schema

1. Read the applicable `AGENTS.md`, local entry point, and relevant `rules/`.
2. Identify the actual project root, managed wiki root, and vault root; never infer them from names.
3. Let local `AGENTS.md` and `rules/` define owners, paths, metadata, and update policy.
4. Use the smallest sufficient scope. Do not add optional sections, templates, registers, or folders in advance.

Ask before writing when a boundary or owner is materially unclear.

Keep three layers distinct:

- Sources: repositories, user material, exports, archives, and observed state.
- Durable wiki: concise maintained knowledge derived from verified sources.
- Project schema: local instructions for this particular wiki.

Do not rewrite sources, duplicate generic workflows in projects, or replace owners of code or operational data.

## Work

### Discover

- Scan read-only first.
- Locate only the index, task owner, decision owner, optional journal, rules, and domain owners that exist.
- Separate current facts, unresolved questions, decisions, history, and obsolete material.
- Assign one canonical owner to each affected durable fact.

### Update

- Make only the approved or locally required change.
- Update an existing owner instead of creating a duplicate.
- Keep summaries navigational; do not repeat details owned elsewhere.
- Update index, tasks, decisions, or journal only if the project schema assigns that role. A journal is optional.
- Preserve provenance during migration and intentional historical paths as history.

### Query

Start from the entry point and schema. Distinguish confirmed state from archived or unverified claims.

## Boundaries

- Resolve and validate Wikilinks only inside the current vault.
- Never create a Wikilink to another vault; use plain text, a path in backticks, or an ordinary external link.
- Do not assume one shared vault, a fixed path, or a fixed layout.
- Keep source code, service worktrees, dependencies, builds, caches, generated files, test outputs, diagnostics, and secrets out of the wiki.
- Keep service requirements, architecture, tests, and deployment in its repository when local rules assign them there.
- Never store credentials, private keys, recovery codes, or complete sensitive configs.

## Validate

For ordinary edits, check only changed files, their index entries, and their incoming and outgoing local links.

For a wiki created by the onboarding standard, run both `scripts/structure_audit.py` and `scripts/link_audit.py` with the confirmed project paths and code.

Run a full audit only on direct request or during an approved migration or reorganization. Scope and index exclusions come from local rules:

```bash
python3 <skill-root>/scripts/link_audit.py <managed-wiki-root> \
  --vault-root <current-vault-root> \
  --strict-exit
```

Use `--index-exclude '<glob>'` only when local schema excludes that path from index coverage.

Before completion verify valid local links, no cross-vault Wikilinks, correct index coverage, one owner per changed fact, no excluded material, and removal of task-created temporary artifacts.
