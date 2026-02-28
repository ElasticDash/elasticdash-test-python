Repository Steering & AI Contributor Guide
=========================================

Purpose
-------
Provide a clear, repeatable workflow for coding AI agents that manage and modify this repository while keeping a human in the approval loop at all times.

High-Level Expectations
-----------------------
- Act as a cautious collaborator: minimize churn, avoid surprises, and preserve user-owned changes.
- Default to small, reviewable increments; avoid speculative or wide-ranging edits without explicit direction.
- Keep communication concise, factual, and action-oriented.
- You are in macOS, so run `source .venv/bin/activate` to use the virtual environment if it exists; avoid global package installs.

Mandatory Plan & Approval Gate
------------------------------
- Before making any code or docs changes, **draft a plan** describing scope, files to touch, and intended steps. The plan should be saved in the markdown file './.temp/plan.md'.
- **Request human approval** for the plan and wait until approval is granted before proceeding with any edits.
- If new information or unexpected changes require a different approach, **update the existing plan**, highlight the differences, and request approval again.
- If an entirely new plan is required, **remove the old plan**, present the new one, and seek approval before continuing.

Change Execution Workflow (post-approval)
-----------------------------------------
1. Re-read relevant files in batches to refresh context and confirm nothing diverged from the approved plan.
2. Implement changes exactly as approved; flag any deviations and pause for guidance.
3. Keep edits minimal and localized; avoid drive-by refactors unless specifically requested.
4. Add or adjust tests when behavior changes; prefer `pytest` in `tests/` for coverage.
5. Run applicable checks (formatters/linters/tests) when possible; report what was run and any results.
6. Summarize outcomes with file and line references, describe side effects/risks, and propose next steps if needed.

Coding & Repo Practices
-----------------------
- Python style: favor readability; add short comments only for non-obvious logic.
- Environments: use the repo’s virtualenv if present (`.venv`), avoid global installs.
- Testing: prefer `pytest`; keep new tests fast and deterministic.
- Documentation: update relevant docs when altering behavior or interfaces.
- Avoid destructive git operations; never revert user changes unless explicitly instructed.

Communication Norms
-------------------
- Ask for clarification only when necessary; suggest sensible defaults to accelerate decisions.
- When presenting changes, lead with findings/impacts before summaries; include risks and testing status.
- Keep responses concise and scoped to the request; no excessive formatting.

Plan Template (copy/paste)
--------------------------
- Goal: what will change and why.
- Scope: bullets of the change boundaries; note any out-of-scope areas.
- Files/areas to touch: list expected files or directories.
- Steps: ordered list of actions with checkboxes (e.g., - [ ] Step 1); keep it short.
- Risks/unknowns: call out uncertainties or potential impacts.
- Testing: what you plan to run (e.g., `pytest tests/...` or "none").
- Approval: explicitly request human approval before execution.

Example
-------
- Goal: Add plan template section to steering doc for AI agents.
- Scope: Update .github/copilot-instructions.md only; no code changes.
- Files/areas to touch: .github/copilot-instructions.md.
- Steps: 
  - [ ] Re-read current guide; 
  - [ ] Append plan template and example; 
  - [ ] Keep tone concise; 
  - [ ] Summarize edit.
- Risks/unknowns: none.
- Testing: none (docs only).
- Approval: request and wait for human approval before editing.
