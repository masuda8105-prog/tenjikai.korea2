$ErrorActionPreference = "Stop"

Write-Host "=== GitHub公開 ===" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "Gitが見つかりません。次を実行してインストールしてください。" -ForegroundColor Yellow
  Write-Host "winget install --id Git.Git -e --source winget"
  exit 1
}

if (-not (Test-Path ".git")) {
  Write-Host "このフォルダーはGitリポジトリではありません。" -ForegroundColor Red
  Write-Host "既存の korea-exibition-sannishimura フォルダーへZIPの中身を上書きしてから実行してください。"
  exit 1
}

git add .
$changes = git status --porcelain
if (-not $changes) {
  Write-Host "コミットする変更はありません。" -ForegroundColor Yellow
  exit 0
}

git commit -m "Complete Korea exhibition order system v2"

$branch = git branch --show-current
if (-not $branch) { $branch = "main" }
git push origin $branch

Write-Host "=== GitHubへの公開が完了しました ===" -ForegroundColor Green
Write-Host "お客様画面: https://masuda8105-prog.github.io/korea-exibition-sannishimura/"
Write-Host "スタッフ画面: https://masuda8105-prog.github.io/korea-exibition-sannishimura/staff.html"
