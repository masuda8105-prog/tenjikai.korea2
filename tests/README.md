# テスト

## 静的検証

```powershell
python tests/static_validate.py
```

商品件数、KRW価格、100ウォン丸め、重複品番、画像参照、必須ファイル、JavaScript構文を確認します。

## ブラウザE2E

同梱Node.jsにPlaywrightがある環境では、次を優先します。

```powershell
node tests/automated_e2e.cjs
```

Python Playwrightが入っている環境では、同じシナリオをPython版でも実行できます。

```powershell
python tests/automated_e2e.py
```

Supabase通信はテスト用モックを使用し、お客様の注文送信・名刺送信失敗・スタッフ状態更新・印刷・スマホ／タブレット／PC表示を確認します。
