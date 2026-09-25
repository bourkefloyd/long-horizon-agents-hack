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
  agents/              (later) same three files for the decision agents target
```

## Trigger a run

- Open an issue with the `lh:web` label, or add the label to an existing issue.
- Comment `/lh <instruction>` on an `lh:web` issue (owner, member, or collaborator only). The text after `/lh` is a one-shot instruction for that run.
- Manual: Actions > "LH web" > Run workflow. `issue_number` 0 means no issue comment; the PR still opens.

Each run works on branch `lh/web/issue-<n>` (or `lh/web/manual-<run-id>`), opens or updates a PR against the branch the workflow ran on, and comments on the issue. Nothing is pushed to `main`. Runs for the same issue queue behind each other (`concurrency`).

## The state file

`state.md` has exactly six H2 sections in this order: Goal, Current plan, Done, Open, Decisions, Dropped. Max 80 lines, 200 chars per line, no log or history. The agent rewrites it from scratch every run. If the rewrite breaks the contract, the workflow restores the previous version and records the rejection in the run log, so the next run sees what went wrong.

Each run's context is only: `prompt.md`, the issue text, `state.md`, and the last K run logs. Full history is in git, not in the prompt.

## Self-improvement

The agent may edit `prompt.md` and `state.md`. Those edits ride in the same PR as the code and take effect only after a human merges. A bad edit cannot brick the next run because it is reviewed first.

## Add a target

1. Create `.lh/<target>/{prompt.md,state.md,checks.sh}` (copy `web/`, keep the six sections).
2. Add `.github/workflows/lh-<target>.yml` that calls `lh-run.yml` with `target: <target>`.
3. Add `web|agents|<target>` to the `Validate inputs` step in `lh-run.yml`.
4. Create the `lh:<target>` label.
