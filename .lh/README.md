# .lh: long-horizon agent state

Working memory and instructions for the GitHub Actions agent runs. Design note: [docs/lh-workflow.md](../docs/lh-workflow.md).

## Layout

```
.lh/
  README.md            this file
  bin/                 deterministic helpers run by the workflow (agent cannot write here)
    check-state.sh     enforce the state.md contract (sections, line cap)
    compose-prompt.sh  build the exact prompt one run sees
    prune-logs.sh      keep the newest K run logs
  log/                 one short summary per run, <run-id>.md, pruned to K (default 5)
  web/                 target: web surface of the campaign automation
    prompt.md          what "improve" means for this target; the agent may edit it
    state.md           the agent's only memory across runs; rewritten every run
    checks.sh          deterministic checks the agent cannot skip
  nimble/              target: Thomas's local-news ad concept and script generator
  owners.json          target -> GitHub owner for approval issues
```

## Give an agent a task

The target is selected by one label: `lh:web` or `lh:nimble` (later, `lh:bfl`).

1. Open an issue describing one reviewable task and add its `lh:<target>` label, or add the label to an existing issue.
2. The target workflow starts on issue creation/labeling. To continue the same task, comment `/lh <instruction>` on that issue
   (owner, member, or collaborator only); the text after `/lh` applies to that run.
3. Manual fallback: Actions > "LH <target>" > Run workflow. `issue_number` 0 opens a PR without commenting on an issue.

Each run works on `lh/<target>/issue-<n>` (or `lh/<target>/manual-<run-id>`), opens or updates a PR, and comments on the
task issue. Nothing is pushed to `main`. Runs for the same target and issue queue behind each other.

## The state file

`state.md` has exactly six H2 sections in this order: Goal, Current plan, Done, Open, Decisions, Dropped. Max 80 lines, 200 chars per line, no log or history. The agent rewrites it from scratch every run. If the rewrite breaks the contract, the workflow restores the previous version and records the rejection in the run log, so the next run sees what went wrong.

Each run's context is only: `prompt.md`, the issue text, `state.md`, and the last K run logs. Full history is in git, not in the prompt.

## Self-improvement

The agent may edit `prompt.md` and `state.md`. Those edits ride in the same PR as the code and take effect only after a human merges. A bad edit cannot brick the next run because it is reviewed first.

## Add a target

1. Create `.lh/<target>/{prompt.md,state.md,checks.sh}`; keep the six state sections and make checks deterministic.
2. Copy a small caller such as `.github/workflows/lh-nimble.yml`, change its name and `target`, and keep `secrets: inherit`.
   Shared label/comment routing is in `lh-target.yml`; execution is in `lh-run.yml`, which accepts any safe target directory name.
3. Add the owner to `.lh/owners.json` and create the `lh:<target>` label.

## Human approvals

An agent that proposes spending money, changing a marketing schema, or publishing content writes
`.lh/<target>/approval-request.md` alongside the proposed change. The first non-empty line is a short summary; it must contain no
secret or private content. The runner removes that file before commit, opens an `lh:approval` + `lh:<target>` issue assigned from
`owners.json`, links the PR, and comments the approval issue on the PR. An assignee reviews the PR and comments `/approve` on the
approval issue; `lh-approve.yml` verifies the assignee and squash-merges the linked PR. No secret belongs in an issue.
