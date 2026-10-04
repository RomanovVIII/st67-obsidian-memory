# Structure Model

This model defines knowledge roles first. Folder paths are examples, not mandatory structure.

## Role Map

Create a project-specific role map before creating files.

| Role | Purpose | Common owner example |
| --- | --- | --- |
| Entry point | Human and agent starting page, registry of managed `.md` files, honoring exclusions | `index.md` |
| Maintenance log | Short reverse-chronological maintenance journal | `log.md` |
| Current state | Confirmed current facts | `wiki/entities/` |
| Procedures | Runbooks, checks, operating rules, link workflow, maintenance rules | `wiki/operations/` |
| Problems | Analyzed problems, incidents, useful diagnostic conclusions | `wiki/operations/troubleshooting/` |
| TODO / open questions | Active questions, deferred checks, and uncertain current-state facts | `wiki/todo.md` |
| Research | Future-option analysis, tradeoffs, risk reviews, comparisons | `wiki/research/` |
| Planning | Plan rules, master/project plans, and active technical plans | `wiki/plans/` |
| Decisions | Decision rules, strategic/project decision register, and accepted technical choices and their rationale | `wiki/decisions/` |
| Completed work | Optional closed records that are not better represented as technical decisions | `wiki/changes/completed/` |
| Raw input | Temporary user-provided materials awaiting processing | `raw/` |
| Archive | User-directed archive material only | `archive/` |

This expanded role map is optional design guidance, not a required read for point maintenance. For a new naming-v1 base, use IDX/CFG and LOG from the first journaled event; shared maintenance and Link Workflow remain in the skill. Legacy filenames in the examples below illustrate roles, not new naming requirements. Other roles are optional and enabled only when needed. An existing base retains its own required files and layout.

Planning and decisions are separate roles. Do not hide decisions under a generic changes folder if the project needs durable decision history.

## Example Complex Structure

Use this only as an example for a larger memory:

```text
<memory_root>/
|-- index.md
|-- log.md
|-- wiki/
|   |-- todo.md
|   |-- entities/
|   |-- operations/
|   |   `-- troubleshooting/
|   |-- plans/
|   |-- decisions/
|   |-- changes/
|   |   `-- completed/
|   `-- research/
|-- raw/
`-- archive/
```

Do not create optional owners merely because they appear in this example. If a project has no analyzed-problem workflow, do not create troubleshooting. If it has no future-option analysis, do not create research. If it has no planning workflow, do not create plans. If it has no decision workflow, do not create decisions.

## Section Rules

Each enabled role has exactly one owner path or file. One durable fact should have one owner.

Generated indexes, lifecycle rules, plan rules, decision rules, completed records, and local agent instructions must mention only enabled owners. Do not write rules for absent folders.

If a role is disabled but a related event occurs, record only the minimum durable note in the closest enabled owner, usually `log.md` or a completed-work owner.

## Planning Owner

Enable a planning owner only when the project needs durable plans.

A planning owner commonly contains:

```text
00_plan_rules.md
01_project_plan.md
YYYY-MM-DD_HH-MM_dev_plan_<topic>.md
```

Use `01_project_plan.md` only if the project needs a master or strategic development plan. Technical plans should be short, scoped, and checklist-driven.

## Decision Owner

Enable a decision owner when the project needs durable decision history.

A decision owner commonly contains:

```text
00_decision_rules.md
01_project_decisions.md
YYYY-MM-DD_HH-MM_dev_decision_<topic>.md
```

Use the project decision register for strategic decisions that define project architecture, future agent behavior, role boundaries, data ownership, long-term workflows, or source-of-truth policy.

Use technical decision files for accepted choices that merit durable rationale. Close completed plans through the local work lifecycle; a finished plan does not automatically become a decision.

## Default Exclusions

Do not create these by default:

- `state/current`;
- `state/static`;
- `concepts`;
- `sources`;
- `changes/approved`;
- decision folders under `changes/`;
- split raw folders such as `raw/assets`, `raw/external`, `raw/snapshots`.

Create excluded sections only when the project scan and user answers justify them. If decisions are enabled, use a separate decision owner with its own rules instead of nesting decisions inside a generic changes folder.

## Naming Rules

Permanent pages use stable names without dates.

Use this pattern for permanent entity, operation, problem, or research pages when it fits the project:

```text
<object-or-topic>_<short-description>.md
```

Use dated names only for time-scoped records:

```text
YYYY-MM-DD_HH-MM_<object-or-topic>_<short-description>.md
```

Good targets for dated names:

- active technical plans;
- accepted technical choices and their rationale;
- completed work records, including retained completed plans;
- time-bound migration plans.

Record plan closure and decision acceptance separately. Naming and placement follow the local lifecycle; no automatic move or rename from plans to decisions.

Every durable `.md` file should include an `Actuality`, `Updated`, or localized equivalent field when the project uses freshness markers.
