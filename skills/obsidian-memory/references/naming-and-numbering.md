# naming-v1: stable identity and allocation

Read only when creating/renaming documents, allocating identifiers, designing a base or migrating names. Routine edits of existing cards do not require this reference. Existing bases keep their names/lifecycle until an approved migration.

## Namespace and hierarchy

Each base has a permanent unique `file_namespace`: 2–16 uppercase ASCII letters/digits, starting with a letter, e.g. `ATLAS`, `LAB01`. Check known participating bases before assigning it; state any inaccessible comparison scope. `base_id` is the logical owner identifier; `parent_base_id` is an optional logical parent, not a file path. Hierarchy level is derived from parent relationships. Reparenting, changing a host or master never renames the namespace. Avoid cycles. No cross-base wiki links: use plain owner routes.

## Exact shared vocabulary and filenames

| Type | Meaning | Filename example |
| --- | --- | --- |
| IDX | Index | `IDX_ATLAS.md` |
| CFG | Configuration | `CFG_ATLAS.json` |
| LOG | Monthly journal | `LOG_ATLAS-0001_2026-10.md` |
| TODO | Open questions/tasks | `TODO_ATLAS.md`; entry `TODO_ATLAS-0001` |
| HOST | Host | `HOST_ATLAS-0001_gateway.md` |
| DEV | Device | `DEV_ATLAS-0001_sensor.md` |
| APP | Application | `APP_ATLAS-0001_client.md` |
| SRV | Service | `SRV_ATLAS-0001_api.md` |
| NET | Network | `NET_ATLAS-0001_lan.md` |
| STO | Storage | `STO_ATLAS-0001_volume.md` |
| PLN | Active plan | `PLN_ATLAS-0001_2026-10-04_12-00_upgrade.md` |
| CPLD | Completed plan/work | `CPLD_ATLAS-0001_2026-10-04_13-00_upgrade.md` |
| TRB | Active problem | `TRB_ATLAS-0001_2026-10-04_12-00_timeout.md` |
| CTRB | Completed problem | `CTRB_ATLAS-0001_2026-10-04_13-00_timeout.md` |
| DEC | Accepted decision | `DEC_ATLAS-0001_2026-10-04_14-00_storage.md` |
| RSR | Research | `RSR_ATLAS-0001_storage_options.md` |
| RPT | Report | `RPT_ATLAS-0001_2026-10-04_link_audit.md` |
| RUL | Base-specific procedure | `RUL_ATLAS-0001_restore.md` |
| ATT | Managed attachment | `ATT_ATLAS-0001_diagram.png` |
| RAW | Source material | `RAW_ATLAS-0001_source.pdf` |
| TMP | Current-work temporary material | `TMP_ATLAS_12345678-1234-4234-8234-123456789abc_probe.txt` |

Generic format: `<TYPE>_<BASE>-<NNNN>_<topic>`, with dates as above. Dates use the task's declared timezone; preserve that timezone in journal/configuration documentation. Topics contain Unicode letters/digits, `_` or `-`, without spaces/control characters; prefer lowercase meaningful words. Prefer storing filenames in NFC; audits accept filesystem NFD equivalents without migration. Markdown uses `.md`; CFG uses `.json`; ATT/RAW/TMP preserve the actual extension. Every numbered knowledge Markdown document (excluding original ATT/RAW Markdown attachments) has frontmatter `id: TYPE_BASE-NNNN`, exactly matching its filename. IDX/CFG/TODO are singletons; TMP uses a full fresh lowercase UUID rather than a sequence.

## Allocate and close

One appointed `allocation_owner` issues numbers for each base. Others prepare content and edit existing records; ask the allocator for new identifiers through an authorized channel, or leave the content pending. Do not infer messaging permission. There is no central allocation service or distributed-lock guarantee in this version.

Each sequential type has its own high-water mark in `last_issued`. Use canonical zero-padding to four digits (`0001`, …, `9999`, `10000`); extra leading zeroes are invalid, start at 1, never reuse issued numbers; gaps and counters above visible files are valid. The allocator reserves/increments the counter before creation, retains the reservation after failure/deletion, and serializes its own allocation operations. Sync does not make a cross-machine allocation lock. Never reduce a counter to the current file maximum.

Close PLN → CPLD and TRB → CTRB only after acceptance criteria are met. Allocate a new destination ID and retain `source_id: PLN_BASE-NNNN` / `TRB_BASE-NNNN`; the original ID remains reserved. Transfer history without rewriting it, repair links and index entries, record the transition; follow the base's retention policy for the source record. References to source IDs are history, not duplicate document identities. Retained source_id values prove issued reservations and must also be covered by their original type high-water mark. Completed work is not automatically a DEC. TODO IDs belong to entries; mentioning another TODO elsewhere is a reference, not allocation.

Filename uniqueness covers managed documents and attachments using NFC plus case-insensitive comparison, including participating bases. Comparison cannot guarantee uniqueness against inaccessible/unknown bases. The allocator owns that coordination; audits detect existing collisions but do not allocate IDs or migrate anything.
