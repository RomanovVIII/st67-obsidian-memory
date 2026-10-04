# Legacy v0.1 onboarding compatibility reference

Only for preserving or explicitly inspecting the legacy structure profile. New bases follow creation.md and naming-v1. The legacy approval wording applies to design-only proposals; direct user authorization takes precedence. Do not read this file during ordinary maintenance.

# Beginner Onboarding

Use this reference only when a project has no coherent local knowledge-base schema or the user explicitly asks to organize an unstructured base. An existing `AGENTS.md`, index, and local rules remain authoritative until the user approves a migration.

## Contents

- Read-only discovery
- Adaptive interview and project identity
- Required and optional structure
- Naming, metadata, and index rules
- Required project instructions
- Template catalog
- Setup proposal, approval, and validation

Use the user's language for human-readable headings, titles, descriptions, explanations, and document text. Keep filenames, YAML keys, project codes, document types, identifiers, and commands in the technical formats defined here.

## Read-only discovery

Ask for the project directory, then inspect without changing it:

- locate `AGENTS.md`, `wiki_*`, Markdown files, attachments, `.obsidian`, and Git metadata;
- identify candidate vaults, existing owners, duplicated subjects, unresolved material, and sensitive-data candidates;
- check whether Obsidian is installed using safe facilities available on the operating system;
- classify the base as absent, unstructured, partially managed, or already managed.

Do not install software, create a repository or backup, edit Obsidian settings, or move, merge, rename, overwrite, or delete material during discovery.

## Ask only what discovery cannot establish

Ask questions one at a time in plain language:

1. What is the full project name?
2. What is the knowledge base for: personal knowledge, software, an organization, infrastructure, research, learning, or a mixed purpose?
3. Which information belongs here: tasks, decisions, events, incidents, entities, instructions, documents, attachments, references, or another confirmed category?
4. Who uses it: one person, a person with agents, a team, or several agents or devices?
5. May existing material only be indexed, proposed for movement, reorganized after separate approval, or left unchanged?
6. Which project code does the user choose?

Ask conditional questions only when relevant: Obsidian installation, synchronization, attachments, archives, templates, references, plans, reports, workflows, subprojects, collaboration, content language, and material that must not be read or moved. Do not propose a daily-notes section.

## Choose the project identity

Create a lowercase Latin `project_slug` with digits and underscores as needed. Propose two to four project codes, explain each, check conflicts in the intended wiki, and wait for the user's choice.

A code matches `^[A-Z][A-Z0-9]{1,7}$`. Once permanent documents use it, changing it requires a separately approved migration.

## Explain the standard before proposing it

The project root contains `AGENTS.md`. The independent wiki or Obsidian vault is `wiki_<project_slug>`:

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

Explain every object in the proposal and preserve the explanation in the main index:

- `AGENTS.md` — Purpose: route agents into the wiki and define mandatory boundaries. Contents: project identity, wiki path, reading order, owners, approval gates, secret protection, and validation duties.
- `wiki_<project_slug>/` — Purpose: hold one managed knowledge base for the project. Contents: durable Markdown knowledge and local Obsidian configuration when used.
- `index_<CODE>.md` — Purpose: provide the only wiki index. Contents: one alphabetical inventory of every permanent folder and Markdown file with a purpose and contents description.
- `todo_<CODE>.md` — Purpose: own current unfinished work. Contents: active `TODO-<CODE>-NNNN` entries only; remove a completed entry after its durable result is recorded by the proper owner.
- `decisions_<CODE>.md` — Purpose: own durable decisions. Contents: newest-first `DEC-<CODE>-NNNN` entries; a changed position is a new decision that names what it replaces.
- `entities/` — Purpose: own current object state. Contents: numbered cards such as `HOST`, `DEV`, `APP`, `SVC`, `ACC`, `PERSON`, and `ORG`; significant changes also go to the log.
- `inbox/` — Purpose: hold unverified material temporarily. Contents: items awaiting classification; do not delete originals automatically or index each item.
- `incidents/` — Purpose: preserve significant problems and recoveries. Contents: one numbered `INC` card per incident with impact, cause, actions, result, and remaining measures.
- `logs/` — Purpose: preserve confirmed history. Contents: one sequential file per month with newest entries first.
- `rules/` — Purpose: govern the base. Contents: the required database-maintenance and link-workflow rules plus separately justified rules.

