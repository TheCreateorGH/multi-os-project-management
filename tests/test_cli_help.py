import pytest

from project_manager.cli import build_parser


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["scan", "--help"], "Discover project markers recursively below a collection folder."),
        (["init", "--help"], "Human-readable project name."),
        (["tui", "--help"], "Open the interactive Textual interface for discovered projects."),
        (["workspace", "--help"], "Manage configured workspace folders and project inventory tools."),
        (["workspace", "add", "--help"], "Folder path to register."),
        (["workspace", "remove", "--help"], "Folder path to unregister."),
        (["workspace", "search", "--help"], "Case-insensitive text query."),
        (["workspace", "export", "--help"], "Output file path (.json or .csv)."),
        (["workspace", "graph", "--help"], "Output format for dependency graph."),
        (["check", "--help"], "Run project health checks for the nearest marked project."),
        (["doctor", "--help"], "Show actionable project diagnostics."),
        (["version", "--help"], "Preview or apply semantic version changes based on project rules."),
        (["version", "preview", "--help"], "Commit message hint used for bump intent (repeatable)."),
        (["version", "bump", "--help"], "Bump level to apply."),
        (["open", "--help"], "Exact project name to open."),
        (["history", "--help"], "Show Git history for the .project.toml marker in a project."),
        (["git", "--help"], "Run project-aware Git helpers"),
    ],
)
def test_command_help_is_available(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args(argv)

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert expected in output
