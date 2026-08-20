# Working agreement

How this project moves from a backlog to shipped code. The point of writing it down is that
the process must not depend on anyone — human or assistant — remembering it between sessions.

## The artefacts

| Artefact | Role |
|---|---|
| `docs/requirements/ai-budget-agent-brd-v1.1.md` | The business requirements. Changes only when the business changes its mind. |
| `docs/planning/backlog.yaml` | **The source of truth for the plan.** Epics, features, tasks. |
| `docs/planning/backlog.md` | A generated, readable view of the YAML. Never edited by hand. |
| GitHub issues / milestones / board | A projection of the YAML, produced by `scripts/backlog_sync.py`. |
| `docs/adr/` | Decisions that constrain later work, with the reasoning that produced them. |

GitHub is downstream. Editing an issue body in the web UI is not how the plan changes — the
next sync overwrites it. Change the YAML, commit, sync.

## Why tasks are not all written up front

Epics carry features from the outset, because features are derived from the BRD and are
therefore as stable as the BRD is. Tasks are different: a task says *how*, and how depends on
what the codebase already looks like. A task written today for an epic three months out would
describe a system that will not exist by then.

So an epic is groomed — decomposed into tasks — immediately before work on it starts.
Ungroomed epics carry the `needs-grooming` label and `groomed: false` in the YAML.

## Phases: what ships, and what is only planned

Epics carry `phase: 1` or `phase: 2`. Phase 1 is the BRD scope and is the only work that
counts as delivery. Phase 2 is commercial scope written down deliberately early — not to be
worked on, but so that phase-1 decisions are made knowing what is meant to come after, since
the expensive mistakes here are the ones that need unpicking later (who owns a receipt, how a
receipt arrives, what a line item records).

Everything under a phase-2 epic is labelled `post-mvp` on sync, so the board filters down to
phase 1. Nothing from phase 2 is picked up while phase-1 epics remain open; promoting one
means changing its `phase` in the YAML and re-syncing, which makes the decision a commit
rather than a mood.

## The cycle

**1. Groom the epic.** Re-read its BRD section, look at what the code actually does now, and
write the tasks into `backlog.yaml` under each feature. Set `groomed: true`. Run
`scripts/backlog_sync.py render && scripts/backlog_sync.py sync`. Commit both the YAML and the
regenerated markdown.

**2. Work the tasks.** The unit of work is a task, unless the ask is a whole feature — then
the unit is the feature, so its tasks land together instead of fighting each other across
several narrow branches:

```
git switch -c task/F1-2-3-refresh-token-rotation   # one task
git switch -c feature/F1-2-consent-flow            # a whole feature, all its tasks
```

A single-task branch closes one issue through one PR. A feature branch implements every
task under that feature as one consistent pass — read all their acceptance criteria first,
reconcile whatever overlaps, and commit as the work naturally divides rather than forcing
one commit per task — then closes all of their issues through one PR. Never do this for a
whole epic; an epic is still worked feature by feature.

The pull request body names every issue it closes (`Closes #42`, and one `Closes #N` line
per additional task issue at feature scope) and the BRD requirement IDs it satisfies, so
tracing a line of code back to a business requirement is mechanical rather than
archaeological. The `Closes #N` lines are not just documentation — they are what both
GitHub's own issue-closing and the board automation below key off, for every issue named.

### Board columns and how a card moves between them

| Column | Entered when | How |
|---|---|---|
| Todo | Issue created | Automatic, set by `backlog_sync.py sync` |
| In Progress | Someone starts the task | Manual — drag the card, or set it before opening the branch |
| Review | A non-draft PR closing the issue is opened | Automatic, `.github/workflows/pr-board-sync.yml` |
| Done | The PR is merged, or the issue is closed directly | Automatic, the board's built-in "Pull request merged" / "Item closed" workflow |

The Review transition needs GitHub's `closingIssuesReferences` to resolve, which only happens
when the PR body actually contains a closing keyword (`Closes`, `Fixes`, `Resolves`) followed
by the issue number — a PR that merely mentions the issue number will not move its card.

**3. Close out the epic.** When its features are done, review what the work taught us. If a
feature in a later epic is now wrong, unnecessary, or shaped differently than planned — edit
the YAML and re-sync. Record anything that constrains future work as an ADR.

## Adjusting the plan mid-flight

This is expected, not exceptional. Discovering that a planned feature is wrong is the work
producing information, which is what it is supposed to do. The rule is only that the
adjustment lands in `backlog.yaml` in a commit, so the reasoning survives in git history
rather than in someone's memory of a conversation.

## Commands

```
scripts/backlog_sync.py render          # regenerate backlog.md from the YAML
scripts/backlog_sync.py sync --dry-run  # preview what would change on GitHub
scripts/backlog_sync.py sync            # apply labels/milestones/issues AND add
                                         # any new card to the board — this is the
                                         # one command that keeps the board current
scripts/backlog_sync.py project         # board-only: layout, Status columns, and
                                         # re-adding anything sync's board step was
                                         # skipped for (e.g. a --dry-run session).
                                         # Not part of the normal grooming loop.
```

`sync` always ends by adding every backlog issue to the board (see [F0.8.1's PR][pr-132]
for the incident that made this the default — a new issue created by `sync` alone used
to sit off the board until someone remembered to run `project` separately). Running
`sync` is enough; there is no second step to remember.

[pr-132]: https://github.com/phase1912/budget-planner/pull/132

The `project` subcommand needs a token scope beyond the default:

```
gh auth refresh -h github.com -s project,read:project
```

## One-time board setup

Two things GitHub does not expose through the API and so cannot be scripted — do these once
in the board UI (⋯ menu → Workflows):

1. **Pull request merged → Status: Done**, and **Item closed → Status: Done** — the built-in
   workflows that close the Review → Done gap without a custom Action.
2. **Auto-add to project**, filtered to this repository — so pull requests themselves (not
   just issues) land on the board when opened, which `pr-board-sync.yml` needs in order to
   find and move them if they are ever tracked as cards in their own right.

## Branch cleanup

The repository has **Automatically delete head branches** enabled (repo Settings →
General), so a merged PR's branch disappears from GitHub on its own — no manual
deletion step.

That only removes the branch on the remote. The local clone keeps a now-dangling
reference until it is told otherwise, so after a merge:

```
git switch main && git pull
git fetch --prune          # drops local tracking refs for branches deleted on the remote
git branch -d task/<name>  # removes the local branch itself, if git didn't already
```

## Board automation secret

`pr-board-sync.yml` moves a PR's closed issues to Review using `gh`, which needs a token with
the `project` scope — the default `GITHUB_TOKEN` Actions provides cannot write to Projects v2.
Create a classic PAT with `repo` and `project` scopes and store it as the repository secret
`PROJECTS_TOKEN` (Settings → Secrets and variables → Actions).
