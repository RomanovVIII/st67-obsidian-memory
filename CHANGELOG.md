# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) after its first release.

## [Unreleased]

### Changed

- Updated GitHub Actions checkout and Python setup steps to their Node.js 24-compatible v7 releases.

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

[Unreleased]: https://github.com/RomanovVIII/st67-obsidian-memory/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/RomanovVIII/st67-obsidian-memory/releases/tag/v0.1.0
