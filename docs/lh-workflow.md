# Long-horizon agent runs on GitHub Actions

How the repo runs an agent that keeps working across many runs without carrying its whole history. Files live in [`.lh/`](../.lh/README.md) and [`.github/workflows/`](../.github/workflows/).

## Why

The product is server-side video ad campaign automation: generate video variants, run campaigns, collect signals, A/B and A/A test, produce the next day's content. That loop runs for days. So does the agent that builds and maintains it. An agent whose context grows with every run slows down, costs more, and trusts stale facts. This workflow gives the agent one small mutable state file it must rewrite each run, plus deterministic guardrails around it.

## Shape

```
Issue gets label lh:<target> (`issues.labeled`, including at create), comment /lh, or manual dispatch
  -> small lh-<target>.yml caller
  -> lh-target.yml (shared guard: right label, right author, not a PR thread)
  -> lh-run.yml (reusable, target=<target>)
       checkout without credentials
       resume branch lh/web/issue-<n> if it exists, else create it
       compose prompt = prompt.md + state.md + issue + last K logs
       install Cursor CLI, run `agent -p --force --trust` (file edits only)
       discard any edits under .github/ .cursor/ .lh/bin/
       enforce state.md contract, restore previous on violation
       run .lh/web/checks.sh (cannot be skipped)
       write .lh/log/<run-id>.md, prune to K
       commit, push branch, open or update PR against the run's base ref
       comment on the issue; open an approval issue if the agent requested one
       fail the job if checks failed (work is still published)
```

## Long-horizon rules

- **Mutable, bounded state.** `state.md` has six fixed sections (Goal, Current plan, Done, Open, Decisions, Dropped), at most 80 lines. The agent rewrites it from scratch every run. A step checks the contract and throws the rewrite away if it is broken. Full history lives in git.
- **Small fixed context.** A run sees only the prompt, the issue, the state, and the last K run logs (K=5). Never the log directory, never earlier issues.
- **Explicit drop.** The `Dropped` section is where the agent writes what it stopped tracking and why it is safe. Pruned logs are gone from the tree; the agent is told which ones will fall off so it can fold them into Decisions or Dropped first.
- **Self-improvement through review.** The agent may edit its own `prompt.md`. The edit rides in the PR and only applies after merge, so a bad instruction cannot brick the next run.
- **Continuity before merge.** If the PR for an issue is open, the next run for that issue checks out the PR branch, so `state.md` carries over even before a human merges.

## Safety

- Agent step gets only `CURSOR_API_KEY`. `actions/checkout` runs with `persist-credentials: false`, so there is nothing to push with. The publish step puts the token on the push URL explicitly.
- CLI permissions in [`.cursor/cli.json`](../.cursor/cli.json) (project-level path per the [Cursor CLI docs](https://cursor.com/docs/cli/reference/permissions)) deny `Shell(git)`, `Shell(gh)`, `Shell(rm)`, `Shell(curl)`, `Shell(bash)`, and writes to `.github/**`, `.cursor/**`, `.lh/bin/**`, `.lh/log/**`, `.env*`. The prompt repeats the rules. A deterministic step reverts any edit under `.github/` or `.cursor/` before commit regardless.
- Workflow permissions: `contents: write`, `pull-requests: write`, `issues: write`. Nothing else.
- Never pushes to `main`. Two guards refuse if the work branch equals the default branch.
- `/lh` comments only count from OWNER, MEMBER, or COLLABORATOR.
- One run per target and issue at a time (`concurrency: lh-<target>-<issue>`).
- `NIMBLE_API_KEY` is exposed only to the `nimble` agent and its deterministic checks; offline checks do not require it.

## Inputs

`lh-run.yml` (`workflow_call`): safe `.lh/<target>` directory name, `issue_number` (0 for manual), `instruction` (text after
`/lh`), `model` (default `composer-2.5`; falls back to `auto` if unavailable), `state_max_lines` (80), `keep_logs` (5).
Secrets: required `CURSOR_API_KEY`; optional `NIMBLE_API_KEY`.

## Setup

- Repo secret `CURSOR_API_KEY` (present).
- Repo secret `NIMBLE_API_KEY` for live Nimble tasks.
- Target labels: `lh:web`, `lh:nimble` (later `lh:bfl`).
- Approval label: `lh:approval`. Target owners live in `.lh/owners.json`.
- Repo setting "Allow GitHub Actions to create and approve pull requests" must be on, or the publish step falls back to a compare link in the issue comment.
- Issue and comment triggers only fire from the default branch. `workflow_dispatch` can target any branch that has the workflow file.

## Routing and approvals

An issue gives an agent a task by carrying exactly the target label used by its caller. Add a target with one
`.lh/<target>/{prompt.md,state.md,checks.sh}` folder, one small caller copied from `lh-nimble.yml`, one owner entry, and one label;
shared workflow logic does not change.

For a proposal that would spend money, change a marketing schema, or publish content, the agent writes
`.lh/<target>/approval-request.md`. The deterministic runner removes it before commit, opens `Approval needed: <summary>` with
`lh:approval` and `lh:<target>`, assigns the configured owner (repository owner fallback), links the PR, and comments the issue link
on the PR. An assignee comments `/approve` on that issue; `lh-approve.yml` verifies assignment and squash-merges the linked PR.
