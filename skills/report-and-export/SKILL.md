---
name: report-and-export
description: Use when analysis is complete and findings must be exported, summarized or handed to another person without overstating coverage.
version: 1.0.0
compatible_registry: "0.1.x"
tools: [analysis_get_report, evidence_get, evidence_list, report_generate, recipe_run]
---

# Report and export

Use this skill after a completed analysis job. The job must be `completed`;
`report_generate` fails for queued, running, failed or cancelled jobs.

## Workflow

1. Call `analysis_get_status` for the job. Stop if it is not `completed`.
2. Call `analysis_get_report`. Capture the report ID, artifact hash, stage list
   and `coverage.limitations`.
3. Call `evidence_list` for the project. Group evidence by kind and verify that
   every finding you plan to publish has at least one evidence ID.
4. Call `evidence_get` for the key records. Preserve authority, representation
   and confidence exactly.
5. Call `report_generate` with `format: "markdown"` for a human handoff or
   `"json"` for automation. Filenames are sanitized and written under
   `<workspace>/exports/<project_id>/`.
6. Return the exported path and a concise summary.

## Reporting rules

- Lead with what is known, then state what is not known.
- Include the SHA-256 so the recipient can confirm the artifact identity.
- Keep findings in their original severity order.
- Never upgrade `inferred` to `observed`. Never describe filename heuristics as
  confirmed engine results.
- Do not include secrets, credentials, user data or proprietary source in an
  export unless the engagement explicitly permits it.
- If the workspace is shared, confirm the export destination before writing.

## Anti-Rationalization Gate
- If `analysis_get_status` is not `completed`, stop immediately — do not summarize partial or cached runs as complete.
- Every finding in the final export must map to at least one `evidence_get` record; drop or mark unverified any claim lacking evidence.

## Project overview

For a status update that does not need a full report, run recipe
`project_overview` with the project ID. It returns the project, artifact count,
artifact list and a bounded evidence sample.
