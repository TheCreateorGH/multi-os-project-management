# Multi OS Project Management

Cross-platform project management application for Windows, macOS, and Linux.

The first usable slice is a project-aware folder scanner with a Textual TUI.
Folders become projects by containing a `.project.toml` marker:

```toml
name = "Website"
kind = "project"
type = "application"
version = "0.1.0"
description = "The public website"
status = "active"
tags = ["web", "production"]
license = "MIT"
auto_version = true
major_change_lines = 500
minor_change_lines = 20
```

Subprojects use the same marker and identify their parent:

```toml
name = "Frontend"
kind = "subproject"
parent = "Website"
type = "component"
```

The marker is deliberately TOML so it is human-editable, cross-platform, and
supported by Python's standard library. A collection folder has no marker of
its own; the scanner can then discover projects and nested subprojects below
it. Once a project marker is found, ordinary folders below it are not treated
as separate projects unless they contain their own marker.

## Usage

```bash
project-manager scan ~/Projects
project-manager init ~/Projects/Website --name Website --type application
project-manager tui ~/Projects
pm workspace add ~/Projects
pm workspace scan
pm workspace search web
pm workspace export projects.json
pm workspace graph --format dot
pm open Website
pm history
pm check
pm doctor
pm version preview
pm version preview --message "feat: add API"
pm git install-hooks
pm git init
pm git commit -m "Implement feature"
```

Run `project-manager tui` without a path to scan the current directory.
`pm` is an alias for `project-manager`. The workspace registry is stored in
`%APPDATA%/project-manager/config.toml` on Windows and
`$XDG_CONFIG_HOME/project-manager/config.toml` (or `~/.config/...`) on Linux.
Use it as the central place for collection folders while every command remains
usable with an explicit path.

## Git and versioning

Git commands are intentionally project-scoped: a `.project.toml` must be found
in the current folder or one of its parents. `pm git commit` analyzes staged
changes (or the working-tree diff), counts added and deleted lines, and bumps
the marker version:

* up to `minor_change_lines`: patch
* above that up to `major_change_lines`: minor
* at or above `major_change_lines`: major, but only after explicit approval

Commands with no project-specific behavior are passed through unchanged. For
example, `pm git remote -v` executes `git remote -v`, while still enforcing the
project boundary.

Useful project commands include:

* `pm check` reports README, test, CI, manifest, dependency, and Git health.
* `pm doctor` prints actionable diagnostics, including missing hooks.
* `pm version preview` explains the proposed bump without changing files;
  repeat `--message` for conventional-commit intent (`feat`, `fix`, or `!`).
* `pm git install-hooks` installs a project-local pre-commit hook.
* `pm git changelog` generates `CHANGELOG.md`; `pm git release` creates a tag.

The marker supports schema-versioned metadata including owners, contributors,
dependencies, environment values, language/framework, release channel,
timestamps, custom string fields, and subproject relationships. Dependencies
and parent references are validated during scans, including cycle detection.

Use `completions/pm.bash` for Bash/Zsh and `completions/pm.ps1` for PowerShell.
For standalone distribution, install the optional `binary` extra and run
`scripts/build-binary.sh` on Linux or `scripts/build-binary.ps1` on Windows.
The resulting `pm` executable keeps the same command interface without
requiring a separate Python installation.
