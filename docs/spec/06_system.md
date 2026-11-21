# 06 システム構成・非機能要件

## 1. 実装言語とライブラリ
- **Python**(3.12 以上)。設計書 §6 は TypeScript だが、CLAUDE.md の「言語は Python。テストは pytest」に合わせた。〔仮決定 U-46〕
  - Discord:`discord.py`
  - MCP:公式 Python SDK(`mcp`)
  - 永続化:標準ライブラリ `sqlite3`
  - JSON Schema 検証:`jsonschema`
  - テスト:`pytest`、property test は `hypothesis`
- プロファイルエディタだけは静的な HTML/CSS/JS(ブラウザで動かすため)。JSON Schema ファイルは Python 側と共有する。

## 2. 構成
```
/src/jinrou/
  engine/        ルール・状態機械(Discord 非依存、乱数はシード注入)
  gm_bot/        Discord 入出力、権限管理、タイマー、送信キュー
  gateway/       モード B 用 HTTP/MCP ゲートウェイ(M5)
  player_kit/    参加者向け MCP サーバー SDK
  sim/           ランダム行動の疑似プレイヤーで全自動シミュレーション
  schema/        プロファイルの JSON Schema
/packages/profile-editor/   静的 Web ツール
/presets/                   プリセット JSON
/tests/
/docs/
```
- 設計書のパッケージ分けを Python のパッケージに置き換えた。player_kit は別配布にするため、将来は別パッケージに切り出す。〔仮決定 U-47〕

## 3. Engine のインターフェース
- Engine は「状態+入力 → 新しい状態+出力イベント」の純粋な関数として作る。時刻は外から渡す(`now` を引数に取る)。
- 入力:`Command`(実行者 ID・コマンド・引数・受信チャンネルの種類)、`Tick`(現在時刻。締切の判定用)。
- 出力:`Event` の列(GM Bot が Discord への投稿・権限更新に変換する)。
- Engine はチャンネル ID を知らず、「`#priv` / `#wolves` / `#village` のどれで受けたか」という種類だけを受け取る。

## 4. GM Bot の要件
- 必要な Intent:Guilds、Guild Messages、**Message Content**(特権)、Guild Members。
- 必要な権限(GM のみ):Manage Channels、Manage Roles、Manage Messages、View Channel、Send Messages、Read Message History、Attach Files、Embed Links。
- タイマー:締切は DB に保存し、1 秒ごとの Tick で判定する。再起動後も締切は保たれる(再起動中に過ぎた締切は、起動直後に処理する)。〔仮決定 U-48〕
- 送信キュー:チャンネルごとのレート制限を守り、夜のプロンプトは全員にほぼ同時(数秒以内)に届くようにする。
- 秘密情報:トークンは環境変数(`.env` はコミットしない)。

## 5. 非機能要件
| 項目 | 要件 |
|---|---|
| 決定性 | 同じシード・同じ入力列で同じ結果(Engine) |
| 秘匿 | 試合中、どの参加者の `get_state` にも他人の役職が出ない。sim+property test で検証 |
| 耐障害 | GM の再起動で試合が失われない(イベントログから復元) |
| 規模 | 最大 15 人+観戦者。登録者は 1 サーバーあたり数百まで(チャンネル上限 500) |
| ログ | 詳細ログはファイル(ローテーション)。`#debug` には要点のみ |

## 6. テスト
- Engine:ルールの単体テスト、sim で 1000 試合(M0 の完了条件)。勝敗の整合と秘匿漏れを property test で検査。
- GM Bot:Discord をモックしたテスト(コマンド解析、権限更新の指示、エラーコード)。
- 実 Discord:PoC(設計書 §8.5)の 6 項目を手動で確認し、結果を `docs/review/` に残す。

## 7. マイルストーン
設計書 §8 のとおり。ただし M0 の前に PoC(M0.5 と呼ばれていたもの)を行う。PoC で「Bot が他 Bot の発言を受信できる」が崩れた場合、モード B を先に作る。
