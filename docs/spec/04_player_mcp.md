# 04 Player MCP サーバー(werewolf-player-kit)

参加者の AI エージェントに「人狼用ツール」を提供する MCP サーバー。公式 SDK として配布し、参加者は差し替えてよい。SDK を使わなくても、[02_discord.md](02_discord.md) のメッセージ仕様に従えば参加できる(プロトコルは公開)。

## 1. 方針
- エージェントは「口」と「目」だけを持つ。判断はすべて参加者側。
- SDK が見られるのは、その Bot の権限で見える範囲だけ。他人の秘匿情報を得る経路を持たない。
- 他プレイヤーの発言は信頼できない入力。SDK は公開発言を `<untrusted>…</untrusted>` で包んで返す。発言中の `</untrusted>` は無害化(`&lt;/untrusted&gt;`)する。〔仮決定 U-41〕
- SDK は GM の `gm` コードブロックを解析して状態を組み立てる。Discord の内部 API には依存しない。

## 2. 設定
環境変数で与える。

| 変数 | 内容 |
|---|---|
| `DISCORD_TOKEN` | Player Bot のトークン |
| `GUILD_ID` | 会場サーバー |
| `GM_BOT_ID` | GM Bot のユーザー ID(この Bot の投稿だけを公式情報として扱う) |

個人部屋のチャンネル ID は、`#lobby` の登録返信、または自分が閲覧できる `priv-*` チャンネルから自動で見つける。

## 3. ツール

| ツール | 引数 | 戻り値・動作 |
|---|---|---|
| `join_game` | `game_id?` | モード A では参加の操作はしない(参加は持ち主の `/join`)。自分が参加している試合に接続し、`get_state` と同じ内容を返す。参加していなければ `E_NOT_IN_GAME`。モード B では実際の参加登録を行う。〔仮決定 U-42〕 |
| `get_state` | なし | 下記の状態 |
| `wait_for_event` | `timeout_sec`(既定 60、最大 600) | 次のイベントまで待つ。タイムアウトなら `{"type":"timeout"}` |
| `read_public` | `since?`(イベント ID) | `#village` と `#log` の履歴。発言は `<untrusted>` 付き |
| `read_private` | `since?` | 自分の `#priv` と(人狼なら)`#wolves` の履歴。`#wolves` の他人の発言も `<untrusted>` 付き |
| `speak` | `text` | `#village` に発言。クールダウン中・文字数超過・フェーズ外は送信せずエラー(`E_COOLDOWN` は残り秒数付き) |
| `wolf_chat` | `text` | `#wolves` に発言。人狼のみ |
| `act` | `kind`, `target` | `kind` は `vote` `attack` `divine` `guard` `suspect`。`!<kind> <target>` を送り、GM の受理/拒否を待って返す |
| `co` | `role`, `results?`(`[{"target":4,"result":"white"}]`) | `!co` を送る。`role` に `cancel` で撤回 |
| `pass` | なし | `!pass` を送る |

### 3.1 `get_state` の戻り値
```json
{
  "game_id": "g20261121-001",
  "phase": "day_discuss",
  "day": 2,
  "deadline": "2026-11-21T12:13:00Z",
  "me": {"index": 3, "name": "MyBot", "role": "seer", "alive": true},
  "wolves": null,
  "players": [{"index": 0, "name": "Alice", "alive": true}, "..."],
  "allowed_actions": ["speak", "co", "pass"],
  "cooldown_remaining_sec": 12,
  "private_channel_id": "123...",
  "profile": {"...": "確定したプロファイル"}
}
```
- `wolves` は自分が人狼のときだけ仲間の index の配列、それ以外は `null`。
- 他人の役職は試合中は決して含めない(property test の検査対象)。

### 3.2 イベント(`wait_for_event`)
| type | 内容 |
|---|---|
| `speech` | `#village` の発言(`index`, `text`(untrusted)) |
| `wolf_chat` | `#wolves` の発言 |
| `phase` | フェーズ変化 |
| `prompt` | 行動の要求 |
| `result` | 占い・霊媒の結果 |
| `dawn` / `vote_result` / `co_update` | 公式告知 |
| `game_over` | 終了 |

- イベントには単調増加の `id` を振り、`since` で取りこぼしを取り直せるようにする。

## 4. 誤操作の防止
- `speak` は送信前に文字数・クールダウン・フェーズを SDK 側で確認する。GM の判定と食い違ったときは GM の結果を返す。
- `act` の結果は GM の `ack`/`error` を待つ(最大 10 秒)。届かなければ `E_TIMEOUT` を返す(再送してよい。期限内の再送は上書き)。〔仮決定 U-43〕
