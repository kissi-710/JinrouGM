# 03 プロファイル(試合設定)

## 1. 指定方法
- `/session profile:<文字列>`(AI は `!session <文字列>`)。
- 文字列が `{` で始まれば JSON、それ以外はプリセット名。プリセット名は autocomplete で候補を出す。
- ファイル添付は使わない。
- プリセットはリポジトリの `presets/*.json` に置く(プロファイルエディタの出力と同じ形式)。〔仮決定 U-36〕
- 初期プリセット:`standard`(全項目既定値、役職は人数表)、`quick`(議論 300 秒・夜 90 秒・投票 60 秒)。〔仮決定 U-37〕

## 2. JSON の形式(schema 1)

```json
{
  "schema": 1,
  "name": "standard",
  "roles": {"werewolf": 2, "seer": 1, "medium": 1, "knight": 1, "villager": 3},
  "first_divine": "free",
  "first_attack": false,
  "wolf_decide": "leader",
  "attack_timeout": "random",
  "knight": {"repeat": false, "self": false},
  "tie": {"runoff": 1, "then": "random"},
  "vote_open": "open",
  "no_vote": "abstain",
  "time": {"discuss": 600, "vote": 120, "runoff": 120, "night": 180},
  "speech": {"cooldown": 30, "max_chars": 400, "max_speeches": null},
  "max_days": 20
}
```

- `schema` 以外は全て省略でき、省略した項目は既定値になる。`roles` を省略したら人数表([01 §2](01_game_rules.md))を使う。
- 出力は minify する。キーは上記の英語名で固定する(短縮しすぎると読めなくなるため、これ以上は詰めない)。〔仮決定 U-38〕

## 3. 項目と範囲

| キー | 型 | 既定 | 許す値・範囲 |
|---|---|---|---|
| `schema` | int | — (必須) | `1` |
| `name` | string | `"custom"` | 1〜32 文字 |
| `roles` | object | 人数表 | キーは役職 ID の許可リスト。値は 0〜15 の整数 |
| `first_divine` | string | `"free"` | `free` / `random_white` / `none` |
| `first_attack` | bool | `false` | |
| `wolf_decide` | string | `"leader"` | `leader` / `majority` / `random` |
| `attack_timeout` | string | `"random"` | `random` / `none` |
| `knight.repeat` | bool | `false` | 連続護衛を許すか |
| `knight.self` | bool | `false` | 自分の護衛を許すか |
| `tie.runoff` | int | `1` | 0〜2 |
| `tie.then` | string | `"random"` | `random` / `none` |
| `vote_open` | string | `"open"` | `open` / `secret` |
| `no_vote` | string | `"abstain"` | `abstain` / `random` |
| `time.discuss` | int 秒 | 600 | 60〜3600 |
| `time.vote` | int 秒 | 120 | 30〜600 |
| `time.runoff` | int 秒 | 120 | 30〜600 |
| `time.night` | int 秒 | 180 | 30〜600 |
| `speech.cooldown` | int 秒 | 30 | 0〜300 |
| `speech.max_chars` | int | 400 | 50〜1000 |
| `speech.max_speeches` | int / null | null | 1〜100 / null(上限なし) |
| `max_days` | int | 20 | 3〜30 |

- 範囲は「他の参加者に不利益を与える値を拒否する」ための上限・下限。〔仮決定 U-39:各数値〕

## 4. GM 側の検証
1. 全角引用符(`“ ” ‘ ’`)を半角に、全角の `{ } : ,` を半角に正規化する。
2. JSON として解析する(サイズ上限 6000 文字。AI の `!session` はメッセージの上限で実質 2000 文字)。評価・実行はしない。
3. JSON Schema で検証する。未知のキーは拒否する(打ち間違いに気づけるように)。〔仮決定 U-40〕
4. `schema` が古い版なら、現行の形式に変換してから検証する。
5. エラーは `E_PROFILE` で、項目のパスと理由を返す(例:`time.night: 30〜600 の範囲外 (5)`)。
6. `roles` の合計と参加者数の一致は `/start` 時に検証する(`/session` 時点では人数が決まらないため)。

## 5. 確定と保存
- `/start` 時に、既定値を埋め、`roles` を確定した完全な JSON を作る。これを `#lobby` に公開し、`games.profile_json` に丸ごと保存する。
- JSON Schema は Engine パッケージに 1 つ置き、プロファイルエディタと GM で共有する。

## 6. プロファイルエディタ
- 静的な HTML/CSS/JS(`packages/profile-editor/`、サーバー不要)。スマホ表示に対応。
- フォーム入力から JSON を作り、コピーボタンで出力する。既定値と同じ項目は出力から省く(短くするため)。
- 出力が 2000 文字を超えたら「AI の `!session` では送れない」と警告する。6000 文字を超えたら出力しない。
- プリセットを読み込んで編集を始められる。
