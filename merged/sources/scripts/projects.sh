#!/usr/bin/env bash
# Run a command inside one or all projects. Author: Juan-Louw Greyling
# Usage: scripts/projects.sh list | install [path|all] | test [path|all] | build [path|all]
set -uo pipefail
cd "$(dirname "$0")/.."
cmd="${1:-list}"
target="${2:-all}"
paths() {
  python3 -c "import json;[print(p['path']+' '+p['kind']+' '+p.get('dir',p['path'])) for p in json.load(open('projects.json'))['projects']]" 
}
run() {
  local p=$1 k=$2 a=$3 dir=$4 status=0
  if ! pushd "$dir" >/dev/null; then
    echo "   missing project directory: $dir" >&2
    return 1
  fi
  case "$k:$a" in
    node:install|expo:install) npm install || status=$? ;;
    node:test|expo:test) npm test --if-present || status=$? ;;
    node:build) npm run build --if-present || status=$? ;;
    pnpm:install) pnpm install || status=$? ;;
    pnpm:test) pnpm -r --if-present test || status=$? ;;
    pnpm:build) pnpm -r --if-present build || status=$? ;;
    python:install)
      if [ -f requirements.txt ]; then pip install -r requirements.txt || status=$?
      elif [ -f pyproject.toml ]; then pip install -e . || status=$?
      else echo "   no Python dependency manifest; refusing guessed installation" >&2; status=2
      fi ;;
    python:test) python -m pytest -q || status=$? ;;
    android:build) ./gradlew assembleDebug || status=$? ;;
    *) echo "   no automated $a command for project kind $k" ;;
  esac
  popd >/dev/null || return 1
  return "$status"
}
case "$cmd" in
  list) paths | awk '{printf "%-45s %s\n", $1, $2}' ;;
  install|test|build)
    failed=0
    while read -r p k dir; do
      [ "$target" = all ] || [ "$target" = "$p" ] || continue
      echo "==> $cmd $p"
      if run "$p" "$k" "$cmd" "$dir"; then
        echo "   PASS: $p"
      else
        echo "   FAILED: $p" >&2
        failed=1
      fi
    done < <(paths)
    exit "$failed" ;;
  *) echo "usage: $0 list|install|test|build [path|all]" >&2; exit 2 ;;
esac
