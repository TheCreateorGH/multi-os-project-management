"""Semantic versioning based on Git intent and change size."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from .models import Project, load_project


@dataclass(frozen=True)
class ChangeSummary:
    added: int
    deleted: int
    files: int
    level: str
    reasons: tuple[str, ...] = ()
    commits: tuple[str, ...] = ()

    @property
    def changed_lines(self) -> int:
        return self.added + self.deleted


def git_change_summary(
    path: Path,
    project: Project,
    *,
    commit_messages: tuple[str, ...] = (),
) -> ChangeSummary:
    output = _git_output(path, ["diff", "--cached", "--numstat"])
    if not output.strip():
        output = _git_output(path, ["diff", "--numstat", "HEAD"])
    added = deleted = files = 0
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] == "-":
            continue
        try:
            added += int(fields[0])
            deleted += int(fields[1])
        except ValueError:
            continue
        files += 1
    commits = commit_messages
    level, reasons = recommend_level(
        added + deleted,
        project,
        commits=commits,
    )
    return ChangeSummary(added, deleted, files, level, reasons, commits)


def recommend_level(
    changed_lines: int,
    project: Project,
    *,
    commits: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    breaking = any(
        "breaking change" in message.lower()
        or "!" in message.split(":", 1)[0]
        for message in commits
    )
    if breaking:
        return "major", ("breaking change in commit history",)
    if changed_lines >= project.major_change_lines:
        return "major", (f"{changed_lines} changed lines exceed major threshold",)
    if changed_lines > project.minor_change_lines:
        reasons.append(f"{changed_lines} changed lines exceed minor threshold")
        return "minor", tuple(reasons)
    if any(message.lower().startswith(("feat", "feature")) for message in commits):
        return "minor", ("feature commit detected",)
    if any(message.lower().startswith(("fix", "bugfix")) for message in commits):
        return "patch", ("fix commit detected",)
    return "patch", ("small change",)


def bump_version(path: Path, level: str) -> str:
    project = load_project(path)
    current = project.version or "0.1.0"
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current)
    if not match:
        raise ValueError(f"Unsupported semantic version: {current}")
    major, minor, patch = map(int, match.groups())
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    elif level == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown version level: {level}")
    version = f"{major}.{minor}.{patch}"
    marker = path / ".project.toml"
    text = marker.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Missing version field in {marker}")
    marker.write_text(updated, encoding="utf-8")
    return version


def generate_changelog(path: Path, *, limit: int = 50) -> str:
    commits = _git_output(path, ["log", f"-{limit}", "--pretty=format:%h %s"])
    return "# Changelog\n\n" + (
        "\n".join(f"- {line}" for line in commits.splitlines())
        if commits.strip()
        else "No commits yet."
    ) + "\n"


def _git_output(path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout
