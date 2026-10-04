# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| 0.1.x | Compatibility baseline; upgrade recommended |
| < 0.1 | No |

## Reporting

Use GitHub private vulnerability reporting; do not publish sensitive details in ordinary issues. Include version, reproduction, impact and suggested mitigation without credentials.

## Runtime boundaries

Both auditors read local documents without writing files or contacting the network by default. Only an explicitly requested link-auditor --json-out writes a JSON report within memory_root. Only explicit --check-urls enables HTTP(S) reachability checks under configured URL policies; TLS certificates are verified. No external processes or third-party runtime dependencies.

Default link boundary is the selected base. --vault-root may widen it only to an explicitly confirmed same-base vault; it is never permission to resolve neighboring knowledge bases. Comparison roots contribute filenames, never link targets. Resolved symlinks and input/index/config paths must remain inside their boundary. Unsafe links are diagnosed without reading external content. Sensitive inventory and text/JSON/stderr diagnostics do not echo raw link values, URL credentials, suspected secret values or unknown index-line content; source paths and original line numbers remain useful.

Audits validate mechanics, not factual truth, acceptance or infrastructure health. Names/counters are not an allocation service: one appointed owner allocates each base's IDs, and asynchronous sync does not provide a distributed lock. Unknown/inaccessible bases limit uniqueness guarantees.

Task instructions authorize their necessary knowledge updates. Scope expansion, structural redesign and irreversible deletion of valuable originals require agreement. Completion cleanup is limited to confirmed task roots; preserve useful/unfinished/recovery/foreign/unclear material. Raw deletion additionally requires a matching-checksum permanent original copy and no active references. No automatic archive or wholesale cleanup. Never store secrets in bases or distribution packages.
