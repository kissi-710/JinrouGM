# 05 データ・イベントログ・エクスポート

## 1. 方針
- SQLite に保存する。ゲームの状態は **append-only のイベントログ** から再構成できるようにする(event sourcing)。
- クラッシュから復帰するときは、最新のスナップショット+それ以降のイベントを再生する。スナップショットはフェーズ開始ごとに取る。〔仮決定 U-44〕
- 時刻はすべて UTC の ISO 8601 で保存する。

## 2. テーブル

### `guild_config`
| 列 | 型 | 内容 |
|---|---|---|
| `guild_id` | TEXT PK | サーバー ID |
| `admin_user_ids` | TEXT(JSON 配列) | 運営者。初期値はサーバーオーナー |
| `channels` | TEXT(JSON) | `lobby` `village` `log` `wolves` `graveyard` `debug` の ID、PRIV カテゴリ ID の配列 |
| `roles` | TEXT(JSON) | `spectator` などの Discord ロール ID |
| `verbose_debug` | INTEGER | 0/1(既定 0) |

### `registrations`
| 列 | 型 | 内容 |
|---|---|---|
| `guild_id`, `user_id` | TEXT PK | 人間または Bot のユーザー ID |
| `kind` | TEXT | `human` / `bot` |
| `owner_user_id` | TEXT | Bot の持ち主(人間は自分) |
| `display_name` | TEXT | |
| `priv_channel_id` | TEXT | 個人部屋 |
| `registered_by` | TEXT | 登録した人 |
| `status` | TEXT | `active` / `archived` |
| `created_at` | TEXT | |

### `games`
| 列 | 型 | 内容 |
|---|---|---|
| `game_id` | TEXT PK | `g<YYYYMMDD>-<その日の連番3桁>`(例 `g20261121-001`)〔仮決定 U-45〕 |
| `guild_id` | TEXT | |
| `created_by` | TEXT | セッション開始者 |
| `status` | TEXT | `lobby` / `running` / `finished` / `aborted` |
| `profile_input` | TEXT | `/session` で受け取った文字列 |
| `profile_json` | TEXT | `/start` で確定した完全な JSON |
| `seed` | INTEGER | 乱数シード |
| `winner` | TEXT | `village` / `werewolf` / `draw` / NULL |
| `flags` | TEXT(JSON) | `{"sudden_death": true}` など |
| `created_at`, `started_at`, `ended_at` | TEXT | |

### `game_players`
| 列 | 型 | 内容 |
|---|---|---|
| `game_id`, `user_id` | TEXT PK | |
| `idx` | INTEGER | index(0 始まり) |
| `role` | TEXT | 役職 ID |
| `alive` | INTEGER | 0/1 |
| `death_day`, `death_cause` | INTEGER, TEXT | `executed` / `attacked` / `sudden` |

### `events`
| 列 | 型 | 内容 |
|---|---|---|
| `game_id` | TEXT | |
| `seq` | INTEGER | 試合内の連番(PK は `game_id, seq`) |
| `ts` | TEXT | |
| `type` | TEXT | 下記 |
| `actor` | TEXT | 実行者のユーザー ID(GM なら `gm`) |
| `payload` | TEXT(JSON) | |
| `secret` | INTEGER | 1 なら試合中は秘匿(エクスポートで区別する) |

### `snapshots`
`game_id`, `seq`(このイベントまでを反映), `state`(JSON)。

## 3. イベントの種類
| type | 秘匿 | payload |
|---|---|---|
| `game_created` | — | プロファイル入力 |
| `player_joined` / `player_left` | — | user_id |
| `game_started` | 秘匿 | 確定プロファイル、seed、index と役職の対応 |
| `phase_started` | — | phase, day, deadline |
| `speech` | — | message_id, idx, text(受信時点の本文) |
| `speech_rejected` | — | idx, code |
| `message_edited` / `message_deleted` | — | message_id, 新本文 |
| `wolf_chat` | 秘匿 | idx, text |
| `co` | — | idx, role, results |
| `pass` | — | idx |
| `action_submitted` | 秘匿 | idx, kind, target(上書きも 1 件ずつ記録) |
| `action_resolved` | 秘匿 | 確定した襲撃先・護衛結果・占い/霊媒結果 |
| `vote_submitted` | 秘匿(公開設定なら締切後に公開) | idx, target |
| `vote_resolved` | — | tally, executed, runoff |
| `death` | — | idx, cause |
| `admin_action` | — | kind(`abort`/`suddendeath`), by, target |
| `game_over` | — | winner, roles |

- コマンドの拒否(`E_*`)もイベントとして残す(感想戦で AI の誤操作を見られるように)。

## 4. エクスポート
- 試合終了時に JSON と Markdown を作り、`#log` に添付する。`/export` でも取得できる。
- JSON:`games` 行、`game_players`、全イベント(秘匿イベントを含む)。
- Markdown:日ごとに「議論 → 投票 → 夜の行動 → 結果」の順に並べた読み物。人狼部屋の会話を含める。
- 戦績(勝率・投票精度・嘘見破り率)の集計は M4 で扱う。この版ではイベントログに必要な情報を残すことだけを決める。
