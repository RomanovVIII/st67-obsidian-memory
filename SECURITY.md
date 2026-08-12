# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| < 0.1 | No |

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. Use this repository's GitHub private vulnerability reporting channel and include affected files or versions, reproduction steps, impact, and any suggested mitigation.

## Security boundaries

The runtime auditors are designed to read local project, Markdown, and attachment paths without modifying the inspected project or vault, accessing the network, or launching external processes. They have no third-party runtime dependencies. The structure inventory reports only relative paths and finding categories; it does not print suspected secret values or the contents of unrecognized index lines.

Onboarding does not install Obsidian, alter application settings, move or delete ambiguous material, replace an existing `AGENTS.md`, or create recovery infrastructure without separate approval. The root template is used only for a missing file or as a checklist of separately approved compatible additions. Treat any change to these boundaries as security-sensitive and add focused regression coverage.
