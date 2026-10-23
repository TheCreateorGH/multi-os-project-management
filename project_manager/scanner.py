"""Project discovery in collection folders and project trees."""

from __future__ import annotations

from pathlib import Path

from .models import MARKER_FILENAME, Project, ProjectMarkerError, load_project
from .relations import relationship_errors


def discover_projects(root: Path) -> tuple[list[Project], list[str]]:
    """Discover projects below ``root``.

    A marked project is yielded once. Its descendants are still inspected for
    marked subprojects, while unmarked folders are ignored as project nodes.
    Invalid markers are returned as diagnostics instead of aborting a scan.
    """

    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    projects: list[Project] = []
    errors: list[str] = []

    def visit(folder: Path, containing_project: Project | None = None) -> None:
        marker = folder / MARKER_FILENAME
        current_project = containing_project
        if marker.exists():
            try:
                project = load_project(folder)
                if containing_project is not None and not project.is_subproject:
                    errors.append(
                        f"{marker}: nested projects must use kind = 'subproject'"
                    )
                else:
                    projects.append(project)
                current_project = project
            except ProjectMarkerError as exc:
                errors.append(str(exc))

        try:
            children = sorted(
                (item for item in folder.iterdir() if item.is_dir()),
                key=lambda item: item.name.casefold(),
            )
        except OSError as exc:
            errors.append(f"{folder}: {exc}")
            return
        for child in children:
            visit(child, current_project)

    visit(root)
    projects.sort(key=lambda project: (project.path.name.casefold(), str(project.path)))
    errors.extend(relationship_errors(projects))
    return projects, errors
