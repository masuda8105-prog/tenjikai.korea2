import csv
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "product_master_multilingual.csv"
FALLBACK_MASTER_PATH = ROOT / "product_master_multilingual.grounded.csv"
CATALOG_PATH = ROOT / ".agents" / "catalog_research_output.csv"
HP_PATH = ROOT / ".agents" / "hp_research_output.csv"
EVIDENCE_PATH = ROOT / ".agents" / "one_line_summary_evidence_report.csv"
AUDIT_PATH = ROOT / ".agents" / "programming_agent_summary_audit.csv"
PDF_PATH = ROOT / "サンニシムラ総合カタログ2025-2027 (1).pdf"

LANG_COLS = {
    "ja": {"summary": "一言要約_JA", "customer": "接客説明_JA", "usage": "用途_JA", "benefit": "メリット_JA"},
    "en": {"summary": "一言要約_EN", "customer": "接客説明_EN", "usage": "用途_EN", "benefit": "メリット_EN"},
    "zh": {"summary": "一言要約_ZH", "customer": "接客説明_ZH", "usage": "用途_ZH", "benefit": "メリット_ZH"},
    "ko": {"summary": "一言要約_KO", "customer": "接客説明_KO", "usage": "用途_KO", "benefit": "メリット_KO"},
}

BENEFIT = {
    "ja": "用途を一目で確認できます",
    "en": "makes the intended use clear",
    "zh": "便于快速确认用途",
    "ko": "용도를 한눈에 확인할 수 있음",
}


def u(ja, en, zh, ko):
    return {"ja": ja, "en": en, "zh": zh, "ko": ko}


