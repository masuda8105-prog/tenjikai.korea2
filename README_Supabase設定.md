# Supabase設定・更新手順

本番Project Refは既存の `qdexhwgzawisiklekfzm` です。別Projectへ適用する場合は、スクリプト・URL・公開設定を先に見直してください。

## 重要な適用順

1. 作業ツリーのバックアップと既存status件数を確認する。
2. DBマイグレーションを適用する。
3. Edge Functionsをデプロイする。
4. cleanup専用secretとCronを設定する。
5. スタッフ登録を確認する。
6. GitHub Pagesを公開する。

フロントを先に公開しないでください。旧DBは `deleted / sent / resend_required` と `order_data` 更新を拒否します。

## 1. 事前監査

Supabase SQL Editorで実行します。

```sql
select status, count(*)
from public.exhibition_orders
group by status
order by status;
```

未知のstatusがある場合はマイグレーションを止め、意味を確認してください。既存行や既存列は削除しません。

## 2. DB・Functions更新

リポジトリルートのPowerShellで実行します。

```powershell
.\01_Supabase更新.ps1
```

新規マイグレーション：

```text
supabase/migrations/20260803120000_exhibition_order_workflow.sql
```

追加内容：

- ソフト削除・復元に必要なstatus、列権限、RLS
- 楽観的ロック用 `updated_at`
- 複数展示会・日付列
- 修正履歴・操作ログ
- 送信バッチ・送信時スナップショット・Batch ID採番RPC
- スタッフ `role`（`staff / admin`）
- クライアント送信IDの一意制約
- 公開キーを使う旧cleanup Cronの停止

## 3. cleanup secretとCron

32文字以上のランダム文字列を作り、Edge Function secretへ設定します。値をGitへ保存しないでください。

```powershell
npx supabase secrets set CLEANUP_SECRET=ここにランダム値
```

`supabase/sql/04_secure_cleanup_schedule.sql` のプレースホルダーを同じ値へ一時的に置換し、Supabase SQL Editorで実行します。実行後、実値を書いたファイルは保存・commitしません。

`cleanup-orders` は `x-cleanup-secret` が一致するリクエストだけを受け付けます。Publishable keyでは起動できません。

## 4. スタッフ登録

Authユーザー作成後、SQL Editorで登録します。

```sql
insert into public.exhibition_staff (user_id, display_name, role)
select id, '表示名', 'staff'
from auth.users
where email = 'スタッフのメールアドレス'
on conflict (user_id)
do update set display_name = excluded.display_name, role = excluded.role, active = true;
```

`role = 'admin'` は将来の管理者機能用に予約されています。現在は管理者を含め、ブラウザーからの完全削除はできません。保存期限後の物理削除はcleanup関数だけが行います。

## 5. RLS確認

- 匿名ユーザーは注文一覧をSELECTできない。
- 許可リスト外のAuthユーザーは注文をSELECT/UPDATEできない。
- staffは注文を編集、確定、ソフト削除、復元できる。
- staffは物理DELETEできない。
- adminでも `status = deleted` 以外は物理DELETEできない。
- お客様の注文作成はEdge Functionだけが行う。

## 6. ロールバック方針

フロント側で問題が出た場合はGitHub Pagesを直前版へ戻せます。追加したDB列・履歴テーブルは既存データを壊さないため、慌ててDROPしません。バッチ作成途中は `cancel_exhibition_order_batch` RPCで解除します。RLSを一時的に `using (true)` へ緩和しないでください。
