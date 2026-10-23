from pathlib import Path

import pytest

from project_manager.models import ProjectMarkerError, load_project, write_project_marker
from project_manager.scanner import discover_projects
from project_manager.versioning import recommend_level


def test_discover_collection_and_subproject(tmp_path: Path) -> None:
    project_path = tmp_path / "Website"
    subproject_path = project_path / "frontend"
    write_project_marker(
        project_path, name="Website", project_type="application", version="1.2.0"
    )
    write_project_marker(
        subproject_path,
        name="Frontend",
        kind="subproject",
        parent="Website",
        project_type="component",
    )
    (project_path / "docs").mkdir()

    projects, errors = discover_projects(tmp_path)

    assert errors == []
    assert [project.name for project in projects] == ["Frontend", "Website"]
    assert projects[0].is_subproject


def test_invalid_subproject_marker_is_reported(tmp_path: Path) -> None:
    marker = tmp_path / ".project.toml"
    marker.write_text('name = "Broken"\nkind = "subproject"\n', encoding="utf-8")

    projects, errors = discover_projects(tmp_path)

    assert projects == []
    assert len(errors) == 1
    assert "require a non-empty 'parent'" in errors[0]


def test_load_project_requires_marker(tmp_path: Path) -> None:
    with pytest.raises(ProjectMarkerError, match="Missing"):
        load_project(tmp_path)


def test_extended_metadata_round_trips(tmp_path: Path) -> None:
    write_project_marker(
        tmp_path,
        name="Tool",
        description="A utility",
        tags=("cli", "python"),
        license_name="MIT",
        major_change_lines=1000,
    )

    project = load_project(tmp_path)

    assert project.description == "A utility"
    assert project.tags == ("cli", "python")
    assert project.license == "MIT"
    assert project.major_change_lines == 1000


def test_relationships_and_schema_metadata_round_trip(tmp_path: Path) -> None:
    write_project_marker(
        tmp_path,
        name="App",
        owner="alice",
        dependencies=("Library",),
        environment=(("python", "3.12"),),
        custom=(("team", "core"),),
    )

    project = load_project(tmp_path)

    assert project.schema_version == 1
    assert project.owner == "alice"
    assert project.dependencies == ("Library",)
    assert project.environment == (("python", "3.12"),)
    assert project.custom == (("team", "core"),)


def test_change_size_and_commit_intent_recommend_levels(tmp_path: Path) -> None:
    write_project_marker(tmp_path, name="App", major_change_lines=100, minor_change_lines=10)
    project = load_project(tmp_path)

    assert recommend_level(2, project)[0] == "patch"
    assert recommend_level(11, project)[0] == "minor"
    assert recommend_level(100, project)[0] == "major"
    assert recommend_level(1, project, commits=("feat: add API",))[0] == "minor"
    assert recommend_level(1, project, commits=("feat!: remove API",))[0] == "major"
    assert recommend_level(1, project, commits=("old feat: unrelated",))[0] == "patch"
