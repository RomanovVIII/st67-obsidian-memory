# Contributing

Thank you for helping improve ST67 Obsidian Memory.

## Before a change

- Read `AGENTS.md`, both README files, and the affected implementation and tests.
- Keep the change focused and avoid unrelated refactoring or new features.
- Do not include personal paths, private data, credentials, tokens, email addresses, generated files, environments, or caches.
- Preserve Python 3.9+ compatibility and standard-library-only runtime code.
- Preserve read-only/offline defaults and explicit --json-out/--check-urls opt-ins, the stable link-auditor CLI, and the documented structure-auditor CLI unless a breaking change is explicitly approved for a future release.
- Keep the conditional mode routes in `SKILL.md`, metadata and corresponding references aligned when behavior changes. Existing local schemas must remain authoritative.
- Keep adaptive templates usable as complete starting points while preserving technical filenames, YAML keys, codes, types, and commands.

## Test the change

Add a regression test before changing behavior, then run:

```bash
python3 -B -m unittest discover -s tests -v
python3 -m compileall -q skills tests
```

Validate the skill directory with the official Agent Skills validator available in your development environment. Update both language versions of the documentation and `CHANGELOG.md` when user-visible facts change.

For auditor changes, also smoke-test both CLIs. Tests must confirm that inspected files remain unchanged and that sensitive candidates or malformed index entries never expose discovered values or line contents. Required files and directories must be tested with type-swapped objects.
