-- Supabase SQL Editorで1回だけ実行してください。
-- ログイン済みスタッフが exhibition_orders を完全削除できるようにします。
-- 通常の「削除履歴へ移す」操作はUPDATEなので、このSQLなしでも動作します。

alter table public.exhibition_orders enable row level security;

drop policy if exists "staff can delete exhibition orders" on public.exhibition_orders;
create policy "staff can delete exhibition orders"
on public.exhibition_orders
for delete
to authenticated
using (true);
