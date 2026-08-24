# jr-west-delay-consecutive-days

JR西日本の各路線ごとに、遅延証明書が発行された連続日数を毎日自動集計し、
結果をカレンダー付きの静的サイトとして GitHub Pages で公開します。

## 機能一覧
- JR西日本の各路線ごとに、遅延が発生している連続日数をカウントする
- 毎日 4:00 (始発前, JST) に GitHub Actions で自動実行し、前日の遅延情報を反映
- 前日に遅延が発生しなかった場合は連続日数をリセット
- 路線ごとの連続日数・日別の遅延有無は `data/` 配下に JSON で永続化し、次回実行時に読み出す
- 結果は `docs/` の静的サイトとしてビルドし、GitHub Pages で公開
  (カレンダー UI から過去の日付の結果も閲覧可能)

## 仕組み
- `scripts/fetch_delay.py`: JR西日本の遅延証明書サイト
  (<https://delay.trafficinfo.westjr.co.jp/>) が使っている JSON API から
  路線マスタと各路線の遅延証明書履歴を取得し、`data/history/*.json` と
  `data/state.json` を更新する
- `scripts/generate_site.py`: `data/` の内容から `docs/data.json` を生成する
- `docs/index.html`: `docs/data.json` を読み込んでカレンダー・結果一覧を表示する
  静的ページ (手動管理、ビルドスクリプトの対象外)
- `.github/workflows/daily.yml`: 上記を毎朝実行し、`data/`・`docs/` の変更を
  コミット、GitHub Pages へデプロイする

## GitHub Pages の有効化 (初回のみ)
リポジトリの Settings → Pages → Build and deployment → Source を
"GitHub Actions" に設定してください。
