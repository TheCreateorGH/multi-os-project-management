"""Project-scoped Git facade."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from .models import MARKER_FILENAME, load_project
from .versioning import bump_version, generate_changelog, git_change_summary

HOOK = """#!/bin/sh
exec pm git _pre-commit
"""


def project_root(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    for folder in (current, *current.parents):
        if (folder / MARKER_FILENAME).is_file():
            return folder
    return None


def run_git(args: list[str], cwd: Path) -> int:
    root = project_root(cwd)
    if root is None:
        print("error: pm git commands must run inside a marked project", file=sys.stderr)
        return 1
    if not args:
        args = ["status"]
    if args[0] == "init":
        return subprocess.run(["git", "init", *args[1:]], cwd=root).returncode
    if not (root / ".git").exists():
        print("error: this project is not a Git repository; run 'pm git init' first", file=sys.stderr)
        return 1
    project = load_project(root)
    if args[0] == "install-hooks":
        hook = root / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(HOOK, encoding="utf-8")
        hook.chmod(0o755)
        print(f"Installed {hook}")
        return 0
    if args[0] == "uninstall-hooks":
        hook = root / ".git" / "hooks" / "pre-commit"
        if hook.is_file() and hook.read_text(encoding="utf-8") == HOOK:
            hook.unlink()
            print("Removed project-manager pre-commit hook")
        return 0
    if args[0] == "_pre-commit":
        return 0
    if args[0] == "changelog":
        (root / "CHANGELOG.md").write_text(generate_changelog(root), encoding="utf-8")
        print(f"Updated {root / 'CHANGELOG.md'}")
        return 0
    if args[0] == "release":
        project = load_project(root)
        tag = f"v{project.version}"
        result = subprocess.run(["git", "tag", "-a", tag, "-m", tag], cwd=root)
        if result.returncode == 0:
            print(f"Created release tag {tag}")
        return result.returncode
    if args[0] == "commit":
        if project.auto_version:
            summary = git_change_summary(root, project)
            if summary.files == 0:
                print("No changed files detected; skipping automatic version bump.")
                return subprocess.run(["git", *args], cwd=root).returncode
            print(
                f"Change analysis: +{summary.added}/-{summary.deleted} "
                f"in {summary.files} file(s) -> {summary.level}"
            )
            if summary.level == "major":
                answer = input("Major change detected. Approve version bump? [y/N] ")
                if answer.strip().lower() not in {"y", "yes"}:
                    print("Commit cancelled; major version bump was not approved.")
                    return 1
            version = bump_version(root, summary.level)
            subprocess.run(["git", "add", MARKER_FILENAME], cwd=root, check=True)
            print(f"Version bumped to {version}")
    return subprocess.run(["git", *args], cwd=root).returncode