USAGES = {
    "sports_band": u("メガネ固定", "keeping glasses in place", "固定眼镜", "안경 고정"),
    "washer": u("ネジまわりの固定補助", "supporting screw-area fastening", "辅助螺丝周边固定", "나사 주변 고정 보조"),
    "nose_pad": u("鼻パッド交換・調整", "nose-pad replacement and adjustment", "更换和调整鼻托", "코패드 교체 및 조정"),
    "air_pad": u("エアーシリコン鼻パッド交換", "air-silicone nose-pad replacement", "更换空气硅胶鼻托", "에어 실리콘 코패드 교체"),
    "adhesive_fit_pad": u("貼るフィット調整", "adhesive fit adjustment", "贴附式贴合调整", "부착식 피팅 조정"),
    "nose_pad_build": u("鼻盛り・掛け位置調整", "nose build-up and fit-position adjustment", "鼻托加高和佩戴位置调整", "코받침 보정 및 착용 위치 조정"),
    "pad_arm": u("パッド足交換・補修", "pad-arm replacement and repair", "更换和维修鼻托臂", "패드 암 교체 및 보수"),
    "temple_tip": u("モダン・先セル交換", "temple-tip replacement", "更换脚套/镜腿末端", "모던/팁 교체"),
    "temple_sheet": u("テンプルの貼るフィット調整", "adhesive temple fit adjustment", "镜腿贴附式贴合调整", "템플 부착식 피팅 조정"),
    "shrink_tube": u("テンプルや小部品の保護・補修", "protecting and repairing temples or small parts", "保护和修补镜腿或小部件", "템플과 소부품 보호 및 보수"),
    "screw": u("眼鏡ネジ交換・固定", "eyewear screw replacement and fastening", "更换和固定眼镜螺丝", "안경 나사 교체 및 고정"),
    "screw_bolt": u("ツーポイントやフレーム部品の固定", "fastening rimless or frame parts", "固定无框或镜架部件", "무테 및 프레임 부품 고정"),
    "nut": u("小ナット交換・固定", "small-nut replacement and fastening", "更换和固定小螺母", "소형 너트 교체 및 고정"),
    "nut_driver": u("ナットの締め外し", "tightening and removing nuts", "拧紧和拆卸螺母", "너트 조임 및 분리"),
    "nylor_string": u("ナイロール用テグス交換", "nylor cord replacement", "更换半框鱼线", "나일론 림 줄 교체"),
    "nylor_sheet": u("ナイロールレンズ着脱", "nylor lens removal and installation", "半框镜片拆装", "나일론 림 렌즈 탈착"),
    "nylor_burner": u("ナイロールのストッパー玉作成", "forming stopper beads on nylor cord", "制作半框鱼线止挡球", "나일론 림 줄 스토퍼 구슬 제작"),
    "nylon_rail": u("ナイロール・溝まわり調整", "nylor and groove adjustment", "半框线槽调整", "나일론 림과 홈 주변 조정"),
    "screwdriver": u("眼鏡ネジの締め外し", "tightening and removing eyewear screws", "拧紧和拆卸眼镜螺丝", "안경 나사 조임 및 분리"),
    "screw_remover": u("固着・折れ込みネジの除去", "removing stuck or broken screws", "拆卸固着或折断螺丝", "고착 또는 부러진 나사 제거"),
    "drill": u("穴あけ・穴調整", "drilling and hole adjustment", "钻孔和修孔", "구멍 가공 및 조정"),
    "drill_stand": u("ハンドドリル固定", "holding a hand drill steady", "固定手钻", "핸드 드릴 고정"),
    "frame_heater": u("フレーム加熱・調整", "frame heating and adjustment", "镜架加热和调整", "프레임 가열 및 조정"),
    "cutting_fluid": u("穴あけ・切削時の潤滑", "lubrication during drilling and cutting", "钻孔和切削时润滑", "구멍 가공 및 절삭 시 윤활"),
    "workbench": u("ネジ締め・加工時の作業台", "workbench use for screw tightening and processing", "拧螺丝和加工用作业台", "나사 조임 및 가공용 작업대"),
    "tweezers": u("精密ネジ・小部品保持", "holding precision screws and small parts", "夹持精密螺丝和小部件", "정밀 나사와 작은 부품 집기"),
    "reamer": u("穴の面取り・微調整", "hole chamfering and fine adjustment", "孔口倒角和微调", "구멍 면취 및 미세 조정"),
    "file_grinding": u("削り・面取り・仕上げ", "filing, chamfering, and finishing", "削磨、倒角和收尾", "절삭, 면취 및 마감"),
    "polish": u("研磨・艶出し", "polishing and gloss finishing", "研磨和抛光", "연마 및 광택 마감"),
    "cleaner": u("メガネ洗浄・清掃", "eyewear washing and cleaning", "眼镜清洗和清洁", "안경 세척 및 청소"),
    "anti_fog": u("くもり止め", "anti-fog treatment", "防雾", "김서림 방지"),
    "tape": u("作業時の保護", "protection during work", "作业时保护", "작업 중 보호"),
    "adhesive": u("接着・ゆるみ止め", "bonding and thread locking", "粘接和防松", "접착 및 풀림 방지"),
    "soldering": u("ロウ付け・加熱補修", "soldering and heat repair", "焊接和加热修理", "납땜 및 가열 보수"),
    "pliers_klings": u("クリングス微調整", "fine pad-arm adjustment", "鼻托臂微调", "클링스 미세 조정"),
    "pliers_pad": u("パッド角度調整", "pad angle adjustment", "鼻托角度调整", "패드 각도 조정"),
    "pliers_pad_stretch": u("パッド足のU字部調整", "pad-arm U-section adjustment", "鼻托臂U形部调整", "패드 암 U자부 조정"),
    "pliers_joint": u("智・丁番まわり固定", "holding bridge-end and hinge areas", "固定桩头和铰链周边", "지와 힌지 주변 고정"),
    "pliers_temple_open": u("テンプル開き調整", "temple opening adjustment", "镜腿开合调整", "템플 벌어짐 조정"),
    "pliers_temple_angle": u("テンプル角度・前傾角調整", "temple angle and pantoscopic tilt adjustment", "镜腿角度和前倾角调整", "템플 각도 및 전경각 조정"),
    "pliers_bridge": u("ブリッジ角度・フロント調整", "bridge angle and front adjustment", "鼻梁角度和前框调整", "브리지 각도 및 프런트 조정"),
    "pliers_modern": u("モダン曲げ", "temple-tip bending", "脚套弯曲", "모던 굽힘"),
    "pliers_rim": u("リム調整", "rim adjustment", "镜圈调整", "림 조정"),
    "pliers_lens_size": u("レンズサイズ確認", "lens-size checking", "确认镜片尺寸", "렌즈 사이즈 확인"),
    "pliers_rimless_hold": u("ツーポイント固定", "rimless screw and nut holding", "无框螺丝/螺母固定", "무테 나사와 너트 고정"),
    "pliers_screw_grip": u("小ネジつかみ", "gripping small screws", "夹取小螺丝", "작은 나사 집기"),
    "pliers_pin_work": u("ピン抜き・Wブッシュ加工", "pin removal and W-bushing work", "拔销和W衬套加工", "핀 제거 및 W부싱 작업"),
    "pliers_generic": u("フレーム調整・部品保持", "frame adjustment and part holding", "镜架调整和部件夹持", "프레임 조정 및 부품 고정"),
    "pliers_screw_cut": u("ツーポイント用ネジ長さ調整", "rimless screw length adjustment", "无框螺丝长度调整", "무테 나사 길이 조정"),
    "pliers_cut": u("切断・喰い切り", "cutting and nipping", "切断和剪切", "절단 및 니핑"),
    "pliers_tip": u("ヤットコ先端交換", "plier-tip replacement", "钳子前端更换", "플라이어 팁 교체"),
    "pliers_cover": u("ヤットコ先端保護", "plier-tip protection", "钳子前端保护", "플라이어 팁 보호"),
    "pad_remover": u("ワンタッチパッド取り外し", "one-touch pad removal", "拆卸一触式鼻托", "원터치 패드 제거"),
    "test_lens": u("検眼用テストレンズ", "trial lenses for refraction", "验光用测试镜片", "검안용 테스트 렌즈"),
    "trial_frame": u("試験枠での検眼", "trial-frame refraction", "试镜架验光", "시험테 검안"),
    "magnifier": u("拡大確認", "magnified viewing", "放大确认", "확대 확인"),
    "checker": u("確認・検査", "checking and inspection", "确认和检查", "확인 및 검사"),
    "mark_light": u("累進レンズの隠しマーク確認", "checking hidden marks on progressive lenses", "确认渐进镜片隐藏标记", "누진렌즈 숨은 마크 확인"),
    "reading": u("近用・手元作業", "near vision and close work", "近用和近距离作业", "근거리 시야 및 손작업"),
    "clip_on": u("まぶしさ対策", "glare control", "防眩光", "눈부심 대책"),
    "sunglasses": u("日差し・まぶしさ対策", "sunlight and glare control", "遮阳和防眩", "햇빛 및 눈부심 대책"),
    "children_frame": u("幼児・子ども用フレーム", "children's frames", "儿童镜架", "어린이용 프레임"),
    "care_frame": u("介護向けフレーム", "care-use frames", "护理用镜架", "케어용 프레임"),
    "pc_glasses": u("PC作業・室内用", "PC work and indoor use", "PC作业和室内使用", "PC 작업 및 실내용"),
    "temple_cable": u("ケーブルテンプル化", "cable-temple conversion", "卷曲镜腿改装", "케이블 템플 전환"),
    "parts_set": u("交換部品の一括準備", "replacement-part setup", "更换部件集中准备", "교체 부품 일괄 준비"),
    "toolset": u("工具一式の準備", "tool-set preparation", "工具套装准备", "공구 세트 준비"),
    "tool_storage": u("工具整理・収納", "tool organization and storage", "工具整理和收纳", "공구 정리 및 수납"),
    "measuring": u("測定・確認", "measurement and checking", "测量和确认", "측정 및 확인"),
    "book": u("眼鏡知識・技術学習", "eyewear knowledge and skill training", "眼镜知识和技术学习", "안경 지식 및 기술 학습"),
    "aftercare": u("アフターケア案内", "aftercare guidance", "售后护理说明", "애프터케어 안내"),
    "machine_part": u("機器部品交換・補修", "equipment part replacement and repair", "设备部件更换和维修", "장비 부품 교체 및 보수"),
    "work_supply": u("作業補助", "work support", "作业辅助", "작업 보조"),
    "battery": u("電池交換", "battery replacement", "更换电池", "배터리 교체"),
    "case": u("収納・保護", "storage and protection", "收纳和保护", "수납 및 보호"),
    "display": u("展示・販売促進", "display and promotion", "展示和促销", "진열 및 판매 촉진"),
    "glass_chain": u("携帯・落下防止", "carrying and drop prevention", "携带和防掉落", "휴대 및 낙하 방지"),
    "retainer": u("ズレ落ち防止", "anti-slip fit support", "防滑佩戴辅助", "흘러내림 방지"),
    "color_repair": u("色補修", "color repair", "颜色修补", "색상 보수"),
    "ink": u("印点・マーキング", "dotting and marking", "印点和标记", "인점 및 마킹"),
    "brush": u("清掃・研磨仕上げ", "cleaning and polishing finish", "清洁和研磨收尾", "청소 및 연마 마감"),
    "parts": u("交換・補修", "replacement and repair", "更换和维修", "교체 및 보수"),
    "unknown": u("用途確認", "use confirmation", "用途确认", "용도 확인"),
}

