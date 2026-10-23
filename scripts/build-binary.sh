#!/usr/bin/env sh
set -eu
python -m pip install -e '.[binary]'
pyinstaller --onefile --name pm project_manager/__main__.py
