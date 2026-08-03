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
        "supabase/functions/exhibition-order/index.ts",
        "supabase/functions/cleanup-orders/index.ts",
        "supabase/migrations/20260730090000_korea_staff_dashboard.sql",
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
    staff = (ROOT / "staff.js").read_text(encoding="utf-8")
    migration = (ROOT / "supabase/migrations/20260730090000_korea_staff_dashboard.sql").read_text(encoding="utf-8")
    markers = [
        "注文を送信 / 주문 전송",
        "名刺画像を送信できませんでした。再試行してください。",
        "受付番号 / 접수 번호",
        "予備QRを表示 / 예비 QR 표시",
    ]
    for marker in markers:
        if marker not in index:
            fail(f"お客様画面の必須文言がありません: {marker}")
    for marker in ["対応開始", "完了", "リアルタイム接続中", "business-cards"]:
        if marker not in staff:
            fail(f"スタッフ画面の必須機能がありません: {marker}")
    for marker in ["next_korea_order_no", "exhibition_staff", "supabase_realtime", "cleanup-expired-exhibition-orders"]:
        if marker not in migration:
            fail(f"DB設定の必須項目がありません: {marker}")


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
