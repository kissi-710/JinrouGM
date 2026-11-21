"""PreToolUse フック: main ブランチ上での git commit と、ファイル編集をブロックする。

例外: コミットがまだ1つもないリポジトリ(最初のルートコミット)は許可する。
終了コード 2 でブロックし、stderr のメッセージが Claude に返る。
"""
import json
import re
import subprocess
import sys

PROTECTED = {"main", "master"}


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main():
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool == "Bash":
        if not re.search(r"\bgit\s+commit\b", tool_input.get("command", "")):
            return 0
    elif tool not in ("Edit", "Write"):
        return 0

    code, _ = git("rev-parse", "--verify", "HEAD")
    if code != 0:  # 初回コミット前は許可
        return 0

    _, branch = git("branch", "--show-current")
    if branch in PROTECTED:
        print(
            f"ブランチ '{branch}' への直接の編集・コミットは禁止です(CLAUDE.md)。"
            "作業ブランチを作成して切り替えてからやり直してください。",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
