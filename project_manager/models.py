"""Data structures and marker-file handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any


MARKER_FILENAME = ".project.toml"
CURRENT_SCHEMA_VERSION = 1


class ProjectMarkerError(ValueError):
    """Raised when a project marker is missing or invalid."""


@dataclass(frozen=True)
class Project:
    """A project or subproject described by a marker file."""

    path: Path
    name: str
    kind: str
    project_type: str
    version: str | None = None
    parent: str | None = None
    description: str | None = None
    status: str = "active"
    tags: tuple[str, ...] = ()
    license: str | None = None
    repository: str | None = None
    auto_version: bool = True
    major_change_lines: int = 500
    minor_change_lines: int = 20
    schema_version: int = CURRENT_SCHEMA_VERSION
    project_id: str | None = None
    owner: str | None = None
    contributors: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()
    language: str | None = None
    framework: str | None = None
    release_channel: str = "stable"
    created_at: str | None = None
    updated_at: str | None = None
    custom: tuple[tuple[str, str], ...] = ()

    @property
    def is_subproject(self) -> bool:
        return self.kind == "subproject"


def load_project(path: Path) -> Project:
    """Load and validate the marker in ``path``."""

    marker = path / MARKER_FILENAME
    if not marker.is_file():
        raise ProjectMarkerError(f"Missing {MARKER_FILENAME} in {path}")

    try:
        with marker.open("rb") as stream:
            data: dict[str, Any] = tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise ProjectMarkerError(f"Invalid TOML in {marker}: {exc}") from exc

    name = data.get("name")
    kind = data.get("kind", "project")
    project_type = data.get("type", "unknown")
    parent = data.get("parent")
    version = data.get("version")
    schema_version = data.get("schema_version", CURRENT_SCHEMA_VERSION)
    project_id = data.get("id")
    owner = data.get("owner")
    contributors = data.get("contributors", [])
    dependencies = data.get("dependencies", [])
    environment = data.get("environment", {})
    language = data.get("language")
    framework = data.get("framework")
    release_channel = data.get("release_channel", "stable")
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    custom = data.get("custom", {})
    description = data.get("description")
    status = data.get("status", "active")
    tags = data.get("tags", [])
    license_name = data.get("license")
    repository = data.get("repository")
    auto_version = data.get("auto_version", True)
    major_change_lines = data.get("major_change_lines", 500)
    minor_change_lines = data.get("minor_change_lines", 20)

    if not isinstance(name, str) or not name.strip():
        raise ProjectMarkerError(f"{marker}: 'name' must be a non-empty string")
    if kind not in {"project", "subproject"}:
        raise ProjectMarkerError(
            f"{marker}: 'kind' must be 'project' or 'subproject'"
        )
    if not isinstance(project_type, str) or not project_type.strip():
        raise ProjectMarkerError(f"{marker}: 'type' must be a non-empty string")
    if kind == "subproject" and (not isinstance(parent, str) or not parent.strip()):
        raise ProjectMarkerError(
            f"{marker}: subprojects require a non-empty 'parent'"
        )
    if version is not None and not isinstance(version, str):
        raise ProjectMarkerError(f"{marker}: 'version' must be a string")
    if not isinstance(status, str) or not status.strip():
        raise ProjectMarkerError(f"{marker}: 'status' must be a non-empty string")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ProjectMarkerError(f"{marker}: 'tags' must be an array of strings")
    if not isinstance(auto_version, bool):
        raise ProjectMarkerError(f"{marker}: 'auto_version' must be boolean")
    if not isinstance(major_change_lines, int) or major_change_lines < 1:
        raise ProjectMarkerError(f"{marker}: 'major_change_lines' must be positive")
    if not isinstance(minor_change_lines, int) or minor_change_lines < 1:
        raise ProjectMarkerError(f"{marker}: 'minor_change_lines' must be positive")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ProjectMarkerError(f"{marker}: 'schema_version' must be positive")
    if schema_version > CURRENT_SCHEMA_VERSION:
        raise ProjectMarkerError(
            f"{marker}: schema version {schema_version} is newer than supported "
            f"version {CURRENT_SCHEMA_VERSION}"
        )
    for field_name, value in (
        ("contributors", contributors),
        ("dependencies", dependencies),
    ):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ProjectMarkerError(f"{marker}: '{field_name}' must be an array of strings")
    for field_name, value in (("environment", environment), ("custom", custom)):
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            raise ProjectMarkerError(f"{marker}: '{field_name}' must be a string table")
    if not isinstance(release_channel, str) or not release_channel.strip():
        raise ProjectMarkerError(f"{marker}: 'release_channel' must be a non-empty string")

    return Project(
        path=path,
        name=name.strip(),
        kind=kind,
        project_type=project_type.strip(),
        version=version,
        parent=parent.strip() if isinstance(parent, str) else None,
        description=description if isinstance(description, str) else None,
        status=status.strip(),
        tags=tuple(tags),
        license=license_name if isinstance(license_name, str) else None,
        repository=repository if isinstance(repository, str) else None,
        auto_version=auto_version,
        major_change_lines=major_change_lines,
        minor_change_lines=minor_change_lines,
        schema_version=schema_version,
        project_id=project_id if isinstance(project_id, str) else None,
        owner=owner if isinstance(owner, str) else None,
        contributors=tuple(contributors),
        dependencies=tuple(dependencies),
        environment=tuple(sorted(environment.items())),
        language=language if isinstance(language, str) else None,
        framework=framework if isinstance(framework, str) else None,
        release_channel=release_channel.strip(),
        created_at=created_at if isinstance(created_at, str) else None,
        updated_at=updated_at if isinstance(updated_at, str) else None,
        custom=tuple(sorted(custom.items())),
    )


def write_project_marker(
    path: Path,
    *,
    name: str,
    kind: str = "project",
    project_type: str = "unknown",
    version: str = "0.1.0",
    parent: str | None = None,
    description: str | None = None,
    status: str = "active",
    tags: tuple[str, ...] = (),
    license_name: str | None = None,
    repository: str | None = None,
    auto_version: bool = True,
    major_change_lines: int = 500,
    minor_change_lines: int = 20,
    project_id: str | None = None,
    owner: str | None = None,
    contributors: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    environment: tuple[tuple[str, str], ...] = (),
    language: str | None = None,
    framework: str | None = None,
    release_channel: str = "stable",
    created_at: str | None = None,
    updated_at: str | None = None,
    custom: tuple[tuple[str, str], ...] = (),
) -> Path:
    """Create a marker file, refusing to overwrite an existing one."""

    path.mkdir(parents=True, exist_ok=True)
    marker = path / MARKER_FILENAME
    if marker.exists():
        raise FileExistsError(f"Marker already exists: {marker}")
    if kind not in {"project", "subproject"}:
        raise ValueError("kind must be 'project' or 'subproject'")
    if kind == "subproject" and not parent:
        raise ValueError("subprojects require a parent")

    lines = [
        f'name = "{_toml_string(name)}"',
        f'kind = "{kind}"',
        f"schema_version = {CURRENT_SCHEMA_VERSION}",
        f'type = "{_toml_string(project_type)}"',
        f'version = "{_toml_string(version)}"',
        f'description = "{_toml_string(description or "")}"',
        f'status = "{_toml_string(status)}"',
        f"tags = [{', '.join(f'\"{_toml_string(tag)}\"' for tag in tags)}]",
        f'license = "{_toml_string(license_name or "")}"',
        f'repository = "{_toml_string(repository or "")}"',
        f"auto_version = {'true' if auto_version else 'false'}",
        f"major_change_lines = {major_change_lines}",
        f"minor_change_lines = {minor_change_lines}",
        f'id = "{_toml_string(project_id or "")}"',
        f'owner = "{_toml_string(owner or "")}"',
        f"contributors = [{', '.join(f'\"{_toml_string(item)}\"' for item in contributors)}]",
        f"dependencies = [{', '.join(f'\"{_toml_string(item)}\"' for item in dependencies)}]",
        f'language = "{_toml_string(language or "")}"',
        f'framework = "{_toml_string(framework or "")}"',
        f'release_channel = "{_toml_string(release_channel)}"',
        f'created_at = "{_toml_string(created_at or "")}"',
        f'updated_at = "{_toml_string(updated_at or "")}"',
    ]
    if parent:
        lines.append(f'parent = "{_toml_string(parent)}"')
    lines.extend((_toml_table("environment", environment), _toml_table("custom", custom)))
    marker.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return marker


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _toml_table(name: str, values: tuple[tuple[str, str], ...]) -> str:
    lines = [f"[{name}]"]
    lines.extend(f'{key} = "{_toml_string(value)}"' for key, value in values)
    return "\n".join(lines)
