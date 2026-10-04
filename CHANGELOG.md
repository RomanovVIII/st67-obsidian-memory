# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) after its first release.

## [Unreleased]

## [0.2.0] - 2026-10-04

### Added

- Separate, conditional creation, migration, maintenance, naming, audit and explicit-completion procedures; targeted prior-work search and same-task context reuse.
- Schema v3/naming-v1 with permanent namespaces, shared type codes (SRV), single-owner allocation and persistent per-type high-water marks; new completed IDs with source_id.
- Minimal IDX/CFG/event-driven LOG layout, optional TODO and meaningful cards; no mandatory empty monthly logs or duplicated shared rules.
- Scoped changed/removed audits, configured lifecycle/placement, filename comparisons across documents/attachments, safe JSON reports and explicit URL checking.
- Installable version marker and expanded regression tests. Legacy schema v1/v2, public CLI flags/counters and legacy structural profile remain supported.

### Changed

- Updated GitHub Actions checkout and Python setup steps to their Node.js 24-compatible v7 releases.

### Fixed

- Unicode NFC/case-insensitive collisions, heading/block checks outside variable code fences, original source line numbers and legitimate parent paths inside confirmed boundaries.
- Diagnostics redact document-controlled values in text/JSON/stderr; TLS verification remains enabled for explicitly requested URL checks.
- Calendar-dependent legacy test fixture. Public runtime excludes personal settings, traces, tests and caches.

### Compatibility and limitations

- Existing knowledge bases and other masters are not migrated automatically. Naming-v1 is opt-in for an existing base through an approved migration.
- No central allocation service or distributed lock; an appointed allocator coordinates each base. Unknown bases limit global uniqueness claims.
- Default audit is read-only/offline; --json-out and --check-urls are explicit opt-ins. No cross-base wiki-link resolution.

## [0.1.0] - 2026-08-12

### Added

- Public-ready baseline of the `obsidian-memory` Agent Skill.
- Beginner onboarding with read-only discovery, an adaptive questionnaire, explained structure, approval gates, and safe migration boundaries.
- Four explicit skill modes: onboarding, maintenance, read-only query, and read-only audit.
- Onboarding reference with adaptive ready-to-use templates for root `AGENTS.md`, frontmatter, the single index, lifecycle owners, base rules, and the preliminary setup proposal.
- Read-only structural inventory and validation CLI with stable counters and redacted sensitive-data candidates.
- Structural validation of required file and directory types, plus content-free reporting of unrecognized index lines.
- Verified exact path inventories in setup proposals so displayed object totals cannot diverge from the proposed scope.
- Cross-platform, standard-library-only link auditor.
- Wikilink heading and block-reference validation plus binary Obsidian embed resolution.
- English and Russian documentation, MIT licensing, contribution and security policies.
- Regression, CLI, onboarding, packaging, privacy, and metadata contract tests.
- CI matrix for Ubuntu, macOS, and Windows on Python 3.9 and 3.14.

### Fixed

- Reject auditor symlinks, Markdown targets, and index paths that resolve outside their confirmed project or vault boundary.
- Redact raw link and stale-index target values from diagnostics while preserving existing counters and exit codes.
- Prevent Python bytecode caches created during test discovery from contaminating repository contract checks in CI.

[Unreleased]: https://github.com/RomanovVIII/st67-obsidian-memory/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/RomanovVIII/st67-obsidian-memory/releases/tag/v0.2.0
[0.1.0]: https://github.com/RomanovVIII/st67-obsidian-memory/releases/tag/v0.1.0