Create all required folders immediately. Create optional folders only when the answers require them:

- `attachments/`
- `archive/`
- `templates/`
- `references/`
- `plans/`
- `reports/`
- `workflows/`
- `projects/`

When a permanent section is created, add it to the main index and recommend a maintenance rule. Put a simple rule in the base maintenance document; create a numbered `RUL` only for an independent or complex area.

## Naming and metadata

Use singleton filenames `index_<CODE>.md`, `todo_<CODE>.md`, and `decisions_<CODE>.md`. Number repeatable documents independently by type:

```text
0001_RUL-<CODE>-<kebab-slug>.md
0001_INC-<CODE>-<kebab-slug>.md
0001_LOG-<CODE>_YYYY-MM.md
0001_<TYPE>-<CODE>-<kebab-slug>.md
```

Every permanent Markdown document has non-empty `title`, `created`, `updated`, `status`, and `tags` frontmatter. A numbered document also has `code: TYPE-CODE-NNNN` and `type`.

Under `## Состав базы`, use exactly one alphabetical bullet list sorted by the Unicode-NFC, case-folded relative path:

```markdown
- [[relative/path/file.md|Readable name]] — Назначение: ... Состав: ...
- `relative/folder/` — Readable name. Назначение: ... Состав: ...
```

Include the index itself, all permanent Markdown files, and all permanent folders. Exclude `.obsidian/`, individual inbox items, temporary files, and individual binary attachments. Never create another index inside the wiki.

## Required project instructions

Keep root `AGENTS.md` short. Preserve existing instructions and add a compatible route instead of replacing the file. It identifies the project and code, points to the wiki and main index, requires index → relevant rule → owner reading, separates sources from durable knowledge and live state, requires read-only discovery, prevents duplicate owners and parallel wikis, gates ambiguous or destructive actions, excludes secrets, and requires index and validation updates.

Never replace an existing `AGENTS.md`. Use the template below only to create a missing file. For an existing file, treat it as a checklist of compatible additions, show the exact proposed additions, and wait for approval.

Create two base rules:

- `0001_RUL-<CODE>-database-maintenance.md` owns structure, metadata, naming, owners, lifecycles, sensitive-data boundaries, migrations, and deletion.
- `0002_RUL-<CODE>-link-workflow.md` owns local-only Wikilinks, external routes, index coverage, normal and full audits, exclusions, zero-error requirements, and revalidation.

## Template catalog

Replace angle-bracket placeholders only after discovery and user confirmation. Translate human-readable text to the user's language while preserving technical tokens.

### Root AGENTS.md template

```markdown
# <PROJECT_NAME>

Project code: `<CODE>`.

## Knowledge base route

The managed knowledge base is `wiki_<project_slug>/`. Start with `wiki_<project_slug>/index_<CODE>.md`, then read the relevant rule and the canonical owner of the subject.

## Boundaries

- Inspect read-only before proposing changes.
- Keep sources, durable wiki knowledge, and live operational state distinct.
- Give each durable fact one canonical owner; do not create a parallel wiki or duplicate index.
- Ask before ambiguous, destructive, bulk, external, or schema-changing actions.
- Never store credentials, tokens, private keys, recovery codes, or complete sensitive configurations in the wiki.
- After an approved wiki change, update the main index when coverage changes and run the validation required by the link-workflow rule.
```

### Common frontmatter template

```yaml
---
title: <HUMAN_READABLE_TITLE>
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - <TAG>
---
```

### Numbered frontmatter template

```yaml
---
title: <HUMAN_READABLE_TITLE>
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - <TAG>
code: <TYPE>-<CODE>-NNNN
type: <TYPE>
---
```

### Main index template

