from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "product_master_multilingual.csv"
CATALOG = ROOT / ".agents" / "catalog_research_output.csv"
AUDIT = ROOT / ".agents" / "catalog_printed_page_audit.csv"
PDF_SOURCE = r"C:\Users\AONUSR02\Desktop\売上データ\サンニシムラ総合カタログ2025-2027 (1).pdf"
VIEWER_OFFSET = 76


PACK_FIXES = {
    "0516": ("12本", "紙面P100に1セット12本入と明記"),
    "250-A": ("", "固定台は単品工具。6組は隣接する鼻盛パッドの混入"),
    "900": ("1000枚", "紙面P257に一束1,000枚入りと明記"),
    "647": ("2巻", "商品名の2巻入と一致"),
    "436-B": ("", "0枚は隣接するアゴ紙の混入"),
    "867": ("", "0枚は隣接するアゴ紙の混入"),
    "1053": ("", "工具本体。2本は周辺テキストの誤抽出"),
    "1054": ("", "工具本体。2本ダキ足は用途名で入数ではない"),
    "1695M-C": ("2000ヶ", "商品名の2,000ヶ入に合わせる"),
}


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows, headers):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def printed_reference(raw: str):
    text = (raw or "").strip()
    numbers = [int(value) for value in re.findall(r"\d+", text)]
    if not numbers:
        return "", "no_reference"
    if "/" in text and any(value < VIEWER_OFFSET + 1 for value in numbers):
        # Front-matter page + explicit printed destination, e.g. P.9 / P.126.
        pages = [numbers[-1]]
        method = "front_matter_explicit_printed_page"
    else:
        pages = [value - VIEWER_OFFSET for value in numbers if value > VIEWER_OFFSET]
        method = "viewer_page_minus_76"
    pages = list(dict.fromkeys(value for value in pages if 1 <= value <= 328))
    return (f"カタログP.{','.join(str(value) for value in pages)}" if pages else ""), method


def main():
    master_rows = read_rows(MASTER)
    master_headers = list(master_rows[0])
    catalog_rows = read_rows(CATALOG)
    catalog_headers = list(catalog_rows[0])
    catalog_by_code = {row.get("品番", ""): row for row in catalog_rows}
    audit_rows = []

    for row in master_rows:
        code = row.get("品番", "")
        cat = catalog_by_code.get(code)
        source_ref = (cat or {}).get("catalog_pages", "") or row.get("カタログ参照", "")
        already_normalized = "printed_pages_normalized" in (cat or {}).get("issue_flags", "")
        old_ref = source_ref
        if already_normalized:
            new_ref, method = source_ref, "already_normalized"
        else:
            new_ref, method = printed_reference(source_ref)
        row["カタログ参照"] = new_ref
        pack_old = row.get("入数", "")
        pack_new, pack_note = PACK_FIXES.get(code, (pack_old, ""))
        if code in PACK_FIXES:
            row["入数"] = pack_new

        if cat is not None:
            cat["catalog_pages"] = new_ref
            evidence = cat.get("catalog_evidence", "")
            if old_ref:
                evidence = evidence.replace(old_ref, new_ref or "印刷ページ未確定")
            if code in {"1053", "1054"}:
                evidence = re.sub(r"(?:入数[:：]?\s*)?2本", "周辺情報の入数2本は表示禁止", evidence)
            cat["catalog_evidence"] = evidence
            flags = [value for value in cat.get("issue_flags", "").split("|") if value]
            if old_ref and not new_ref:
                flags.append("printed_page_unconfirmed_front_matter")
            if code == "1029":
                flags.append("unit_conflict_hp_catalog")
            if pack_note:
                flags.append("pack_quantity_corrected_from_printed_catalog")
            flags.append("printed_pages_normalized")
            cat["issue_flags"] = "|".join(dict.fromkeys(flags))

        audit_rows.append(
            {
                "品番": code,
                "商品名": row.get("商品名_JA", ""),
                "旧カタログ参照": old_ref,
                "印刷ページ参照": new_ref,
                "変換方法": method,
                "旧入数": pack_old,
                "修正入数": pack_new,
                "入数修正根拠": pack_note,
                "確認元PDF": PDF_SOURCE,
            }
        )

    write_rows(MASTER, master_rows, master_headers)
    write_rows(CATALOG, catalog_rows, catalog_headers)
    write_rows(
        AUDIT,
        audit_rows,
        ["品番", "商品名", "旧カタログ参照", "印刷ページ参照", "変換方法", "旧入数", "修正入数", "入数修正根拠", "確認元PDF"],
    )
    changed = sum(row["旧カタログ参照"] != row["印刷ページ参照"] for row in audit_rows)
    unresolved = sum(bool(row["旧カタログ参照"]) and not row["印刷ページ参照"] for row in audit_rows)
    print(f"rows={len(master_rows)} changed_refs={changed} unresolved_front_matter={unresolved}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