CODE_OVERRIDES = {
    "104": "pliers_klings",
    "1053": "pliers_pad",
    "1054": "pliers_pad",
    "2": "pliers_modern",
    "3": "pliers_klings",
    "190": "pliers_klings",
    "662": "pliers_klings",
    "651": "pliers_klings",
    "858": "pliers_klings",
    "854": "pliers_klings",
    "357": "pliers_pad_stretch",
    "395-B": "pliers_pad",
    "356": "pliers_pad",
    "617": "pliers_pad",
    "969": "pliers_pad",
    "997": "pliers_pad",
    "1006": "pliers_pad",
    "5": "pliers_cut",
    "225": "pliers_cut",
    "304": "pliers_cut",
    "156-B": "pliers_cut",
    "372": "pliers_cut",
    "971-P": "pliers_cut",
    "1569": "pliers_cut",
    "1577-10N": "pliers_cut",
    "174": "pliers_screw_cut",
    "661": "pliers_screw_cut",
    "612-B": "pliers_screw_cut",
    "22-B": "pliers_lens_size",
    "335-B": "pliers_lens_size",
    "1542": "pliers_lens_size",
    "717": "pliers_rimless_hold",
    "20-B": "pliers_joint",
    "193": "pliers_joint",
    "308-B": "pliers_joint",
    "386": "pliers_joint",
    "765": "pliers_joint",
    "766": "pliers_joint",
    "76-B": "pliers_joint",
    "1551-00": "pliers_joint",
    "1553": "pliers_joint",
    "614": "pliers_joint",
    "937": "pliers_joint",
    "996": "pliers_joint",
    "40-P": "pliers_temple_open",
    "642-P": "pliers_temple_open",
    "1596": "pliers_temple_open",
    "859": "pliers_temple_angle",
    "1548": "pliers_temple_angle",
    "25-B": "pliers_bridge",
    "352": "pliers_bridge",
    "642": "pliers_bridge",
    "720": "pliers_bridge",
    "613-B": "pliers_bridge",
    "610-A": "pliers_rim",
    "1507": "pliers_rim",
    "1029": "pliers_cover",
    "149-B": "tweezers",
    "1634": "tweezers",
    "1651": "tweezers",
    "191-B": "tweezers",
    "192-A": "tweezers",
    "192-B": "tweezers",
    "242": "tweezers",
    "348": "tweezers",
    "814": "tweezers",
    "665": "tweezers",
    "669": "tweezers",
    "168": "screw_remover",
    "2221-02": "screw_remover",
    "985": "screw_remover",
    "1742": "nut_driver",
    "309": "nut_driver",
    "309-A": "nut_driver",
    "336-C": "nut_driver",
    "336-D": "nut_driver",
    "336-E": "nut_driver",
    "339": "nut_driver",
    "6006": "nut_driver",
    "6007": "nut_driver",
    "6008": "nut_driver",
    "6009": "nut_driver",
    "726-C": "nut_driver",
    "726-D": "nut_driver",
    "726-E": "nut_driver",
    "726-F": "nut_driver",
    "169-MBK": "frame_heater",
    "237": "cutting_fluid",
    "284": "workbench",
    "298": "drill_stand",
    "310": "aftercare",
    "310-1": "aftercare",
    "350": "aftercare",
    "441-A": "case",
    "752-WX": "book",
    "1007": "color_repair",
    "670-C": "cleaner",
    "810-A": "nylor_string",
    "962-EX": "nylor_string",
    "1042N": "nylor_burner",
    "141-766": "nylor_sheet",
    "1013": "file_grinding",
    "1014": "file_grinding",
    "68": "parts_set",
    "710": "parts_set",
    "206": "temple_cable",
    "315": "temple_cable",
    "809-B": "children_frame",
    "809-P": "children_frame",
    "828-B-36": "children_frame",
    "828-B-38": "children_frame",
    "828-P-36": "children_frame",
    "828-P-38": "children_frame",
    "E29945100": "pc_glasses",
    "E29945200": "pc_glasses",
    "E29945300": "pc_glasses",
    "E29945500": "pc_glasses",
    "E1619": "machine_part",
    "E1625S": "measuring",
    "E1625T": "machine_part",
    "E1630": "measuring",
    "E16321": "measuring",
    "N40350-M372": "drill",
    "N40360-M103": "drill",
}

