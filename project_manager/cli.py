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

    scan = subparsers.add_parser(
        "scan",
        help="discover projects below a folder",
        description="Discover project markers recursively below a collection folder.",
    )
    scan.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Folder to scan (defaults to current directory).",
    )

    init = subparsers.add_parser(
        "init", help="create a project marker", description="Create a .project.toml marker."
    )
    init.add_argument("path", type=Path, help="Project folder where the marker is written.")
    init.add_argument("--name", required=True, help="Human-readable project name.")
    init.add_argument("--type", default="unknown", dest="project_type", help="Project type label.")
    init.add_argument("--version", default="0.1.0", help="Initial semantic version.")
    init.add_argument(
        "--kind",
        choices=("project", "subproject"),
        default="project",
        help="Marker kind.",
    )
    init.add_argument("--parent", help="Parent project name (required for subprojects).")
    init.add_argument("--description", default="", help="Project description.")
    init.add_argument("--status", default="active", help="Lifecycle status.")
    init.add_argument("--tags", default="", help="Comma-separated tag list.")
    init.add_argument("--license", dest="license_name", help="License identifier.")
    init.add_argument("--repository", help="Repository URL or identifier.")
    init.add_argument("--owner", help="Project owner.")
    init.add_argument("--language", help="Primary implementation language.")
    init.add_argument("--framework", help="Primary framework or platform.")
    init.add_argument("--release-channel", default="stable", help="Release channel name.")
    init.add_argument(
        "--dependency", action="append", default=[], help="Dependency project name (repeatable)."
    )

    tui = subparsers.add_parser(
        "tui",
        help="open the Textual interface",
        description="Open the interactive Textual interface for discovered projects.",
    )
    tui.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Collection folder to scan (defaults to current directory).",
    )
    workspace = subparsers.add_parser(
        "workspace",
        help="manage centrally registered collection folders",
        description="Manage configured workspace folders and project inventory tools.",
    )
    workspace_subparsers = workspace.add_subparsers(dest="workspace_command", required=True)
    workspace_subparsers.add_parser(
        "list", help="list registered folders", description="List all registered workspace folders."
    )
    add = workspace_subparsers.add_parser(
        "add",
        help="register a collection folder",
        description="Register a folder in the central workspace configuration.",
    )
    add.add_argument("path", type=Path, help="Folder path to register.")
    remove = workspace_subparsers.add_parser(
        "remove",
        help="unregister a collection folder",
        description="Remove a folder from the central workspace configuration.",
    )
    remove.add_argument("path", type=Path, help="Folder path to unregister.")
    workspace_subparsers.add_parser(
        "scan",
        help="scan all registered folders",
        description="Scan every registered workspace folder for projects.",
    )
    search = workspace_subparsers.add_parser(
        "search",
        help="search registered projects",
        description="Search project names and tags across registered workspace folders.",
    )
    search.add_argument("query", help="Case-insensitive text query.")
    export = workspace_subparsers.add_parser(
        "export",
        help="export registered projects",
        description="Export discovered workspace projects to JSON or CSV.",
    )
    export.add_argument("path", type=Path, help="Output file path (.json or .csv).")
    graph = workspace_subparsers.add_parser(
        "graph",
        help="show project dependencies",
        description="Display dependency relationships for workspace projects.",
    )
    graph.add_argument(
        "--format",
        choices=("text", "dot"),
        default="text",
        help="Output format for dependency graph.",
    )

    check = subparsers.add_parser(
        "check",
        help="run project health checks",
        description="Run project health checks for the nearest marked project.",
    )
    check.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Path inside a marked project (defaults to current directory).",
    )
    doctor_parser = subparsers.add_parser(
        "doctor", help="show project diagnostics", description="Show actionable project diagnostics."
    )
    doctor_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Path inside a marked project (defaults to current directory).",
    )
    version = subparsers.add_parser(
        "version",
        help="preview or apply a version bump",
        description="Preview or apply semantic version changes based on project rules.",
    )
    version_sub = version.add_subparsers(dest="version_command", required=True)
    version_preview = version_sub.add_parser(
        "preview",
        help="preview the recommended version bump",
        description="Show recommended version bump and reasons without editing files.",
    )
    version_preview.add_argument(
        "--message",
        action="append",
        default=[],
        help="Commit message hint used for bump intent (repeatable).",
    )
    version_bump = version_sub.add_parser(
        "bump",
        help="apply an explicit version bump",
        description="Apply a semantic version bump to the project marker.",
    )
    version_bump.add_argument(
        "level", choices=("patch", "minor", "major"), help="Bump level to apply."
    )
    open_parser = subparsers.add_parser(
        "open", help="open a registered project", description="Open a project by exact registered name."
    )
    open_parser.add_argument("name", help="Exact project name to open.")
    history = subparsers.add_parser(
        "history",
        help="show project metadata history",
        description="Show Git history for the .project.toml marker in a project.",
    )
    history.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Path inside a marked project (defaults to current directory).",
    )

    git = subparsers.add_parser(
        "git",
        help="run project-aware Git commands, passing unknown commands to Git",
        description=(
            "Run project-aware Git helpers (install-hooks, uninstall-hooks, changelog, "
            "release) or pass commands through to Git."
        ),
    )
    git.add_argument("git_args", nargs=argparse.REMAINDER, help="Git subcommand and arguments.")
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
