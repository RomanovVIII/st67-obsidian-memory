# Audit configuration and detailed findings

Read this only when designing/changing audit policy or interpreting a finding that needs its details. Ordinary point checks use the short [Link Workflow](link-workflow.md).

## Base configuration

The optional root file `obsidian-memory.config.json` is owned by the knowledge base, not by a specific agent. The skill supplies one identical execution mechanism; the base supplies its own policy.

Schema version `1` supports:

- `index`: relative path to the base index;
- `required_paths`: files or folders that must exist;
- `excluded_folders`: paths omitted from scanning and index coverage;
- `known_top_level_folders`: allowed root directories;
- `rules_roots`: locations scanned for lifecycle-like codes;
- `lifecycle_codes`: allowed codes such as `TODO`, `PLN`, or `TRB`;
- `legacy_markers`: obsolete names or lifecycle markers;
- `historical_source_patterns`: regular expressions whose legacy markers are advisory rather than strict;
- `url.timeout_seconds`, `url.workers`, and ordered `url.classes`;
- each URL class has `name`, `url_patterns`, `source_patterns`, `check`, and `strict`.

All configured paths are relative and must stay inside the supplied memory root. Excluded folders are not read. Neighbouring project files such as agent-local `AGENTS.md`, `THREADS.md`, scripts, or credential documentation are outside the audit scope.
Schema version `2` rejects unknown keys and uses:

- identity and scope fields: `base_id`, `scope`, and `index_path`;
- path fields: `required_paths`, `excluded_paths`, `known_top_level_folders`, and `rules_roots`;
- lifecycle and history fields: `lifecycle_codes`, `legacy_markers`, and `historical_source_patterns`;
- `disallowed_lifecycle_codes`: objects with `code` and `path_prefixes`;
- `forbidden_path_patterns`: regular expressions for active non-code link targets and plain-text routes;
- `index_section_rules`: objects with `heading`, `path_prefixes`, and `lifecycle_codes`;
- the same ordered `url` policy as schema v1.
`base_id` and `scope` are optional strings. When a base uses a scoped todo page,
name it `todo_<base-id>.md`; no separate `todo_path` field is required.


Wiki targets resolve within the primary vault in this order: exact root-relative path,
source-directory-relative path, then a unique case-insensitive basename/stem match.
Multiple matches are strict `AMBIGUOUS_WIKI_LINK` findings; candidates are never
chosen arbitrarily. Index links use the same inventory-aware resolver.

All configured paths stay relative and inside the primary root.

Inside a Markdown table, escape the wiki alias or embed-size delimiter as `\|`: use `[[path\|alias]]` and `![[image.png\|200]]`. The resolver treats `\|` as the alias or size separator while resolving the target without the escape character. An unescaped delimiter in a real table row is a strict `UNESCAPED_WIKI_ALIAS_IN_TABLE` finding.

## Findings

Strict findings include:

- broken wiki-links and embeds;
- unescaped wiki alias or embed-size delimiters inside Markdown tables (`UNESCAPED_WIKI_ALIAS_IN_TABLE`);
- ambiguous wiki links and case-insensitive duplicate managed filenames;
- missing configured index headings, misplaced entries, and duplicate index entries;
- disallowed lifecycle codes in configured paths or active index/todo entries;
- forbidden active routes outside configured historical sources;
- broken local Markdown links and attachments inside the memory root;
- files missing from the index and stale index entries;
- missing required paths;
- active legacy lifecycle markers;
- `TBD_` placeholders;
- unreachable URLs only when their configured class is strict.

Disallowed-code active-entry scanning reads the configured index, `todo.md`,
managed files whose stem starts with `todo_`, and managed files inside a rule's
configured `path_prefixes`. It evaluates link-entry lines, not arbitrary prose.

Forbidden-route scanning evaluates parsed wiki/Markdown targets plus standalone or
explicitly route/path-labeled plain-text paths. It ignores link aliases, unrelated
prose, YAML frontmatter, fenced code, and inline code. Fences may use three or more
backticks or tildes; inline code spans may use matching backtick delimiters of any
length.

Preflight warnings include unknown top-level folders and lifecycle-like codes found in configured rule folders but absent from `lifecycle_codes`.

Advisory findings include orphan/weak-orphan pages, legacy markers and forbidden routes
in configured historical paths, and unreachable advisory URL classes.

Report strict, advisory, and preflight findings separately. These are structural/configured checks; review meaning, fact validity, ownership and completion criteria separately. Repair findings within the authorized task only; unrelated findings require their own scope.

## URL behavior

URL reachability is never checked unless `--check-urls` is passed. The helper checks configured classes concurrently, tries `HEAD` first, and falls back to `GET` when needed. HTTP `2xx`, `3xx`, `401`, and `403` are treated as reachable.

## Manual fallback

If Python is unavailable, perform a targeted manual review of the changed files and report that a full automated inventory was not run. Do not replace the helper with a copied, base-specific shell script unless the user explicitly asks for a new maintained implementation.

## Schema v3 (new naming-v1 bases only)

Schema v3 extends v2, retaining its policy fields and strict unknown-key validation. Add required file_namespace (2–16 uppercase ASCII letters/digits, starting with a letter), naming_profile: naming-v1, allocation_owner (nonempty), and last_issued (object of used sequential types to nonnegative integer high-water marks). base_id is required/nonempty; parent_base_id is optional/nonempty and cannot equal base_id. Hierarchy changes never alter namespace. Examples are in file-templates; allocation/closure semantics are in naming-and-numbering. Schema v2 rejects these new fields, and existing bases are not opted in automatically.

Automatic selection: explicit --config wins, then legacy obsidian-memory.config.json, then the only root CFG_*.json. Multiple CFG candidates return 2; absent configuration preserves index.md. --index remains an explicit override. Both auditors use the same discovery for naming-v1. Existing CLI counters/strict exit modes remain; new naming diagnostics are additive.
