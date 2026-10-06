#!/usr/bin/env python3
"""Sync docs/planning/backlog.yaml into GitHub milestones, labels and issues.

The YAML file is authoritative; GitHub is a projection of it. Every issue carries a
hidden marker comment (``<!-- backlog-key: F0.1 -->``) which is how a re-run recognises
what it already created, so the script is safe to run repeatedly: existing issues are
updated in place rather than duplicated.

Usage:
    scripts/backlog_sync.py render            # regenerate docs/planning/backlog.md
    scripts/backlog_sync.py sync --dry-run    # show what would change
    scripts/backlog_sync.py sync              # create/update labels, milestones, issues,
                                              # and add them to the Projects v2 board
    scripts/backlog_sync.py project           # (re)configure the board on its own: layout,
                                              # Status columns, and adding any issue missed
                                              # by sync — (requires: gh auth refresh -s project)
    scripts/backlog_sync.py pr-review --pr 42 # move #42's closed issues to Review
                                              # (called by .github/workflows/pr-board-sync.yml)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "planning" / "backlog.yaml"
MARKDOWN = ROOT / "docs" / "planning" / "backlog.md"
MARKER = re.compile(r"<!-- backlog-key: (?P<key>[^ ]+) -->")
SCOPES = {"diploma": "Diploma", "out-of-scope": "Out of scope"}
"""Epic scope -> the option it takes in the board's Scope field; the key is also the label."""
SCOPE_FIELD = "Scope"


# --------------------------------------------------------------------------- gh


