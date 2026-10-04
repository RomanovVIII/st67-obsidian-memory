# Conditional templates (naming-v1)

Read only the section needed. Adapt language, actual paths, owner and enabled roles; do not instantiate the entire catalog. Existing bases retain their own templates until approved migration.

## Index: IDX_ATLAS.md

```markdown
# Atlas knowledge base

Owner/base_id: atlas. Namespace: ATLAS. Allocator: designated-master.
Parent: platform (optional); hierarchy follows logical parent ownership.
Canonical maintenance and Link Workflow: installed obsidian-memory; base-specific exceptions: none.
Configuration: [CFG_ATLAS.json](CFG_ATLAS.json).

## Managed documents

- [[IDX_ATLAS|Index]] — navigation and document registration.
- [[LOG_ATLAS-0001_2026-10|Journal]] — confirmed creation and maintenance events.
```

Add TODO/cards only when actually present. Register every managed Markdown exactly once, respecting audit exclusions. Shared rules are referenced as skill procedures, not registered as duplicate local files.

## Configuration: CFG_ATLAS.json

```json
{
  "schema_version": 3,
  "base_id": "atlas",
  "scope": "atlas-service",
  "index_path": "IDX_ATLAS.md",
  "file_namespace": "ATLAS",
  "parent_base_id": "platform",
  "naming_profile": "naming-v1",
  "allocation_owner": "designated-master",
  "last_issued": {"LOG": 1},
  "required_paths": ["IDX_ATLAS.md", "CFG_ATLAS.json"],
  "excluded_paths": [".obsidian"],
  "known_top_level_folders": [],
  "rules_roots": [],
  "lifecycle_codes": ["TODO", "PLN", "CPLD", "TRB", "CTRB", "DEC"],
  "historical_source_patterns": [],
  "legacy_markers": [],
  "forbidden_path_patterns": [],
  "disallowed_lifecycle_codes": [],
  "index_section_rules": []
}
```

Omit parent_base_id for a root base. Add role paths/exclusions only when confirmed. last_issued is the allocator's persistent high-water mark, not an automatically derived file count. No secrets in configuration.

## Journal: LOG_ATLAS-0001_2026-10.md

```markdown
---
id: LOG_ATLAS-0001
---
# October journal

Timezone: UTC (replace with confirmed project timezone).

## 2026-10-04 12:00 — create

Changed: created the agreed minimal knowledge base.
Touched: [[IDX_ATLAS|Index]].
Checked: structure profile naming-v1 and full links; separate ownership review.
Result: confirmed base owner and allocator; no unresolved setup issues.
```

Newest events first. Allocate another LOG identifier only for a month with a real event. Do not require an empty current-month file.

## Current state: SRV_ATLAS-0001_api.md

```markdown
---
id: SRV_ATLAS-0001
---
# Atlas API

Verified: YYYY-MM-DD HH:mm, declared timezone; evidence: confirmed source.
Role: ...
Current state: ...
Dependencies: links to relevant cards in this base; plain owner-route for another base.
Open issues: ... (link only to real existing records).
```

## TODO_ATLAS.md

```markdown
# Open questions

## TODO_ATLAS-0001 — verify recovery

Owner: ...
Related: [[SRV_ATLAS-0001_api|API]].
Question and acceptance criterion: ...
Status: open; incomplete checks remain open when the conversation ends.
```

Do not reset counters or create empty TODO. TODO identifiers are assigned once per entry; references to entries may repeat.

## Plans/problems/completed records

```markdown
---
id: CPLD_ATLAS-0001
source_id: PLN_ATLAS-0003
---
# Completed upgrade

Original criterion: ...
Result, evidence and remaining limitations: ...
Related: [[SRV_ATLAS-0001_api|API]].
```

PLN and TRB record owner, trigger/symptom, acceptance criteria, work, evidence and unresolved checks. CPLD/CTRB get their own IDs and source_id. Preserve source history and reservations according to the agreed lifecycle. DEC records an accepted choice and rationale; RSR records unaccepted options; RPT reports evidence. Use the relevant type/date filename from naming-and-numbering, not this example's placeholder as a real filename.
