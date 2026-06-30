# AGENTS.md

## Project goal

Create a mobile-first exhibition order app for Sannishimura and overseas distributors.

The app should help booth staff:

1. Search products quickly by product code or keyword.
2. Show product images, descriptions, and prices.
3. Switch display language between Japanese, English, Korean, and Chinese.
4. Add products to a provisional order cart.
5. Generate a QR code so the customer can download a provisional order receipt without sharing email, phone number, LINE, KakaoTalk, or other personal contact information.

## Current architecture

This prototype is a static GitHub Pages app.

- Main app: `index.html`
- Product master: `product_master_multilingual.csv`
- Product images: `images/products/`
- No backend is required for this prototype.

## Product CSV schema

Support these columns:

- `品番`
- `商品名_JA`
- `一言要約_JA`
- `商品名_EN`
- `一言要約_EN`
- `商品名_ZH`
- `一言要約_ZH`
- `商品名_KO`
- `一言要約_KO`
- `卸価格`
- `カタログ参照`
- `要約タイプ`
- `PDF抽出メモ`
- `画像ファイル名` optional
- `画像URL` optional

When no image column exists, automatically try:

```text
images/products/<product_code>.jpg
```

## UX priorities

Mobile-first. Booth staff must be able to operate it with one hand.

Important flows:

- Product search → Add to order should be very fast.
- Product detail should show image, multilingual name, description, price, and catalog reference.
- Order receipt should be usable even without customer personal information.
- Price display must be switchable between “with prices” and “without prices”.

## Privacy design

Do not add required fields for:

- Email
- Phone number
- LINE
- KakaoTalk
- WhatsApp

The order should be managed by order number.

## Future production recommendation

The current QR receipt stores encoded order data in the URL hash. This is good for a no-backend demo, but not ideal for production.

For production, implement:

- Backend order storage
- Short random receipt URL
- Expiration date
- Optional access token
- Admin order dashboard
- CSV/Excel export
- Server-side PDF generation

Recommended production flow:

```text
Create order
↓
Save order to server
↓
Generate random receipt token
↓
QR points to /receipt/<token>
↓
Customer downloads PDF
```


## v0.5 development note

The app supports package quantity / pack size display for parts. Keep the `packQty` field through product cards, detail modal, cart, receipt data, receipt rendering, and history CSV export. Supported CSV headers include `入数`, `入り数`, `内容量`, `袋入数`, `包装入数`, `販売単位`, `注文単位`, `pack_qty`, `pack_quantity`, and `pieces_per_pack`.


## v0.6 note
Do not add preset product-number shortcut buttons under the keypad unless explicitly requested. Keep the keypad area compact.

## v0.7 UI / Data Rules

- Do not focus the product search input after keypad taps. This prevents mobile soft keyboards from opening during booth operation.
- Keep the product search input readonly unless a deliberate keyboard-input mode is added later.
- Normalize Excel date-corrupted product codes at import time. Examples: `1月20日` => `20-1`, `Jan-40` => `40-1`, `1960/4/2` => `60-4-2`.
- Never display Excel date strings as product codes in search results, cart, or receipt PDFs.



## Pack quantity rule

The `入数` column may contain Japanese unit strings such as `10本`, `25ヶ`, `3組`, `10ペア`, or length/count strings such as `1m×3本`. The UI must translate these labels per language where possible and must keep unknown strings unchanged. Do not fabricate pack quantities when source text is ambiguous.


## v0.10 keypad UI rule

- Do not place the numeric keypad inline under the search field. Keep it as a small floating panel opened by the テンキー button.
- The keypad must remain draggable and closable.
- Keep the product code input readonly and inputmode=none to avoid opening the mobile software keyboard during keypad operation.


## v0.11 UI note
テンキーは展示会現場で迷わず使えるよう、ドラッグ式ではなく右下固定を基本とする。検索欄・クリア・左右ボタンは大きくしすぎず、商品一覧の表示面積を優先する。


## v0.13 update
- テンキーは画面下部に固定表示。
- テンキーは「左へ / 右へ」ボタンで左右に移動可能。
- スマホ幅では、注文明細・お客様情報・履歴エリアに入るとテンキーを自動で隠す。


