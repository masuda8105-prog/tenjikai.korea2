$ErrorActionPreference = "Stop"

Write-Host "=== SAN NISHIMURA 韓国展示会：Supabase更新 ===" -ForegroundColor Cyan

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  Write-Host "Node.js / npx が見つかりません。Node.jsをインストールしてから再実行してください。" -ForegroundColor Red
  exit 1
}

npx supabase login
npx supabase link --project-ref qdexhwgzawisiklekfzm

# ブラウザ公開用の設定値です。Secret keyはファイルへ保存しません。
npx supabase secrets set `
  ALLOWED_ORIGINS=https://masuda8105-prog.github.io `
  BUSINESS_CARD_BUCKET=business-cards `
  ORDER_RETENTION_DAYS=14 `
  SIGNED_URL_SECONDS=3600

npx supabase db push --include-all
npx supabase functions deploy exhibition-order --no-verify-jwt --use-api
npx supabase functions deploy cleanup-orders --no-verify-jwt --use-api

Write-Host "=== Supabase更新完了 ===" -ForegroundColor Green
Write-Host "次はSupabase Dashboardでスタッフユーザーを作成し、exhibition_staffへ登録してください。"
