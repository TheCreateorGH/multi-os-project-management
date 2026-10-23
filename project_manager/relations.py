"""Validation of project and subproject relationships."""

from __future__ import annotations

from collections import defaultdict

from .models import Project


def relationship_errors(projects: list[Project]) -> list[str]:
    by_name = {project.name: project for project in projects}
    errors: list[str] = []
    graph: dict[str, set[str]] = defaultdict(set)
    for project in projects:
        if project.is_subproject and project.parent not in by_name:
            errors.append(f"{project.name}: parent {project.parent!r} was not found")
        for dependency in project.dependencies:
            if dependency not in by_name:
                errors.append(f"{project.name}: dependency {dependency!r} was not found")
            else:
                graph[project.name].add(dependency)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> bool:
        if name in visiting:
            return True
        if name in visited:
            return False
        visiting.add(name)
        cyclic = any(visit(child) for child in graph[name])
        visiting.remove(name)
        visited.add(name)
        return cyclic

    for name in graph:
        if visit(name):
            errors.append(f"dependency cycle detected at {name}")
    return errors
