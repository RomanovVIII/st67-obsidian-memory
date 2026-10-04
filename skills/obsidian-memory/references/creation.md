# Create/design a base

Inspect only the prospective root, existing entry/rules and relevant source material. Distinguish a new base from an established schema. Resolve only missing choices: scope/owner, root, permanent namespace and designated allocator, participating bases and optional parent. Use interview questions only for unresolved decisions.

For a new base, read [naming-and-numbering.md](naming-and-numbering.md) and the relevant [file-templates.md](file-templates.md) sections. The minimum is `IDX_<BASE>.md`, `CFG_<BASE>.json` and `LOG_<BASE>-<NNNN>_YYYY-MM.md` from the first journaled event; initial creation is normally that event. Do not create empty monthly logs. TODO is created at the first unresolved question; state cards, plans, problems, decisions, research, reports, procedures and material folders appear only as needed.

Shared maintenance and Link Workflow are in the installed skill, not mandatory duplicated RUL files. The index identifies its canonical maintenance entry (the skill plus any base-specific rule) and enabled owners. Store paths, exceptions, allocator, hierarchy and lifecycle parameters in CFG/index; procedures peculiar to the base may have RUL records. Explain each proposed file and enumerate exact paths when presenting a setup proposal.

A direct implementation instruction authorizes its necessary writes; do not ask again for the same permission. A design-only request produces a proposal. Agree separately on scope expansion, replacing existing agent rules and deleting valuable source materials. Never replace an existing AGENTS wholesale. Adapt [agent-integration.md](agent-integration.md) only if integration is requested. Preserve source code, dependencies, builds, test outputs and secrets outside managed knowledge. Do not create optional owners from a template checklist.

Register each managed Markdown document exactly once in the index, honoring exclusions; attachments use real meaningful links. After creation run the structural auditor with `--profile naming-v1` and a full link audit, then review meaning and ownership. Existing legacy onboarding is only a compatibility reference, not the new default.
