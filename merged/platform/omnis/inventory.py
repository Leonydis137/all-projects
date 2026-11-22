# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Static analysis of everything in sources/: size, languages, Python structure,
third-party dependencies and TODO density per project. Run as a module to (re)build catalog.json:
    python -m omnis.inventory > catalog.json"""
import ast
import json
import sys
from collections import Counter
from pathlib import Path

from .config import CATALOG, SOURCES

SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build", ".gradle", "coverage"}
CODE_EXT = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
            ".tsx": "TypeScript", ".kt": "Kotlin", ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
            ".yml": "YAML", ".yaml": "YAML", ".md": "Markdown", ".json": "JSON"}
STDLIB = set(getattr(sys, "stdlib_module_names", ()))


def _files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            yield p


def scan_project(root: Path) -> dict:
    langs, loc, size, n = Counter(), Counter(), 0, 0
    py = {"files": 0, "classes": 0, "functions": 0, "syntax_errors": 0}
    deps: Counter = Counter()
    todos = 0
    for f in _files(root):
        n += 1
        size += f.stat().st_size
        lang = CODE_EXT.get(f.suffix.lower())
        if not lang or f.stat().st_size > 2_000_000:
            continue
        langs[lang] += 1
        try:
            text = f.read_text(encoding="utf8", errors="ignore")
        except OSError:
            continue
        if lang in ("Markdown", "JSON", "YAML"):
            continue
        loc[lang] += text.count("\n") + 1
        todos += text.count("TODO") + text.count("FIXME")
        if lang == "Python":
            py["files"] += 1
            try:
                tree = ast.parse(text)
            except SyntaxError:
                py["syntax_errors"] += 1
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    py["classes"] += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    py["functions"] += 1
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        deps[a.name.split(".")[0]] += 1
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    deps[node.module.split(".")[0]] += 1
    local = {p.name for p in root.iterdir()} if root.is_dir() else set()
    third = {k: v for k, v in deps.most_common() if k not in STDLIB and k not in local and k not in ("src", "covenant", "app")}
    return {"files": n, "bytes": size, "languages": dict(langs.most_common()), "loc": dict(loc.most_common()),
            "python": py, "python_deps": dict(list(third.items())[:15]), "todos": todos}


def build(projects: list[dict]) -> dict:
    out = []
    for p in projects:
        root = SOURCES / p["path"]
        out.append({**p, **(scan_project(root) if root.is_dir() else {"missing": True})})
    totals = Counter()
    for p in out:
        for k in ("files", "bytes", "todos"):
            totals[k] += p.get(k, 0)
        for lang, v in p.get("loc", {}).items():
            totals["loc:" + lang] += v
    return {"projects": out, "totals": dict(totals)}


def main() -> None:
    projects = json.loads((SOURCES / "projects.json").read_text())["projects"]
    json.dump(build(projects), sys.stdout, indent=1)


if __name__ == "__main__":
    main()