```markdown
---
title: <PROJECT_NAME> — knowledge base index
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - index
---

# <PROJECT_NAME>

## Состав базы

- [[decisions_<CODE>.md|Decisions]] — Назначение: Own durable project decisions. Состав: Newest-first decision entries and the decisions they replace.
- `entities/` — Entities. Назначение: Own current states of durable project entities. Состав: Numbered entity cards updated in place.
- `inbox/` — Inbox. Назначение: Hold unverified material pending classification. Состав: Unclassified items that are not individually indexed.
- `incidents/` — Incidents. Назначение: Preserve significant problems and recoveries. Состав: One numbered card per incident.
- [[index_<CODE>.md|Knowledge base index]] — Назначение: Provide the only complete navigation inventory. Состав: Every permanent folder and Markdown file with its purpose and contents.
- `logs/` — Logs. Назначение: Preserve confirmed project history. Состав: One sequential file per month with newest entries first.
- `rules/` — Rules. Назначение: Govern the knowledge base. Состав: Database-maintenance and link-workflow rules plus approved independent rules.
- [[todo_<CODE>.md|Current TODO]] — Назначение: Own unfinished work. Состав: Current unresolved entries only.
```

The example must be adapted to the confirmed paths and language, then sorted by the full relative path after Unicode NFC normalization and case folding. Add every permanent Markdown file, including both rules and the current log.

### Current TODO template

```markdown
---
title: <PROJECT_NAME> — current TODO
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - todo
---

# Current TODO

## TODO-<CODE>-0001 — <CURRENT_UNRESOLVED_ITEM>

- Status: open
- Result needed: <DURABLE_RESULT>
- Next step: <NEXT_ACTION>
```

Keep only current unresolved items and place the newest item first. Remove an item after its durable result is recorded by the correct owner.

### Accumulated decisions template

```markdown
---
title: <PROJECT_NAME> — decisions
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - decisions
---

# Decisions

## DEC-<CODE>-0001 — <DECISION_TITLE>

- Date: YYYY-MM-DD
- Status: active
- Decision: <CONFIRMED_DECISION>
- Reason: <WHY>
- Replaces: none
```

Add new decisions at the top. When a position changes, add a new decision and identify the replaced decision rather than rewriting history.

### Monthly log template

```markdown
---
title: <PROJECT_NAME> — log YYYY-MM
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - log
code: LOG-<CODE>-NNNN
type: LOG
---

# Log YYYY-MM

## YYYY-MM-DD HH:MM — <EVENT_TITLE>

- Confirmed result: <RESULT>
- Affected owner: <CANONICAL_DOCUMENT_OR_ENTITY>
- Validation: <CHECK_AND_OUTCOME>
```

Create one sequential log file for each month that receives an entry. Add new entries at the top.

### Incident card template

```markdown
---
title: <INCIDENT_TITLE>
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - incident
code: INC-<CODE>-NNNN
type: INC
---

# <INCIDENT_TITLE>

## Impact

<CONFIRMED_IMPACT>

## Cause

<CONFIRMED_CAUSE_OR_UNRESOLVED>

## Actions and result

<ACTIONS_AND_VERIFIED_RESULT>

## Remaining measures

<CURRENT_MEASURES_OR_NONE>
```

### Entity card template

```markdown
---
title: <ENTITY_NAME>
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - entity
code: <TYPE>-<CODE>-NNNN
type: <TYPE>
---

# <ENTITY_NAME>

## Purpose

<WHY_THE_ENTITY_EXISTS>

## Current state

<CONFIRMED_CURRENT_FACTS>

## Relationships

<LOCAL_WIKILINKS_OR_PLAIN_EXTERNAL_ROUTES>
```

Update an entity card in place. Record significant confirmed changes in the current monthly log.

### Database maintenance rule template

```markdown
---
title: <PROJECT_NAME> — database maintenance rule
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - rule
code: RUL-<CODE>-0001
type: RUL
---

# Database maintenance

## Scope and owners

Define the project root, wiki root, single main index, and canonical owners.

## Structure, naming, and metadata

Require the confirmed structure, technical filenames, numbering by type, frontmatter, monthly logs, newest-first accumulated documents, and current-only TODO.

## Safe changes

Require read-only discovery, an explicit proposal and approval, recovery before bulk moves, preservation of unknown material, and no automatic deletion of inbox contents.

## Sensitive material

Do not place secrets or complete sensitive configurations in the wiki. Report candidates by category and relative path without exposing values.
```

