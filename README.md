# SAN NISHIMURA 韓国展示会専用受注システム v2.0

韓国の展示会で使用する、**韓国ウォン価格専用**の受注システムです。

## 画面

- `index.html`：お客様用注文画面
- `staff.html`：スタッフ用注文管理画面（Supabase Authログイン必須）

## お客様側

1. 商品を検索してカートへ追加
2. 会社名・氏名・電話番号を入力
3. 必要に応じて名刺を撮影
4. 注文を送信
5. 受付番号（例：`K260730-001`）を表示

注文はSupabaseへ保存され、スタッフ画面へ反映されます。QRは通常運用では使わず、受付完了画面の「予備QR」にだけ残しています。

## スタッフ側

- スタッフログイン
- `NEW → 対応中 → 完了`
- 受付番号・会社名・氏名・電話番号・品番検索
- Realtime受信（接続できない場合は10秒ごとの自動更新）
- 通知音ON／OFF
- 名刺プレビューと原寸画像
- 担当者表示
- A4印刷

## 名刺画像

- 元画像：高画質のまま非公開Storageへ保存
- プレビュー：画面表示用の軽量画像
- スタッフ画面：プレビューをタップすると原寸画像を表示
- 名刺付き注文の送信に失敗した場合：受付番号を発行せず、再試行を案内

## セキュリティ

- ブラウザにはPublishable keyだけを配置
- Secret key / service_role keyはGitHubへ保存しない
- お客様の注文作成はEdge Function経由
- スタッフ一覧はSupabase Auth＋`exhibition_staff`許可リストで保護
- 名刺Storageは非公開
- 注文と名刺は14日後に削除対象となり、Cronが毎日処理

## 本番設定

- Supabase Project Ref：`qdexhwgzawisiklekfzm`
- お客様画面：`https://masuda8105-prog.github.io/korea-exibition-sannishimura/`
- スタッフ画面：`https://masuda8105-prog.github.io/korea-exibition-sannishimura/staff.html`

`online-config.js` は本番Project URLとPublishable keyを設定済みです。

## 明日の反映

最初に **`明日_本番反映手順.md`** を開いてください。

新しいスタッフ画面にはDB列・RLS・Realtime・自動削除Cronが必要です。GitHubへpushする前に、`01_Supabase更新.ps1`を1回実行します。

## 主なファイル

```text
index.html
staff.html
staff.js
online-config.js
product_master_korea.csv
product-images/
assets/
vendor/
supabase/
01_Supabase更新.ps1
02_GitHub公開.ps1
明日_本番反映手順.md
テスト結果.md
```
