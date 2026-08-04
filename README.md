# SAN NISHIMURA 韓国展示会 受注管理システム v3.0

GitHub Pages と Supabase を使う、展示会場向けの注文受付・スタッフ確認・代理店送付ツールです。韓国語を初期表示とし、日本語へ切り替えられます。

## 画面と基本操作

- `index.html`：お客様用。商品検索 → カート確認 → お客様情報・注文送信の3ステップです。
- `staff.html`：スタッフ用。Supabase Authログイン後、確認・修正・確定・一括送付を行います。

お客様の注文はEdge Function経由で `public.exhibition_orders` に保存されます。送信ごとにクライアント冪等IDを持つため、通信断後に再送しても同じ注文を重複登録しません。入力途中のカートとお客様情報は端末内の下書きとして保持され、送信失敗時にも消えません。

## 注文状態

```text
submitted        受付番号発行済み・確認待ち
in_progress      確認中
confirmed        注文確定・代理店送付待ち
sent             代理店送付済み
resend_required  修正版・再送待ち
deleted          削除履歴（復元可能）
```

旧注文の `new / completed` も互換状態として読み込み、それぞれ `submitted / confirmed` と同じ表示・操作になります。受付番号発行後は、スタッフが `confirmed` にするまで、お客様の公開トークンと更新時刻を照合して同じ注文IDを更新できます。注文ID・受付番号・QRは変更されません。

通常削除は物理DELETEではなく、`status = deleted` へのPATCHです。削除理由・担当・削除前状態を保存し、削除履歴から復元できます。完全削除は通常スタッフ画面に表示しません。

確定注文は日付単位で一つのA4印刷用PDFへまとめ、メール本文を開き、PDF添付・メール送信のチェック後に送付済みへ登録します。送信時点の注文スナップショットを `order_batch_items` に残します。送付済み注文を修正すると `resend_required` へ移り、元の送信情報を保持します。

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
supabase/functions/
supabase/migrations/
supabase/sql/
AGENTS.md
README_当日操作.md
README_Supabase設定.md
tests/
```

## セキュリティ

- ブラウザにはPublishable keyだけを配置します。
- Secret key / service_role keyをフロントエンドやGitへ保存しません。
- お客様の注文作成はEdge Function経由です。
- 注文一覧・更新・名刺閲覧はAuth＋`exhibition_staff`＋RLSで保護します。
- ブラウザーからの完全削除権限は付与しません。保存期限後の物理削除は、サーバー側のcleanup関数だけが行います。
- 期限cleanupは公開キーでは起動できず、`CLEANUP_SECRET` 専用です。

## 初回・更新時の設定

[README_Supabase設定.md](README_Supabase設定.md) の順序で、DBマイグレーション → Edge Functions → cleanup secret/Cron → スタッフ登録を行います。DBを更新する前に新しいスタッフ画面だけを公開すると、追加statusや列が拒否されます。

会場当日の操作は [README_当日操作.md](README_当日操作.md) を使用してください。

## 検証

この環境でPython/NodeがPATHにある場合：

```powershell
python tests/static_validate.py
python tests/automated_e2e.py
node --check staff.js
node --check online-config.js
```

公開前には、お客様送信（名刺あり・なし・失敗・再試行）、スタッフの全status遷移、編集、競合、ソフト削除・復元、バッチPDF・メール・送付済み、390px/820px/PC表示を確認します。