### Link workflow rule template

````markdown
---
title: <PROJECT_NAME> — link workflow rule
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
tags:
  - rule
code: RUL-<CODE>-0002
type: RUL
---

# Link workflow

## Local links

Resolve Wikilinks and embeds only inside the current vault. Use plain text, a path in backticks, or an ordinary external link for another vault.

## Main index

Keep one `## Состав базы` inventory. Cover every permanent folder and Markdown file; exclude `.obsidian/`, individual inbox items, temporary files, and individual binary attachments.

## Validation

After an ordinary change, validate changed files, index coverage, and incoming and outgoing local links. For a full confirmed audit run:

```bash
python3 <skill-root>/scripts/structure_audit.py <project_root> --wiki-root <wiki_root> --code <CODE> --strict-exit
python3 <skill-root>/scripts/link_audit.py <wiki_root> --vault-root <wiki_root> --strict-exit
```

Finish only with no unexplained structural or link errors.
````

### Setup proposal template

```markdown
# Preliminary knowledge-base setup proposal

## Discovery result

- Project root: `<RELATIVE_OR_CONFIRMED_PATH>`
- Existing instructions and indexes: <FOUND_OBJECTS>
- Candidate vaults: <FOUND_VAULTS>
- Classification: <ABSENT_OR_UNSTRUCTURED_OR_PARTIAL_OR_MANAGED>
- Sensitive candidates: <CATEGORIES_AND_RELATIVE_PATHS_ONLY>

## Identity choices

- Project name: <PROJECT_NAME>
- Proposed slug: `<project_slug>`
- Code options: `<CODE1>`, `<CODE2>` — <SHORT_EXPLANATION>
- User-selected code: <PENDING_OR_CODE>

## Proposed structure

- Mandatory objects: <OBJECTS_WITH_PURPOSE_AND_CONTENTS>
- Confirmed optional objects: <OBJECTS_WITH_PURPOSE_AND_CONTENTS_OR_NONE>

## Exact scope

- Create: <PATHS_OR_NONE>
- Edit: <PATHS_AND_EXACT_COMPATIBLE_ADDITIONS_OR_NONE>
- Proposed moves: <SOURCE_TO_DESTINATION_OR_NONE>
- Leave unchanged: <PATHS>
- Ambiguous candidates: <QUESTIONS_OR_NONE>

## Safety and validation

- Risks: <RISKS>
- Recovery method: <EXISTING_OR_SEPARATELY_PROPOSED_METHOD>
- Planned checks: `structure_audit.py`, `link_audit.py`, and local required validation
- Separate approvals still required: <MIGRATION_INSTALLATION_SETTINGS_BACKUP_GIT_OR_NONE>

No files will be created, changed, moved, or deleted until the user explicitly approves this exact proposal.
```

## Show the proposed structure

Before writing, show:

- discovered facts and classification;
- the mandatory and selected optional structure;
- Purpose: why each object exists;
- Contents: what belongs in each object;
- exact creations, edits, and proposed moves;
- objects left unchanged;
- ambiguous candidates requiring a decision;
- risks and the recovery method.

In the exact scope, enumerate every path individually rather than referring only to a tree or an approximate total. If a total is useful, derive it from the final path inventory and verify that it matches the listed files and folders before showing the proposal.

Wait for explicit approval of this proposal. Approval of discovery is not approval to reorganize files, install Obsidian, initialize Git, create a backup, or change application settings.

## Apply safely and validate

Before a mass move or rename, verify an existing recovery method or separately offer Git or a safe backup. Never choose between conflicting duplicates. Leave unknown material in place or move it to `inbox/` only after approval.

After approved changes, run `structure_audit.py` for the onboarding schema and `link_audit.py` for local links. If either check fails, report the remaining findings and do not claim completion or remove originals or recovery material.

If Obsidian is absent, explain that Markdown remains usable and offer the official installation route. Installation, opening the wiki as a vault, and selecting `attachments/` for new attachments are separate confirmed actions. Preserve all other settings, themes, and plugins.
