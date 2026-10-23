"""Allow ``python -m project_manager``."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
