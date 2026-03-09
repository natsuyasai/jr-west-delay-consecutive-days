# 設計ドキュメント

## アーキテクチャ概要

```
[Scheduler (cron 4:00)]
        |
        v
    main.py
   /   |   \
  v    v    v
fetcher counter poster
  |      |      |
  v      v      v
JR西日本  state.yaml  X(Twitter)
JSON API
```

## モジュール構成

```
jr-west-delay-consecutive-days/
├── src/
│   ├── main.py           # エントリーポイント・処理フロー制御
│   ├── fetcher.py        # JR西日本 JSON APIから遅延情報を取得
│   ├── counter.py        # 連続日数カウントロジック
│   ├── storage.py        # YAMLファイルへの状態保存・読み込み
│   └── poster.py         # X(Twitter)への投稿
├── data/
│   └── state.yaml        # 路線ごとの連続日数状態（永続化）
├── tests/
│   ├── test_counter.py
│   ├── test_storage.py
│   └── test_fetcher.py
├── .env.example          # 環境変数テンプレート
├── pyproject.toml
└── requirements.txt
```

## 処理フロー

1. **起動** (毎日 04:00)
2. **状態読み込み** (`storage.py`): `data/state.yaml` から現在の連続日数を読み込む
   - 初回実行時: `area_{area}_master.json` から路線一覧を動的取得して初期化
3. **遅延情報取得** (`fetcher.py`): 各エリアの `trafficinfo` API を取得
4. **連続日数更新** (`counter.py`):
   - 遅延あり → `consecutive_days += 1`, `start_date` を初日に設定
   - 遅延なし → `consecutive_days = 0`, `start_date = None`
5. **状態保存** (`storage.py`): 更新後の状態を `data/state.yaml` に書き込む
6. **X投稿** (`poster.py`): 連続日数のサマリーを投稿

## データソース (JR西日本 非公式API)

