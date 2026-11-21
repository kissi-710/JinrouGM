"""PostToolUse フック: 複雑さを解析して WARNINGS.md を毎回上書き生成する(警告のみ・ブロックしない)。

指標: 関数の循環的複雑度 / 引数の数 / 関数の長さ / ネストの深さ /
      ファイルの長さ / import 数(依存先) / 他ファイルからの被 import 数(依存元)
しきい値は THRESHOLDS を編集して調整する。常に終了コード 0。
"""
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE = {".venv", "venv", ".git", ".claude", "node_modules", "__pycache__", "tests"}
THRESHOLDS = {
    "complexity": 10,
    "args": 5,
    "func_lines": 50,
    "nesting": 4,
    "file_lines": 300,
    "imports": 15,
    "fan_in": 8,
}
BRANCH_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
                ast.With, ast.AsyncWith, ast.IfExp, ast.comprehension, ast.Assert)
NEST_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)


def complexity(func):
    score = 1
    for n in ast.walk(func):
        if isinstance(n, BRANCH_NODES):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
    return score


def max_nesting(node, depth=0):
    deepest = depth
    for child in ast.iter_child_nodes(node):
        d = depth + 1 if isinstance(child, NEST_NODES) else depth
        deepest = max(deepest, max_nesting(child, d))
    return deepest


def py_files():
    return [p for p in ROOT.rglob("*.py")
            if not (set(p.relative_to(ROOT).parts) & EXCLUDE)]


def analyze(path, tree, text, warnings):
    rel = path.relative_to(ROOT).as_posix()
    lines = len(text.splitlines())
    if lines > THRESHOLDS["file_lines"]:
        warnings.append(f"`{rel}`: ファイルが長い ({lines}行 > {THRESHOLDS['file_lines']})")
    imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {(n.module or "").split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom) and n.level == 0}
    imports.discard("")
    if len(imports) > THRESHOLDS["imports"]:
        warnings.append(f"`{rel}`: 依存先が多い ({len(imports)}モジュール > {THRESHOLDS['imports']})")
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = n.args
        nargs = len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs) + bool(a.vararg) + bool(a.kwarg)
        if nargs and a.args and a.args[0].arg in ("self", "cls"):
            nargs -= 1
        checks = [
            ("complexity", complexity(n), "循環的複雑度が高い"),
            ("args", nargs, "引数が多い"),
            ("func_lines", (n.end_lineno or n.lineno) - n.lineno + 1, "関数が長い"),
            ("nesting", max_nesting(n), "ネストが深い"),
        ]
        for key, value, label in checks:
            if value > THRESHOLDS[key]:
                warnings.append(f"`{rel}:{n.lineno}` `{n.name}()`: {label} ({value} > {THRESHOLDS[key]})")
    return imports


def main():
    try:
        json.load(sys.stdin)
    except ValueError:
        pass
    files = py_files()
    stems = {p.stem for p in files}
    fan_in = defaultdict(set)
    warnings = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            warnings.append(f"`{p.relative_to(ROOT).as_posix()}`: 構文エラー ({e.msg})")
            continue
        for mod in analyze(p, tree, text, warnings):
            if mod in stems and mod != p.stem:
                fan_in[mod].add(p.stem)
    for mod, importers in fan_in.items():
        if len(importers) > THRESHOLDS["fan_in"]:
            warnings.append(f"`{mod}.py`: 依存元が多い ({len(importers)}ファイルから参照 > {THRESHOLDS['fan_in']})")

    out = ROOT / "WARNINGS.md"
    if warnings:
        body = "# WARNINGS\n\n複雑さの警告です(自動生成・編集不要・コミット対象外)。\n\n"
        body += "\n".join(f"- {w}" for w in sorted(warnings)) + "\n"
        out.write_text(body, encoding="utf-8")
    elif out.exists():
        out.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