## v0.13 update
- テンキーを固定位置のまま、少し大きくして押しやすく調整。
- 下部固定・左右移動・明細/お客様情報エリアでの自動非表示は維持。


## Description rules
- 商品説明は、単なるカテゴリ名ではなく「何に使うか」「お客様・眼鏡店にとって何が良いか」がすぐ分かる表現を優先する。
- CSVに接客説明_*、用途_*、メリット_* がある場合は、必ずアプリ表示に使う。

## Product detail URL policy

- Keep official website links inside the product detail modal, not in the compact product card.
- Prefer exact product page URLs from `商品ページURL` when available.
- If no exact URL is available, fall back to the San Nishimura website search URL using the product code.
- Do not expose distributor-only price data on public official pages.

## Catalog page number rule

When filling or correcting `カタログ参照`, use the printed page number shown at the bottom left or bottom right of the catalog page. Do not use the PDF viewer page index if it differs from the printed catalog page number.

## Hidden settings rule

Do not reintroduce a visible “Settings / Import data” card in the main exhibition UI unless explicitly requested. The app should load `product_master_multilingual.csv` automatically and keep operation simple for booth staff.

## v0.14 One-line summary quality workflow

一言要約は、推測ではなく次の3段階で作成・監査する。

1. HP情報調査エージェント
   - `商品ページURL` または品番検索結果から公式HPの該当商品ページを確認する。
   - `hp_match_status` が `exact` の場合のみ、HP情報を強い根拠として採用する。
   - `mismatch` や検索URLのみの場合は、公式HP未確定としてカタログ情報を優先する。

2. カタログ情報調査エージェント
   - PDFカタログ抽出メモ、既存カタログデータ、印刷ページ番号を確認する。
   - ページ番号はPDFビューア番号ではなく、カタログ紙面の下部に印字されたページ番号を使う。
   - 周辺商品の情報が混入している場合は `issue_flags` や `要約品質メモ` に残す。

3. 一言要約エージェント
   - HP情報とカタログ情報の一致部分を優先して、4言語の一言要約を作成する。
   - 「何に使うか」「どんな特徴・メリットがあるか」を短く入れる。
   - 根拠が弱い場合は汎用的に言い切らず、要確認として監査CSVに残す。

監査出力は `.agents/one_line_summary_evidence_report.csv` に保存する。
列は、品番、商品名、HPから確認した情報、カタログから確認した情報、日本語/英語/中国語/韓国語の一言要約、確認元URLまたはカタログ掲載ページを含める。

## v0.14 critical fixes

- No.104 は公式HPで「平ヤットコ 先細・先曲がり」「主にクリングス調整用」「主な使用用途: クリングスの微調整」と確認できるため、ブリッジ角度調整の説明を使わない。
- No.1053 / No.1054 は工具本体のため、旧CSVの入数「2本」は表示しない。No.1054 の「2本」は商品用途名の「2本ダキ足」であり入数ではない。
- 単品工具の入数は、カタログや商品名に明確なセット・入り数表記がある場合のみ表示する。

## v0.15 mobile receipt download rule

スマホでは `a.download` と自動クリックだけに依存しない。

- PC: 生成後に従来通り自動ダウンロードを試す。
- スマホ: `navigator.share({ files })` を優先する。
- 共有シートが使えない、またはキャンセルされた場合は、生成済みBlobへの「PDFを開く / 保存」「画像を開く / 保存」リンクを表示する。
- LINE / Instagramなどのアプリ内ブラウザでは保存が不安定なため、Safari / Chromeで開く案内を表示する。
- PDF印刷ボタンは最後の保険として残す。

## v0.16 programming agent summary rebuild

`.agents/programming_agent_rebuild_summaries.py` を一言要約の再構築エージェントとして追加。

- 全商品を対象に、HP調査CSV・カタログ調査CSV・商品名ルールを使って用途カテゴリを再判定する。
- 「眼鏡店の作業や店頭提案を補助する商品です」のような汎用要約は禁止。
- No.104 / No.1053 / No.1054 は重要品番として個別上書きする。
- No.1053 / No.1054 の工具本体には、誤抽出された入数「2本」を表示しない。
- 結果は `.agents/one_line_summary_evidence_report.csv` と `.agents/programming_agent_summary_audit.csv` に出力する。
