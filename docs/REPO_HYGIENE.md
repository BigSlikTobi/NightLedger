# Repo Hygiene Policy (Issue #66)

This document defines the repo hygiene policy for stale branches and generated
artifacts.

Closure track for cleanup umbrella #62: Issue #66.
Operationalization update: SI-62B (#89).

## Branch Inventory Snapshot (2026-02-17)

Audit commands used:

```bash
git branch -r --merged origin/main --format='%(refname:short)' | sort
git branch -r --no-merged origin/main --format='%(refname:short)' | sort
for b in $(git for-each-ref refs/remotes/origin --format='%(refname:short)' | rg -v '^origin$|^origin/HEAD|^origin/main$'); do
  printf '%s|' "$b"
  git rev-list --left-right --count origin/main..."$b"
done
```

Merged into `origin/main` (deletion candidates, `right=0` in ahead/behind
check):

- `origin/Coder/backend_triage_inbox_orchestration`
- `origin/Coder/issue-33-journal-projection-tests`
- `origin/Coder/issue-35-journal-docs`
- `origin/Coder/issue-53-integration-timing-verification`
- `origin/Coder/issue-54-demo-script-handoff`
- `origin/Coder/issue-59-ui-live-api-mode`
- `origin/Coder/issue-63-ci-bootstrap-parity`
- `origin/Coder/issue-64-docs-source-of-truth`
- `origin/Coder/issue30-restart`
- `origin/Coder/issue32-journal-endpoint`
- `origin/Coder/issue34-journal-api-tests`
- `origin/chore/hackathon-prep`
- `origin/docs/update-agent-constitution`
- `origin/feat/impl-business-rules-issue-11`
- `origin/feat/journal_projection_serrvice`
- `origin/feat/state_machine`
- `origin/feat/status_endpoint`
- `origin/feat/ui-approvals-7`
- `origin/feat/ui-journal-timeline-6`
- `origin/feature/payload_validation`
- `origin/issue65`

Not yet merged into `origin/main` (retain for now):

- `origin/Integration/triage_inbox_phase1` (`22` behind, `2` ahead)
- `origin/feature/API_contract_spec` (`71` behind, `1` ahead)
- `origin/fix/base-url-autostart-sync` (`22` behind, `1` ahead)
- `origin/chore/sync-now` (`113` behind, `3` ahead)
- `origin/chore/sync-now-2` (`102` behind, `1` ahead)

Proposed deletion batch (after human confirmation and safety checks):

- all merged candidates listed above, excluding protected branches.

Execution status: deferred.

Reason:

- remote branch deletion is destructive and requires explicit maintainer
  confirmation for this repository.

Approved operator command template once confirmed:

```bash
git push origin --delete <branch-name>
```

## Operational Workflow (SI-62B)

Branch hygiene execution remains operator-confirmed and non-destructive by
default.

Inventory command:

```bash
bash tasks/branch_hygiene_inventory.sh
```

Guardrails:

- dry-run output only; no remote deletion execution.
- protected refs (`origin/main`, `origin/HEAD`, `origin`) are excluded.
- deletion commands are output as templates for a human operator to run.

## Branch Retention Policy

- `Coder/` branches are short-lived issue branches.
- `feat/`, `fix/`, `feature/`, `docs/`, and `chore/` branches follow the same
  merge-then-delete lifecycle unless explicitly marked long-lived.
- Delete merged remote branches within 7 days.
- Keep unmerged branches only while there is an active PR or active issue work.
- Never delete `main`.
- Never delete `origin/HEAD`.
- Require ahead/behind check before deletion.
- Require PR merge confirmation before deletion.

## Generated Artifact History Strategy

Decision: keep git history as-is (no rewrite).

Why:

- history rewrite changes SHAs and increases collaboration risk.
- existing generated artifacts are historical and currently not tracked in HEAD.
- preserving immutable history aligns with transparent auditability.

Evidence from audit:

- `git log --all --name-only --pretty=format: | rg "(__pycache__/|\.pyc$|\.pyo$|\$py\.class$)"` shows historical generated artifacts in old commits.
- `git ls-files | rg "(__pycache__/|\.pyc$|\.pyo$|\$py\.class$|\.pytest_cache/)"` returns no tracked generated artifacts in current HEAD.

History rewrite guardrail:

- consider history rewrite only for legal/security events that require
  repository redaction; otherwise avoid rewrite.

## .gitignore Coverage Check

Current generated-artifact protections remain aligned with daily workflows:

- `__pycache__/`
- `*.py[cod]`
- `*$py.class`
- `.pytest_cache/`
- `coverage`
- `dist`
- `node_modules`
