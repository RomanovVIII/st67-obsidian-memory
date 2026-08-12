# Security Policy

## Supported versions

The project is currently `Unreleased`; there is no supported public release yet. Security fixes will be applied to the current development line until a versioned support policy is published.

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. When the future GitHub repository enables private vulnerability reporting, use that private channel and include affected files or versions, reproduction steps, impact, and any suggested mitigation.

This local baseline has no public reporting channel. Publication and its disclosure channel are separate future actions.

## Security boundaries

The runtime auditors are designed to read local project, Markdown, and attachment paths without modifying the inspected project or vault, accessing the network, or launching external processes. They have no third-party runtime dependencies. The structure inventory reports only relative paths and finding categories; it does not print suspected secret values or the contents of unrecognized index lines.

Onboarding does not install Obsidian, alter application settings, move or delete ambiguous material, replace an existing `AGENTS.md`, or create recovery infrastructure without separate approval. The root template is used only for a missing file or as a checklist of separately approved compatible additions. Treat any change to these boundaries as security-sensitive and add focused regression coverage.
