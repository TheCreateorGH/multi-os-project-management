"""Project health and repair diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .models import Project, load_project


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def project_checks(path: Path) -> list[CheckResult]:
    project = load_project(path)
    results = [
        CheckResult("marker", True, "valid .project.toml"),
        CheckResult("readme", any((path / name).is_file() for name in ("README.md", "README.rst", "README")), "README found" if any((path / name).is_file() for name in ("README.md", "README.rst", "README")) else "README missing"),
        CheckResult("git", (path / ".git").exists(), "Git repository found" if (path / ".git").exists() else "Git repository missing"),
        CheckResult("dependencies", bool(project.dependencies), f"{len(project.dependencies)} declared" if project.dependencies else "none declared"),
        CheckResult("tests", any((path / name).exists() for name in ("tests", "test", "__tests__")), "test directory found" if any((path / name).exists() for name in ("tests", "test", "__tests__")) else "test directory missing"),
        CheckResult("ci", (path / ".github" / "workflows").is_dir() or (path / ".gitlab-ci.yml").is_file(), "CI configuration found" if (path / ".github" / "workflows").is_dir() or (path / ".gitlab-ci.yml").is_file() else "CI configuration missing"),
    ]
    manifests = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "*.csproj")
    found_manifest = any((path / name).exists() for name in manifests if "*" not in name)
    if not found_manifest:
        found_manifest = bool(list(path.glob("*.csproj")))
    results.append(CheckResult("manifest", found_manifest, "build manifest found" if found_manifest else "no recognized build manifest"))
    return results


def doctor(path: Path) -> list[str]:
    """Return actionable diagnostics without changing project files."""
    issues: list[str] = []
    try:
        results = project_checks(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    for result in results:
        if not result.ok:
            issues.append(f"{result.name}: {result.detail}")
    if (path / ".git").exists():
        hooks = path / ".git" / "hooks"
        if not (hooks / "pre-commit").exists():
            issues.append("hooks: pre-commit hook is not installed")
    return issues


def run_check_command(path: Path, command: list[str]) -> CheckResult:
    try:
        result = subprocess.run(command, cwd=path, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult("command", False, str(exc))
    detail = (result.stdout or result.stderr).strip().splitlines()
    return CheckResult("command", result.returncode == 0, detail[-1] if detail else "completed")
