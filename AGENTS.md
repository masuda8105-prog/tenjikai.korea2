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
