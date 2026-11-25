#!/usr/bin/env bash
# Run commands against projects listed in the root projects.json catalog.
# Usage: scripts/projects.sh list | install|test|build [catalog-path|all]
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALOG="${PROJECTS_CATALOG:-$ROOT/projects.json}"
cd "$ROOT"

usage() {
  echo "usage: $0 list|install|test|build [catalog-path|all]" >&2
  exit 2
}

catalog_rows() {
  python3 - "$CATALOG" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
try:
    payload = json.loads(source.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"cannot read project catalog {source}: {exc}")
projects = payload.get("projects")
if not isinstance(projects, list):
    raise SystemExit("project catalog must contain a projects array")
seen = set()
supported = {"node", "expo", "pnpm", "python", "static", "android"}
for item in projects:
    if not isinstance(item, dict):
        raise SystemExit("every project entry must be an object")
    path = item.get("path")
    kind = item.get("kind")
    directory = item.get("dir", path)
    if not isinstance(path, str) or not path or path in seen:
        raise SystemExit(f"invalid or duplicate project path: {path!r}")
    if not isinstance(directory, str) or not directory:
        raise SystemExit(f"invalid directory for {path}")
    if not isinstance(kind, str) or kind not in supported:
        raise SystemExit(f"unsupported project kind for {path}: {kind!r}")
    if any("\t" in value or "\n" in value for value in (path, kind, directory)):
        raise SystemExit(f"tab/newline is not allowed in catalog fields: {path}")
    candidate = Path(directory)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe project directory for {path}: {directory}")
    root = Path.cwd().resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise SystemExit(f"project directory escapes repository root: {directory}")
    seen.add(path)
    print(path, kind, directory, sep="\t")
PY
}

run_project() {
  local project="$1" kind="$2" action="$3" directory="$4"
  if [[ ! -d "$ROOT/$directory" ]]; then
    echo "ERROR: project directory does not exist: $directory" >&2
    return 1
  fi
  cd "$ROOT/$directory"
  case "$kind:$action" in
    node:install|expo:install)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
      ;;
    node:test|expo:test)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      npm test --if-present
      ;;
    node:build|expo:build)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      npm run build --if-present
      ;;
    pnpm:install)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      if [[ -f pnpm-lock.yaml ]]; then pnpm install --frozen-lockfile; else pnpm install; fi
      ;;
    pnpm:test)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      pnpm -r --if-present test
      ;;
    pnpm:build)
      [[ -f package.json ]] || { echo "ERROR: missing package.json in $directory" >&2; return 1; }
      pnpm -r --if-present build
      ;;
    python:install)
      if [[ -f requirements.txt ]]; then
        python3 -m pip install -r requirements.txt
      elif [[ -f pyproject.toml || -f setup.py ]]; then
        python3 -m pip install -e .
      else
        echo "ERROR: no Python dependency manifest in $directory" >&2
        return 1
      fi
      ;;
    python:test)
      if [[ -d tests ]] || compgen -G "test_*.py" >/dev/null || compgen -G "*_test.py" >/dev/null; then
        python3 -m pytest -q
      else
        echo "SKIP: no Python test suite declared in $directory"
      fi
      ;;
    python:build)
      python3 -m compileall -q .
      ;;
    static:install)
      echo "SKIP: static project has no dependency installation"
      ;;
    static:test|static:build)
      if ! find . -type f -name index.html -print -quit | grep -q .; then
        echo "ERROR: no index.html found in static project $directory" >&2
        return 1
      fi
      echo "OK: static entry point exists in $directory"
      ;;
    android:install)
      echo "SKIP: Android dependencies are resolved by the Gradle wrapper during build"
      ;;
    android:test)
      if [[ -x ./gradlew ]]; then ./gradlew test; else echo "SKIP: no checked-in Gradle wrapper in $directory"; fi
      ;;
    android:build)
      if [[ -x ./gradlew ]]; then ./gradlew assembleDebug; else echo "SKIP: no checked-in Gradle wrapper in $directory"; fi
      ;;
    *)
      echo "ERROR: unsupported action $kind:$action" >&2
      return 2
      ;;
  esac
}

cmd="${1:-list}"
target="${2:-all}"
case "$cmd" in
  list)
    catalog_rows | awk -F '\t' '{ printf "%-45s %-8s %s\n", $1, $2, $3 }'
    ;;
  install|test|build)
    found=0
    failures=0
    rows="$(catalog_rows)"
    while IFS=$'\t' read -r project kind directory; do
      [[ -n "$project" ]] || continue
      if [[ "$target" != all && "$target" != "$project" ]]; then
        continue
      fi
      found=1
      echo "==> $cmd $project ($kind)"
      if ! run_project "$project" "$kind" "$cmd" "$directory"; then
        echo "FAILED: $project" >&2
        failures=$((failures + 1))
      fi
    done <<< "$rows"

    if [[ "$found" -eq 0 ]]; then
      echo "ERROR: no catalog entry matches '$target'" >&2
      exit 2
    fi
    if [[ "$failures" -gt 0 ]]; then
      echo "$failures project operation(s) failed." >&2
      exit 1
    fi
    ;;
  *)
    usage
    ;;
esac
