-- 互換用の安全化SQLです。
-- 通常の削除はDELETEではなく、staff.jsからstatus='deleted'へ更新します。
-- 本番ではsupabase/migrations/20260803120000_exhibition_order_workflow.sqlを適用してください。

alter table public.exhibition_orders enable row level security;

drop policy if exists "staff can delete exhibition orders" on public.exhibition_orders;
drop policy if exists exhibition_orders_admin_delete on public.exhibition_orders;

revoke delete on table public.exhibition_orders from authenticated;

-- 物理削除はブラウザーへ許可しません。保存期限後の削除は、秘密鍵で保護された
-- cleanup-orders Edge Functionだけが実行します。
