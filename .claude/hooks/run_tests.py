"""Stop フック: Python ファイルに変更があればテストを実行し、失敗なら Claude に修正を続けさせる。

- 変更が .py 以外のみ、または tests が存在しない場合はスキップ(クォータ節約)。
- stop_hook_active が真(=すでにこのフックで続行させた後)の場合は無限ループ防止のため通す。
- 終了コード 2 で停止をブロックし、stderr が Claude に返る。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def changed_py_files():
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", "*.py"],
        capture_output=True, text=True, cwd=ROOT,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def main():
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return 0
    if not changed_py_files():
        return 0
    if not any(ROOT.glob("tests/**/test_*.py")) and not any(ROOT.glob("test_*.py")):
        return 0

    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--tb=short"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if r.returncode == 0:
        return 0
    if "No module named pytest" in r.stderr:
        print("pytest が未インストールのためテストを実行できません。", file=sys.stderr)
        return 0
    out = (r.stdout + r.stderr)[-3000:]
    print(f"テストが失敗しています。修正して通してください。\n{out}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
