# ST67 Obsidian Memory

This repository is the technical source of truth for ST67 Obsidian Memory.

## Working rules

1. Read `README.md`, `README.ru.md`, and the affected source and tests before changes.
2. Keep the public skill ID `obsidian-memory`, the stable link-auditor CLI contract, and the documented structure-auditor CLI unchanged unless a separately approved release changes them.
3. Keep runtime code compatible with Python 3.9+ and the Python standard library only.
4. Both auditors must be read-only and offline by default and never start external processes. Only the link auditor’s explicit --json-out may write inside the selected root; explicit --check-urls may access the network. Preserve these opt-in boundaries.
5. Add or update a failing regression test before changing runtime behavior, then run the complete test suite.
6. Keep distributable runtime files under `skills/obsidian-memory/`; keep repository tests under `tests/`.
7. Do not add a plugin manifest, remote, tag, release, or publication configuration without explicit approval.
8. Do not alter an installed skill during development. A separately authorized installation must use verified release runtime files and preserve recovery.
9. Do not commit secrets, personal paths, email addresses, caches, environments, builds, or diagnostic output.
10. Update both English and Russian user documentation when their shared facts change.

## Required local checks

```bash
python3 -B -m unittest discover -s tests -v
python3 -m compileall -q skills tests
python3 /path/to/skill-creator/scripts/quick_validate.py skills/obsidian-memory
```

Before completion, also smoke-test both CLIs and inspect the repository for personal data, secrets, prohibited runtime dependencies, network access, and external-process calls.
