#!/usr/bin/env bash
# Render the Quarto site (site/ -> site/_site) with the project's Python environment.
# Usage: ./scripts/render_site.sh            render
#        ./scripts/render_site.sh publish    render and push to the gh-pages branch
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group site
uv run python site/_sync_assets.py   # docs pages must exist before Quarto scans the project
QUARTO_PYTHON="$(uv run --group site python -c 'import sys; print(sys.executable)')"
export QUARTO_PYTHON
if [[ "${1:-}" == "publish" ]]; then
  uv run --group site quarto publish gh-pages site --no-prompt
else
  uv run --group site quarto render site
fi
