from __future__ import annotations

import csv
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_catalog() -> None:
    path = ROOT / "product_master_korea.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 3831:
        fail(f"商品件数が想定外です: {len(rows)}")
    codes: list[str] = []
    for line, row in enumerate(rows, 2):
        code = (row.get("品番") or "").strip()
        if not code:
            fail(f"品番が空です: {line}行")
        codes.append(code)
        price_text = (row.get("韓国眼鏡店への販売価格（KRW）") or "").strip()
        try:
            price = int(float(price_text))
        except ValueError as exc:
            raise AssertionError(f"価格が数値ではありません: {line}行 {price_text!r}") from exc
        if price < 0 or price % 100:
            fail(f"100ウォン丸めではありません: {line}行 {price}")
        if (row.get("通貨") or "").strip() != "KRW":
            fail(f"通貨がKRWではありません: {line}行")
        image = (row.get("画像ファイル名") or "").strip()
        if image and not (ROOT / "product-images" / image).is_file():
            fail(f"画像ファイルがありません: {code} / {image}")
    duplicates = [code for code, count in Counter(codes).items() if count > 1]
    if duplicates:
        fail(f"品番重複: {duplicates[:10]}")


def validate_files() -> None:
    required = [
        "index.html", "staff.html", "staff.js", "online-config.js",
        "vendor/html2canvas.min.js",
        "supabase/functions/exhibition-order/index.ts",
        "supabase/functions/cleanup-orders/index.ts",
        "supabase/migrations/20260730090000_korea_staff_dashboard.sql",
        "supabase/migrations/20260803120000_exhibition_order_workflow.sql",
        "supabase/migrations/20260803150000_lock_browser_order_permissions.sql",
        "supabase/migrations/20260803151000_remove_legacy_order_policies.sql",
        "supabase/sql/04_secure_cleanup_schedule.sql",
        "AGENTS.md", "README_当日操作.md", "README_Supabase設定.md",
        "01_Supabase更新.ps1", "02_GitHub公開.ps1",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        fail(f"必須ファイル不足: {missing}")
    image_count = sum(1 for path in (ROOT / "product-images").iterdir() if path.is_file())
    if image_count != 2753:
        fail(f"商品画像数が想定外です: {image_count}")


def check_js() -> None:
    files = [ROOT / "staff.js", ROOT / "online-config.js"]
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", index, flags=re.I | re.S)
    with tempfile.TemporaryDirectory() as temp:
        for number, script in enumerate(scripts):
            if not script.strip():
                continue
            path = Path(temp) / f"index-inline-{number}.js"
            path.write_text(script, encoding="utf-8")
            files.append(path)
        for path in files:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
            if result.returncode:
                fail(f"JavaScript構文エラー: {path.name}\n{result.stderr}")


def check_required_markers() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    staff_js = (ROOT / "staff.js").read_text(encoding="utf-8")
    staff_html = (ROOT / "staff.html").read_text(encoding="utf-8")
    migration = (ROOT / "supabase/migrations/20260730090000_korea_staff_dashboard.sql").read_text(encoding="utf-8")
    workflow = (ROOT / "supabase/migrations/20260803120000_exhibition_order_workflow.sql").read_text(encoding="utf-8")
    permissions = (ROOT / "supabase/migrations/20260803150000_lock_browser_order_permissions.sql").read_text(encoding="utf-8")
    edge = (ROOT / "supabase/functions/exhibition-order/index.ts").read_text(encoding="utf-8")
    cleanup = (ROOT / "supabase/functions/cleanup-orders/index.ts").read_text(encoding="utf-8")
    for forbidden in ["packBadgeHtml(", "specsInfoHtml(", "'pack_qty','qty'", "i.pack||''"]:
        if forbidden in index:
            fail(f"Pack quantity is visible in the UI or order-history export: {forbidden}")
    for marker in ["detailProductThumb", "ordersSnapshotSignature", "viewChanged", "silent: true"]:
        if marker not in staff_js + staff_html:
            fail(f"Staff detail image or stable refresh marker is missing: {marker}")
    for marker in ["受付番号を発行", "近くのスタッフにお見せください"]:
        if marker not in index:
            fail(f"Reception-number guidance marker is missing: {marker}")
    for marker in ["shippingAddress", "saveReceiptImage", "html2canvas.min.js", "receiptImagePanel", "prepareReceiptImagePreview", "receiptImageDownloadFab", "画像を長押し"]:
        if marker not in index:
            fail(f"Shipping-address or image-save marker is missing: {marker}")
    markers = [
        "受付番号を発行 / 접수 번호 발급",
        "名刺画像を送信できませんでした。再試行してください。",
        "受付番号 / 접수 번호",
        "予備QRを表示 / 예비 QR 표시",
    ]
    for marker in markers:
        if marker not in index:
            fail(f"お客様画面の必須文言がありません: {marker}")
    if "notesPlaceholder:''" in index:
        fail("備考欄の翻訳プレースホルダーが空です")
    for marker in ["対応開始", "注文を確定する", "確定注文をまとめて送る", "削除履歴へ移す"]:
        if marker not in staff_html:
            fail(f"スタッフ画面の必須機能がありません: {marker}")
    for marker in ["batchDateSelect", "batchSelectAll", "editShippingAddress", "signedBusinessCardUrl", "waitForPrintImages", "receiptShippingAddress"]:
        if marker not in staff_js + staff_html:
            fail(f"日付別送信・住所・名刺印刷の必須機能がありません: {marker}")
    if "送信する日付を上の日付フィルターで1日選択してください。" in staff_js:
        fail("一括送信が画面上部の日付フィルターに依存しています")
    for marker in ["リアルタイム接続中", "business-cards", "updated_at=eq.", "resend_required", "CONFLICT"]:
        if marker not in staff_js:
            fail(f"スタッフ画面の必須機能がありません: {marker}")
    for marker in ["next_korea_order_no", "exhibition_staff", "supabase_realtime", "cleanup-expired-exhibition-orders"]:
        if marker not in migration:
            fail(f"DB設定の必須項目がありません: {marker}")
    for marker in ["client_submission_id", "order_revisions", "order_batches", "order_batch_items", "status = 'deleted'", "is_exhibition_admin", "resend_required"]:
        if marker not in workflow:
            fail(f"ワークフローDB設定の必須項目がありません: {marker}")
    for marker in ["clientSubmissionId", "duplicatePrevented", "client_submission_id"]:
        if marker not in edge:
            fail(f"注文APIの二重送信防止がありません: {marker}")
    if "acceptedPublicKeys" in cleanup:
        fail("cleanup-ordersが公開用キーを認証に使用しています")
    if "method:'DELETE'" in staff_js or 'method: "DELETE"' in staff_js:
        fail("通常スタッフ画面から物理DELETEを実行しています")
    if re.search(r"grant\s+delete\s+on\s+(?:table\s+)?public\.exhibition_orders\s+to\s+authenticated", workflow + permissions, re.I):
        fail("ブラウザー利用者へ注文の物理DELETE権限を付与しています")

    html_ids = re.findall(r'\bid=["\']([^"\']+)["\']', staff_html, flags=re.I)
    duplicate_ids = [name for name, count in Counter(html_ids).items() if count > 1]
    if duplicate_ids:
        fail(f"staff.htmlに重複IDがあります: {duplicate_ids}")
    referenced_ids = set(re.findall(r'\$\(\s*["\']([^"\']+)["\']\s*\)', staff_js))
    dynamic_ids = set(re.findall(r'\bid=["\']([^"\'\\$<>]+)["\']', staff_js, flags=re.I))
    missing_ids = sorted(referenced_ids - set(html_ids) - dynamic_ids)
    if missing_ids:
        fail(f"staff.jsが存在しない画面IDを参照しています: {missing_ids}")


def main() -> None:
    validate_files()
    validate_catalog()
    check_js()
    check_required_markers()
    print("STATIC_VALIDATION_PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"STATIC_VALIDATION_FAIL: {error}", file=sys.stderr)
        raise