**ベースURL**: `https://www.train-guide.westjr.co.jp/api/v3/`
**参考**: [JR西日本の指定路線の1分以上遅延のある電車を調べる](https://qiita.com/k_kado__j_ichi/items/7081bc62618bef32eb0e)

### 使用エンドポイント

| エンドポイント | 用途 |
|---|---|
| `area_{AREA}_trafficinfo.json` | 遅延・運行障害が発生している路線を取得 |
| `area_{AREA}_master.json` | 全路線ID・路線名の一覧を取得（初回初期化用） |

**エリア一覧**: `kinki`, `chugoku`, `hokuriku`, `shinkansen`

### trafficinfo レスポンス構造

```json
// 平常時
{"lines": {}, "express": {}}

// 障害発生時 (lines の各キーが遅延路線ID)
{
  "lines": {
    "kobesanyo": {"info": "遅延", "detail": "..."},
    "bantan":    {"info": "運転見合わせ", "detail": "..."}
  },
  "express": {}
}
```

### 実行タイミングの考慮点

朝4時実行時の `trafficinfo` は深夜〜早朝の障害を反映している。
前日昼間に発生・解消済みの障害はこの時点では検知されない。

## データ構造

### `data/state.yaml`

路線IDは `trafficinfo` レスポンスのキーと一致させる。

```yaml
last_updated: "2024-03-08"
lines:
  - id: sanyoshinkansen
    name: 山陽新幹線
    consecutive_days: 0
    start_date: null
  - id: kobesanyo
    name: JR神戸線・山陽線
    consecutive_days: 3
    start_date: "2024-03-06"
  # ... 他の路線
```

### `fetcher.py` の返却型

```python
# 遅延発生中の路線IDセット (trafficinfo の lines キーと同一)
delayed_line_ids: set[str]
# 例: {"kobesanyo", "bantan"}
```

## 各モジュールの責務

### `fetcher.py` - 遅延情報取得

- **データソース**: `area_{area}_trafficinfo.json`
- **処理**: 各エリアを順にフェッチし、`lines` キーの路線IDを収集
- **出力**: 遅延発生路線IDのセット
- **考慮点**:
  - エリアによってエンドポイントが存在しない場合は `HTTPError` をキャッチしてスキップ
  - `fetch_all_line_ids()` は初回の `state.yaml` 生成時のみ使用

### `counter.py` - 連続日数カウント

- **入力**: 現在の状態(YAML) + 遅延路線IDセット
- **処理**:
  - 遅延あり: `consecutive_days += 1`、`start_date` が未設定なら当日に設定
  - 遅延なし: `consecutive_days = 0`、`start_date = None`
- **出力**: 更新後の状態

### `storage.py` - YAML永続化

- `load_state(path)`: YAMLファイル読み込み、存在しない場合は `FALLBACK_LINES` で初期化
- `build_initial_state(line_defs)`: 路線定義リストから初期状態を生成（初回用）
- `save_state(path, state)`: YAMLファイル書き込み

### `poster.py` - X投稿

- **ライブラリ**: `tweepy` (X API v2)
- **投稿内容**: 連続日数が1以上の路線を列挙
- **投稿フォーマット例**:
  ```
  【JR西日本 遅延連続日数】2024/3/9時点

  JR神戸線・山陽線: 3日連続(3/6〜)
  播但線: 1日

  ※前日に遅延が発生した路線を掲載
  ```

## 環境変数

```
# X (Twitter) API認証情報
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# 設定
STATE_FILE_PATH=data/state.yaml
```

## スケジューリング

- **方式**: システムのcronジョブ
- **設定例** (`crontab -e`):
  ```
  0 4 * * * cd /path/to/jr-west-delay-consecutive-days && python src/main.py
  ```

## 対象路線一覧 (フォールバック定義)

初回実行時は `area_master` APIから動的取得するが、API障害時は以下を使用する。
**IDは `trafficinfo` レスポンスのキーと一致させること。**

| ID | 路線名 | エリア |
|---|---|---|
| hokurikubiwako | 北陸線・琵琶湖線 | 近畿 |
| kobesanyo | JR神戸線・山陽線 | 近畿/中国 |
| kyoto | JR京都線 | 近畿 |
| ako | 赤穂線 | 近畿 |
| kosei | 湖西線 | 近畿 |
| nara | 奈良線 | 近畿 |
| sagano | 嵯峨野線 | 近畿 |
| sanin1 | 山陰線（近畿） | 近畿 |
| osakahigashi | おおさか東線 | 近畿 |
| takarazuka | JR宝塚線 | 近畿 |
| gakkentoshi | 学研都市線・JR東西線 | 近畿 |
| osakaloop | 大阪環状線・JRゆめ咲線 | 近畿 |
| yamatoji | 大和路線 | 近畿 |
| hanwa | 阪和線・関西空港線 | 近畿 |
| kusatsu | 草津線 | 近畿 |
| fukuchiyama | JR宝塚線・福知山線 | 近畿 |
| sanin2 | 山陰線（中国） | 中国 |
| bantan | 播但線 | 中国 |
| hishin | 姫新線 | 中国 |
| hakubi | 伯備線 | 中国 |
| geibi | 芸備線 | 中国 |
| kisuki | 木次線 | 中国 |
| yamaguchi | 山口線 | 中国 |
| unominato | 宇野みなと線 | 中国 |
| setoohashi | 本四備讃線(瀬戸大橋線) | 中国 |
| tsuyama | 津山線 | 中国 |
| kibi | 吉備線 | 中国 |
| inbi | 因美線 | 中国 |
| fukuen | 福塩線 | 中国 |
| kabe | 可部線 | 中国 |
| kure | 呉線 | 中国 |
| iwatoku | 岩徳線 | 中国 |
| onoda | 小野田線 | 中国 |
| ube | 宇部線 | 中国 |
| sakai | 境線 | 中国 |
| kakogawa | 加古川線 | 中国 |
| hokuriku | 北陸線 | 北陸 |
| sanyoshinkansen | 山陽新幹線 | 新幹線 |

> **注意**: 上記IDは調査時点での推定値。`area_master` API の実際のレスポンスで確認・修正すること。