BAD_CATALOG_TOKENS = [
    "視力測定 加",
    "販売・販促 ドライバー",
    "ライトブラウン 視力測定",
    "フタ収納時",
    "Grid Sticker",
]


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, headers, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compact(value, limit=700):
    text = re.sub(r"\s+", " ", value or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def has(text, *words):
    return any(w in text for w in words)


def source_text(row, catalog_row, hp_row):
    name = row.get("商品名_JA", "")
    catalog_usage = catalog_row.get("catalog_usage", "")
    hp_status = hp_row.get("hp_match_status", "")
    hp_text = ""
    if hp_status == "exact":
        hp_text = " ".join([hp_row.get("hp_product_name", ""), hp_row.get("hp_categories", ""), hp_row.get("hp_description", "")])
    return name, catalog_usage, hp_text, " ".join([name, catalog_usage, hp_text])


def catalog_usage_is_safe(usage):
    if not usage:
        return False
    if any(token in usage for token in BAD_CATALOG_TOKENS):
        return False
    return True


def hp_usage_sentence(hp_row):
    if hp_row.get("hp_match_status") != "exact":
        return ""
    desc = hp_row.get("hp_description", "")
    m = re.search(r"(?:主な使用用途|使用用途)[:：]\s*([^|。]+)", desc)
    if m:
        return m.group(1).strip()
    first = desc.split("|")[0].strip()
    if len(first) <= 80 and has(first, "用", "ため", "向け", "使"):
        return first
    return ""


def detect_usage_key(row, catalog_row, hp_row):
    code = row.get("品番", "").strip()
    if code in CODE_OVERRIDES:
        return CODE_OVERRIDES[code], "code_verified"

    name, catalog_usage, hp_text, all_text = source_text(row, catalog_row, hp_row)
    hp_sentence = hp_usage_sentence(hp_row)
    primary = " ".join([hp_sentence, hp_text]) if hp_sentence else hp_text
    safe_catalog = catalog_usage if catalog_usage_is_safe(catalog_usage) else ""
    text = " ".join([primary, safe_catalog, name])

    # High-precision product-name rules first.
    if has(name, "ヤットコ先", "先プラスチック", "先ビニール", "先プラ", "交換用先端"):
        return "pliers_tip", "product_name"
    if has(name, "滑り止めシール") and has(name, "ヤットコ"):
        return "pliers_cover", "product_name"
    if has(name, "ピンセット"):
        return "tweezers", "product_name"
    if has(name, "ナット廻し", "ナット回し"):
        return "nut_driver", "product_name"
    if has(name, "ネジ抜き", "ねじ抜き", "折込ネジ抜き", "折れ込ネジ抜き"):
        return "screw_remover", "product_name"
    if has(name, "フレームヒーター"):
        return "frame_heater", "product_name"
    if has(name, "カットルーブ", "切削剤"):
        return "cutting_fluid", "product_name"
    if has(name, "ハンドドリルスタンド"):
        return "drill_stand", "product_name"
    if name == "作業台" or has(name, " 作業台"):
        return "workbench", "product_name"

    # Official exact HP text and catalog usage for tool bodies only.
    is_pliers = has(name, "ヤットコ", "プライヤー", "ニッパー") or has(hp_text, "ヤットコ", "プライヤー", "ニッパー")
    if is_pliers:
        if has(text, "クリングスの微調整", "主にクリングス", "クリングス調整", "パット足を直接", "パッド足を直接"):
            return "pliers_klings", "hp_or_catalog_usage"
        if has(text, "パッド角度", "パット角度", "パット調整", "パッド調整", "箱蝶", "ボックス", "プッシュロック", "2本ダキ足", "ダキ足"):
            return "pliers_pad", "hp_or_catalog_usage"
        if has(text, "U字部分を伸ば", "パットの足を伸ば", "パッドの足を伸ば"):
            return "pliers_pad_stretch", "hp_or_catalog_usage"
        if has(text, "智固定", "智等", "智の固定", "丁番の固定", "智・リムまわり固定"):
            return "pliers_joint", "hp_or_catalog_usage"
        if has(text, "テンプル開き"):
            return "pliers_temple_open", "hp_or_catalog_usage"
        if has(text, "テンプル角度", "前傾角", "丁番ゴマ", "智のねじれ"):
            return "pliers_temple_angle", "hp_or_catalog_usage"
        if has(text, "ブリッジ角度", "フロント調整", "フロントバランス"):
            return "pliers_bridge", "hp_or_catalog_usage"
        if has(text, "モダン曲げ", "先セル曲げ"):
            return "pliers_modern", "hp_or_catalog_usage"
        if has(text, "レンズサイズ", "歪度計", "リム止め"):
            return "pliers_lens_size", "hp_or_catalog_usage"
        if has(text, "ツーポイントの固定", "ナット部分を収めて固定", "固定前", "固定後"):
            return "pliers_rimless_hold", "hp_or_catalog_usage"
        if has(text, "小ネジつかみ", "ネジつかみ", "ネジ掴み"):
            return "pliers_screw_grip", "hp_or_catalog_usage"
        if has(name, "ピン抜き", "Wブッシュ") and not has(text, "カット", "喰い切り", "ニッパー"):
            return "pliers_pin_work", "product_name"
        if has(text, "ツーポネジ切り", "ツーポイント用ネジ切り", "ネジの長さ", "ねじ切り用"):
            return "pliers_screw_cut", "hp_or_catalog_usage"
        if (has(name, "ニッパー") or has(primary, "ニッパー", "喰い切り", "Wブッシュをカット", "カット用")) and not has(name, "ヤットコ先"):
            return "pliers_cut", "hp_or_catalog_usage"
        if has(text, "リム調整", "リムのアール", "リムを変形", "ナイロール型直し"):
            return "pliers_rim", "hp_or_catalog_usage"
        if has(text, "ワンタッチパッド取り外し", "ワンタッチパッド外し", "パットはずし", "パッドはずし"):
            return "pad_remover", "hp_or_catalog_usage"

    # Product families.
    if has(name, "エアシリコン", "エアーシリコン"):
        return "air_pad", "product_name"
    if has(name, "セルピタ", "セルシール", "セルモリー", "クビフリー"):
        return "adhesive_fit_pad", "product_name"
    if has(name, "鼻盛"):
        return "nose_pad_build", "product_name"
    if has(name, "パット足", "パッド足", "グースネック", "U型", "Ｕ型", "ダキ足", "アイアーム", "ガードアーム"):
        return "pad_arm", "product_name"
    if has(name, "パット", "パッド", "箱蝶", "ワンタッチ", "ビルトイン", "巻式"):
        return "nose_pad", "product_name"
    if has(name, "シートモダン"):
        return "temple_sheet", "product_name"
    if has(name, "モダン", "先セル"):
        return "temple_tip", "product_name"
    if has(name, "シュリンクチューブ"):
        return "shrink_tube", "product_name"
    if has(name, "テグス", "フロロカーボン"):
        return "nylor_string", "product_name"
    if has(name, "ナイロールシート"):
        return "nylor_sheet", "product_name"
    if has(name, "ナイロールストッパーバーナー"):
        return "nylor_burner", "product_name"
    if has(name, "ナイロンレール", "溝セル", "プロテクトリング"):
        return "nylon_rail", "product_name"
    if has(name, "ワッシャ", "座金"):
        return "washer", "product_name"
    if has(name, "ドライバー"):
        return "screwdriver", "product_name"
    if has(name, "ネジ", "スクリュー", "ダブルロック", "ハイブリッドロック", "OSロック", "ボルト"):
        return "screw_bolt" if has(name, "ツーポ", "ボルト", "ダブルロック", "OS") else "screw", "product_name"
    if has(name, "ナット"):
        return "nut", "product_name"
    if has(name, "ドリル", "穴明", "穴広げ", "エンドミル"):
        return "drill", "product_name"
    if has(name, "リーマ"):
        return "reamer", "product_name"
    if has(name, "ヤスリ", "砥石", "面取り", "サンドペーパー"):
        return "file_grinding", "product_name"
    if has(name, "バフ", "ポリッシャ", "みがき", "磨き", "コンパウンド", "マンドレール", "フェルト"):
        return "polish", "product_name"
    if has(name, "メガネブク", "洗浄", "クリーナー", "クロス", "セーム革", "メガネふき"):
        return "cleaner", "product_name"
    if has(name, "くもり", "曇り"):
        return "anti_fog", "product_name"
    if has(name, "テープ", "フィルム"):
        return "tape", "product_name"
    if has(name, "接着", "アロンタイト", "固着剤"):
        return "adhesive", "product_name"
    if has(name, "ロウ付", "フラックス", "トーチ", "銀ロウ"):
        return "soldering", "product_name"
    if has(name, "テストレンズ", "レンズセット") and not has(name, "カバンのみ", "台のみ", "ケースのみ"):
        return "test_lens", "product_name"
    if has(name, "試験枠"):
        return "trial_frame", "product_name"
    if has(name, "ルーペ", "リネンテスター", "拡大", "ローグラス"):
        return "magnifier", "product_name"
    if has(name, "チェックライト", "チェッカー", "検査器", "テスター", "ビームライト"):
        return "mark_light" if has(name, "累進") else "checker", "product_name"
    if has(name, "リーディング", "近用", "老眼"):
        return "reading", "product_name"
    if has(name, "クリップオン"):
        return "clip_on", "product_name"
    if has(name, "サングラス"):
        return "sunglasses", "product_name"
    if has(name, "ビーバ"):
        return "children_frame", "product_name"
    if has(name, "介護"):
        return "care_frame", "product_name"
    if has(name, "エアーPC", "PC II度無し"):
        return "pc_glasses", "product_name"
    if has(name, "ビコーケーブル", "ジュニアケーブル", "ケーブルF"):
        return "temple_cable", "product_name"
    if has(name, "部品セット", "パーツセット"):
        return "parts_set", "product_name"
    if has(name, "工具セット", "外販工具セット", "技能士試験工具", "基本工具セット"):
        return "toolset", "product_name"
    if has(name, "工具台", "ツールスタンド", "ツールバー"):
        return "tool_storage", "product_name"
    if has(name, "測定", "ゲージ", "メジャー", "カーブ計", "厚み計"):
        return "measuring", "product_name"
    if has(name, "書籍", "講座", "眼鏡学", "フィッティング術", "手順"):
        return "book", "product_name"
    if has(name, "アフターケア"):
        return "aftercare", "product_name"
    if has(name, "電池", "充電", "USB"):
        return "battery", "product_name"
    if has(name, "ケース", "バッグ", "袋", "カバンのみ"):
        return "case", "product_name"
    if has(name, "のぼり", "POP", "吊下台紙", "ディスプレイ"):
        return "display", "product_name"
    if has(name, "グラスコード", "グラスチェーン", "チェーン", "コード"):
        return "glass_chain", "product_name"
    if has(name, "メガロック", "メガネグリップ"):
        return "retainer", "product_name"
    if has(name, "カラーリペア", "タッチアップ", "染色"):
        return "color_repair", "product_name"
    if has(name, "インク", "マーカー", "印点"):
        return "ink", "product_name"
    if has(name, "ブラシ"):
        return "brush", "product_name"
    if has(name, "ヤットコ", "プライヤー"):
        return "pliers_generic", "catalog_generic" if safe_catalog else "product_name_generic"
    if safe_catalog:
        return "parts", "catalog_generic"
    return "parts", "product_name_generic"


def make_summary(usage):
    ja = f"{usage['ja']}です。" if "用" in usage["ja"] else f"{usage['ja']}用です。"
    ko = f"{usage['ko']}입니다." if "용" in usage["ko"] else f"{usage['ko']}용입니다."
    return {
        "ja": ja,
        "en": f"For {usage['en']}.",
        "zh": f"用于{usage['zh']}。",
        "ko": ko,
    }


def hp_info(row, hp_row):
    status = hp_row.get("hp_match_status", "") or row.get("HP確認ステータス", "")
    if status == "exact":
        parts = [
            hp_row.get("hp_url", ""),
            hp_row.get("hp_product_name", ""),
            hp_row.get("hp_product_code", ""),
            hp_row.get("hp_categories", ""),
            hp_row.get("hp_description", ""),
        ]
        return compact(" / ".join(p for p in parts if p))
    if status:
        return f"HP照合ステータス: {status}。exact未確認のためHP情報は用途根拠に未使用。"
    return ""


def catalog_info(row, catalog_row):
    parts = [
        catalog_row.get("catalog_pages") or row.get("カタログ参照", ""),
        catalog_row.get("catalog_usage", ""),
        catalog_row.get("catalog_info", ""),
        catalog_row.get("issue_flags", ""),
    ]
    return compact(" / ".join(p for p in parts if p))


def source_label(row, catalog_row, hp_row):
    sources = []
    if hp_row.get("hp_match_status") == "exact" and hp_row.get("hp_url"):
        sources.append(hp_row["hp_url"])
    pages = catalog_row.get("catalog_pages") or row.get("カタログ参照")
    if pages:
        sources.append(pages)
    if PDF_PATH.exists():
        sources.append(f"PDF:{PDF_PATH.name}")
    return " / ".join(dict.fromkeys(sources))


def apply_usage(row, key, basis, hp_row, catalog_row):
    usage = USAGES.get(key, USAGES["unknown"])
    summaries = make_summary(usage)
    for lang, cols in LANG_COLS.items():
        row[cols["summary"]] = summaries[lang]
        row[cols["customer"]] = summaries[lang]
        row[cols["usage"]] = usage[lang]
        row[cols["benefit"]] = BENEFIT[lang]
    row["説明カテゴリ"] = key
    row["説明強化元"] = "rebuild_summaries_grounded_usage.py"
    row["HP確認ステータス"] = hp_row.get("hp_match_status", "") or row.get("HP確認ステータス", "")
    row["HPから確認した情報"] = hp_info(row, hp_row)
    row["カタログから確認した情報"] = catalog_info(row, catalog_row)
    if basis == "needs_check":
        note = "用途キー再構築: HP exactまたは明確なカタログ用途が弱いため、用途断定を避けた。要確認。"
    elif basis == "code_verified":
        note = "用途キー再構築: HP/csv監査で確認済みの重要品番ルールを使用。"
    elif basis.startswith("hp"):
        note = "用途キー再構築: HP exactまたはカタログ用途の明示表現を優先。"
    elif basis.startswith("catalog"):
        note = "用途キー再構築: カタログ用途を優先。"
    else:
        note = "用途キー再構築: 商品名の明示語から最小用途に限定。"
    row["要約品質メモ"] = note

    if row.get("品番") in {"1053", "1054"}:
        row["入数"] = ""
        row["要約品質メモ"] += " 工具本体のため誤抽出された入数は表示しない。"
    if row.get("品番") in {"828-B-36", "828-B-38", "828-P-36", "828-P-38"}:
        row["入数"] = ""
        row["要約品質メモ"] += " 36/38はサイズ表記のため入数として表示しない。"


def main():
    rows = read_rows(MASTER_PATH)
    headers = list(rows[0].keys())
    catalog_rows = {r.get("品番", ""): r for r in read_rows(CATALOG_PATH)}
    hp_rows = {r.get("品番", ""): r for r in read_rows(HP_PATH)}
    evidence_rows = []
    audit_rows = []
    counts = Counter()
    basis_counts = Counter()

    for row in rows:
        code = row.get("品番", "")
        catalog_row = catalog_rows.get(code, {})
        hp_row = hp_rows.get(code, {})
        old_summary = row.get("一言要約_JA", "")
        old_category = row.get("説明カテゴリ", "")
        key, basis = detect_usage_key(row, catalog_row, hp_row)
        apply_usage(row, key, basis, hp_row, catalog_row)
        counts[key] += 1
        basis_counts[basis] += 1
        evidence_rows.append(
            {
                "品番": code,
                "商品名": row.get("商品名_JA", ""),
                "HPから確認した情報": row.get("HPから確認した情報", ""),
                "カタログから確認した情報": row.get("カタログから確認した情報", ""),
                "日本語の一言要約": row.get("一言要約_JA", ""),
                "英語の一言要約": row.get("一言要約_EN", ""),
                "中国語の一言要約": row.get("一言要約_ZH", ""),
                "韓国語の一言要約": row.get("一言要約_KO", ""),
                "確認元URLまたはカタログ掲載ページ": source_label(row, catalog_row, hp_row),
                "用途キー": key,
                "判定根拠種別": basis,
            }
        )
        audit_rows.append(
            {
                "品番": code,
                "商品名_JA": row.get("商品名_JA", ""),
                "old_category": old_category,
                "new_category": key,
                "basis": basis,
                "hp_match_status": row.get("HP確認ステータス", ""),
                "catalog_usage": catalog_row.get("catalog_usage", ""),
                "old_summary_ja": old_summary,
                "new_summary_ja": row.get("一言要約_JA", ""),
                "source": source_label(row, catalog_row, hp_row),
                "quality_note": row.get("要約品質メモ", ""),
            }
        )

    master_written = MASTER_PATH
    try:
        write_rows(MASTER_PATH, headers, rows)
    except PermissionError:
        write_rows(FALLBACK_MASTER_PATH, headers, rows)
        master_written = FALLBACK_MASTER_PATH
    write_rows(EVIDENCE_PATH, list(evidence_rows[0].keys()), evidence_rows)
    write_rows(AUDIT_PATH, list(audit_rows[0].keys()), audit_rows)

    print(f"rows={len(rows)}")
    print(f"master_written={master_written}")
    print("basis_counts")
    for key, count in basis_counts.most_common():
        print(f"{key}\t{count}")
    print("usage_counts")
    for key, count in counts.most_common():
        print(f"{key}\t{count}")


if __name__ == "__main__":
    main()
