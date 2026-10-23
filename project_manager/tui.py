"""Textual user interface."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from .scanner import discover_projects


class ProjectManagerApp(App[None]):
    """A small first-screen project browser."""

    TITLE = "Multi OS Project Management"
    CSS = """
    Screen { layout: vertical; }
    #status { height: 2; padding: 1; background: $panel; }
    .project { padding: 1; border: round $accent; margin: 0 1; }
    #filter { margin: 0 1; }
    """
    BINDINGS = [("r", "refresh", "Refresh"), ("q", "quit", "Quit")]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Scanning: {self.root}", id="status")
        yield Input(placeholder="Filter projects...", id="filter")
        yield VerticalScroll(id="projects")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_projects()

    def action_refresh(self) -> None:
        self.refresh_projects()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self.refresh_projects()

    def refresh_projects(self) -> None:
        projects, errors = discover_projects(self.root)
        status = self.query_one("#status", Static)
        status.update(f"{len(projects)} project(s) found in {self.root}")
        container = self.query_one("#projects", VerticalScroll)
        container.remove_children()
        query = self.query_one("#filter", Input).value.casefold()
        projects = [
            project for project in projects
            if not query or query in project.name.casefold() or query in " ".join(project.tags).casefold()
        ]
        if not projects:
            container.mount(Static("No projects found.", classes="project"))
        for project in projects:
            kind = "subproject" if project.is_subproject else "project"
            version = project.version or "unversioned"
            container.mount(
                Static(
                    f"{project.name} [{kind}]\n"
                    f"type: {project.project_type} | version: {version} | status: {project.status}\n"
                    f"owner: {project.owner or '-'} | tags: {', '.join(project.tags) or '-'}\n"
                    f"path: {project.path}",
                    classes="project",
                )
            )
        if errors:
            container.mount(Static("\n".join(f"Warning: {error}" for error in errors)))
