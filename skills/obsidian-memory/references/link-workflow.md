# Link Workflow

Use a local read-only check for ordinary edits; full inventory for a new base, major migration/restructure or an explicit request. The helper writes nothing and contacts no network by default. Content meaning and live facts require separate verification.

## Point checks

Run `scripts/link_audit.py` from the installed skill with the selected base root. Use `python` (Windows) or `python3` where appropriate; do not copy another checker into each base.

```text
link_audit.py <memory_root> --changed wiki/service.md --strict-exit
link_audit.py <memory_root> --changed wiki/new.md --removed wiki/old.md --strict-exit
link_audit.py <memory_root> --removed raw/processed.pdf --strict-exit
```

Repeat `--changed` for existing changed documents/attachments; repeat `--removed` for absent former file paths. For a move include the new and old paths. The helper inventories managed names and scans other documents' links for affected references; unrelated content errors are excluded from results and exit status. The report lists local scope and checked documents, and is not a full-base audit.

It checks changed documents and outgoing links, affected backlinks, index registration and applicable configured placement/lifecycle constraints. A short wiki link that could silently retarget after deletion raises `WIKI_TARGET_CHANGED_AFTER_REMOVAL`.

All scope paths are relative to the root. Absolute, escaping, excluded or invalid paths, missing changed files, existing removed paths and changed directories return `2`. Do not bypass exclusions for working material: check its references manually and, where needed, check affected managed documents with `--changed`.

## Full audit and options

Without `--changed`/`--removed`, full audit applies; schema v1/v2 remain supported and schema v3 enables naming-v1:

```text
link_audit.py <memory_root> [--config <path>] [--index <relative-path>]
  [--compare-root <path>]... [--json] [--json-out <path>]
  [--strict-exit] [--check-urls]
```

- Configuration uses explicit `--config`, otherwise `obsidian-memory.config.json`, otherwise a unique root `CFG_*.json`; several CFG candidates are usage error `2`; `--config` selects a file inside the root and `--index` overrides its index path.
- `--compare-root` compares managed filenames only; in local mode only touched names. Never resolve links across roots; `.obsidian/**` is omitted from filename comparisons.
- `--json` prints the report. Only explicit `--json-out` writes a report, confined to the root.
- Only explicit `--check-urls` enables network access, and only for changed documents in local mode. Do not pass it without a URL-check request.
- With `--strict-exit`, strict findings return `1`; valid execution otherwise returns `0`. Usage/config/path errors return `2`.

Follow the base's required checks without duplicating an identical check. Report strict, advisory and preflight results separately. Repair only findings within the authorized scope; orphan advisories do not require invented links.

Read [audit-configuration.md](audit-configuration.md) only to configure schema/policy or understand a particular detailed finding. Routine checks do not require it. If Python is unavailable, review affected links manually and state the automation limitation.

## New-base structural profile and imported compatibility

`structure_audit.py <base_root> --profile naming-v1 --strict-exit` checks the new minimal IDX/CFG layout and names/IDs/counters, without mandatory current-month logs or contiguous numbering. The older `--wiki-root <root> --code <CODE>` call retains the legacy onboarding profile. Never apply the legacy profile to a new naming-v1 base.

Both link-auditor `--vault-root` and `--index-exclude` remain supported. The vault boundary must be explicitly confirmed as the same base, never a neighboring base or arbitrary shared directory; by default it is memory_root. Index-only glob exclusions skip registration checks, not link or identity checks. Legal parent paths inside that boundary work. Absolute/escaping links are findings; unsafe input/symlinks return `2`. Headings, block references and Unicode NFC/NFD are checked outside code examples; reported line numbers refer to the original document. Diagnostics omit raw link values and URL credentials in text/JSON/stderr.

Filename comparisons include managed documents and attachments with NFC and case-insensitive matching. Other roots never resolve links. Unavailable comparison roots are reported as a limitation; unique namespaces still require allocator coordination across participating bases. Scoped checks ignore unrelated content/naming findings; inventory/link scans needed to find affected references are permitted.
