---
name: obsidian-memory
description: Create, migrate, maintain, or audit an Obsidian-compatible knowledge base; find prior work by topic and reconcile project memory on an explicit request to finish a thread. Use when the user requests these workflows or project instructions require them. Follow the existing base's ownership and lifecycle.
---

# Obsidian Memory

Release: 0.2.0 (authoritative marker: `VERSION`).

## Entry and authority

Choose the object, owner, base root, and requested mode. Use project routing; do not infer ownership from the execution host, IP, or service name. Global Codex rules/settings use the global library. For mixed work, separate owners before writing. Never resolve wiki-links across bases or invent another agent's local base.

Read the chosen base's index and canonical maintenance rule once, then only relevant cards and required procedures. Reuse instructions and context already read in the continuing task; do not re-read unchanged files just because the skill was invoked again. Refresh when the file changed, scope changed, a material pause made it stale, or evidence conflicts. A changed card may be read to verify the edit.

Reading and auditing write nothing and contact no network by default. A user instruction to implement or maintain authorizes necessary knowledge updates within that task without repeated approval. Discussion/research alone does not authorize implementation. Agree separately on scope expansion, structural redesign, or irreversible deletion of valuable material. Never store or expose secrets.

At the first substantive use on a topic, a substantial topic change, or an explicit request to check the base, perform the targeted lookup below. Reuse its result within the same object and scope unless related documents changed. This is a small search, not a full inventory.

## Targeted prior-work lookup

1. Identify the object, its known aliases, and a few specific keywords from the task or index.
2. Search existing TODO/open-question records, plans, active and completed problems, decisions, and completed work in the owner base. Use index/configured paths and narrow text matches; if paths are unclear, discover filenames first. Pass explicit base paths to filename discovery and text searches (for example, `rg --files <memory_root>`); never rely on the shell's current directory or `workdir`, since startup profiles may change it. Do not create absent roles or read every card.
3. Read useful matches and their necessary related cards/procedures. With no matches, stop; with excessive matches, narrow the object/keywords. Mention a match when it affects the work.
4. Historical decisions do not prove current infrastructure state. A matched TODO/plan does not authorize extra work. Follow the base's mandatory checks, avoiding identical duplicate checks. No persistent caches or thread registries.

## Modes and conditional reading

Load only the material needed for the selected mode, and only if it is not already known in this task.

| Mode | Material and action |
| --- | --- |
| Maintain an existing base | [maintenance.md](references/maintenance.md); preserve its paths, owners and lifecycle; edit only relevant documents. |
| Find prior work | Use the lookup above; no other skill reference is required for a search alone. |
| Design/create a base | [creation.md](references/creation.md), then only necessary naming/template sections. |
| Migrate an existing base | [migration.md](references/migration.md); preserve the old schema until migration is authorized. |
| Create/rename/allocate a document | [naming-and-numbering.md](references/naming-and-numbering.md) only for a new base or one adopting naming-v1; ordinary card edits need no naming reference. |
| Audit/check links | [link-workflow.md](references/link-workflow.md); point edits use `--changed` / `--removed`, broad audit only for a new base, major migration/restructure, or explicit request. |
| Finish a thread | Only an explicit command such as “завершить тред” triggers [thread-completion.md](references/thread-completion.md). Ordinary farewells and discussion of finishing do not. |

In a maintenance task needing link checks, read the Link Workflow in addition to maintenance guidance. Do not load creation, interview, template, or completion material for an ordinary point edit. Existing mandatory local procedures take precedence over generic layouts. Source code, dependencies, builds, test outputs and secrets are not managed knowledge. New bases use naming-v1; existing names/lifecycle stay until an approved migration.

## Verification and result

Use the existing base's Link Workflow and the bundled `scripts/link_audit.py` where applicable; do not copy a second checker into each base. Local checks may scan filenames and other documents' links to find affected references, while unrelated errors stay outside the result. No network without an explicit URL-check request; no output file without an explicit report destination.

Automated checks establish syntax, registration, placement and configured lifecycle constraints. Separately review meaning: verified facts versus assumptions, ownership, useful relationships, acceptance criteria, and preserved unfinished work. A clean script result does not prove these or live infrastructure state.

Report the changes, actual scope/check result, and material open issues briefly. Follow existing journal requirements; do not create separate reports, decisions, or owners for each small edit. Archive a chat only on a separate explicit instruction.
