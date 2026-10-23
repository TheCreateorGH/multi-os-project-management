"""Central workspace registry for folders managed by the application."""

from __future__ import annotations

import os
from pathlib import Path
import tomllib


def config_path() -> Path:
    base = os.environ.get("PROJECT_MANAGER_HOME")
    if not base:
        base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config")
        )
    return Path(base) / "project-manager" / "config.toml"


def load_roots() -> list[Path]:
    path = config_path()
    if not path.is_file():
        return []
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    roots = data.get("roots", [])
    return [Path(root).expanduser().resolve() for root in roots if isinstance(root, str)]


def add_root(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    roots = load_roots()
    if root not in roots:
        roots.append(root)
    _save_roots(roots)
    return roots


def remove_root(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    roots = [item for item in load_roots() if item != root]
    _save_roots(roots)
    return roots


def _save_roots(roots: list[Path]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "roots = [\n" + "".join(f'    "{_toml_string(str(root))}",\n' for root in roots)
    path.write_text(content + "]\n", encoding="utf-8")


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
