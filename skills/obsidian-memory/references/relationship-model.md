# Relationship Model

This model makes the memory useful in Obsidian and reusable by Codex without forcing one project's folder structure onto another.

## Core Ownership

One durable fact should have one owner.

- Confirmed current facts belong to the configured current-state owner, if enabled.
- Procedures belong to the configured procedure owner.
- Analyzed problems belong to the configured problem owner, if enabled.
- Open current-state questions, deferred checks, and uncertain facts belong to the configured todo/open-question owner, if enabled.
- Future-option analysis belongs to the configured research owner, if enabled.
- Active project and technical plans belong to the configured planning owner, if enabled.
- Accepted strategic/project and technical choices with their rationale belong to the configured decision owner, if enabled.
- Completed work that is not better represented as a technical decision belongs to the configured completed-work owner, if enabled.
- Memory maintenance history belongs in the base's configured journal.

Do not create duplicate overview state files that repeat facts already owned by current-state pages. Do not mention absent owners in generated rules, plans, decisions, or agent instructions.

## Required Links

The base index registers each managed `.md` file once, respecting its configured exclusions.

Current-state pages should link to:

- parent project, system, contour, domain, or context page when one exists;
- related current-state pages;
- relevant procedures;
- relevant problem, plan, decision, or completed-work pages when those owners exist and the link is useful;
- sources of verification inside the page text.

Procedure pages should link to affected current-state pages when a current-state owner exists.

Problem pages should link to affected owners, relevant procedures, and any completed work or technical decision that fixed the problem. If a problem owner does not exist, keep problem detail out of completed plans unless the user asks; link to the durable problem record when one exists.

Research pages should link to affected owners and to planned work created from the research when both roles exist.

Planning pages must identify their source:

- todo/open question;
- research;
- direct user instruction;
- service task;
- follow-up to completed work.

Technical decision pages describe an accepted choice and rationale and link to affected owners, retained source plans, relevant problem records, and log entries when useful. They should not duplicate current-state facts or full troubleshooting content if those have their own owners.

the base's configured journal entries should link to existing files only. Deleted files should be written as plain paths or inline code, not as wiki-links.

## Lifecycles

Use only lifecycle stages whose owners are enabled.

TODO / open current-state question:

```text
todo/open-question owner -> planning owner -> execution -> decision owner/log -> current-state owner
```

Future-option analysis:

```text
research owner -> planning owner -> execution -> decision owner/log -> current-state owner
```

Analyzed problem:

```text
diagnosis -> problem owner -> optional plan -> decision/completed work -> current-state/log
```

Technical plan:

```text
planning owner -> execution with checklist updates -> verified result / completed-work lifecycle
```

Raw input:

```text
raw-input owner -> authorized processing -> verified knowledge at its owner -> retain original; conditional cleanup on explicit thread completion
```

Archive:

```text
user command -> archive owner
```

Archive is not automatic and not the current source of truth.

## Plan Closure And Decisions

Close a plan only after its acceptance criteria are met. Preserve its checklist and add the actual result and verification through the existing completed-work lifecycle. Keep incomplete work open at its existing owner. Do not automatically move or rename the plan into a decision.

Record an accepted decision when there is a durable choice, rationale and consequence worth retaining, whether or not a plan existed. Link the plan/result if useful; avoid copying the checklist or current facts into a second record. Existing bases retain their own closure procedure. Raw cleanup follows [thread-completion.md](thread-completion.md), not automatic deletion after processing.

## Strategic Decision Rules

Use a cumulative project decision register for strategic decisions that define durable behavior, such as:

- architecture;
- future agent behavior;
- role boundaries;
- data ownership;
- long-term workflows;
- source-of-truth policy;
- migration or integration strategy.

Do not put routine implementation notes, transient debugging notes, or checklist progress into the strategic decision register.

## TODO / Open Question Rules

Use the configured todo/open-question owner for active questions, deferred checks, and uncertain facts about current state:

- conflicting sources;
- unverified current fact;
- unclear location, owner, endpoint, route, dependency, setting, or state;
- old source fact not confirmed in the new memory.

Do not put future strategy analysis in the todo/open-question owner; use the configured research owner if one exists.

## Research Rules

Use the configured research owner for future-oriented analysis:

- compare alternatives;
- evaluate migration options;
- analyze risks and consequences;
- explain why one approach is preferred;
- prepare a decision before a plan exists.

If research leads to action, create planned work only after user instruction and link the planned file back to the research page as rationale.

## Problem Rules

Use the configured problem owner for analyzed problems with a useful result. The problem does not have to be repeatable.

Save a problem record when there is:

- a symptom;
- affected object;
- diagnostic path;
- useful conclusion;
- root cause, workaround, fix, or explicit decision not to change;
- verification result or a clear reason why verification is incomplete.

Do not save raw logs without conclusions, temporary guesses, active open questions, or ordinary procedures as problem records.
