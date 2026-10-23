"""Command-line entry point."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from .checks import doctor, project_checks
from .git import project_root, run_git
from .models import load_project, write_project_marker
from .scanner import discover_projects
from .versioning import bump_version, git_change_summary
from .workspace import add_root, load_roots, remove_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-manager",
        description="Discover and manage projects in collection folders.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="discover projects below a folder")
    scan.add_argument("path", nargs="?", type=Path, default=Path.cwd())

    init = subparsers.add_parser("init", help="create a project marker")
    init.add_argument("path", type=Path)
    init.add_argument("--name", required=True)
    init.add_argument("--type", default="unknown", dest="project_type")
    init.add_argument("--version", default="0.1.0")
    init.add_argument("--kind", choices=("project", "subproject"), default="project")
    init.add_argument("--parent")
    init.add_argument("--description", default="")
    init.add_argument("--status", default="active")
    init.add_argument("--tags", default="")
    init.add_argument("--license", dest="license_name")
    init.add_argument("--repository")
    init.add_argument("--owner")
    init.add_argument("--language")
    init.add_argument("--framework")
    init.add_argument("--release-channel", default="stable")
    init.add_argument("--dependency", action="append", default=[])

    tui = subparsers.add_parser("tui", help="open the Textual interface")
    tui.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    workspace = subparsers.add_parser(
        "workspace", help="manage centrally registered collection folders"
    )
    workspace_subparsers = workspace.add_subparsers(dest="workspace_command", required=True)
    workspace_subparsers.add_parser("list", help="list registered folders")
    add = workspace_subparsers.add_parser("add", help="register a collection folder")
    add.add_argument("path", type=Path)
    remove = workspace_subparsers.add_parser("remove", help="unregister a collection folder")
    remove.add_argument("path", type=Path)
    workspace_subparsers.add_parser("scan", help="scan all registered folders")
    search = workspace_subparsers.add_parser("search", help="search registered projects")
    search.add_argument("query")
    export = workspace_subparsers.add_parser("export", help="export registered projects")
    export.add_argument("path", type=Path)
    graph = workspace_subparsers.add_parser("graph", help="show project dependencies")
    graph.add_argument("--format", choices=("text", "dot"), default="text")

    check = subparsers.add_parser("check", help="run project health checks")
    check.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    doctor_parser = subparsers.add_parser("doctor", help="show project diagnostics")
    doctor_parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    version = subparsers.add_parser("version", help="preview or apply a version bump")
    version_sub = version.add_subparsers(dest="version_command", required=True)
    version_sub.add_parser("preview")
    version_sub.choices["preview"].add_argument("--message", action="append", default=[])
    version_bump = version_sub.add_parser("bump")
    version_bump.add_argument("level", choices=("patch", "minor", "major"))
    open_parser = subparsers.add_parser("open", help="open a registered project")
    open_parser.add_argument("name")
    history = subparsers.add_parser("history", help="show project metadata history")
    history.add_argument("path", nargs="?", type=Path, default=Path.cwd())

    git = subparsers.add_parser(
        "git", help="run project-aware Git commands, passing unknown commands to Git"
    )
    git.add_argument("git_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return _scan(args.path)
    if args.command == "init":
        return _init(args)
    if args.command == "tui":
        return _tui(args.path)
    if args.command == "workspace":
        return _workspace(args)
    if args.command == "git":
        return run_git(args.git_args, Path.cwd())
    if args.command == "check":
        return _check(args.path)
    if args.command == "doctor":
        return _doctor(args.path)
    if args.command == "version":
        return _version(args)
    if args.command == "open":
        return _open(args.name)
    if args.command == "history":
        return _history(args.path)
    return 2


def _scan(path: Path) -> int:
    try:
        projects, errors = discover_projects(path)
    except (NotADirectoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not projects:
        print("No projects found.")
    for project in projects:
        suffix = f" v{project.version}" if project.version else ""
        kind = "subproject" if project.is_subproject else "project"
        print(f"{kind}: {project.name} [{project.project_type}]{suffix} - {project.path}")
    for error in errors:
        print(f"warning: {error}", file=sys.stderr)
    return 0 if not errors else 1


def _init(args: argparse.Namespace) -> int:
    try:
        marker = write_project_marker(
            args.path,
            name=args.name,
            kind=args.kind,
            project_type=args.project_type,
            version=args.version,
            parent=args.parent,
            description=args.description,
            status=args.status,
            tags=tuple(tag.strip() for tag in args.tags.split(",") if tag.strip()),
            license_name=args.license_name,
            repository=args.repository,
            owner=args.owner,
            language=args.language,
            framework=args.framework,
            release_channel=args.release_channel,
            dependencies=tuple(args.dependency),
        )
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created {marker}")
    return 0


def _tui(path: Path) -> int:
    try:
        from .tui import ProjectManagerApp
    except ImportError:
        print("error: install dependencies with 'pip install -e .'", file=sys.stderr)
        return 1
    ProjectManagerApp(path).run()
    return 0


def _workspace(args: argparse.Namespace) -> int:
    try:
        if args.workspace_command == "list":
            roots = load_roots()
            if not roots:
                print("No workspace folders registered.")
            for root in roots:
                print(root)
            return 0
        if args.workspace_command == "add":
            roots = add_root(args.path)
            print(f"Registered {args.path.expanduser().resolve()}")
            print(f"{len(roots)} workspace folder(s) configured.")
            return 0
        if args.workspace_command == "remove":
            remove_root(args.path)
            print(f"Unregistered {args.path.expanduser().resolve()}")
            return 0
        if args.workspace_command == "scan":
            exit_code = 0
            for root in load_roots():
                print(f"\n{root}")
                exit_code = max(exit_code, _scan(root))
            return exit_code
        if args.workspace_command == "search":
            query = args.query.casefold()
            for root in load_roots():
                projects, _ = discover_projects(root)
                for project in projects:
                    haystack = f"{project.name} {' '.join(project.tags)}".casefold()
                    if query in haystack:
                        print(f"{project.name}\t{project.version or '-'}\t{project.path}")
            return 0
        if args.workspace_command == "export":
            records = []
            for root in load_roots():
                projects, _ = discover_projects(root)
                records.extend(_project_record(project) for project in projects)
            args.path.parent.mkdir(parents=True, exist_ok=True)
            if args.path.suffix.casefold() == ".csv":
                fields = sorted(records[0]) if records else ["name", "path"]
                with args.path.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(records)
            else:
                args.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
            print(f"Exported {len(records)} project(s) to {args.path}")
            return 0
        if args.workspace_command == "graph":
            all_projects = []
            for root in load_roots():
                projects, _ = discover_projects(root)
                all_projects.extend(projects)
            if args.format == "dot":
                print("digraph projects {")
                for project in all_projects:
                    for dependency in project.dependencies:
                        print(f'  "{project.name}" -> "{dependency}";')
                print("}")
            else:
                for project in all_projects:
                    print(f"{project.name}: {', '.join(project.dependencies) or '-'}")
            return 0
    except (NotADirectoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


def _check(path: Path) -> int:
    root = project_root(path)
    if root is None:
        print("error: check must run inside a marked project", file=sys.stderr)
        return 1
    for result in project_checks(root):
        print(f"{'OK' if result.ok else 'WARN'} {result.name}: {result.detail}")
    return 0


def _doctor(path: Path) -> int:
    root = project_root(path)
    if root is None:
        print("error: doctor must run inside a marked project", file=sys.stderr)
        return 1
    issues = doctor(root)
    for issue in issues:
        print(f"- {issue}")
    if not issues:
        print("No issues found.")
    return 0 if not issues else 1


def _version(args: argparse.Namespace) -> int:
    root = project_root(Path.cwd())
    if root is None:
        print("error: version commands must run inside a marked project", file=sys.stderr)
        return 1
    project = load_project(root)
    if args.version_command == "preview":
        summary = git_change_summary(root, project, commit_messages=tuple(args.message))
        print(f"{summary.level}: +{summary.added}/-{summary.deleted} in {summary.files} file(s)")
        for reason in summary.reasons:
            print(f"reason: {reason}")
        return 0
    if args.level == "major":
        answer = input("Approve major version bump? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Major bump not approved.")
            return 1
    print(f"Bumped to {bump_version(root, args.level)}")
    return 0


def _project_record(project) -> dict[str, str]:
    return {
        "name": project.name,
        "path": str(project.path),
        "kind": project.kind,
        "type": project.project_type,
        "version": project.version or "",
        "status": project.status,
        "tags": ",".join(project.tags),
        "owner": project.owner or "",
        "repository": project.repository or "",
    }


def _open(name: str) -> int:
    query = name.casefold()
    matches = []
    for root in load_roots():
        projects, _ = discover_projects(root)
        matches.extend(project for project in projects if project.name.casefold() == query)
    if len(matches) != 1:
        print(f"error: expected one project named {name!r}, found {len(matches)}", file=sys.stderr)
        return 1
    project_path = matches[0].path
    editor = os.environ.get("PM_EDITOR") or os.environ.get("EDITOR")
    if not editor:
        print(project_path)
        return 0
    return subprocess.run([*shlex.split(editor), str(project_path)]).returncode


def _history(path: Path) -> int:
    root = project_root(path)
    if root is None:
        print("error: history must run inside a marked project", file=sys.stderr)
        return 1
    result = subprocess.run(
        ["git", "-C", str(root), "log", "--oneline", "--", ".project.toml"],
        text=True,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
