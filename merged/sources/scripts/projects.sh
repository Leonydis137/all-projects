#!/usr/bin/env bash
# Run a command inside one or all projects. Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
# Usage: scripts/projects.sh list | install [path|all] | test [path|all] | build [path|all]
set -uo pipefail
cd "$(dirname "$0")/.."
cmd="${1:-list}"; target="${2:-all}"
paths() { python3 -c "import json;[print(p['path']+' '+p['kind']+' '+p.get('dir',p['path'])) for p in json.load(open('projects.json'))['projects']]"; }
run() { # path kind action
  local p=$1 k=$2 a=$3 dir=$4; pushd "$dir" >/dev/null || return
  case "$k:$a" in
    node:install|expo:install) npm install ;;
    node:test|expo:test) npm test --if-present ;;
    node:build) npm run build --if-present ;;
    pnpm:install) pnpm install ;;
    pnpm:test) pnpm -r --if-present test ;;
    pnpm:build) pnpm -r --if-present build ;;
    python:install) [ -f requirements.txt ] && pip install -r requirements.txt || pip install -e . ;;
    python:test) python -m pytest -q ;;
    android:build) ./gradlew assembleDebug ;;
    *) echo "  (nothing to do for $k:$a)" ;;
  esac
  popd >/dev/null
}
case "$cmd" in
  list) paths | awk '{printf "%-45s %s\n", $1, $2}' ;;
  install|test|build)
    paths | while read -r p k dir; do
      [ "$target" = all ] || [ "$target" = "$p" ] || continue
      echo "==> $cmd $p"; run "$p" "$k" "$cmd" "$dir" || echo "   FAILED: $p"
    done ;;
  *) echo "usage: $0 list|install|test|build [path|all]"; exit 1 ;;
esac
