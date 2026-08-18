#!/usr/bin/env python3
"""Sync docs/planning/backlog.yaml into GitHub milestones, labels and issues.

The YAML file is authoritative; GitHub is a projection of it. Every issue carries a
hidden marker comment (``<!-- backlog-key: F0.1 -->``) which is how a re-run recognises
what it already created, so the script is safe to run repeatedly: existing issues are
updated in place rather than duplicated.

Usage:
    scripts/backlog_sync.py render            # regenerate docs/planning/backlog.md
    scripts/backlog_sync.py sync --dry-run    # show what would change
    scripts/backlog_sync.py sync              # create/update labels, milestones, issues
    scripts/backlog_sync.py project           # create/populate the Projects v2 board
                                              # (requires: gh auth refresh -s project)
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


def task_key(feature_key: str, index: int) -> str:
    return f"{feature_key}.{index}"


def clean(text: str | None) -> str:
    """Collapse YAML folded-block whitespace back into flowing prose."""
    return " ".join((text or "").split())


def requirement_line(refs: list[str] | None) -> str:
    return ", ".join(refs) if refs else "—"


# ------------------------------------------------------------------ issue bodies


def epic_body(epic: dict, feature_numbers: dict[str, int]) -> str:
    lines = [
        f"<!-- backlog-key: {epic['key']} -->",
        "**Epic**",
        "",
        f"- **BRD sections:** {requirement_line(epic.get('br'))}",
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
                 task_numbers: dict[str, int]) -> str:
    lines = [
        f"<!-- backlog-key: {feature['key']} -->",
        "**Feature**",
        "",
        f"- **Epic:** {f'#{epic_number}' if epic_number else ''} {epic['key']} {epic['title']}",
        f"- **BRD requirements:** {requirement_line(feature.get('requirements'))}",
        "",
        "### Intent",
        clean(feature.get("intent")),
    ]
    tasks = feature.get("tasks") or []
    if tasks:
        lines += ["", "### Tasks"]
        for index, task in enumerate(tasks, start=1):
            key = task_key(feature["key"], index)
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


def task_body(task: dict, key: str, feature: dict, feature_number: int | None) -> str:
    return "\n".join([
        f"<!-- backlog-key: {key} -->",
        "**Task**",
        "",
        f"- **Feature:** {f'#{feature_number}' if feature_number else ''} {feature['key']} {feature['title']}",
        f"- **BRD requirements:** {requirement_line(feature.get('requirements'))}",
        "",
        "### What to do",
        clean(task.get("detail")),
        "",
        "### Done when",
        "- [ ] Implemented and covered by tests",
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
    lines += [
        f"{len(data['epics'])} epics · {total_features} features · {total_tasks} tasks written so far.",
        "",
        "| Epic | Title | BRD | Features | Groomed |",
        "|---|---|---|---|---|",
    ]
    for epic in data["epics"]:
        lines.append(
            f"| {epic['key']} | {epic['title']} | {requirement_line(epic.get('br'))} "
            f"| {len(epic['features'])} | {'yes' if epic.get('groomed') else 'no'} |"
        )
    lines.append("")

    for epic in data["epics"]:
        lines += [
            "---",
            "",
            f"## {epic['key']} — {epic['title']}",
            "",
            f"**BRD sections:** {requirement_line(epic.get('br'))}",
            "",
            clean(epic.get("summary")),
            "",
        ]
        for feature in epic["features"]:
            lines += [
                f"### {feature['key']} — {feature['title']}",
                "",
                f"*Requirements: {requirement_line(feature.get('requirements'))}*",
                "",
                clean(feature.get("intent")),
                "",
            ]
            tasks = feature.get("tasks") or []
            if tasks:
                for index, task in enumerate(tasks, start=1):
                    lines.append(f"- **{task_key(feature['key'], index)}** {task['title']} — {clean(task.get('detail'))}")
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
                        ["epic"] + ([] if epic.get("groomed") else ["needs-grooming"]),
                        milestone, index, dry_run)
        if number:
            epic_numbers[epic["key"]] = number

        for feature in epic["features"]:
            f_number = upsert(repo, feature["key"], f"[{feature['key']}] {feature['title']}",
                              feature_body(feature, epic, epic_numbers.get(epic["key"]), task_numbers),
                              ["feature"] + list(feature.get("labels") or []),
                              milestone, index, dry_run)
            if f_number:
                feature_numbers[feature["key"]] = f_number

            for i, task in enumerate(feature.get("tasks") or [], start=1):
                key = task_key(feature["key"], i)
                t_number = upsert(repo, key, f"[{key}] {task['title']}",
                                  task_body(task, key, feature, feature_numbers.get(feature["key"])),
                                  ["task"] + list(task.get("labels") or feature.get("labels") or []),
                                  milestone, index, dry_run)
                if t_number:
                    task_numbers[key] = t_number

    if dry_run:
        print("\nDry run — nothing was written. Issue cross-links are resolved on the real run.")
        return

    print("Issues (pass 2 — cross-link):")
    for epic in data["epics"]:
        number = epic_numbers[epic["key"]]
        gh_api(f"repos/{repo}/issues/{number}", "PATCH",
               {"body": epic_body(epic, feature_numbers)})
        for feature in epic["features"]:
            f_number = feature_numbers[feature["key"]]
            gh_api(f"repos/{repo}/issues/{f_number}", "PATCH",
                   {"body": feature_body(feature, epic, number, task_numbers)})
    print(f"  linked {len(epic_numbers)} epics and {len(feature_numbers)} features")


# ----------------------------------------------------------------------- project


PROJECT_TITLE = "AI Budget Agent — Delivery"


def project(data: dict) -> None:
    """Create the Projects v2 board if absent and add every backlog issue to it."""
    repo = data["project"]["repo"]
    owner = repo.split("/")[0]

    owner_data = gh("api", "graphql", "-f", f"login={owner}", "-f", """query=
        query($login: String!) {
          user(login: $login) {
            id
            projectsV2(first: 50) { nodes { id title number } }
          }
        }""")
    user = owner_data["data"]["user"]
    board = next((p for p in user["projectsV2"]["nodes"] if p["title"] == PROJECT_TITLE), None)

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

    issues = [i for i in gh_paginate(f"repos/{repo}/issues?state=all&per_page=100")
              if "pull_request" not in i and MARKER.search(i.get("body") or "")]
    print(f"Adding {len(issues)} issues to the board...")
    for issue in issues:
        gh("api", "graphql", "-f", f"projectId={board['id']}", "-f", f"contentId={issue['node_id']}",
           "-f", """query=
            mutation($projectId: ID!, $contentId: ID!) {
              addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item { id }
              }
            }""")
    print(f"Board ready: https://github.com/users/{owner}/projects/{board['number']}")


# -------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("render", help="regenerate docs/planning/backlog.md from the YAML")
    sync_parser = sub.add_parser("sync", help="push labels, milestones and issues to GitHub")
    sync_parser.add_argument("--dry-run", action="store_true")
    sub.add_parser("project", help="create and populate the Projects v2 board")

    args = parser.parse_args()
    data = load()

    if args.command == "render":
        MARKDOWN.write_text(render_markdown(data))
        print(f"Wrote {MARKDOWN.relative_to(ROOT)}")
    elif args.command == "sync":
        sync(data, args.dry_run)
    elif args.command == "project":
        project(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
