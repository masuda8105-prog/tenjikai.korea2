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