def gh(*args: str, stdin: str | None = None) -> Any:
    """Run a gh command, returning parsed JSON when the response has a body."""
    result = subprocess.run(
        ["gh", *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed:\n{result.stderr.strip()}")
    out = result.stdout.strip()
    return json.loads(out) if out else None


def gh_api(path: str, method: str = "GET", payload: dict | None = None) -> Any:
    args = ["api", "-X", method, path]
    if payload is not None:
        args += ["--input", "-"]
    return gh(*args, stdin=json.dumps(payload) if payload is not None else None)


def gh_paginate(path: str) -> list[dict]:
    return gh("api", "--paginate", path) or []


# ------------------------------------------------------------------- backlog IO


def load() -> dict:
    with BACKLOG.open() as handle:
        return yaml.safe_load(handle)


def task_key(feature_key: str, index: int, task: dict | None = None) -> str:
    """Return a task's backlog key, preferring the explicit `key:` it declares.

    The key is what `sync` matches an existing GitHub issue against, so it has to
    survive the task moving position inside its feature. Deriving it from the
    index alone means deleting a task re-points every issue below it at the wrong
    task and orphans the last one — silently, because the marker still parses.

    The positional fallback stays for tasks written but not yet synced; anything
    that already owns an issue carries an explicit key.
    """
    if task is not None and task.get("key"):
        return str(task["key"])
    return f"{feature_key}.{index}"


def depends_line(refs: list[str] | None, numbers: dict[str, int]) -> str | None:
    """Render the blocked-by bullet, resolving backlog keys to issue numbers.

    Returns None when nothing is declared, so the bullet is absent rather than
    present-and-empty. A key with no issue yet — a dependency pointing into an
    ungroomed epic — renders as the bare key: the constraint is still stated,
    which is the whole point of recording it before the work is decomposed.
    """
    if not refs:
        return None
    rendered = [f"#{numbers[r]} ({r})" if r in numbers else r for r in refs]
    return f"- **Blocked by:** {', '.join(rendered)}"


def clean(text: str | None) -> str:
    """Collapse YAML folded-block whitespace back into flowing prose."""
    return " ".join((text or "").split())


def requirement_line(refs: list[str] | None) -> str:
    return ", ".join(refs) if refs else "—"


def phase_of(epic: dict) -> int:
    """Where an epic's requirement came from: 1 for the BRD, 2 for scope beyond it.

    Informational only since the diploma split: what gets built is `scope_of`.
    """
    return int(epic.get("phase", 1))


def phase_line(epic: dict) -> str:
    if phase_of(epic) == 1:
        return "- **Phase:** 1 — BRD scope"
    return f"- **Phase:** {phase_of(epic)} — beyond the BRD"


def scope_of(epic: dict) -> str:
    """Whether an epic is built for the diploma project or left out of it.

    Scope is an epic-level decision: its features and tasks inherit it. Every epic
    must state one, so nothing lands on the board without an answer.
    """
    scope = epic.get("scope")
    if scope not in SCOPES:
        raise SystemExit(f"{epic['key']}: scope must be one of {sorted(SCOPES)}, got {scope!r}")
    return str(scope)


def scope_line(epic: dict) -> str:
    if scope_of(epic) == "diploma":
        return "- **Scope:** diploma project"
    return "- **Scope:** out of scope for the diploma project"


def scope_labels(epic: dict) -> list[str]:
    return [scope_of(epic)]


# ------------------------------------------------------------------ issue bodies


def epic_body(epic: dict, feature_numbers: dict[str, int]) -> str:
    lines = [
        f"<!-- backlog-key: {epic['key']} -->",
        "**Epic**",
        "",
        f"- **BRD sections:** {requirement_line(epic.get('br'))}",
        phase_line(epic),
        scope_line(epic),
        f"- **Grooming:** {'decomposed into tasks' if epic.get('groomed') else 'features only — tasks are written when this epic is picked up'}",
        "",
        clean(epic.get("summary")),
        "",
        "### Features",
    ]
    for feature in epic["features"]:
        number = feature_numbers.get(feature["key"])
        ref = f"#{number}" if number else "(pending)"
        lines.append(f"- [ ] {ref} — {feature['key']} {feature['title']}")
    lines += [
        "",
        "---",
        f"Source of truth: [`docs/planning/backlog.yaml`](../blob/main/docs/planning/backlog.yaml) · "
        f"[BRD](../blob/main/docs/requirements/ai-budget-agent-brd-v1.1.md)",
    ]
    return "\n".join(lines)


def feature_body(feature: dict, epic: dict, epic_number: int | None,
                 task_numbers: dict[str, int], numbers: dict[str, int] | None = None) -> str:
    lines = [
        f"<!-- backlog-key: {feature['key']} -->",
        "**Feature**",
        "",
        f"- **Epic:** {f'#{epic_number}' if epic_number else ''} {epic['key']} {epic['title']}",
        f"- **BRD requirements:** {requirement_line(feature.get('requirements'))}",
        phase_line(epic),
        scope_line(epic),
    ]
    blocked = depends_line(feature.get("depends_on"), numbers or {})
    if blocked:
        lines.append(blocked)
    lines += [
        "",
        "### Intent",
        clean(feature.get("intent")),
    ]
    demo = clean(feature.get("demo"))
    if demo:
        lines += ["", "### Demonstrated by", demo]
    tasks = (feature.get("tasks") or []) if epic.get("groomed") else []
    if tasks:
        lines += ["", "### Tasks"]
        for index, task in enumerate(tasks, start=1):
            key = task_key(feature["key"], index, task)
            number = task_numbers.get(key)
            ref = f"#{number}" if number else "(pending)"
            lines.append(f"- [ ] {ref} — {task['title']}")
    else:
        lines += [
            "",
            "### Tasks",
            "_Not yet decomposed. Tasks are written when this epic is picked up, so that "
            "they reflect the codebase as it actually is at that point rather than as it was "
            "planned to be._",
        ]
    return "\n".join(lines)


def task_body(task: dict, key: str, feature: dict, feature_number: int | None,
              epic: dict, numbers: dict[str, int] | None = None) -> str:
    header = [
        f"<!-- backlog-key: {key} -->",
        "**Task**",
        "",
        f"- **Feature:** {f'#{feature_number}' if feature_number else ''} {feature['key']} {feature['title']}",
        f"- **BRD requirements:** {requirement_line(feature.get('requirements'))}",
        phase_line(epic),
        scope_line(epic),
    ]
    blocked = depends_line(task.get("depends_on"), numbers or {})
    if blocked:
        header.append(blocked)
    return "\n".join([
        *header,
        "",
        "### What to do",
        clean(task.get("detail")),
        "",
        "### Done when",
        "- [ ] Implemented and covered by tests",
        "- [ ] `docs/architecture/overview.md` and `domain-model.md` updated if this "
        "changes a component boundary, data flow or business rule (see CLAUDE.md)",
        "- [ ] Lint, type check and the full suite pass in CI",
        "- [ ] Merged via a pull request that closes this issue",
    ])


# ------------------------------------------------------------------------ render


def render_markdown(data: dict) -> str:
    lines = [
        "# Delivery backlog",
        "",
        "> Generated from [`backlog.yaml`](backlog.yaml) by `scripts/backlog_sync.py render`.",
        "> Edit the YAML, not this file.",
        "",
    ]
    total_features = sum(len(e["features"]) for e in data["epics"])
    total_tasks = sum(len(f.get("tasks") or []) for e in data["epics"] for f in e["features"])
    diploma = [e for e in data["epics"] if scope_of(e) == "diploma"]
    lines += [
        f"{len(data['epics'])} epics · {total_features} features · {total_tasks} tasks written so far.",
        "",
        f"{len(diploma)} epics are in the diploma project's scope; "
        f"{len(data['epics']) - len(diploma)} are planned but out of it.",
        "",
        "| Epic | Title | BRD | Features | Groomed | Phase | Scope |",
        "|---|---|---|---|---|---|---|",
    ]
    for epic in data["epics"]:
        lines.append(
            f"| {epic['key']} | {epic['title']} | {requirement_line(epic.get('br'))} "
            f"| {len(epic['features'])} | {'yes' if epic.get('groomed') else 'no'} "
            f"| {phase_of(epic)} | {SCOPES[scope_of(epic)]} |"
        )
    lines.append("")

    for epic in data["epics"]:
        lines += [
            "---",
            "",
            f"## {epic['key']} — {epic['title']}",
            "",
            f"**BRD sections:** {requirement_line(epic.get('br'))} · "
            f"**Phase:** {phase_of(epic)} · **Scope:** {SCOPES[scope_of(epic)]}",
            "",
            clean(epic.get("summary")),
            "",
        ]
        for feature in epic["features"]:
            blocked = feature.get("depends_on")
            lines += [
                f"### {feature['key']} — {feature['title']}",
                "",
                f"*Requirements: {requirement_line(feature.get('requirements'))}*"
                + (f" · *Blocked by: {', '.join(blocked)}*" if blocked else ""),
                "",
                clean(feature.get("intent")),
                "",
            ]
            demo = clean(feature.get("demo"))
            if demo:
                lines += [f"**Demonstrated by:** {demo}", ""]
            tasks = (feature.get("tasks") or []) if epic.get("groomed") else []
            if tasks:
                for index, task in enumerate(tasks, start=1):
                    blocked = task.get("depends_on")
                    suffix = f" _(blocked by: {', '.join(blocked)})_" if blocked else ""
                    lines.append(
                        f"- **{task_key(feature['key'], index, task)}** {task['title']} — "
                        f"{clean(task.get('detail'))}{suffix}"
                    )
                lines.append("")
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------------- sync


def sync_labels(repo: str, labels: list[dict], dry_run: bool) -> None:
    existing = {label["name"] for label in gh_paginate(f"repos/{repo}/labels?per_page=100")}
    for label in labels:
        if label["name"] in existing:
            if not dry_run:
                gh_api(f"repos/{repo}/labels/{label['name']}", "PATCH",
                       {"color": label["color"], "description": label["description"]})
            print(f"  label ~ {label['name']}")
        else:
            if not dry_run:
                gh_api(f"repos/{repo}/labels", "POST", label)
            print(f"  label + {label['name']}")


def sync_milestones(repo: str, epics: list[dict], dry_run: bool) -> dict[str, int]:
    existing = {m["title"]: m["number"]
                for m in gh_paginate(f"repos/{repo}/milestones?state=all&per_page=100")}
    numbers: dict[str, int] = {}
    for epic in epics:
        title = f"{epic['key']} — {epic['title']}"
        payload = {"title": title, "description": clean(epic.get("summary"))[:1000]}
        if title in existing:
            numbers[epic["key"]] = existing[title]
            print(f"  milestone ~ {title}")
        elif dry_run:
            print(f"  milestone + {title}")
        else:
            created = gh_api(f"repos/{repo}/milestones", "POST", payload)
            numbers[epic["key"]] = created["number"]
            print(f"  milestone + {title}")
    return numbers


def existing_issues(repo: str) -> dict[str, dict]:
    issues = gh_paginate(f"repos/{repo}/issues?state=all&per_page=100")
    index: dict[str, dict] = {}
    for issue in issues:
        if "pull_request" in issue:
            continue
        match = MARKER.search(issue.get("body") or "")
        if match:
            index[match.group("key")] = issue
    return index


def upsert(repo: str, key: str, title: str, body: str, labels: list[str],
           milestone: int | None, index: dict[str, dict], dry_run: bool) -> int | None:
    payload: dict[str, Any] = {"title": title, "body": body, "labels": labels}
    if milestone is not None:
        payload["milestone"] = milestone
    if key in index:
        number = index[key]["number"]
        if not dry_run:
            gh_api(f"repos/{repo}/issues/{number}", "PATCH", payload)
        print(f"  issue ~ #{number} {title}")
        return number
    if dry_run:
        print(f"  issue + {title}")
        return None
    created = gh_api(f"repos/{repo}/issues", "POST", payload)
    index[key] = created
    print(f"  issue + #{created['number']} {title}")
    return created["number"]


def backlog_keys(data: dict) -> set[str]:
    """Every key the YAML currently declares, across all three levels."""
    keys: set[str] = set()
    for epic in data["epics"]:
        keys.add(epic["key"])
        for feature in epic["features"]:
            keys.add(feature["key"])
            for i, task in enumerate((feature.get("tasks") or []) if epic.get("groomed") else [], start=1):
                keys.add(task_key(feature["key"], i, task))
    return keys


def report_orphans(data: dict, index: dict[str, dict]) -> None:
    """Report open issues whose backlog key no longer exists in the YAML.

    Removing a task from the plan leaves its issue behind: `upsert` only ever
    touches keys the YAML still declares, so the abandoned issue stays open with
    stale content and nothing points at it. Deliberately reports rather than
    closes — deciding that a dropped task is finished, superseded or merely
    deferred is a judgement call, not something a sync run should make.
    """
    declared = backlog_keys(data)
    orphans = [(key, issue) for key, issue in index.items()
               if key not in declared and issue.get("state") == "open"]
    if not orphans:
        return
    print("Orphans (open issues whose backlog key is gone from the YAML):")
    for _, issue in sorted(orphans):
        print(f"  ! #{issue['number']} {issue['title']}")
    print("  Close, re-key or restore each by hand — sync will not touch them again.")


def sync(data: dict, dry_run: bool) -> None:
    repo = data["project"]["repo"]
    print("Labels:")
    sync_labels(repo, data["labels"], dry_run)
    print("Milestones:")
    milestones = sync_milestones(repo, data["epics"], dry_run)
    print("Issues (pass 1 — create):")
    index = existing_issues(repo)

    epic_numbers: dict[str, int] = {}
    feature_numbers: dict[str, int] = {}
    task_numbers: dict[str, int] = {}

    for epic in data["epics"]:
        milestone = milestones.get(epic["key"])
        number = upsert(repo, epic["key"], f"[{epic['key']}] {epic['title']}",
                        epic_body(epic, feature_numbers),
                        ["epic"] + ([] if epic.get("groomed") else ["needs-grooming"])
                        + scope_labels(epic),
                        milestone, index, dry_run)
        if number:
            epic_numbers[epic["key"]] = number

        for feature in epic["features"]:
            f_number = upsert(repo, feature["key"], f"[{feature['key']}] {feature['title']}",
                              feature_body(feature, epic, epic_numbers.get(epic["key"]), task_numbers),
                              ["feature"] + list(feature.get("labels") or []) + scope_labels(epic),
                              milestone, index, dry_run)
            if f_number:
                feature_numbers[feature["key"]] = f_number

            for i, task in enumerate((feature.get("tasks") or []) if epic.get("groomed") else [], start=1):
                key = task_key(feature["key"], i, task)
                t_number = upsert(repo, key, f"[{key}] {task['title']}",
                                  task_body(task, key, feature,
                                            feature_numbers.get(feature["key"]), epic),
                                  ["task"] + list(task.get("labels") or feature.get("labels") or [])
                                  + scope_labels(epic),
                                  milestone, index, dry_run)
                if t_number:
                    task_numbers[key] = t_number

    report_orphans(data, index)

    if dry_run:
        print("\nDry run — nothing was written. Issue cross-links are resolved on the real run.")
        return

    print("Issues (pass 2 — cross-link):")
    # A depends_on may point at anything, including an issue created later in
    # pass 1, so blocked-by links can only be resolved once every key has a number.
    numbers = {**epic_numbers, **feature_numbers, **task_numbers}
    relinked = 0
    for epic in data["epics"]:
        number = epic_numbers[epic["key"]]
        gh_api(f"repos/{repo}/issues/{number}", "PATCH",
               {"body": epic_body(epic, feature_numbers)})
        for feature in epic["features"]:
            f_number = feature_numbers[feature["key"]]
            gh_api(f"repos/{repo}/issues/{f_number}", "PATCH",
                   {"body": feature_body(feature, epic, number, task_numbers, numbers)})
            for i, task in enumerate((feature.get("tasks") or []) if epic.get("groomed") else [], start=1):
                if not task.get("depends_on"):
                    continue
                key = task_key(feature["key"], i, task)
                gh_api(f"repos/{repo}/issues/{task_numbers[key]}", "PATCH",
                       {"body": task_body(task, key, feature, f_number, epic, numbers)})
                relinked += 1
    print(f"  linked {len(epic_numbers)} epics and {len(feature_numbers)} features"
          f"{f', {relinked} blocked-by tasks' if relinked else ''}")

    print("Board:")
    project(data)


# ----------------------------------------------------------------------- project


PROJECT_TITLE = "AI Budget Agent — Delivery"


def find_board(owner: str) -> dict | None:
    owner_data = gh("api", "graphql", "-f", f"login={owner}", "-f", """query=
        query($login: String!) {
          user(login: $login) {
            id
            projectsV2(first: 50) { nodes { id title number } }
          }
        }""")
    user = owner_data["data"]["user"]
    return next((p for p in user["projectsV2"]["nodes"] if p["title"] == PROJECT_TITLE), None), user["id"]


def project(data: dict) -> None:
    """Create the Projects v2 board if absent and add every backlog issue to it."""
    repo = data["project"]["repo"]
    owner = repo.split("/")[0]

    board, owner_id = find_board(owner)
    user = {"id": owner_id}

    if board is None:
        created = gh("api", "graphql", "-f", f"ownerId={user['id']}", "-f", f"title={PROJECT_TITLE}",
                     "-f", """query=
            mutation($ownerId: ID!, $title: String!) {
              createProjectV2(input: {ownerId: $ownerId, title: $title}) {
                projectV2 { id title number }
              }
            }""")
        board = created["data"]["createProjectV2"]["projectV2"]
        print(f"Created project #{board['number']}: {board['title']}")
    else:
        print(f"Using existing project #{board['number']}: {board['title']}")

    ensure_board_layout(board["id"])
    ensure_status_columns(board["id"])
    issues = [i for i in gh_paginate(f"repos/{repo}/issues?state=all&per_page=100")
              if "pull_request" not in i and MARKER.search(i.get("body") or "")]
    scope_field = ensure_scope_field(board["id"])
    print(f"Adding {len(issues)} issues to the board, each with its {SCOPE_FIELD}...")
    for issue in issues:
        added = gh("api", "graphql", "-f", f"projectId={board['id']}",
                   "-f", f"contentId={issue['node_id']}", "-f", """query=
            mutation($projectId: ID!, $contentId: ID!) {
              addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item { id }
              }
            }""")
        labels = {label["name"] for label in issue.get("labels") or []}
        scope = next((key for key in SCOPES if key in labels), None)
        if scope:
            item_id = added["data"]["addProjectV2ItemById"]["item"]["id"]
            set_single_select(board["id"], item_id, scope_field["id"],
                              scope_field["options"][SCOPES[scope]])

    set_default_status(board["id"])
    print(f"Board ready: https://github.com/users/{owner}/projects/{board['number']}")


def ensure_scope_field(project_id: str) -> dict:
    """The board's Scope field, created with its options if absent (the diploma split).

    Grouping a board view by it splits the work into what the diploma project builds
    and what it leaves out. Returns the field id and its option ids by option name.
    Existing options are never rewritten: replacing them would clear every item's value.
    """
    def fetch() -> dict | None:
        nodes = gh("api", "graphql", "-f", f"projectId={project_id}", "-f", """query=
            query($projectId: ID!) {
              node(id: $projectId) {
                ... on ProjectV2 {
                  fields(first: 30) {
                    nodes { ... on ProjectV2SingleSelectField { id name options { id name } } }
                  }
                }
              }
            }""")["data"]["node"]["fields"]["nodes"]
        return next((f for f in nodes if f.get("name") == SCOPE_FIELD), None)

    field = fetch()
    if field is None:
        options = ", ".join(
            f'{{name: "{name}", color: {color}, description: "{description}"}}'
            for name, color, description in [
                (SCOPES["diploma"], "GREEN", "Built for the diploma project"),
                (SCOPES["out-of-scope"], "GRAY", "Planned, not part of the diploma project"),
            ]
        )
        gh("api", "graphql", "-f", f"projectId={project_id}", "-f", f"""query=
            mutation($projectId: ID!) {{
              createProjectV2Field(input: {{
                projectId: $projectId, dataType: SINGLE_SELECT, name: "{SCOPE_FIELD}",
                singleSelectOptions: [{options}]
              }}) {{ projectV2Field {{ ... on ProjectV2SingleSelectField {{ id }} }} }}
            }}""")
        print(f"  created the {SCOPE_FIELD} field")
        field = fetch()
    assert field is not None
    missing = set(SCOPES.values()) - {o["name"] for o in field["options"]}
    if missing:
        raise SystemExit(f"The board's {SCOPE_FIELD} field lacks options {sorted(missing)}; "
                         f"add them by hand rather than let a sync clear every item's value")
    return {"id": field["id"], "options": {o["name"]: o["id"] for o in field["options"]}}


def set_single_select(project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    """Set one board item's single-select field, e.g. its Status or Scope."""
    gh("api", "graphql", "-f", f"projectId={project_id}", "-f", f"itemId={item_id}",
       "-f", f"fieldId={field_id}", "-f", f"optionId={option_id}", "-f", """query=
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
            value: {singleSelectOptionId: $optionId}
          }) { projectV2Item { id } }
        }""")


def ensure_board_layout(project_id: str) -> None:
    """Projects v2 defaults new views to a table. Switch every table view to a board
    (kanban) so the columns the user actually wants — grouped by Status — show up."""
    views = gh("api", "graphql", "-f", f"projectId={project_id}", "-f", """query=
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 { views(first: 10) { nodes { id layout } } }
          }
        }""")
    for view in views["data"]["node"]["views"]["nodes"]:
        if view["layout"] != "BOARD_LAYOUT":
            gh("api", "graphql", "-f", f"viewId={view['id']}", "-f", """query=
                mutation($viewId: ID!) {
                  updateProjectV2View(input: {viewId: $viewId, layout: BOARD_LAYOUT}) {
                    projectV2View { id }
                  }
                }""")
            print(f"  view {view['id']} -> board layout")


STATUS_COLUMNS = [
    ("Todo", "GRAY", "Not started"),
    ("In Progress", "YELLOW", "Being worked on"),
    ("Review", "PURPLE", "Pull request open, awaiting review/merge"),
    ("Done", "GREEN", "Merged to main"),
]


def ensure_status_columns(project_id: str) -> None:
    """Make sure the Status field has exactly the Todo/In Progress/Review/Done
    columns the working agreement expects, in that order. Existing options keep
    their id (and therefore the status of any card already set to them); only
    missing ones are created."""
    schema = gh("api", "graphql", "-f", f"projectId={project_id}", "-f", """query=
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 30) {
                nodes {
                  ... on ProjectV2SingleSelectField { id name options { id name } }
                }
              }
            }
          }
        }""")
    fields = schema["data"]["node"]["fields"]["nodes"]
    status = next((f for f in fields if f.get("name") == "Status"), None)
    if not status:
        print("  no Status field on this board — skipping column setup")
        return

    existing = {o["name"]: o["id"] for o in status["options"]}
    if list(existing) == [name for name, _, _ in STATUS_COLUMNS]:
        return  # already exactly right, in order

    options_arg = ", ".join(
        (f'{{ id: "{existing[name]}", name: "{name}", color: {color}, description: "{desc}" }}'
         if name in existing else
         f'{{ name: "{name}", color: {color}, description: "{desc}" }}')
        for name, color, desc in STATUS_COLUMNS
    )
    gh("api", "graphql", "-f", f"fieldId={status['id']}", "-f", f"""query=
        mutation {{
          updateProjectV2Field(input: {{
            fieldId: "{status['id']}"
            singleSelectOptions: [{options_arg}]
          }}) {{
            projectV2Field {{ ... on ProjectV2SingleSelectField {{ id }} }}
          }}
        }}""")
    print(f"  Status columns set: {', '.join(name for name, _, _ in STATUS_COLUMNS)}")


def set_default_status(project_id: str) -> None:
    """Park every unstatused card in Todo, so the board shows columns rather than a
    single undifferentiated 'No Status' pile."""
    schema = gh("api", "graphql", "-f", f"projectId={project_id}", "-f", """query=
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 30) {
                nodes {
                  ... on ProjectV2SingleSelectField { id name options { id name } }
                }
              }
            }
          }
        }""")
    fields = schema["data"]["node"]["fields"]["nodes"]
    status = next((f for f in fields if f.get("name") == "Status"), None)
    if not status:
        print("  no Status field on this board — skipping")
        return
    todo = next((o for o in status["options"] if o["name"] == "Todo"), None)
    if not todo:
        print("  no Todo option on the Status field — skipping")
        return

    # gh's --paginate emits concatenated JSON documents for GraphQL rather than one
    # array, so the cursor is walked by hand instead.
    query = """query=
        query($projectId: ID!, $after: String) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100, after: $after) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  fieldValueByName(name: "Status") {
                    ... on ProjectV2ItemFieldSingleSelectValue { name }
                  }
                }
              }
            }
          }
        }"""
    nodes: list[dict] = []
    after = ""
    while True:
        page = gh("api", "graphql", "-f", f"projectId={project_id}", "-f", f"after={after}", "-f", query)
        block = page["data"]["node"]["items"]
        nodes += block["nodes"]
        if not block["pageInfo"]["hasNextPage"]:
            break
        after = block["pageInfo"]["endCursor"]

    pending = [n for n in nodes if not n.get("fieldValueByName")]
    print(f"  setting Status=Todo on {len(pending)} unstatused cards...")
    for node in pending:
        gh("api", "graphql", "-f", f"projectId={project_id}", "-f", f"itemId={node['id']}",
           "-f", f"fieldId={status['id']}", "-f", f"optionId={todo['id']}", "-f", """query=
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
              updateProjectV2ItemFieldValue(input: {
                projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
                value: {singleSelectOptionId: $optionId}
              }) { projectV2Item { id } }
            }""")


def pr_review(data: dict, pr_number: int) -> None:
    """Move the board card(s) a pull request closes into the Review column.

    Called from .github/workflows/pr-board-sync.yml when a PR is opened, reopened,
    or marked ready for review. Resolves the issues GitHub's own closing-keyword
    parser (Closes #N, Fixes #N, ...) found on the PR, rather than re-parsing the
    body by hand.
    """
    repo = data["project"]["repo"]
    owner, name = repo.split("/")
    owner_login = repo.split("/")[0]

    pr_data = gh("api", "graphql", "-f", f"owner={owner}", "-f", f"name={name}",
                "-F", f"number={pr_number}", "-f", """query=
        query($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              closingIssuesReferences(first: 20) { nodes { id number } }
            }
          }
        }""")
    closed_issues = pr_data["data"]["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]
    if not closed_issues:
        print(f"PR #{pr_number} does not close any issue — nothing to move")
        return

    board, _ = find_board(owner_login)
    if board is None:
        print(f"No project titled {PROJECT_TITLE!r} found — nothing to move")
        return

    fields = gh("api", "graphql", "-f", f"projectId={board['id']}", "-f", """query=
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 30) {
                nodes { ... on ProjectV2SingleSelectField { id name options { id name } } }
              }
            }
          }
        }""")["data"]["node"]["fields"]["nodes"]
    status = next((f for f in fields if f.get("name") == "Status"), None)
    review = next((o for o in (status or {}).get("options", []) if o["name"] == "Review"), None)
    if not status or not review:
        print("No Status/Review column found on the board — nothing to move")
        return

    for issue in closed_issues:
        item = gh("api", "graphql", "-f", f"issueId={issue['id']}", "-f", """query=
            query($issueId: ID!) {
              node(id: $issueId) {
                ... on Issue { projectItems(first: 10) { nodes { id project { id } } } }
              }
            }""")
        matches = [n for n in item["data"]["node"]["projectItems"]["nodes"]
                   if n["project"]["id"] == board["id"]]
        if not matches:
            print(f"  issue #{issue['number']} is not on the board — skipping")
            continue
        gh("api", "graphql", "-f", f"projectId={board['id']}", "-f", f"itemId={matches[0]['id']}",
           "-f", f"fieldId={status['id']}", "-f", f"optionId={review['id']}", "-f", """query=
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
              updateProjectV2ItemFieldValue(input: {
                projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
                value: {singleSelectOptionId: $optionId}
              }) { projectV2Item { id } }
            }""")
        print(f"  issue #{issue['number']} -> Review")


# -------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("render", help="regenerate docs/planning/backlog.md from the YAML")
    sync_parser = sub.add_parser("sync", help="push labels, milestones and issues to GitHub")
    sync_parser.add_argument("--dry-run", action="store_true")
    sub.add_parser("project", help="create and populate the Projects v2 board")
    pr_review_parser = sub.add_parser("pr-review", help="move a PR's closed issues to Review")
    pr_review_parser.add_argument("--pr", type=int, required=True)

    args = parser.parse_args()
    data = load()

    if args.command == "render":
        MARKDOWN.write_text(render_markdown(data))
        print(f"Wrote {MARKDOWN.relative_to(ROOT)}")
    elif args.command == "sync":
        sync(data, args.dry_run)
    elif args.command == "project":
        project(data)
    elif args.command == "pr-review":
        pr_review(data, args.pr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
