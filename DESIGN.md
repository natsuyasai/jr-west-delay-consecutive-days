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
JR西日本 state.yaml X(Twitter)
 Website
```

## モジュール構成

```
jr-west-delay-consecutive-days/
├── src/
│   ├── main.py           # エントリーポイント・処理フロー制御
│   ├── fetcher.py        # JR西日本Webサイトから遅延情報を取得
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
2. **対象日付の決定**: 前日の日付を計算
3. **遅延情報取得** (`fetcher.py`): JR西日本Webサイトをスクレイピング
4. **状態読み込み** (`storage.py`): `data/state.yaml` から現在の連続日数を読み込む
5. **連続日数更新** (`counter.py`):
   - 遅延あり → `consecutive_days += 1`, `start_date` を初日に設定
   - 遅延なし → `consecutive_days = 0`, `start_date = None`
6. **状態保存** (`storage.py`): 更新後の状態を `data/state.yaml` に書き込む
7. **X投稿** (`poster.py`): 連続日数のサマリーを投稿

## データ構造

### `data/state.yaml`

```yaml
last_updated: "2024-03-08"
lines:
  - id: "sanyo-shinkansen"
    name: "山陽新幹線"
    consecutive_days: 0
    start_date: null
  - id: "kyoto-kobe"
    name: "JR京都線・神戸線"
    consecutive_days: 3
    start_date: "2024-03-06"
  # ... 他の路線
```

### `fetcher.py` の返却型

```python
# 遅延発生中の路線IDセット
delayed_line_ids: set[str]
# 例: {"kyoto-kobe", "osaka-loop"}
```

## 各モジュールの責務

### `fetcher.py` - 遅延情報取得

- **データソース**: JR西日本 列車運行情報ページ
  - URL: `https://www.jr-odekake.net/railroad/train_info/index.html`
- **処理**: `requests` + `BeautifulSoup` でスクレイピング
- **出力**: 前日に遅延が発生した路線IDのセット
- **考慮点**:
  - スクレイピングのため、ページ構造変更に注意
  - 実行は朝4時なので「前日」の情報が必要（サイトに掲載されている当日情報を使用）

### `counter.py` - 連続日数カウント

- **入力**: 現在の状態(YAML) + 遅延路線IDセット
- **処理**:
  - 遅延あり: `consecutive_days += 1`、`start_date`が未設定なら当日に設定
  - 遅延なし: `consecutive_days = 0`、`start_date = None`
- **出力**: 更新後の状態

### `storage.py` - YAML永続化

- `load_state(path)`: YAMLファイル読み込み、存在しない場合はデフォルト状態を返す
- `save_state(path, state)`: YAMLファイル書き込み
- ファイルが存在しない初回実行時はJR西日本の全路線を初期値(0日)で生成

### `poster.py` - X投稿

- **ライブラリ**: `tweepy` (X API v2)
- **投稿内容**: 連続日数が1以上の路線を列挙
- **投稿フォーマット例**:
  ```
  【JR西日本 遅延連続日数】2024/3/9時点

  JR京都線・神戸線: 3日連続(3/6〜)
  大阪環状線: 1日

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

## 対象路線一覧 (JR西日本)

| ID | 路線名 |
|---|---|
| sanyo-shinkansen | 山陽新幹線 |
| kyoto-kobe | JR京都線・神戸線 |
| osaka-loop | 大阪環状線 |
| gakkentoshi | 学研都市線 |
| osaka-higashi | おおさか東線 |
| yamatoji | 大和路線 |
| hanwa | 阪和線 |
| kinokuni | きのくに線 |
| kosei | 湖西線 |
| biwako | びわこ線 |
| hokuriku | 北陸線 |
| sanin | 山陰線 |
| bantan | 播但線 |
| kakogawa | 加古川線 |
| hishin | 姫新線 |
| ako | 赤穂線 |
| sakaiminato | 境線 |
| hakubi | 伯備線 |
| geibi | 芸備線 |
| kisuki | 木次線 |
| yamaguchi | 山口線 |
| uno-minato | 宇野みなと線 |
| seto-ohashi | 本四備讃線(瀬戸大橋線) |
| tsuyama | 津山線 |
| kibi | 吉備線 |
| inbi | 因美線 |
| fukuen | 福塩線 |
| kabe | 可部線 |
| sanyo | 山陽線 |
| kure | 呉線 |
| iwatoku | 岩徳線 |
| onoda | 小野田線 |
| ube | 宇部線 |
| wakayama | 和歌山線 |
| sakurai | 桜井線 |
| kusatsu | 草津線 |
| kansai | 関西線 |
| fukuchiyama | 福知山線 |
| sagano | 嵯峨野線 |
