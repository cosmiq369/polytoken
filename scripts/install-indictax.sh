#!/bin/sh
# Redirect setuptools metadata/build output so ../solve-it stays read-only.
set -eu
POLYTOKEN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$POLYTOKEN_ROOT"
mkdir -p .cache/indictax/metadata .cache/indictax/build
CONFIG="$POLYTOKEN_ROOT/.cache/indictax/setup.cfg"
cat > "$CONFIG" <<EOF
[egg_info]
egg_base = $POLYTOKEN_ROOT/.cache/indictax/metadata
[build]
build_base = $POLYTOKEN_ROOT/.cache/indictax/build
EOF
export DIST_EXTRA_CONFIG="$CONFIG"
export UV_CACHE_DIR="$POLYTOKEN_ROOT/.cache/uv"
uv pip install --python "$POLYTOKEN_ROOT/.venv/bin/python" --editable ../solve-it
