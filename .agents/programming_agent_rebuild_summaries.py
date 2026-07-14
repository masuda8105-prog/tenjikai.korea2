import csv
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "product_master_multilingual.csv"
LEGACY_MASTER_PATH = ROOT / "product_master_multilingual.rebuilt.csv"
FALLBACK_MASTER_PATH = ROOT / "product_master_multilingual.generated.csv"
CATALOG_PATH = ROOT / ".agents" / "catalog_research_output.csv"
HP_PATH = ROOT / ".agents" / "hp_research_output.csv"
EVIDENCE_PATH = ROOT / ".agents" / "one_line_summary_evidence_report.csv"
AUDIT_PATH = ROOT / ".agents" / "programming_agent_summary_audit.csv"
WORKSPACE_CATALOG_PDF_PATH = ROOT / "サンニシムラ総合カタログ2025-2027 (1).pdf"
EXTERNAL_CATALOG_PDF_PATH = Path(
    r"C:\Users\AONUSR02\Desktop\売上データ\サンニシムラ総合カタログ2025-2027 (1).pdf"
)
CATALOG_PDF_PATH = (
    WORKSPACE_CATALOG_PDF_PATH
    if WORKSPACE_CATALOG_PDF_PATH.exists()
    else EXTERNAL_CATALOG_PDF_PATH
)


LANG_COLS = {
    "ja": {
        "summary": "一言要約_JA",
        "customer": "接客説明_JA",
        "usage": "用途_JA",
        "benefit": "メリット_JA",
    },
    "en": {
        "summary": "一言要約_EN",
        "customer": "接客説明_EN",
        "usage": "用途_EN",
        "benefit": "メリット_EN",
    },
    "zh": {
        "summary": "一言要約_ZH",
        "customer": "接客説明_ZH",
        "usage": "用途_ZH",
        "benefit": "メリット_ZH",
    },
    "ko": {
        "summary": "一言要約_KO",
        "customer": "接客説明_KO",
        "usage": "用途_KO",
        "benefit": "メリット_KO",
    },
}


def t(ja, en, zh, ko):
    return {"ja": ja, "en": en, "zh": zh, "ko": ko}


def template(summary, usage, benefit):
    return {"summary": summary, "usage": usage, "benefit": benefit}


TEMPLATES = {
    "nose_pad": template(
        t(
            "鼻パッドの交換・調整に使うパーツです。形状や素材を合わせて選ぶことで、鼻への当たりを整え、掛け心地を改善しやすくします。",
            "A part for replacing or adjusting nose pads. Choosing the right shape and material helps improve nose contact and wearing comfort.",
            "用于更换或调整鼻托的部件。按形状和材质选择，可改善鼻部接触感和佩戴舒适度。",
            "코패드 교체와 조정에 사용하는 부품입니다. 형태와 소재를 맞춰 선택하면 코에 닿는 느낌과 착용감을 개선하기 쉽습니다.",
        ),
        t("鼻パッド交換・調整", "nose-pad replacement and adjustment", "鼻托更换与调整", "코패드 교체 및 조정"),
        t("当たりと掛け心地を整えやすい", "helps improve fit and comfort", "有助于改善贴合和舒适度", "맞닿는 느낌과 착용감을 조정하기 쉬움"),
    ),
    "air_pad": template(
        t(
            "エアクッション入りの鼻パッドです。鼻への圧迫感をやわらげ、掛け心地をやさしく整えたい時に提案しやすい商品です。",
            "An air-cushioned nose pad. It helps soften pressure on the nose and is easy to recommend when comfort is the priority.",
            "带空气缓冲的鼻托。可减轻鼻部压迫感，适合向重视舒适度的顾客推荐。",
            "에어 쿠션이 들어간 코패드입니다. 코 압박감을 줄여 착용감을 부드럽게 조정하고 싶을 때 제안하기 좋습니다.",
        ),
        t("鼻当たりの軽減", "reducing nose pressure", "减轻鼻部压迫", "코 압박 완화"),
        t("やわらかい掛け心地を提案しやすい", "easy to recommend for softer comfort", "便于推荐更柔和的佩戴感", "부드러운 착용감을 제안하기 쉬움"),
    ),
    "antibacterial_pad": template(
        t(
            "抗菌仕様の鼻パッドです。交換時に清潔感を伝えやすく、店頭でのメンテナンス提案に使いやすいパーツです。",
            "An antibacterial nose pad. It helps communicate a cleaner feel during replacement and supports in-store maintenance proposals.",
            "抗菌规格鼻托。更换时容易传达清洁感，适合门店维护建议使用。",
            "항균 사양 코패드입니다. 교체 시 위생적인 인상을 전달하기 쉬워 매장 관리 제안에 쓰기 좋습니다.",
        ),
        t("抗菌鼻パッド交換", "antibacterial nose-pad replacement", "抗菌鼻托更换", "항균 코패드 교체"),
        t("清潔感を伝えやすい", "helps present a cleaner feel", "有助于传达清洁感", "위생적인 느낌을 전달하기 쉬움"),
    ),
    "adhesive_fit_pad": template(
        t(
            "貼り付けてズレや鼻当たりを調整するフィット補助パーツです。加工なしで提案しやすく、店頭で短時間に対応できます。",
            "An adhesive fitting aid for reducing slipping or adjusting nose contact. It is easy to offer without frame processing and can be applied quickly in store.",
            "用于粘贴调整防滑或鼻部接触的贴附型配件。无需加工，门店可快速处理并推荐。",
            "붙여서 흘러내림이나 코 닿는 부분을 조정하는 피팅 보조 부품입니다. 가공 없이 매장에서 빠르게 제안하기 쉽습니다.",
        ),
        t("貼るフィット調整", "adhesive fit adjustment", "贴附式贴合调整", "부착식 피팅 조정"),
        t("加工なしでズレや当たりを調整しやすい", "helps adjust slipping or contact without processing", "无需加工即可调整防滑和接触感", "가공 없이 흘러내림과 닿는 느낌을 조정하기 쉬움"),
    ),
    "nose_pad_build": template(
        t(
            "プラスチックフレームなどの鼻盛りに使うパーツです。高さや当たりを補正し、低い鼻当てでも掛け位置を整えやすくします。",
            "A part for building up the nose area on plastic frames. It helps adjust height and contact so the glasses sit more comfortably.",
            "用于塑料镜架等鼻托加高的部件。可补正高度和接触位置，使佩戴位置更容易调整。",
            "플라스틱 프레임 등의 코받침 높이를 보정하는 부품입니다. 높이와 닿는 위치를 조정해 착용 위치를 맞추기 쉽습니다.",
        ),
        t("鼻盛り・掛け位置調整", "nose build-up and fit position adjustment", "鼻托加高与佩戴位置调整", "코받침 보정 및 착용 위치 조정"),
        t("低い鼻当てでも掛け位置を整えやすい", "helps improve fit position on low nose areas", "低鼻托也便于调整佩戴位置", "낮은 코받침도 착용 위치를 맞추기 쉬움"),
    ),
    "pad_arm": template(
        t(
            "パッド足やアームまわりの交換・補修に使う小部品です。破損や紛失時に必要な形状だけを選んで修理対応しやすくします。",
            "A small part for replacing or repairing pad arms and related hardware. It helps stores handle breakage or loss by selecting the needed shape.",
            "用于更换或修理鼻托臂及相关金具的小部件。破损或遗失时，可按需要选择形状进行维修。",
            "코패드 암과 주변 금구의 교체·수리에 사용하는 소부품입니다. 파손이나 분실 시 필요한 형태만 골라 대응하기 쉽습니다.",
        ),
        t("パッド足交換・補修", "pad-arm replacement and repair", "鼻托臂更换与修理", "코패드 암 교체 및 수리"),
        t("必要な形状だけを選んで補修しやすい", "helps repair only the needed shape", "便于只更换需要的形状", "필요한 형태만 골라 보수하기 쉬움"),
    ),
    "temple_tip": template(
        t(
            "モダン・先セルの交換に使うパーツです。傷みや汚れを交換し、耳まわりの掛け心地と見た目を整えやすくします。",
            "A replacement part for temple tips. It helps refresh worn or dirty tips and improve comfort and appearance around the ears.",
            "用于更换脚套/镜腿末端的部件。可替换磨损或污损部位，改善耳周佩戴感和外观。",
            "모던과 팁 교체에 사용하는 부품입니다. 낡거나 오염된 부분을 교체해 귀 주변 착용감과 외관을 정돈하기 쉽습니다.",
        ),
        t("モダン交換", "temple-tip replacement", "脚套更换", "모던 교체"),
        t("耳まわりの掛け心地と見た目を整えやすい", "helps refresh comfort and appearance around the ears", "便于改善耳部佩戴感和外观", "귀 주변 착용감과 외관을 정돈하기 쉬움"),
    ),
    "temple_sheet_grip": template(
        t(
            "テンプルに貼って耳まわりの当たりやズレを調整するシート状パーツです。加工を増やさず、掛け心地の微調整を短時間で提案できます。",
            "A sheet-type part applied to temples to adjust ear-area contact and slipping. It helps offer quick fit tweaks without extra processing.",
            "贴在镜腿上、用于调整耳周接触和防滑的片状配件。无需增加加工，便于快速提出佩戴感微调方案。",
            "템플에 붙여 귀 주변 닿는 느낌과 미끄러짐을 조정하는 시트형 부품입니다. 추가 가공 없이 착용감 미세 조정을 빠르게 제안할 수 있습니다.",
        ),
        t("テンプルの貼るフィット調整", "adhesive temple fit adjustment", "镜腿贴附式贴合调整", "템플 부착식 피팅 조정"),
        t("短時間で掛け心地を微調整しやすい", "helps fine-tune fit quickly", "便于快速微调佩戴感", "착용감을 빠르게 미세 조정하기 쉬움"),
    ),
    "shrink_tube": template(
        t(
            "熱で収縮してテンプルや小部品に密着するチューブです。保護・補修・滑り止め加工を短時間で行いやすくします。",
            "A heat-shrink tube that fits closely around temples or small parts. It helps with protection, repair, and anti-slip finishing.",
            "加热后收缩并贴合镜腿或小部件的套管。便于进行保护、修补和防滑加工。",
            "열로 수축해 템플이나 작은 부품에 밀착되는 튜브입니다. 보호, 보수, 미끄럼 방지 가공을 빠르게 하기 쉽습니다.",
        ),
        t("保護・補修・滑り止め加工", "protection, repair, and anti-slip work", "保护、修补与防滑加工", "보호·보수·미끄럼 방지 가공"),
        t("熱で密着し、必要部位を保護しやすい", "heat-shrinks to protect the needed area", "加热贴合，便于保护所需部位", "열로 밀착되어 필요한 부위를 보호하기 쉬움"),
    ),
    "screw": template(
        t(
            "眼鏡フレームの固定や修理に使うネジです。サイズを合わせて交換することで、ゆるみや紛失時の対応をスムーズにします。",
            "A screw for fastening and repairing eyewear frames. Matching the size helps handle loosened or missing screws smoothly.",
            "用于眼镜架固定和维修的螺丝。按尺寸更换，可顺利处理松动或遗失问题。",
            "안경 프레임 고정과 수리에 사용하는 나사입니다. 사이즈를 맞춰 교체하면 풀림이나 분실 시 대응하기 쉽습니다.",
        ),
        t("ネジ交換・固定", "screw replacement and fastening", "螺丝更换与固定", "나사 교체 및 고정"),
        t("ゆるみや紛失時に対応しやすい", "helps handle loosened or missing screws", "便于处理松动或遗失", "풀림이나 분실에 대응하기 쉬움"),
    ),
    "screw_bolt": template(
        t(
            "ツーポイントやフレーム部品の固定に使うネジ・ボルトです。寸法を合わせて交換し、ゆるみや外れを補修しやすくします。",
            "A screw or bolt for rimless frames and frame parts. Matching the dimensions helps repair loose or detached areas.",
            "用于无框架和镜架部件固定的螺丝/螺栓。按尺寸更换，便于修理松动或脱落。",
            "무테 프레임과 프레임 부품 고정에 쓰는 나사·볼트입니다. 치수를 맞춰 교체하면 풀림이나 이탈을 보수하기 쉽습니다.",
        ),
        t("ツーポイント固定・補修", "rimless-frame fastening and repair", "无框架固定与修理", "무테 프레임 고정 및 보수"),
        t("寸法を合わせて外れを補修しやすい", "helps repair loose or detached parts by size", "按尺寸修理脱落部位更方便", "치수를 맞춰 이탈 부위를 보수하기 쉬움"),
    ),
    "nut": template(
        t(
            "ツーポイントや小部品の固定に使うナットです。サイズを合わせて交換することで、ガタつきを抑えて仕上がりを安定させやすくします。",
            "A nut for rimless frames and small parts. Selecting the right size helps reduce looseness and stabilize the finish.",
            "用于无框架和小部件固定的螺母。按尺寸更换，可减少松动并稳定完成度。",
            "무테 프레임과 작은 부품 고정에 사용하는 너트입니다. 사이즈를 맞춰 교체하면 흔들림을 줄이고 마감을 안정시키기 쉽습니다.",
        ),
        t("ナット固定・交換", "nut fastening and replacement", "螺母固定与更换", "너트 고정 및 교체"),
        t("ガタつきを抑えて仕上がりを安定させやすい", "helps reduce looseness and stabilize the finish", "有助于减少松动并稳定成品", "흔들림을 줄이고 마감을 안정시키기 쉬움"),
    ),
    "washer": template(
        t(
            "ネジまわりや小部品の固定を補助するワッシャです。部品の当たりやガタつきを抑え、フレームの仕上がりを安定させやすくします。",
            "A washer that supports screws and small parts. It helps reduce contact damage and looseness for a more stable frame finish.",
            "辅助螺丝和小部件固定的垫圈。可减少接触损伤和松动，使镜架完成度更稳定。",
            "나사 주변과 작은 부품 고정을 보조하는 와셔입니다. 접촉 손상과 흔들림을 줄여 프레임 마감을 안정시키기 쉽습니다.",
        ),
        t("固定補助", "fastening support", "固定辅助", "고정 보조"),
        t("当たりやガタつきを抑えやすい", "helps reduce contact damage and looseness", "有助于减少接触和松动", "닿는 손상과 흔들림을 줄이기 쉬움"),
    ),
    "nylon_rail": template(
        t(
            "ナイロールや溝まわりの交換・調整に使う部材です。太さや形状を合わせることで、レンズ保持を安定させやすくします。",
            "A material for nylor or groove-related replacement and adjustment. Matching thickness and shape helps stabilize lens holding.",
            "用于半框线槽周边更换和调整的材料。按粗细和形状选择，可稳定镜片固定。",
            "나일론 림과 홈 주변 교체·조정에 쓰는 부재입니다. 굵기와 형태를 맞추면 렌즈 고정을 안정시키기 쉽습니다.",
        ),
        t("ナイロール・溝まわり調整", "nylor and groove adjustment", "半框线槽调整", "나일론 림·홈 주변 조정"),
        t("レンズ保持を安定させやすい", "helps stabilize lens holding", "便于稳定镜片固定", "렌즈 고정을 안정시키기 쉬움"),
    ),
    "nylor_string": template(
        t(
            "ナイロールフレームのレンズ保持に使うテグスです。太さや素材を合わせて交換し、レンズを安定して固定しやすくします。",
            "A cord for holding lenses in nylor frames. Matching thickness and material helps replace the cord and secure lenses steadily.",
            "用于半框眼镜固定镜片的鱼线。按粗细和材质更换，可更稳定地固定镜片。",
            "나일론 림 프레임의 렌즈 고정에 쓰는 줄입니다. 굵기와 소재를 맞춰 교체하면 렌즈를 안정적으로 고정하기 쉽습니다.",
        ),
        t("ナイロール用テグス交換", "nylor cord replacement", "半框鱼线更换", "나일론 림 줄 교체"),
        t("レンズを安定して固定しやすい", "helps secure lenses steadily", "便于稳定固定镜片", "렌즈를 안정적으로 고정하기 쉬움"),
    ),
    "nylor_sheet": template(
        t(
            "ナイロールレンズの着脱に使う専用シートです。テグスとレンズの間に差し込み、傷や糸残りを抑えて作業しやすくします。",
            "A dedicated sheet for removing and installing nylor lenses. It goes between the cord and lens to reduce scratches and loose fibers.",
            "用于半框镜片拆装的专用片材。插入鱼线和镜片之间，可减少划伤和纤维残留。",
            "나일론 림 렌즈 탈착에 쓰는 전용 시트입니다. 줄과 렌즈 사이에 넣어 흠집과 섬유 잔여물을 줄이며 작업하기 쉽습니다.",
        ),
        t("ナイロールレンズ着脱", "nylor lens removal and installation", "半框镜片拆装", "나일론 림 렌즈 탈착"),
        t("傷や糸残りを抑えて着脱しやすい", "helps reduce scratches and fibers during lens work", "拆装时有助于减少划伤和残留", "탈착 시 흠집과 잔여물을 줄이기 쉬움"),
    ),
    "nylor_burner": template(
        t(
            "ナイロールのストッパー玉を作るための電子バーナーです。火を使う作業を抑え、テグス端の処理を安定して行いやすくします。",
            "An electronic burner for forming stopper beads on nylor cord. It helps process cord ends steadily with less open-flame work.",
            "用于制作半框鱼线止挡球的电子加热器。可减少明火作业，使鱼线端处理更稳定。",
            "나일론 림 줄의 스토퍼 구슬을 만드는 전자 버너입니다. 불꽃 작업을 줄이고 줄 끝 처리를 안정적으로 하기 쉽습니다.",
        ),
        t("ナイロール端処理", "nylor cord-end finishing", "半框鱼线端处理", "나일론 림 줄 끝 처리"),
        t("テグス端を安定して処理しやすい", "helps finish cord ends steadily", "便于稳定处理鱼线端部", "줄 끝을 안정적으로 처리하기 쉬움"),
    ),
    "screwdriver": template(
        t(
            "眼鏡修理用のドライバーです。丁番・パッド・リムレス部品などのネジ調整を、店頭作業でスムーズに行いやすくします。",
            "A screwdriver for eyewear repair. It helps handle screws around hinges, pads, and rimless parts smoothly at the counter.",
            "眼镜维修用螺丝刀。便于门店处理铰链、鼻托和无框部件等螺丝调整。",
            "안경 수리용 드라이버입니다. 힌지, 코패드, 무테 부품의 나사 조정을 매장에서 부드럽게 처리하기 쉽습니다.",
        ),
        t("ネジ調整", "screw adjustment", "螺丝调整", "나사 조정"),
        t("日常修理をスムーズにしやすい", "helps make daily repairs smoother", "便于顺利进行日常维修", "일상 수리를 원활하게 하기 쉬움"),
    ),
    "screwdriver_handle": template(
        t(
            "交換式ドライバー先に使う柄・関連部品です。作業内容に合わせて先端を替え、修理工具を無駄なく使いやすくします。",
            "A handle or related part for interchangeable screwdriver tips. It helps switch tips by task and use repair tools efficiently.",
            "用于可更换螺丝刀头的手柄或相关部件。可按作业更换刀头，提高维修工具使用效率。",
            "교체식 드라이버 팁에 쓰는 손잡이와 관련 부품입니다. 작업에 맞게 팁을 바꿔 수리 공구를 효율적으로 쓰기 쉽습니다.",
        ),
        t("交換式ドライバー部品", "interchangeable screwdriver parts", "可更换螺丝刀部件", "교체식 드라이버 부품"),
        t("作業に合わせて先端を替えやすい", "makes it easy to switch tips by task", "便于按作业更换刀头", "작업에 맞춰 팁을 바꾸기 쉬움"),
    ),
    "nut_driver": template(
        t(
            "ツーポイントや六角ナットの締め外しに使うナット廻しです。サイズを合わせて使うことで、小さなナットを確実に扱いやすくします。",
            "A nut driver for tightening or loosening rimless and hex nuts. Matching the size helps handle small nuts securely.",
            "用于拧紧或拆卸无框和六角螺母的套筒工具。按尺寸选择，便于稳定处理小螺母。",
            "무테와 육각 너트를 조이거나 풀 때 쓰는 너트 드라이버입니다. 사이즈를 맞춰 작은 너트를 확실하게 다루기 쉽습니다.",
        ),
        t("ナット締め外し", "nut tightening and removal", "螺母拧紧与拆卸", "너트 조임 및 분리"),
        t("小さなナットを確実に扱いやすい", "helps handle small nuts securely", "便于稳定处理小螺母", "작은 너트를 확실하게 다루기 쉬움"),
    ),
    "screw_remover": template(
        t(
            "固着・折れ込みなどで外しにくいネジを抜くための工具・用品です。通常作業で外れないネジにも対応し、修理を進めやすくします。",
            "A tool or supply for removing stuck or broken screws. It helps continue repairs when screws cannot be removed normally.",
            "用于取出固着或折断等难拆螺丝的工具/用品。普通作业无法拆下时，也便于继续维修。",
            "고착되거나 부러져 빼기 어려운 나사를 제거하는 공구·용품입니다. 일반 작업으로 빠지지 않는 나사도 수리 진행을 돕습니다.",
        ),
        t("固着ネジの除去", "stuck-screw removal", "固着螺丝拆卸", "고착 나사 제거"),
        t("外れにくいネジにも対応しやすい", "helps remove hard-to-remove screws", "便于处理难拆螺丝", "빼기 어려운 나사에도 대응하기 쉬움"),
    ),
    "drill": template(
        t(
            "眼鏡加工時の穴あけや穴調整に使う工具です。穴径や位置を整え、ツーポイントや部品取付の精度を高めやすくします。",
            "A tool for drilling or adjusting holes in eyewear work. It helps refine hole size and position for rimless frames and part installation.",
            "用于眼镜加工中钻孔或修孔的工具。可调整孔径和位置，提高无框和部件安装精度。",
            "안경 가공 시 구멍을 뚫거나 조정하는 공구입니다. 구멍 크기와 위치를 맞춰 무테와 부품 장착 정밀도를 높이기 쉽습니다.",
        ),
        t("穴あけ・穴調整", "hole drilling and adjustment", "钻孔与修孔", "구멍 가공 및 조정"),
        t("穴径や位置を整えやすい", "helps refine hole size and position", "便于调整孔径和位置", "구멍 크기와 위치를 맞추기 쉬움"),
    ),
    "drill_stand": template(
        t(
            "ハンドドリルを安定して保持する穴あけ作業用スタンドです。位置ぶれを抑え、ツーポイントや部品取付の加工を安定させやすくします。",
            "A stand that holds a hand drill steady for drilling work. It helps reduce wobble and stabilize rimless or part-installation processing.",
            "用于稳定固定手钻的钻孔作业支架。可减少位置偏移，使无框和部件安装加工更稳定。",
            "핸드 드릴을 안정적으로 고정하는 구멍 가공용 스탠드입니다. 위치 흔들림을 줄여 무테와 부품 장착 가공을 안정시키기 쉽습니다.",
        ),
        t("穴あけ作業の固定補助", "drilling support and stabilization", "钻孔作业固定辅助", "구멍 가공 고정 보조"),
        t("位置ぶれを抑えて加工しやすい", "helps reduce wobble while drilling", "有助于减少钻孔偏移", "가공 중 흔들림을 줄이기 쉬움"),
    ),
    "frame_heater": template(
        t(
            "フレームを温めて調整・加工しやすくするヒーターです。素材を焦がしにくく、フィッティングや修理作業を安定して進めやすくします。",
            "A heater that warms frames for easier adjustment and processing. It helps avoid scorching and supports stable fitting or repair work.",
            "用于加热镜架、便于调整和加工的加热器。可降低烤焦风险，使验配和维修作业更稳定。",
            "프레임을 데워 조정과 가공을 쉽게 하는 히터입니다. 소재가 타는 위험을 줄여 피팅과 수리 작업을 안정적으로 진행하기 쉽습니다.",
        ),
        t("フレーム加熱・調整", "frame heating and adjustment", "镜架加热与调整", "프레임 가열 및 조정"),
        t("素材を焦がしにくく調整しやすい", "helps adjust frames without scorching", "便于在不易烤焦的情况下调整", "타는 위험을 줄이며 조정하기 쉬움"),
    ),
    "cutting_fluid": template(
        t(
            "穴あけや切削時に使う切削剤です。刃先の滑りを良くして摩擦熱を抑え、素材や工具を傷めにくくします。",
            "A cutting fluid for drilling or cutting work. It improves tool glide, reduces friction heat, and helps protect materials and bits.",
            "用于钻孔和切削作业的切削剂。可提高刀尖滑动性并降低摩擦热，保护材料和刀具。",
            "구멍 가공과 절삭 작업에 쓰는 절삭제입니다. 날끝의 미끄러짐을 좋게 하고 마찰열을 줄여 소재와 공구 손상을 줄입니다.",
        ),
        t("穴あけ・切削補助", "drilling and cutting support", "钻孔与切削辅助", "구멍 가공 및 절삭 보조"),
        t("摩擦熱を抑えて刃先を守りやすい", "helps reduce friction heat and protect bits", "有助于降低摩擦热并保护刀具", "마찰열을 줄여 날끝을 보호하기 쉬움"),
    ),
    "workbench": template(
        t(
            "ネジ締めや加工を安定して行うための作業台です。小さな部品やフレームを扱う店頭作業を、姿勢良く進めやすくします。",
            "A workbench for steady screw tightening and processing. It helps stores handle small parts and frames with better working posture.",
            "用于稳定进行拧螺丝和加工的作业台。便于门店以更稳定的姿势处理小部件和镜架。",
            "나사 조임과 가공을 안정적으로 하기 위한 작업대입니다. 작은 부품과 프레임을 다루는 매장 작업을 바른 자세로 진행하기 쉽습니다.",
        ),
        t("作業台・加工補助", "workbench and processing support", "作业台与加工辅助", "작업대 및 가공 보조"),
        t("小部品作業を安定させやすい", "helps stabilize small-part work", "便于稳定小部件作业", "작은 부품 작업을 안정시키기 쉬움"),
    ),
    "tweezers": template(
        t(
            "精密ネジや小さな部品をつかむためのピンセットです。細かな修理やパッドまわりの作業で、部品を落とさず扱いやすくします。",
            "Tweezers for gripping precision screws and small parts. They help handle parts without dropping them during fine repair or pad-area work.",
            "用于夹取精密螺丝和小部件的镊子。适合细部维修和鼻托周边作业，便于稳定拿取部件。",
            "정밀 나사와 작은 부품을 집는 핀셋입니다. 세밀한 수리와 코패드 주변 작업에서 부품을 떨어뜨리지 않고 다루기 쉽습니다.",
        ),
        t("小部品保持", "small-part handling", "小部件夹持", "작은 부품 집기"),
        t("細かな部品を落とさず扱いやすい", "helps handle tiny parts without dropping them", "便于稳定处理细小部件", "작은 부품을 떨어뜨리지 않고 다루기 쉬움"),
    ),
    "reamer": template(
        t(
            "穴の面取りや微調整に使うリーマーです。ツーポイントやモダン穴などを整え、部品を合わせやすくします。",
            "A reamer for chamfering and fine hole adjustment. It helps prepare rimless and temple-tip holes for better part fitting.",
            "用于孔口倒角和微调的铰刀。可整理无框孔或脚套孔，使部件更易配合。",
            "구멍 면취와 미세 조정에 쓰는 리머입니다. 무테와 모던 구멍을 정돈해 부품을 맞추기 쉽습니다.",
        ),
        t("穴の面取り・微調整", "hole chamfering and fine adjustment", "孔口倒角与微调", "구멍 면취 및 미세 조정"),
        t("部品を合わせやすい穴に整えられる", "helps prepare holes for part fitting", "可把孔整理到便于装配", "부품에 맞는 구멍으로 정돈하기 쉬움"),
    ),
    "file_grinding": template(
        t(
            "フレームや部品の削り・仕上げに使うヤスリ類です。細かな形状調整や面取りを行い、修理後の仕上がりを整えやすくします。",
            "A file or grinding tool for frames and parts. It supports fine shaping and chamfering to improve the repair finish.",
            "用于镜架和部件削磨、收尾的锉刀类工具。可进行细部修形和倒角，使维修后效果更整洁。",
            "프레임과 부품을 깎고 마감하는 줄·연마 공구입니다. 세부 형상 조정과 면취로 수리 후 마감을 정돈하기 쉽습니다.",
        ),
        t("削り・仕上げ加工", "filing and finishing", "削磨与收尾加工", "절삭 및 마감 가공"),
        t("細かな形状調整と面取りをしやすい", "helps with fine shaping and chamfering", "便于细部修形和倒角", "세밀한 형상 조정과 면취가 쉬움"),
    ),
    "polish": template(
        t(
            "フレームやパーツの研磨・艶出しに使う用品です。細かなキズやくすみを整え、きれいな仕上がりに近づけます。",
            "A polishing supply for frames and parts. It helps reduce small scratches and dullness for a cleaner finish.",
            "用于镜架和部件研磨、抛光的用品。可处理细小划痕和暗淡，使完成效果更干净。",
            "프레임과 부품의 연마·광택 작업에 쓰는 용품입니다. 작은 흠집과 칙칙함을 정돈해 깔끔한 마감에 가깝게 합니다.",
        ),
        t("研磨・艶出し", "polishing and gloss finishing", "研磨与抛光", "연마 및 광택 마감"),
        t("キズやくすみを整えやすい", "helps reduce scratches and dullness", "有助于处理划痕和暗淡", "흠집과 칙칙함을 정돈하기 쉬움"),
    ),
    "cleaner": template(
        t(
            "眼鏡や作業まわりの清掃に使う商品です。汚れを落として見た目を整え、お渡し前の最終仕上げにも使いやすい商品です。",
            "A product for cleaning eyewear or the work area. It helps remove dirt and present glasses neatly before handover.",
            "用于清洁眼镜或作业区域的商品。可去除污渍，让交付前的外观更整洁。",
            "안경이나 작업 주변 청소에 사용하는 상품입니다. 오염을 제거해 고객 전달 전 외관을 깔끔하게 정돈하기 쉽습니다.",
        ),
        t("清掃・仕上げ", "cleaning and final finishing", "清洁与最终整理", "청소 및 최종 마감"),
        t("お渡し前の見た目を整えやすい", "helps present glasses neatly before handover", "便于交付前整理外观", "전달 전 외관을 정돈하기 쉬움"),
    ),
    "tape": template(
        t(
            "レンズやフレームを保護しながら作業するためのテープです。加工・調整時のキズや汚れを防ぎ、作業品質を安定させやすくします。",
            "A tape for protecting lenses or frames during work. It helps prevent scratches and dirt during processing or adjustment.",
            "用于作业时保护镜片或镜架的胶带。可防止加工和调整时产生划伤或污渍。",
            "작업 중 렌즈와 프레임을 보호하는 테이프입니다. 가공·조정 중 흠집과 오염을 막아 작업 품질을 안정시키기 쉽습니다.",
        ),
        t("作業時の保護", "work protection", "作业保护", "작업 중 보호"),
        t("キズや汚れを防ぎやすい", "helps prevent scratches and dirt", "有助于防止划伤和污渍", "흠집과 오염을 막기 쉬움"),
    ),
    "adhesive": template(
        t(
            "眼鏡部品の接着やネジゆるみ止めに使う液剤です。用途に合わせて使うことで、補修後の固定を安定させやすくします。",
            "A liquid for bonding eyewear parts or preventing screw loosening. Using the right type helps stabilize repaired areas.",
            "用于眼镜部件粘接或螺丝防松的液剂。按用途使用，可使修理后的固定更稳定。",
            "안경 부품 접착이나 나사 풀림 방지에 쓰는 액제입니다. 용도에 맞게 사용하면 보수 후 고정을 안정시키기 쉽습니다.",
        ),
        t("接着・ゆるみ止め", "bonding and thread locking", "粘接与防松", "접착 및 풀림 방지"),
        t("補修後の固定を安定させやすい", "helps stabilize repaired areas", "便于稳定修理后的固定", "보수 후 고정을 안정시키기 쉬움"),
    ),
    "soldering": template(
        t(
            "ロウ付けや加熱補修に使う工具・材料です。メタルフレームや小部品の修理で、必要な箇所を固定・補修しやすくします。",
            "A tool or material for soldering and heat repair. It helps fix or repair metal frames and small parts at the needed point.",
            "用于焊接和加热修理的工具或材料。便于在金属镜架和小部件维修中固定、修补需要部位。",
            "납땜과 가열 보수에 쓰는 공구·재료입니다. 메탈 프레임과 작은 부품 수리에서 필요한 부위를 고정·보수하기 쉽습니다.",
        ),
        t("ロウ付け・加熱補修", "soldering and heat repair", "焊接与加热修理", "납땜 및 가열 보수"),
        t("必要箇所を固定・補修しやすい", "helps repair or fix the needed point", "便于固定或修补所需部位", "필요한 부위를 고정·보수하기 쉬움"),
    ),
    "pliers_generic": template(
        t(
            "眼鏡フレームの調整や小部品の保持に使うヤットコです。先端形状に合わせて使い分け、狙った部分を安定してつかめます。",
            "Pliers for adjusting eyewear frames or holding small parts. Different tip shapes help grip the target area steadily.",
            "用于眼镜架调整和小部件夹持的钳子。可按前端形状区分使用，稳定夹住目标部位。",
            "안경 프레임 조정과 작은 부품 고정에 사용하는 플라이어입니다. 팁 형태에 맞춰 사용하면 원하는 부분을 안정적으로 잡기 쉽습니다.",
        ),
        t("フレーム調整・部品保持", "frame adjustment and part holding", "镜架调整与部件夹持", "프레임 조정 및 부품 고정"),
        t("狙った部分を安定してつかみやすい", "helps grip the target area steadily", "便于稳定夹住目标部位", "원하는 부분을 안정적으로 잡기 쉬움"),
    ),
    "pliers_klings_adjustment": template(
        t(
            "クリングスの微調整に使うヤットコです。小さなパット足を正確につかみ、鼻パッド位置を細かく整えやすくします。",
            "Pliers for fine klings pad-arm adjustment. They help grip small pad arms accurately and refine nose-pad position.",
            "用于鼻托臂微调的钳子。可准确夹住小型鼻托臂，细致调整鼻托位置。",
            "클링스 코패드 암 미세 조정용 플라이어입니다. 작은 패드 암을 정확히 잡아 코패드 위치를 세밀하게 맞추기 쉽습니다.",
        ),
        t("クリングス微調整", "fine klings adjustment", "鼻托臂微调", "클링스 미세 조정"),
        t("小さなパット足を正確につかみやすい", "helps grip small pad arms accurately", "便于准确夹住小型鼻托臂", "작은 패드 암을 정확히 잡기 쉬움"),
    ),
    "pliers_pad_adjustment": template(
        t(
            "鼻パッドまわりの角度調整に使うヤットコです。箱蝶や取付金具を安定してつかみ、フィッティング時の細かな調整をしやすくします。",
            "Pliers for adjusting the angle around nose pads. They hold pad boxes or mounting hardware steadily for fine fitting work.",
            "用于鼻托周边角度调整的钳子。可稳定夹持鼻托盒或安装金具，便于验配时微调。",
            "코패드 주변 각도 조정에 쓰는 플라이어입니다. 박스나 장착 금구를 안정적으로 잡아 피팅 시 세밀한 조정이 쉽습니다.",
        ),
        t("鼻パッド角度調整", "nose-pad angle adjustment", "鼻托角度调整", "코패드 각도 조정"),
        t("取付金具を安定してつかみやすい", "helps hold mounting hardware steadily", "便于稳定夹持安装金具", "장착 금구를 안정적으로 잡기 쉬움"),
    ),
    "pliers_temple_opening": template(
        t(
            "テンプル開きの調整に使うヤットコです。左右の開き具合を整え、掛け心地とフレームの安定感を合わせやすくします。",
            "Pliers for temple opening adjustment. They help balance left and right temple spread and stabilize the frame fit.",
            "用于调整镜腿开合的钳子。可平衡左右开度，帮助稳定佩戴感和镜架状态。",
            "템플 벌어짐 조정용 플라이어입니다. 좌우 벌어짐을 맞춰 착용감과 프레임 안정감을 조정하기 쉽습니다.",
        ),
        t("テンプル開き調整", "temple opening adjustment", "镜腿开合调整", "템플 벌어짐 조정"),
        t("左右の開きと掛け心地を整えやすい", "helps balance temple spread and fit", "便于平衡左右开度和佩戴感", "좌우 벌어짐과 착용감을 맞추기 쉬움"),
    ),
    "pliers_temple_angle": template(
        t(
            "テンプル角度や前傾角の調整に使うヤットコです。掛け位置や視線のバランスを見ながら、フィッティングを細かく整えられます。",
            "Pliers for temple angle or pantoscopic tilt adjustment. They help refine fit position and visual balance during fitting.",
            "用于调整镜腿角度和前倾角的钳子。可结合佩戴位置和视线平衡进行细致验配。",
            "템플 각도와 전경각 조정용 플라이어입니다. 착용 위치와 시선 균형을 보며 피팅을 세밀하게 맞추기 쉽습니다.",
        ),
        t("テンプル角度・前傾角調整", "temple angle and pantoscopic tilt adjustment", "镜腿角度/前倾角调整", "템플 각도·전경각 조정"),
        t("掛け位置と視線バランスを整えやすい", "helps refine fit position and visual balance", "便于调整佩戴位置和视线平衡", "착용 위치와 시선 균형을 맞추기 쉬움"),
    ),
    "pliers_bridge_angle": template(
        t(
            "ブリッジ角度やフロントバランスの調整に使うヤットコです。左右レンズ位置や前面の傾きを整え、掛け心地を合わせやすくします。",
            "Pliers for bridge angle and front balance adjustment. They help align lens position and front tilt for a better fit.",
            "用于调整鼻梁角度和前框平衡的钳子。可整理左右镜片位置和前框倾斜，改善佩戴感。",
            "브리지 각도와 프런트 밸런스 조정용 플라이어입니다. 좌우 렌즈 위치와 전면 기울기를 맞춰 착용감을 조정하기 쉽습니다.",
        ),
        t("ブリッジ角度調整", "bridge angle adjustment", "鼻梁角度调整", "브리지 각도 조정"),
        t("前面バランスを整えやすい", "helps align front balance", "便于整理前框平衡", "전면 밸런스를 맞추기 쉬움"),
    ),
    "pliers_modern_bending": template(
        t(
            "モダン曲げや先セル調整に使うヤットコです。手では曲げにくい部分へ力をかけ、耳まわりのフィットを整えやすくします。",
            "Pliers for bending temple tips. They help apply force to areas that are hard to bend by hand and refine comfort around the ears.",
            "用于弯曲脚套和调整镜腿末端的钳子。可对手难以弯曲的部位施力，改善耳周贴合。",
            "모던 굽힘과 팁 조정에 쓰는 플라이어입니다. 손으로 굽히기 어려운 부위에 힘을 전달해 귀 주변 피팅을 맞추기 쉽습니다.",
        ),
        t("モダン曲げ調整", "temple-tip bending", "脚套弯曲调整", "모던 굽힘 조정"),
        t("耳まわりのフィットを整えやすい", "helps refine fit around the ears", "便于改善耳周贴合", "귀 주변 피팅을 맞추기 쉬움"),
    ),
    "pliers_rim_shape": template(
        t(
            "リム形状やナイロールまわりの調整に使うヤットコです。レンズ保持部の形を整え、レンズ合わせを安定させやすくします。",
            "Pliers for rim shape and nylor-area adjustment. They help refine the lens-holding area for a more stable lens fit.",
            "用于调整镜圈形状和半框线槽周边的钳子。可整理镜片固定部位，提高配片稳定性。",
            "림 형상과 나일론 림 주변 조정용 플라이어입니다. 렌즈 고정 부위를 정돈해 렌즈 맞춤을 안정시키기 쉽습니다.",
        ),
        t("リム形状調整", "rim-shape adjustment", "镜圈形状调整", "림 형상 조정"),
        t("レンズ合わせを安定させやすい", "helps stabilize lens fitting", "有助于稳定配片", "렌즈 맞춤을 안정시키기 쉬움"),
    ),
    "pliers_rimless_screw_cutter": template(
        t(
            "ツーポイント用ネジの長さ調整に使うヤットコです。必要な長さに切りそろえ、ネジ先を処理しやすくします。",
            "Pliers for trimming rimless-frame screws. They help cut screws to the needed length and finish the screw end.",
            "用于调整无框螺丝长度的钳子。可按需要裁切长度，并便于处理螺丝端部。",
            "무테용 나사 길이 조정 플라이어입니다. 필요한 길이로 자르고 나사 끝을 처리하기 쉽습니다.",
        ),
        t("ツーポネジ長さ調整", "rimless screw length adjustment", "无框螺丝长度调整", "무테 나사 길이 조정"),
        t("必要な長さに切りそろえやすい", "helps trim screws to the needed length", "便于裁切到所需长度", "필요한 길이로 자르기 쉬움"),
    ),
    "pliers_cutting": template(
        t(
            "テンプル・ネジ・小部品のカットに使うニッパー類です。狙った位置を切りやすく、修理や加工の仕上げを進めやすくします。",
            "Cutters or nippers for temples, screws, and small parts. They help cut at the target point and support repair or finishing work.",
            "用于剪切镜腿、螺丝和小部件的剪钳类工具。便于在目标位置切断，推进维修和加工收尾。",
            "템플, 나사, 작은 부품 절단에 쓰는 니퍼류입니다. 원하는 위치를 자르기 쉬워 수리와 가공 마감을 돕습니다.",
        ),
        t("カット加工", "cutting work", "剪切加工", "절단 가공"),
        t("狙った位置を切りやすい", "helps cut at the target point", "便于在目标位置切断", "원하는 위치를 자르기 쉬움"),
    ),
    "pliers_replacement_tip": template(
        t(
            "ヤットコ先端の交換・保護に使う部品です。接触面を整え、フレームや部品へのキズを抑えながら調整しやすくします。",
            "A replacement or protective part for plier tips. It helps keep the contact surface suitable and reduce scratches during adjustment.",
            "用于钳子前端更换或保护的部件。可整理接触面，减少调整时对镜架和部件的划伤。",
            "플라이어 팁 교체·보호용 부품입니다. 접촉면을 정돈해 조정 중 프레임과 부품의 흠집을 줄이기 쉽습니다.",
        ),
        t("ヤットコ先端交換・保護", "plier-tip replacement and protection", "钳尖更换与保护", "플라이어 팁 교체 및 보호"),
        t("調整時のキズを抑えやすい", "helps reduce scratches during adjustment", "有助于减少调整时划伤", "조정 중 흠집을 줄이기 쉬움"),
    ),
    "pliers_protective_cover": template(
        t(
            "ヤットコや工具の接触面を保護する用品です。滑り止めやキズ防止を追加し、フレーム調整をより安定して行いやすくします。",
            "A supply for protecting the contact surface of pliers or tools. It adds grip or scratch protection for more stable frame adjustment.",
            "用于保护钳子或工具接触面的用品。可增加防滑和防划保护，使镜架调整更稳定。",
            "플라이어와 공구의 접촉면을 보호하는 용품입니다. 미끄럼 방지와 흠집 방지를 더해 프레임 조정을 안정적으로 하기 쉽습니다.",
        ),
        t("工具接触面の保護", "tool contact-surface protection", "工具接触面保护", "공구 접촉면 보호"),
        t("滑り止めやキズ防止を追加しやすい", "adds grip and scratch protection", "便于增加防滑和防划保护", "미끄럼 방지와 흠집 방지를 더하기 쉬움"),
    ),
    "pliers_lens_size_check": template(
        t(
            "レンズサイズ確認に使うヤットコです。歪度計使用時にリム止めネジの代わりに挟み、レンズ合わせと検品を効率化しやすくします。",
            "Pliers for checking lens size. They clamp in place of a rim screw when using a lensmeter or strain tester, helping lens fitting and inspection.",
            "用于确认镜片尺寸的钳子。使用应力仪等时可代替镜圈固定螺丝夹持，提高配片和检查效率。",
            "렌즈 사이즈 확인용 플라이어입니다. 왜곡계 사용 시 림 고정 나사 대신 끼워 렌즈 맞춤과 검품을 효율화하기 쉽습니다.",
        ),
        t("レンズサイズ確認", "lens size checking", "镜片尺寸确认", "렌즈 사이즈 확인"),
        t("レンズ合わせと検品を効率化しやすい", "helps make lens fitting and inspection efficient", "有助于提高配片和检查效率", "렌즈 맞춤과 검품을 효율화하기 쉬움"),
    ),
    "pliers_pad_remover": template(
        t(
            "ワンタッチパッドの取り外しや関連作業に使うヤットコです。細かなパッド部品を扱いやすく、交換作業を進めやすくします。",
            "Pliers for removing one-touch pads and related work. They help handle small pad parts and make replacement work smoother.",
            "用于拆卸一触式鼻托及相关作业的钳子。便于处理细小鼻托部件，推进更换作业。",
            "원터치 패드 분리와 관련 작업에 쓰는 플라이어입니다. 작은 패드 부품을 다루기 쉬워 교체 작업을 원활하게 합니다.",
        ),
        t("パッド取り外し・交換", "pad removal and replacement", "鼻托拆卸与更换", "패드 분리 및 교체"),
        t("細かなパッド部品を扱いやすい", "helps handle small pad parts", "便于处理细小鼻托部件", "작은 패드 부품을 다루기 쉬움"),
    ),
    "pliers_screw_grip": template(
        t(
            "ネジつかみや丁番まわりの補修に使うヤットコです。小さなネジやコマを安定して保持し、修理作業を進めやすくします。",
            "Pliers for gripping screws and repairing hinge areas. They help hold tiny screws or hinge pieces steadily during repair.",
            "用于夹持螺丝和修理铰链周边的钳子。可稳定保持小螺丝或铰链块，便于维修。",
            "나사 잡기와 힌지 주변 보수에 쓰는 플라이어입니다. 작은 나사나 힌지 부품을 안정적으로 잡아 수리를 진행하기 쉽습니다.",
        ),
        t("ネジつかみ・丁番補修", "screw gripping and hinge repair", "螺丝夹持与铰链修理", "나사 잡기 및 힌지 보수"),
        t("小さなネジを安定して保持しやすい", "helps hold tiny screws steadily", "便于稳定夹持小螺丝", "작은 나사를 안정적으로 잡기 쉬움"),
    ),
    "pliers_joint_hold": template(
        t(
            "智や丁番まわりを固定して調整を支えるヤットコです。テンプル調整時にフレームを安定させ、狙った角度に合わせやすくします。",
            "Pliers that hold the lug or hinge area during adjustment. They stabilize the frame when adjusting temples and angles.",
            "用于固定桩头或铰链周边以辅助调整的钳子。调整镜腿时可稳定镜架，更容易对准目标角度。",
            "엔드피스나 힌지 주변을 고정해 조정을 돕는 플라이어입니다. 템플 조정 시 프레임을 안정시켜 원하는 각도에 맞추기 쉽습니다.",
        ),
        t("智固定・調整補助", "lug holding and adjustment support", "桩头固定与调整辅助", "엔드피스 고정 및 조정 보조"),
        t("フレームを安定させて角度調整しやすい", "stabilizes the frame for angle adjustment", "稳定镜架，便于角度调整", "프레임을 안정시켜 각도 조정이 쉬움"),
    ),
    "toolset": template(
        t(
            "眼鏡店の作業に必要な工具や部品をまとめたセットです。新店準備、スタッフ教育、工具入れ替え時に導入しやすい構成です。",
            "A set of tools or parts needed for eyewear work. It is useful for new-store setup, staff training, or tool replacement.",
            "汇集眼镜店作业所需工具或部件的套装。适合新店准备、员工培训或工具更新时导入。",
            "안경 작업에 필요한 공구나 부품을 모은 세트입니다. 신규 매장 준비, 직원 교육, 공구 교체 시 도입하기 쉽습니다.",
        ),
        t("工具・部品の一括準備", "tool and part setup", "工具/部件集中准备", "공구·부품 일괄 준비"),
        t("必要なものをまとめて揃えやすい", "helps prepare essentials at once", "便于一次性准备所需物品", "필요한 것을 한 번에 갖추기 쉬움"),
    ),
    "tool_storage": template(
        t(
            "工具を見やすく整理して置くためのスタンド・収納用品です。作業台まわりを整え、必要な工具を取り出しやすくします。",
            "A stand or storage item for organizing tools visibly. It keeps the workbench tidy and makes tools easier to pick up.",
            "用于清楚整理工具的支架或收纳用品。可整理工作台周边，便于取用需要的工具。",
            "공구를 보기 좋게 정리해 두는 스탠드·수납용품입니다. 작업대 주변을 정돈하고 필요한 공구를 꺼내기 쉽게 합니다.",
        ),
        t("工具整理・収納", "tool organization and storage", "工具整理与收纳", "공구 정리 및 수납"),
        t("必要な工具を取り出しやすい", "makes needed tools easier to access", "便于取用所需工具", "필요한 공구를 꺼내기 쉬움"),
    ),
    "measuring_device": template(
        t(
            "眼鏡店の検査・測定に使う器具です。フレームやレンズの状態を数値や目視で確認し、接客や加工判断をしやすくします。",
            "An instrument for inspection or measurement in optical shops. It helps check frames or lenses visually or by numbers for service and processing decisions.",
            "眼镜店检查和测量用器具。可通过数值或目视确认镜架、镜片状态，便于顾客接待和加工判断。",
            "안경점의 검사·측정에 사용하는 기기입니다. 프레임과 렌즈 상태를 수치나 눈으로 확인해 상담과 가공 판단을 돕습니다.",
        ),
        t("検査・測定", "inspection and measurement", "检查与测量", "검사 및 측정"),
        t("状態確認と加工判断をしやすい", "helps with condition checks and processing decisions", "便于状态确认和加工判断", "상태 확인과 가공 판단이 쉬움"),
    ),
    "test_lens": template(
        t(
            "検眼時に試験枠へ入れて使うテストレンズです。必要な度数や種類を選び、見え方の確認を行いやすくします。",
            "A trial lens used in a trial frame during refraction. It helps check vision by selecting the needed power or type.",
            "验光时放入试镜架使用的测试镜片。可按需要选择度数和类型，便于确认视力效果。",
            "검안 시 시험테에 넣어 사용하는 테스트 렌즈입니다. 필요한 도수와 종류를 선택해 보이는 상태를 확인하기 쉽습니다.",
        ),
        t("検眼・見え方確認", "refraction and vision checking", "验光与视力确认", "검안 및 시야 확인"),
        t("必要な度数を選んで確認しやすい", "helps check vision with the needed power", "便于选择所需度数进行确认", "필요한 도수를 골라 확인하기 쉬움"),
    ),
    "trial_frame": template(
        t(
            "検眼でテストレンズを装用するための試験枠です。PDや装用位置を合わせながら、見え方を確認しやすくします。",
            "A trial frame for wearing trial lenses during refraction. It helps check vision while adjusting PD and wearing position.",
            "验光时佩戴测试镜片用的试镜架。可调整PD和佩戴位置，便于确认视力效果。",
            "검안에서 테스트 렌즈를 착용하기 위한 시험테입니다. PD와 착용 위치를 맞추며 보이는 상태를 확인하기 쉽습니다.",
        ),
        t("試験枠での検眼", "trial-frame refraction", "试镜架验光", "시험테 검안"),
        t("装用位置を合わせて確認しやすい", "helps check vision with adjusted wearing position", "便于调整佩戴位置后确认", "착용 위치를 맞춰 확인하기 쉬움"),
    ),
    "magnifier": template(
        t(
            "細かな文字や部品を拡大して確認するためのルーペです。検品・修理・読書などで細部を見やすくします。",
            "A magnifier for viewing small text or parts. It makes details easier to see for inspection, repair, or reading.",
            "用于放大查看细小文字或部件的放大镜。适合检查、维修和阅读时看清细节。",
            "작은 글자나 부품을 확대해 확인하는 확대경입니다. 검품, 수리, 독서 등에서 세부를 보기 쉽게 합니다.",
        ),
        t("拡大確認", "magnified viewing", "放大确认", "확대 확인"),
        t("細部を見やすくする", "makes details easier to see", "让细节更容易看清", "세부를 보기 쉽게 함"),
    ),
    "checker": template(
        t(
            "レンズや表示内容の確認に使うチェッカー・ライト類です。性能説明や店頭デモで、お客様に状態を見せやすくします。",
            "A checker or light for confirming lens or display conditions. It helps show the condition to customers during demonstrations.",
            "用于确认镜片或显示内容的检测器/灯具。便于在门店演示中向顾客展示状态。",
            "렌즈나 표시 상태를 확인하는 체커·라이트류입니다. 매장 데모에서 고객에게 상태를 보여주기 쉽습니다.",
        ),
        t("レンズ・状態確認", "lens and condition checking", "镜片/状态确认", "렌즈·상태 확인"),
        t("店頭デモで説明しやすい", "easy to use in customer demonstrations", "便于门店演示说明", "매장 데모에서 설명하기 쉬움"),
    ),
    "reading_glasses": template(
        t(
            "手元の文字や細かな作業を見やすくする近用関連商品です。度数や用途に合わせて、店頭で提案しやすい商品です。",
            "A near-vision product for reading or close work. It is easy to recommend in store by power or use case.",
            "用于看清近距离文字或细小作业的近用相关商品。可按度数和用途在门店推荐。",
            "손에 가까운 글자나 세밀한 작업을 보기 쉽게 하는 근거리용 관련 상품입니다. 도수와 용도에 맞춰 매장에서 제안하기 쉽습니다.",
        ),
        t("近用・手元作業", "near vision and close work", "近用与手边作业", "근거리 시야 및 손작업"),
        t("度数や用途に合わせて提案しやすい", "easy to recommend by power or use", "便于按度数和用途推荐", "도수와 용도에 맞춰 제안하기 쉬움"),
    ),
    "clip_on": template(
        t(
            "普段のメガネに取り付けて使うクリップオングラスです。必要な時だけ装着でき、日差しやまぶしさ対策に使いやすい商品です。",
            "Clip-on glasses that attach to regular eyewear. They can be used only when needed for sunlight or glare control.",
            "可安装在常用眼镜上的夹片眼镜。需要时再装上，适合遮阳和防眩使用。",
            "평소 안경에 장착해 사용하는 클립온 글라스입니다. 필요할 때만 붙여 햇빛이나 눈부심 대책으로 쓰기 좋습니다.",
        ),
        t("まぶしさ対策", "glare control", "防眩光", "눈부심 대책"),
        t("必要な時だけ装着しやすい", "easy to attach only when needed", "需要时即可装卸", "필요할 때만 장착하기 쉬움"),
    ),
    "sunglasses": template(
        t(
            "日差しやまぶしさを抑えるサングラスです。屋外用や店頭販売用として、用途や濃度を説明しやすい商品です。",
            "Sunglasses for reducing sunlight and glare. They are easy to explain by outdoor use, lens color, or density.",
            "用于减少阳光和眩光的太阳镜。适合户外和门店销售，可按用途和颜色浓度说明。",
            "햇빛과 눈부심을 줄이는 선글라스입니다. 야외용이나 매장 판매용으로 용도와 농도를 설명하기 쉽습니다.",
        ),
        t("日差し・まぶしさ対策", "sunlight and glare control", "遮阳与防眩", "햇빛·눈부심 대책"),
        t("用途や濃度を説明しやすい", "easy to explain by use or tint density", "便于按用途和浓度说明", "용도와 농도를 설명하기 쉬움"),
    ),
    "sports_band": template(
        t(
            "スポーツ時や動きの多い場面でメガネを固定するバンドです。ズレ落ちを防ぎやすく、店頭販売にも説明しやすい商品です。",
            "A band for keeping glasses in place during sports or active use. It helps prevent slipping and is easy to explain as an add-on item.",
            "用于运动或活动场景固定眼镜的绑带。可帮助防止滑落，作为门店配件也容易说明。",
            "운동이나 활동이 많은 상황에서 안경을 고정하는 밴드입니다. 흘러내림을 줄여 매장 판매용으로도 설명하기 쉽습니다.",
        ),
        t("眼鏡固定", "eyewear retention", "眼镜固定", "안경 고정"),
        t("動いてもズレ落ちを防ぎやすい", "helps prevent slipping during movement", "活动时有助于防止滑落", "움직일 때 흘러내림을 줄이기 쉬움"),
    ),
    "anti_slip_retainer": template(
        t(
            "テンプルや耳まわりに装着してメガネのズレ落ちを防ぐ補助パーツです。日常使いの掛け心地を安定させたいお客様に提案しやすい商品です。",
            "An anti-slip aid attached around the temples or ears. It helps stabilize everyday fit and is easy to recommend to customers whose glasses slip.",
            "安装在镜腿或耳周位置的防滑辅助配件。可稳定日常佩戴，适合向眼镜容易下滑的顾客推荐。",
            "템플이나 귀 주변에 장착해 안경 흘러내림을 줄이는 보조 부품입니다. 일상 착용감을 안정시키고 싶은 고객에게 제안하기 쉽습니다.",
        ),
        t("ズレ落ち防止", "anti-slip fit support", "防滑佩戴辅助", "흘러내림 방지"),
        t("日常の掛け心地を安定させやすい", "helps stabilize everyday fit", "有助于稳定日常佩戴", "일상 착용감을 안정시키기 쉬움"),
    ),
    "children_frame": template(
        t(
            "幼児・子ども向けフレームや専用交換部品です。サイズや色を合わせて選び、動きの多いお子様にも安定した掛け心地を提案しやすくします。",
            "A children's frame or dedicated replacement part. Matching size and color helps recommend a stable fit for active children.",
            "幼儿/儿童用镜架或专用更换部件。可按尺寸和颜色选择，便于向活动量大的儿童推荐稳定佩戴。",
            "유아·어린이용 프레임 또는 전용 교체 부품입니다. 사이즈와 색상을 맞춰 활동이 많은 어린이에게 안정적인 착용감을 제안하기 쉽습니다.",
        ),
        t("子ども用フレーム・部品", "children's frames and parts", "儿童镜架与部件", "어린이용 프레임·부품"),
        t("サイズや色を合わせて提案しやすい", "easy to recommend by size and color", "便于按尺寸和颜色推荐", "사이즈와 색상에 맞춰 제안하기 쉬움"),
    ),
    "pc_glasses": template(
        t(
            "度なしのPC作業向けグラスです。画面作業や室内用として、色や用途を説明しながら店頭販売しやすい商品です。",
            "Non-prescription glasses for PC work. They are easy to sell in store by explaining color and screen-use needs.",
            "无度数PC作业用眼镜。适合屏幕作业和室内使用，可按颜色和用途向顾客说明。",
            "도수 없는 PC 작업용 안경입니다. 화면 작업이나 실내용으로 색상과 용도를 설명하며 매장 판매하기 쉽습니다.",
        ),
        t("PC作業・室内用", "PC work and indoor use", "PC作业与室内使用", "PC 작업 및 실내용"),
        t("色や用途を説明して提案しやすい", "easy to explain by color and use", "便于按颜色和用途说明", "색상과 용도를 설명해 제안하기 쉬움"),
    ),
    "temple_cable": template(
        t(
            "テンプルをケーブル・巻きつるタイプにするための部材です。耳まわりの保持を高めたい用途に合わせて、交換や提案がしやすい商品です。",
            "A part for converting temples to cable-style ends. It helps support replacement or proposals when stronger ear-area retention is needed.",
            "用于将镜腿改为卷曲/线缆式末端的部件。需要增强耳周固定时，便于更换或推荐。",
            "템플을 케이블·말림 다리 타입으로 만드는 부재입니다. 귀 주변 고정을 높이고 싶을 때 교체와 제안이 쉽습니다.",
        ),
        t("ケーブルテンプル化", "cable-temple conversion", "卷曲镜腿改装", "케이블 템플 전환"),
        t("耳まわりの保持を高めやすい", "helps improve ear-area retention", "有助于增强耳周固定", "귀 주변 고정을 높이기 쉬움"),
    ),
    "parts_set": template(
        t(
            "交換・補修用パーツをまとめたセットです。よく使う部品を一括で備えられ、急な修理や店頭対応を進めやすくします。",
            "A set of replacement and repair parts. Keeping common parts together helps stores handle urgent repairs and counter work.",
            "更换和维修部件套装。可集中准备常用部件，便于应对临时维修和门店服务。",
            "교체·보수용 부품을 모은 세트입니다. 자주 쓰는 부품을 한 번에 준비해 갑작스러운 수리와 매장 대응을 진행하기 쉽습니다.",
        ),
        t("交換部品の一括準備", "replacement-part setup", "更换部件集中准备", "교체 부품 일괄 준비"),
        t("急な修理に備えやすい", "helps prepare for urgent repairs", "便于准备临时维修", "갑작스러운 수리에 대비하기 쉬움"),
    ),
    "glass_code_chain": template(
        t(
            "メガネを首から下げて携帯するためのコード・チェーンです。外した時の置き忘れや落下を防ぎやすくします。",
            "A cord or chain for wearing glasses around the neck. It helps prevent misplacement or drops when glasses are removed.",
            "用于将眼镜挂在颈部携带的眼镜绳/链。摘下时有助于防止遗忘或掉落。",
            "안경을 목에 걸어 휴대하는 코드·체인입니다. 벗었을 때 두고 가거나 떨어뜨리는 것을 줄이기 쉽습니다.",
        ),
        t("携帯・落下防止", "carrying and drop prevention", "携带与防掉落", "휴대 및 낙하 방지"),
        t("置き忘れや落下を防ぎやすい", "helps prevent misplacement and drops", "有助于防止遗忘和掉落", "두고 가거나 떨어뜨리는 일을 줄이기 쉬움"),
    ),
    "case": template(
        t(
            "眼鏡や小物の収納・保護に使うケース関連商品です。持ち帰り、保管、ディスプレイ時にも扱いやすい商品です。",
            "A case-related product for storing and protecting eyewear or small items. It is useful for carryout, storage, or display.",
            "用于收纳和保护眼镜或小物的盒类商品。适合携带、保管和陈列使用。",
            "안경이나 작은 물품의 수납·보호에 쓰는 케이스 관련 상품입니다. 휴대, 보관, 진열 시 다루기 쉽습니다.",
        ),
        t("収納・保護", "storage and protection", "收纳与保护", "수납 및 보호"),
        t("持ち帰りや保管に使いやすい", "useful for carryout and storage", "便于携带和保管", "휴대와 보관에 쓰기 쉬움"),
    ),
    "pop_display": template(
        t(
            "店頭での商品展示や販売促進に使う用品です。商品やサービスを見やすく示し、接客時の提案をしやすくします。",
            "A display or promotion item for the store. It helps present products or services clearly and supports customer proposals.",
            "用于门店展示和促销的用品。可清楚展示商品或服务，便于向顾客推荐。",
            "매장 상품 진열과 판매 촉진에 쓰는 용품입니다. 상품과 서비스를 보기 좋게 보여 상담 제안을 돕습니다.",
        ),
        t("展示・販売促進", "display and promotion", "展示与促销", "진열 및 판매 촉진"),
        t("商品やサービスを見せやすい", "helps present products or services clearly", "便于展示商品或服务", "상품과 서비스를 보여주기 쉬움"),
    ),
    "book_training": template(
        t(
            "眼鏡の知識や技術を学ぶための書籍・教材です。スタッフ教育や接客前の確認に使いやすい商品です。",
            "A book or training material for eyewear knowledge and techniques. It is useful for staff education or pre-service review.",
            "用于学习眼镜知识和技术的书籍/教材。适合员工培训或顾客接待前复习使用。",
            "안경 지식과 기술을 배우기 위한 서적·교재입니다. 직원 교육이나 상담 전 확인용으로 쓰기 좋습니다.",
        ),
        t("教育・技術確認", "training and technical review", "培训与技术确认", "교육 및 기술 확인"),
        t("スタッフ教育に使いやすい", "useful for staff training", "适合员工培训", "직원 교육에 쓰기 좋음"),
    ),
    "aftercare_kit": template(
        t(
            "メガネの簡易メンテナンスを案内しやすいアフターケア用品です。店頭でのお渡しや販売時に、日常のネジ確認やお手入れを提案しやすくします。",
            "An aftercare item for simple eyewear maintenance. It helps stores suggest daily screw checks and care when handing over or selling glasses.",
            "便于说明眼镜简易维护的售后护理用品。门店交付或销售时，可建议顾客进行日常螺丝检查和保养。",
            "안경의 간단한 유지 관리를 안내하기 쉬운 애프터케어 용품입니다. 매장 전달이나 판매 시 일상 나사 확인과 관리를 제안하기 좋습니다.",
        ),
        t("簡易メンテナンス提案", "simple aftercare support", "简易售后维护建议", "간단한 애프터케어 제안"),
        t("お渡し時の日常ケアを提案しやすい", "helps suggest daily care at handover", "便于交付时建议日常护理", "전달 시 일상 관리를 제안하기 쉬움"),
    ),
    "machine_part": template(
        t(
            "機械や専用器具の交換・補修に使う部品です。消耗や破損時に必要箇所を交換し、機器を使い続けやすくします。",
            "A replacement or repair part for machines or dedicated devices. It helps keep equipment usable when parts wear or break.",
            "用于机器或专用器具更换、维修的部件。磨损或破损时可更换所需部位，延长设备使用。",
            "기계나 전용 기기의 교체·보수에 사용하는 부품입니다. 소모나 파손 시 필요한 부분을 교체해 장비를 계속 쓰기 쉽습니다.",
        ),
        t("機器部品交換・補修", "equipment part replacement and repair", "设备部件更换与维修", "장비 부품 교체 및 보수"),
        t("機器を使い続けやすい", "helps keep equipment in use", "有助于继续使用设备", "장비를 계속 사용하기 쉬움"),
    ),
    "work_supply": template(
        t(
            "加工・修理作業を補助する消耗品や関連用品です。用途に合わせて備えておくことで、店頭作業を進めやすくします。",
            "A consumable or related supply that supports processing and repair work. Keeping it on hand helps store work proceed smoothly.",
            "辅助加工和维修作业的消耗品或相关用品。按用途准备，可让门店作业更顺利。",
            "가공·수리 작업을 보조하는 소모품과 관련 용품입니다. 용도에 맞춰 준비해 두면 매장 작업을 진행하기 쉽습니다.",
        ),
        t("作業補助・消耗品", "work support and consumables", "作业辅助与耗材", "작업 보조 및 소모품"),
        t("店頭作業を進めやすい", "helps store work proceed smoothly", "便于推进门店作业", "매장 작업을 진행하기 쉬움"),
    ),
    "battery": template(
        t(
            "測定器やライトなどに使う電池・電源関連品です。必要な機器をすぐ使える状態に保ち、店頭作業を止めにくくします。",
            "A battery or power-related item for instruments and lights. It helps keep needed devices ready for store work.",
            "用于测量器和灯具等的电池/电源相关商品。可保持设备随时可用，减少门店作业中断。",
            "측정기나 라이트 등에 쓰는 배터리·전원 관련 상품입니다. 필요한 기기를 바로 쓸 수 있게 유지해 매장 작업 중단을 줄입니다.",
        ),
        t("電源・電池交換", "power and battery replacement", "电源与电池更换", "전원 및 배터리 교체"),
        t("機器をすぐ使える状態にしやすい", "helps keep devices ready", "便于保持设备可用", "기기를 바로 쓸 수 있게 하기 쉬움"),
    ),
    "decorative_part": template(
        t(
            "フレーム装飾やカスタマイズに使う小部品です。色や形を選び、修理だけでなく店頭提案の幅を広げやすくします。",
            "A small part for frame decoration or customization. Choosing color or shape helps expand proposals beyond repair.",
            "用于镜架装饰和定制的小部件。可选择颜色和形状，拓展维修以外的门店提案。",
            "프레임 장식과 커스터마이징에 쓰는 소부품입니다. 색상과 형태를 골라 수리 외의 매장 제안 폭을 넓히기 쉽습니다.",
        ),
        t("装飾・カスタマイズ", "decoration and customization", "装饰与定制", "장식 및 커스터마이징"),
        t("店頭提案の幅を広げやすい", "helps expand in-store proposals", "有助于拓展门店提案", "매장 제안 폭을 넓히기 쉬움"),
    ),
    "color_repair": template(
        t(
            "フレームや部品の色補修に使う用品です。小さな色剥げやキズを目立ちにくくし、修理後の見た目を整えやすくします。",
            "A supply for color repair on frames or parts. It helps make small color loss or scratches less noticeable after repair.",
            "用于镜架或部件颜色修补的用品。可让小面积掉色或划伤不明显，整理维修后的外观。",
            "프레임과 부품의 색 보수에 쓰는 용품입니다. 작은 도장 벗겨짐이나 흠집을 덜 눈에 띄게 해 수리 후 외관을 정돈합니다.",
        ),
        t("色補修", "color repair", "颜色修补", "색상 보수"),
        t("色剥げやキズを目立ちにくくしやすい", "helps reduce the appearance of color loss and scratches", "有助于减轻掉色和划伤的可见性", "도장 벗겨짐과 흠집을 덜 눈에 띄게 하기 쉬움"),
    ),
    "ink_marker": template(
        t(
            "印点・マーキング・表示に使うインクや関連用品です。レンズ加工や値札作成などで、必要な印を見やすく入れられます。",
            "Ink or related supplies for dots, marking, and labels. They help add clear marks for lens processing or price labels.",
            "用于印点、标记和显示的油墨及相关用品。适合镜片加工和价签制作时清楚标记。",
            "인점, 마킹, 표시용 잉크와 관련 용품입니다. 렌즈 가공이나 가격표 작성 시 필요한 표시를 보기 좋게 넣기 쉽습니다.",
        ),
        t("印点・マーキング", "dotting and marking", "印点与标记", "인점 및 마킹"),
        t("必要な印を見やすく入れやすい", "helps make needed marks visible", "便于清楚标记", "필요한 표시를 보기 좋게 넣기 쉬움"),
    ),
    "brush": template(
        t(
            "研磨や清掃の仕上げに使うブラシです。細かな汚れや研磨あとを整え、作業後の見た目を仕上げやすくします。",
            "A brush for polishing or cleaning finish work. It helps tidy fine dirt or polishing marks after work.",
            "用于研磨或清洁收尾的刷子。可整理细小污渍或研磨痕迹，使作业后外观更干净。",
            "연마나 청소 마감에 쓰는 브러시입니다. 작은 오염과 연마 자국을 정돈해 작업 후 외관을 마감하기 쉽습니다.",
        ),
        t("清掃・研磨仕上げ", "cleaning and polishing finish", "清洁与研磨收尾", "청소 및 연마 마감"),
        t("作業後の見た目を整えやすい", "helps tidy the finish after work", "便于整理作业后的外观", "작업 후 외관을 정돈하기 쉬움"),
    ),
    "eye_point_chart": template(
        t(
            "眼鏡に貼るだけでアイポイントを確認しやすくするシール式チャートです。手書き線を省き、確認作業の効率と精度を高めます。",
            "A sticker chart that makes eyewear eye points easy to check. It removes the need for hand-drawn lines and improves checking speed and accuracy.",
            "贴在眼镜上即可方便确认视点的贴纸式图表。无需手动画线，可提高确认效率和精度。",
            "안경에 붙이기만 하면 아이포인트를 확인하기 쉬운 스티커형 차트입니다. 손으로 선을 그릴 필요가 없어 확인 효율과 정확도를 높입니다.",
        ),
        t("アイポイント・PD確認", "eye-point and PD checking", "视点与瞳距确认", "아이포인트 및 PD 확인"),
        t("確認作業の効率と精度を高めやすい", "helps improve checking speed and accuracy", "有助于提高确认效率和精度", "확인 효율과 정확도를 높이기 쉬움"),
    ),
    "near_point_chart": template(
        t(
            "近距離の見え方を確認するための近点表です。複数の視標で近用視力や老眼鏡の見え方を確認しやすくします。",
            "A near-point chart for checking close vision. Its multiple targets help assess near acuity and reading-glasses performance.",
            "用于确认近距离视力的近点表。通过多种视标，便于检查近用视力和老花镜的视觉效果。",
            "근거리 시야를 확인하는 근점표입니다. 여러 시표로 근용 시력과 돋보기안경의 보임을 확인하기 쉽습니다.",
        ),
        t("近距離視力の確認", "near-vision checking", "近距离视力确认", "근거리 시력 확인"),
        t("近用の見え方を確認しやすい", "makes near vision easy to assess", "便于确认近用视觉", "근용 시야를 확인하기 쉬움"),
    ),
    "visual_acuity_chart": template(
        t(
            "視標を使って見え方を確認する視力検査用チャートです。検査条件をそろえ、結果を読み取りやすくします。",
            "A visual-acuity chart for checking vision with standardized targets. It helps keep test conditions consistent and results easy to read.",
            "使用标准视标确认视力的检查表。可统一检查条件，便于读取结果。",
            "표준 시표로 시야를 확인하는 시력검사용 차트입니다. 검사 조건을 맞추고 결과를 읽기 쉽게 합니다.",
        ),
        t("視力・見え方の確認", "visual-acuity checking", "视力与视觉确认", "시력 및 시야 확인"),
        t("検査条件をそろえやすい", "helps standardize test conditions", "便于统一检查条件", "검사 조건을 맞추기 쉬움"),
    ),
    "color_vision_chart": template(
        t(
            "数字やランドルト環などの視標で色の見え方を確認する色覚検査表です。検査を手順化し、判定を進めやすくします。",
            "A color-vision test chart using numbers and Landolt-ring targets. It helps standardize the procedure and supports clear assessment.",
            "通过数字和兰氏环等视标确认色觉的检查表。可规范检查步骤，便于判定。",
            "숫자와 란돌트 고리 시표로 색각을 확인하는 검사표입니다. 검사 절차를 표준화해 판정을 진행하기 쉽습니다.",
        ),
        t("色覚の確認", "color-vision checking", "色觉确认", "색각 확인"),
        t("色覚検査を進めやすい", "helps conduct color-vision testing", "便于进行色觉检查", "색각 검사를 진행하기 쉬움"),
    ),
    "vision_test_accessory": template(
        t(
            "視力検査で片眼の遮閉や視標提示などに使う補助器具です。検査条件を整え、見え方を確認しやすくします。",
            "An accessory for occlusion, target presentation, or other vision-test tasks. It helps prepare consistent conditions for checking vision.",
            "用于视力检查中的单眼遮挡、视标呈现等辅助器具。可整理检查条件，便于确认视力。",
            "시력검사에서 한쪽 눈 가림이나 시표 제시 등에 쓰는 보조기구입니다. 검사 조건을 갖춰 시야를 확인하기 쉽게 합니다.",
        ),
        t("視力検査の補助", "vision-test support", "视力检查辅助", "시력검사 보조"),
        t("検査条件を整えやすい", "helps prepare test conditions", "便于整理检查条件", "검사 조건을 갖추기 쉬움"),
    ),
    "hinge_part": template(
        t(
            "丁番・箱足・ブッシュなど、テンプルの開閉部を交換・補修する部品です。対応形状を合わせ、動きやガタつきを整えやすくします。",
            "A hinge-area part such as a hinge, end piece, or bushing. Matching the shape helps restore temple movement and reduce looseness.",
            "用于更换或维修铰链、桩头、衬套等镜腿开合部位的零件。匹配形状后，便于改善开合和松动。",
            "힌지, 엔드피스, 부싱 등 템플 개폐부를 교체·보수하는 부품입니다. 대응 형태를 맞춰 움직임과 흔들림을 정돈하기 쉽습니다.",
        ),
        t("丁番・テンプル開閉部の補修", "hinge and temple-joint repair", "铰链与镜腿开合部维修", "힌지 및 템플 개폐부 보수"),
        t("開閉の動きやガタつきを整えやすい", "helps restore movement and reduce looseness", "便于改善开合和松动", "개폐 움직임과 흔들림을 정돈하기 쉬움"),
    ),
    "lubricant": template(
        t(
            "眼鏡の丁番や細かな可動部に使う潤滑用品です。動きの固さやきしみを抑え、開閉を滑らかにしやすくします。",
            "A lubricant for eyewear hinges and small moving parts. It helps reduce stiffness and squeaking for smoother movement.",
            "用于眼镜铰链和细小活动部位的润滑用品。可减轻发涩和异响，使开合更顺畅。",
            "안경 힌지와 작은 가동부에 쓰는 윤활용품입니다. 뻑뻑함과 마찰음을 줄여 개폐를 부드럽게 하기 쉽습니다.",
        ),
        t("丁番・可動部の潤滑", "hinge and moving-part lubrication", "铰链与活动部润滑", "힌지 및 가동부 윤활"),
        t("開閉を滑らかにしやすい", "helps smooth movement", "便于顺畅开合", "개폐를 부드럽게 하기 쉬움"),
    ),
    "processing_chemical": template(
        t(
            "レンズ加工時の泡・臭い・削りカスなどを処理する作業用薬剤です。加工後の清掃や設備管理を行いやすくします。",
            "A processing chemical for foam, odor, swarf, or similar issues during lens work. It helps simplify cleanup and equipment care.",
            "用于处理镜片加工时泡沫、气味、切削屑等问题的作业药剂。便于加工后的清洁和设备管理。",
            "렌즈 가공 중 거품, 냄새, 가공 찌꺼기 등을 처리하는 작업용 약제입니다. 가공 후 청소와 장비 관리를 하기 쉽게 합니다.",
        ),
        t("レンズ加工環境の処理", "lens-processing environment treatment", "镜片加工环境处理", "렌즈 가공 환경 처리"),
        t("清掃や設備管理を行いやすい", "helps simplify cleanup and equipment care", "便于清洁和设备管理", "청소와 장비 관리를 하기 쉬움"),
    ),
    "optical_machine": template(
        t(
            "眼鏡レンズやフレームの加工・仕上げに使う専用機器です。作業を安定させ、加工精度や仕上がりをそろえやすくします。",
            "Dedicated equipment for processing or finishing eyewear lenses and frames. It helps stabilize work and produce consistent results.",
            "用于眼镜镜片或镜架加工、收尾的专用设备。可稳定作业，便于统一加工精度和完成效果。",
            "안경 렌즈와 프레임의 가공·마감에 쓰는 전용 장비입니다. 작업을 안정시켜 가공 정밀도와 마감을 일정하게 하기 쉽습니다.",
        ),
        t("レンズ・フレーム加工", "lens and frame processing", "镜片与镜架加工", "렌즈 및 프레임 가공"),
        t("加工精度や仕上がりをそろえやすい", "helps produce consistent processing results", "便于统一加工精度和效果", "가공 정밀도와 마감을 일정하게 하기 쉬움"),
    ),
    "anti_fog": template(
        t(
            "眼鏡レンズのくもりを防ぐための用品です。温度差やマスク使用時でも視界を保ちやすくします。",
            "An anti-fog product for eyewear lenses. It helps maintain clear vision during temperature changes or mask use.",
            "用于防止眼镜镜片起雾的用品。在温差变化或佩戴口罩时也有助于保持清晰视野。",
            "안경 렌즈의 김서림을 막는 용품입니다. 온도 차이나 마스크 착용 시에도 시야를 선명하게 유지하기 쉽습니다.",
        ),
        t("レンズのくもり止め", "lens anti-fog treatment", "镜片防雾", "렌즈 김서림 방지"),
        t("視界をクリアに保ちやすい", "helps keep vision clear", "有助于保持清晰视野", "시야를 선명하게 유지하기 쉬움"),
    ),
    "hearing_accessory": template(
        t(
            "補聴器や集音器の耳まわりに使う交換・装着部品です。対応サイズを選び、耳への収まりや衛生状態を整えやすくします。",
            "A replacement or fitting part used around the ear with hearing devices. Choosing the right size helps improve fit and hygiene.",
            "用于助听器或集音器耳部的更换、佩戴零件。选择合适尺寸，便于改善贴合和卫生状态。",
            "보청기나 집음기의 귀 주변에 쓰는 교체·장착 부품입니다. 맞는 크기를 골라 착용감과 위생 상태를 정돈하기 쉽습니다.",
        ),
        t("補聴器・集音器の装着補助", "hearing-device fitting support", "助听设备佩戴辅助", "청각기기 착용 보조"),
        t("耳への収まりを整えやすい", "helps improve ear fit", "便于改善耳部贴合", "귀에 맞는 착용감을 정돈하기 쉬움"),
    ),
    "service": template(
        t(
            "フレームやレンズに指定の加工・修理を行うサービス項目です。加工内容を明確にし、注文時の指示をそろえやすくします。",
            "A service item for specified frame or lens processing and repair. It makes the requested work clear when ordering.",
            "针对镜架或镜片进行指定加工、维修的服务项目。可明确加工内容，便于统一下单指示。",
            "프레임이나 렌즈에 지정 가공·수리를 하는 서비스 항목입니다. 가공 내용을 명확히 해 주문 지시를 맞추기 쉽습니다.",
        ),
        t("指定加工・修理", "specified processing and repair", "指定加工与维修", "지정 가공 및 수리"),
        t("注文時の加工指示をそろえやすい", "helps clarify processing instructions", "便于明确加工指示", "주문 시 가공 지시를 맞추기 쉬움"),
    ),
    "eyewear_frame": template(
        t(
            "掛け心地や用途に合わせて選ぶ眼鏡フレームです。サイズや設計の特徴を比べ、使用者に合う一本を提案しやすくします。",
            "An eyewear frame selected for fit and intended use. Its size and design features help staff recommend a suitable option.",
            "根据佩戴舒适度和用途选择的眼镜架。可比较尺寸和设计特点，便于推荐合适款式。",
            "착용감과 용도에 맞춰 고르는 안경 프레임입니다. 크기와 설계 특징을 비교해 사용자에게 맞는 제품을 제안하기 쉽습니다.",
        ),
        t("眼鏡フレームの提案", "eyewear-frame selection", "眼镜架推荐", "안경 프레임 제안"),
        t("用途と掛け心地に合う一本を選びやすい", "helps select a frame suited to use and fit", "便于选择符合用途和舒适度的镜架", "용도와 착용감에 맞는 프레임을 고르기 쉬움"),
    ),
    "watch_tool": template(
        t(
            "腕時計の裏蓋開けや部品保持などに使う時計用工具です。細かな部品を扱う作業を安定させやすくします。",
            "A watch tool for opening case backs or holding small components. It helps stabilize detailed watch work.",
            "用于打开手表后盖或夹持小部件的钟表工具。便于稳定进行精细作业。",
            "손목시계 뒷면 덮개 열기나 소부품 고정에 쓰는 시계용 공구입니다. 세밀한 작업을 안정적으로 하기 쉽습니다.",
        ),
        t("腕時計の分解・調整", "watch opening and adjustment", "手表拆装与调整", "손목시계 분해 및 조정"),
        t("細かな時計作業を安定させやすい", "helps stabilize detailed watch work", "便于稳定进行精细钟表作业", "세밀한 시계 작업을 안정시키기 쉬움"),
    ),
    "eyewear_measurement_chart": template(
        t(
            "フレーム幅やそり角など、眼鏡作りに必要な寸法・角度を確認する測定チャートです。採寸項目をそろえて確認しやすくします。",
            "A measurement chart for frame width, face-form angle, and other eyewear-making dimensions. It helps standardize the items being checked.",
            "用于确认镜架宽度、弯曲角等眼镜制作所需尺寸和角度的测量图表。便于统一检查项目。",
            "프레임 폭과 안면각 등 안경 제작에 필요한 치수·각도를 확인하는 측정 차트입니다. 측정 항목을 맞춰 확인하기 쉽습니다.",
        ),
        t("眼鏡寸法・角度の測定", "eyewear dimensions and angle measurement", "眼镜尺寸与角度测量", "안경 치수 및 각도 측정"),
        t("必要な採寸項目をまとめて確認しやすい", "helps check required measurements together", "便于集中确认所需测量项目", "필요한 측정 항목을 함께 확인하기 쉬움"),
    ),
    "measurement_chart_accessory": template(
        t(
            "測定チャート上で眼鏡を滑りにくくし、眼鏡とチャートを保護するシリコンシートです。位置を保って測定しやすくします。",
            "A silicone sheet that reduces slipping on a measurement chart and protects both the eyewear and chart. It helps keep items positioned during measurement.",
            "用于测量图表的防滑硅胶垫，可保护眼镜和图表，并便于在测量时保持位置。",
            "측정 차트 위에서 안경이 미끄러지는 것을 줄이고 안경과 차트를 보호하는 실리콘 시트입니다. 위치를 유지해 측정하기 쉽습니다.",
        ),
        t("測定チャートの滑り止め・保護", "measurement-chart grip and protection", "测量图表防滑与保护", "측정 차트 미끄럼 방지 및 보호"),
        t("眼鏡の位置を保って測定しやすい", "helps hold eyewear in position for measurement", "便于固定眼镜位置进行测量", "안경 위치를 유지해 측정하기 쉬움"),
    ),
    "lens_selection_chart": template(
        t(
            "フレームに必要なレンズの最小有効径を確認する測定チャートです。適切なレンズサイズを選び、加工判断をしやすくします。",
            "A chart for checking the minimum effective lens diameter required by a frame. It helps select an appropriate lens size for processing.",
            "用于确认镜架所需镜片最小有效直径的测量图表。便于选择合适镜片尺寸并判断加工。",
            "프레임에 필요한 렌즈의 최소 유효 지름을 확인하는 측정 차트입니다. 적절한 렌즈 크기를 골라 가공 판단을 하기 쉽습니다.",
        ),
        t("レンズ最小有効径の確認", "minimum effective lens-diameter checking", "镜片最小有效直径确认", "렌즈 최소 유효 지름 확인"),
        t("適切なレンズサイズを選びやすい", "helps select the appropriate lens size", "便于选择合适镜片尺寸", "적절한 렌즈 크기를 고르기 쉬움"),
    ),
    "curve_scale": template(
        t(
            "レンズカーブを測るためのスケールです。測定箇所に合うサイズを使い分け、レンズを傷つけにくく確認できます。",
            "A scale for measuring lens curvature. Different sizes suit different areas and help check curves without easily scratching lenses.",
            "用于测量镜片弯度的量尺。可按测量部位选择尺寸，并减少镜片划伤。",
            "렌즈 커브를 측정하는 스케일입니다. 측정 부위에 맞는 크기를 골라 렌즈에 흠집을 내기 어렵게 확인할 수 있습니다.",
        ),
        t("レンズカーブの測定", "lens-curve measurement", "镜片弯度测量", "렌즈 커브 측정"),
        t("測定箇所に合わせて確認しやすい", "helps measure the appropriate area", "便于按测量部位确认", "측정 부위에 맞춰 확인하기 쉬움"),
    ),
    "lens_template": template(
        t(
            "レンズ加工用の形状を写し取る型板です。対応サイズを選び、レンズの形や加工位置をそろえやすくします。",
            "A lens-processing template for transferring frame shape. Choosing the matching size helps keep lens shape and processing position consistent.",
            "用于描取镜片加工形状的模板。选择对应尺寸，便于统一镜片形状和加工位置。",
            "렌즈 가공 형상을 옮기는 형판입니다. 맞는 크기를 골라 렌즈 모양과 가공 위치를 일정하게 하기 쉽습니다.",
        ),
        t("レンズ加工形状の型取り", "lens-shape templating", "镜片加工形状取样", "렌즈 가공 형상 본뜨기"),
        t("加工形状をそろえやすい", "helps keep processing shape consistent", "便于统一加工形状", "가공 형상을 일정하게 하기 쉬움"),
    ),
    "pliers_axis_adjustment": template(
        t(
            "レンズの水平や軸位置を調整するヤットコです。レンズ位置を確認しながら、左右の傾きをそろえやすくします。",
            "Pliers for adjusting lens level and axis position. They help align left and right lens tilt while checking lens position.",
            "用于调整镜片水平和轴位的钳子。可边确认镜片位置，边统一左右倾斜。",
            "렌즈 수평과 축 위치를 조정하는 플라이어입니다. 렌즈 위치를 확인하며 좌우 기울기를 맞추기 쉽습니다.",
        ),
        t("レンズ水平・軸位置の調整", "lens level and axis adjustment", "镜片水平与轴位调整", "렌즈 수평 및 축 위치 조정"),
        t("左右の傾きをそろえやすい", "helps align lens tilt", "便于统一左右倾斜", "좌우 기울기를 맞추기 쉬움"),
    ),
    "sanitizing_box": template(
        t(
            "紫外線照射でトライアルフレームを清潔に保管するボックスです。短時間で全体を照射し、次の検査に備えやすくします。",
            "A UV sanitizing box for storing trial frames hygienically. It irradiates the frame from all sides and helps prepare it for the next examination.",
            "利用紫外线清洁并存放试镜架的消毒箱。可从各方向照射，便于为下一次检查做好准备。",
            "자외선 조사로 시험테를 위생적으로 보관하는 살균함입니다. 전체를 골고루 조사해 다음 검사에 대비하기 쉽습니다.",
        ),
        t("トライアルフレームの衛生管理", "trial-frame hygiene", "试镜架卫生管理", "시험테 위생 관리"),
        t("次の検査に清潔な状態で備えやすい", "helps prepare hygienically for the next exam", "便于以清洁状态准备下次检查", "다음 검사에 깨끗한 상태로 대비하기 쉬움"),
    ),
    "coating_supply": template(
        t(
            "コーティング剤の下処理・希釈・塗布に使う関連用品です。指定の材料と組み合わせ、被膜を均一に仕上げやすくします。",
            "A supply for preparing, thinning, or applying coatings. Used with the specified material, it helps produce an even coating.",
            "用于涂层剂的预处理、稀释或涂布。与指定材料配合使用，便于形成均匀涂层。",
            "코팅제 전처리, 희석 또는 도포에 쓰는 관련 용품입니다. 지정 재료와 함께 사용해 피막을 균일하게 마감하기 쉽습니다.",
        ),
        t("コーティング作業", "coating work", "涂层作业", "코팅 작업"),
        t("被膜を均一に仕上げやすい", "helps produce an even coating", "便于形成均匀涂层", "피막을 균일하게 마감하기 쉬움"),
    ),
    "frame_coating": template(
        t(
            "眼鏡フレーム表面を保護するコーティング剤です。肌との直接接触や汗の影響を抑え、白化や緑青も予防しやすくします。",
            "A protective coating for eyewear frames. It helps reduce direct skin contact and perspiration effects while preventing whitening and verdigris.",
            "用于保护眼镜架表面的涂层剂。可减少皮肤直接接触和汗液影响，并有助于预防发白和铜绿。",
            "안경테 표면을 보호하는 코팅제입니다. 피부 직접 접촉과 땀의 영향을 줄이고 백화와 녹청을 예방하기 쉽습니다.",
        ),
        t("フレーム表面の保護", "frame-surface protection", "镜架表面保护", "안경테 표면 보호"),
        t("汗や肌接触による劣化を抑えやすい", "helps reduce wear from sweat and skin contact", "有助于减少汗液和皮肤接触造成的劣化", "땀과 피부 접촉으로 인한 열화를 줄이기 쉬움"),
    ),
    "tool_grip_aid": template(
        t(
            "ドライバーや工具の滑りを抑える作業補助材です。接触部のグリップを高め、ネジ頭のつぶれや作業中のズレを防ぎやすくします。",
            "A grip aid that reduces slipping between tools and workpieces. It improves contact and helps prevent damaged screw heads or unwanted movement.",
            "用于减少螺丝刀和工具打滑的辅助材料。可提高接触部摩擦力，减少螺丝头损伤和作业偏移。",
            "드라이버와 공구의 미끄러짐을 줄이는 작업 보조재입니다. 접촉부 그립을 높여 나사머리 손상과 작업 중 어긋남을 줄이기 쉽습니다.",
        ),
        t("工具の滑り止め", "tool grip support", "工具防滑", "공구 미끄럼 방지"),
        t("ネジ頭のつぶれやズレを防ぎやすい", "helps prevent damaged screw heads and slipping", "有助于防止螺丝头损伤和打滑", "나사머리 손상과 미끄러짐을 줄이기 쉬움"),
    ),
    "fitting_support_tool": template(
        t(
            "テンプル曲げやブリッジ調整、ネジ締め時の支えに使うフィッティング補助工具です。小さなフレーム作業を安定させやすくします。",
            "A fitting support tool for temple bending, bridge adjustment, and screw work. It helps stabilize small frame tasks.",
            "用于镜腿弯曲、鼻梁调整和拧螺丝时支撑的验配辅助工具。便于稳定进行细小镜架作业。",
            "템플 굽힘, 브리지 조정, 나사 조임 때 받침으로 쓰는 피팅 보조 공구입니다. 작은 프레임 작업을 안정시키기 쉽습니다.",
        ),
        t("フレーム調整の保持・補助", "frame-adjustment support", "镜架调整支撑", "프레임 조정 지지 및 보조"),
        t("小さな作業を安定させやすい", "helps stabilize small tasks", "便于稳定细小作业", "작은 작업을 안정시키기 쉬움"),
    ),
    "pin_removal_tool": template(
        t(
            "丁番やブッシュ部のピンを押し抜くための専用工具です。対象部を保持しながら、細いピンを外しやすくします。",
            "A dedicated tool for pushing pins out of hinges or bushings. It holds the area steady and makes fine pins easier to remove.",
            "用于推出铰链或衬套部位销钉的专用工具。可稳定固定目标部位，便于拆下细销。",
            "힌지와 부싱 부분의 핀을 밀어 빼는 전용 공구입니다. 대상 부위를 고정하면서 가는 핀을 제거하기 쉽습니다.",
        ),
        t("丁番・ブッシュのピン抜き", "hinge and bushing pin removal", "铰链与衬套销钉拆卸", "힌지 및 부싱 핀 제거"),
        t("細いピンを外しやすい", "makes fine pins easier to remove", "便于拆下细销", "가는 핀을 제거하기 쉬움"),
    ),
    "lens_removal_tool": template(
        t(
            "フレームからレンズやナイロール糸を外すための専用工具です。周囲を傷つけにくく、レンズ交換作業を進めやすくします。",
            "A dedicated tool for removing lenses or nylor cord from frames. It helps replacement work proceed with less risk of surrounding damage.",
            "用于从镜架拆下镜片或尼龙丝的专用工具。可减少周围划伤，便于进行镜片更换。",
            "프레임에서 렌즈나 나일론 실을 분리하는 전용 공구입니다. 주변 흠집을 줄이며 렌즈 교체 작업을 진행하기 쉽습니다.",
        ),
        t("レンズ・ナイロール糸の取り外し", "lens and nylor-cord removal", "镜片与尼龙丝拆卸", "렌즈 및 나일론 실 분리"),
        t("交換時の傷を抑えやすい", "helps reduce damage during replacement", "有助于减少更换时的划伤", "교체 중 흠집을 줄이기 쉬움"),
    ),
    "binoculars": template(
        t(
            "遠くの対象を拡大して見るための双眼鏡・オペラグラスです。観劇や屋外観察で、見たい対象を捉えやすくします。",
            "Binoculars or opera glasses for magnifying distant subjects. They make targets easier to see at performances or outdoors.",
            "用于放大观察远处目标的双筒望远镜或观剧镜。便于在观演和户外观察时看清目标。",
            "먼 대상을 확대해 보는 쌍안경·오페라글라스입니다. 공연 관람과 야외 관찰에서 보고 싶은 대상을 찾기 쉽습니다.",
        ),
        t("遠方観察", "distance viewing", "远距离观察", "원거리 관찰"),
        t("遠くの対象を捉えやすい", "makes distant subjects easier to see", "便于看清远处目标", "먼 대상을 보기 쉬움"),
    ),
    "price_tag_printer": template(
        t(
            "商品値札を定位置へ見やすく印字するタッチパネル式プリンターです。多言語や各種文字に対応し、値札作成を効率化します。",
            "A touch-panel printer for placing clear text on product tags. Multilingual and varied character support helps streamline tag creation.",
            "用于在商品吊牌指定位置清晰打印的触摸屏打印机。支持多语言和多种字符，可提高标签制作效率。",
            "상품 가격표의 정해진 위치에 선명하게 인쇄하는 터치패널 프린터입니다. 다국어와 다양한 문자에 대응해 가격표 제작을 효율화합니다.",
        ),
        t("商品値札の印刷", "product-tag printing", "商品标签打印", "상품 가격표 인쇄"),
        t("多言語の値札を作りやすい", "helps create multilingual tags", "便于制作多语言标签", "다국어 가격표를 만들기 쉬움"),
    ),
    "eyelid_support": template(
        t(
            "眼瞼下垂で下がったまぶたをやさしく支える眼鏡装着用の補助具です。左右と高さを合わせ、視界を確保しやすくします。",
            "An eyewear-mounted aid that gently supports a drooping eyelid. Selecting the correct side and height helps maintain the field of view.",
            "安装在眼镜上、用于轻柔支撑下垂眼睑的辅助器具。选择对应左右和高度，便于保持视野。",
            "안검하수로 처진 눈꺼풀을 부드럽게 받치는 안경 장착형 보조기구입니다. 좌우와 높이를 맞춰 시야를 확보하기 쉽습니다.",
        ),
        t("眼瞼下垂の視界補助", "drooping-eyelid vision support", "眼睑下垂视野辅助", "안검하수 시야 보조"),
        t("まぶたを支えて視界を確保しやすい", "helps support the eyelid and maintain vision", "便于支撑眼睑并保持视野", "눈꺼풀을 받쳐 시야를 확보하기 쉬움"),
    ),
    "high_curve_demo": template(
        t(
            "ハイカーブレンズの見え方を店頭で体験してもらうためのセットです。度数や乱視条件を組み合わせ、装用前に見え方を比べやすくします。",
            "A demonstration set for experiencing high-curve lens vision in store. Combining prescription and astigmatism conditions makes pre-wear comparison easier.",
            "用于在店内体验高弯镜片视觉效果的套装。可组合度数和散光条件，便于佩戴前比较视野。",
            "하이커브 렌즈의 보임을 매장에서 체험하는 세트입니다. 도수와 난시 조건을 조합해 착용 전에 시야를 비교하기 쉽습니다.",
        ),
        t("ハイカーブレンズの見え方体験", "high-curve lens vision demonstration", "高弯镜片视觉体验", "하이커브 렌즈 시야 체험"),
        t("装用前に見え方を比べやすい", "helps compare vision before wear", "便于佩戴前比较视觉效果", "착용 전에 보임을 비교하기 쉬움"),
    ),
    "parts": template(
        t(
            "眼鏡フレームや関連器具の交換・補修に使うパーツです。対応部位やサイズを合わせ、必要な部分だけを補修しやすくします。",
            "A part for replacing or repairing eyewear frames or related devices. Matching the location and size helps repair only the needed area.",
            "用于眼镜架或相关器具更换、维修的部件。按对应部位和尺寸选择，便于只修补所需位置。",
            "안경 프레임과 관련 기기의 교체·보수에 쓰는 부품입니다. 대응 부위와 사이즈를 맞춰 필요한 부분만 보수하기 쉽습니다.",
        ),
        t("交換・補修", "replacement and repair", "更换与维修", "교체 및 보수"),
        t("必要な部分だけを補修しやすい", "helps repair only the needed area", "便于只修补所需部位", "필요한 부분만 보수하기 쉬움"),
    ),
    "temple_tip_bending_support": template(
        t(
            "モダン曲げを補助する専用ツールです。フィッティング時の指を保護しながら、狙った位置でモダンを曲げやすくします。",
            "A support tool for bending temple tips. It helps protect fingers during fitting and makes it easier to bend at the target point.",
            "用于辅助脚套弯曲的专用工具。验配时可保护手指，并便于在目标位置弯曲脚套。",
            "모던 굽힘을 보조하는 전용 도구입니다. 피팅 중 손가락을 보호하면서 원하는 위치에서 모던을 굽히기 쉽습니다.",
        ),
        t("モダン曲げ補助", "temple-tip bending support", "脚套弯曲辅助", "모던 굽힘 보조"),
        t("指を保護しながら曲げやすい", "helps bend while protecting fingers", "保护手指并便于弯曲", "손가락을 보호하면서 굽히기 쉬움"),
    ),
    "special_104": template(
        t(
            "クリングスの微調整に使う、先細・先曲がりの平ヤットコです。狭い隙間でも小さな部位を正確につかみ、細かく調整できます。",
            "Flat pliers with slim, curved tips for fine klings adjustment. They grip small parts accurately even in narrow spaces.",
            "用于鼻托臂微调的先细弯头平口钳。即使在狭窄间隙中，也能准确夹住小部位并进行细调。",
            "클링스 미세 조정에 쓰는 가늘고 굽은 평 플라이어입니다. 좁은 틈에서도 작은 부위를 정확히 잡아 세밀하게 조정할 수 있습니다.",
        ),
        t("クリングスの微調整", "fine klings adjustment", "鼻托臂微调", "클링스 미세 조정"),
        t("狭い隙間でも正確につかみやすい", "grips accurately even in narrow spaces", "狭窄处也便于准确夹持", "좁은 틈에서도 정확히 잡기 쉬움"),
    ),
    "special_1053": template(
        t(
            "プッシュロックパッド専用の調整ヤットコです。金具を面で挟むことでカラー剥げや傷を抑え、狭い場所でも調整しやすくします。",
            "Dedicated pliers for push-lock pad adjustment. The flat gripping surface helps reduce color loss and scratches in narrow spaces.",
            "推锁式鼻托专用调整钳。以面接触夹持金具，可减少掉色和划伤，并便于在狭小位置调整。",
            "푸시록 패드 전용 조정 플라이어입니다. 금구를 면으로 잡아 도장 벗겨짐과 흠집을 줄이고 좁은 곳에서도 조정하기 쉽습니다.",
        ),
        t("プッシュロックパッド調整", "push-lock pad adjustment", "推锁式鼻托调整", "푸시록 패드 조정"),
        t("カラー剥げや傷を抑えて調整しやすい", "helps adjust while reducing scratches and color loss", "减少划伤和掉色并便于调整", "흠집과 도장 벗겨짐을 줄이며 조정하기 쉬움"),
    ),
    "special_1054": template(
        t(
            "2本ダキ足パッド専用の調整ヤットコです。取付金具とパッドを包み込んで保持し、抱き込み部分の緩みを防ぎながら作業できます。",
            "Dedicated pliers for twin pad-arm pads. They wrap and hold the mounting hardware and pad to help prevent looseness during adjustment.",
            "双脚鼻托专用调整钳。可包住安装金具和鼻托进行保持，有助于调整时防止抱合部位松动。",
            "두 갈래 패드 다리 전용 조정 플라이어입니다. 장착 금구와 패드를 감싸 잡아 조정 중 풀림을 줄이며 작업할 수 있습니다.",
        ),
        t("2本ダキ足パッド調整", "twin pad-arm adjustment", "双脚鼻托调整", "두 갈래 패드 다리 조정"),
        t("抱き込み部分の緩みを防ぎやすい", "helps prevent looseness while adjusting", "便于防止抱合部位松动", "감싸는 부분의 풀림을 줄이기 쉬움"),
    ),
}

TEMPLATES.update(
    {
        "special_1510": template(
            t(
                "レンズ止め部のリム曲がりを整える専用ヤットコです。レンズ周辺のリムを狙った位置で修正しやすくします。",
                "Dedicated pliers for straightening a bent rim at the lens-retaining area. They help correct the rim precisely around the lens.",
                "用于矫正镜片固定部位镜圈弯曲的专用钳。便于在镜片周围准确修整镜圈。",
                "렌즈 고정부의 림 휨을 바로잡는 전용 플라이어입니다. 렌즈 주변 림을 원하는 위치에서 정밀하게 교정하기 쉽습니다.",
            ),
            t("レンズ止め部のリム曲がり修正", "rim straightening at the lens-retaining area", "镜片固定部位镜圈矫正", "렌즈 고정부 림 휨 교정"),
            t("レンズ周辺のリムを狙って修正しやすい", "helps correct the rim precisely around the lens", "便于准确修整镜片周围的镜圈", "렌즈 주변 림을 정밀하게 교정하기 쉬움"),
        ),
        "special_194_w17": template(
            t(
                "ネジ頭にマイナス溝を作る、軸径2.3mmのネジ頭切りです。折れ込んだネジにドライバーを掛ける溝を付けられます。",
                "A 2.3 mm-shank screw-head cutter that makes a flat-blade slot. It lets a screwdriver engage a broken-off screw.",
                "轴径2.3mm的螺钉头开槽工具，可加工一字槽，使螺丝刀能够拧动断入的螺钉。",
                "축경 2.3mm의 나사 머리 홈 가공 도구입니다. 부러져 박힌 나사에 일자 드라이버 홈을 만들 수 있습니다.",
            ),
            t("ネジ頭へのマイナス溝加工", "cutting a flat-blade slot in a screw head", "螺钉头一字槽加工", "나사 머리 일자 홈 가공"),
            t("折れ込んだネジを回すための溝を作れる", "creates a slot for turning a broken-off screw", "可为断入螺钉加工便于拧出的槽", "부러져 박힌 나사를 돌릴 홈을 만들 수 있음"),
        ),
        "special_669": template(
            t("時計の電池交換時に電池をつかむプラスチックピンセットです。金属接触によるショートを避けながら扱えます。", "Plastic tweezers for holding batteries during watch-battery replacement. They help avoid short circuits caused by metal contact.", "用于更换手表电池时夹持电池的塑料镊子，可避免金属接触造成短路。", "시계 배터리 교체 시 배터리를 집는 플라스틱 핀셋입니다. 금속 접촉에 의한 단락을 피하며 다룰 수 있습니다."),
            t("時計電池の交換", "watch-battery replacement", "手表电池更换", "시계 배터리 교체"),
            t("金属接触によるショートを避けやすい", "helps avoid short circuits from metal contact", "有助于避免金属接触短路", "금속 접촉에 의한 단락을 피하기 쉬움"),
        ),
        "special_775": template(
            t("レンズのアイポイントや加工位置を示す1mm方眼シールです。貼ったまま位置を見比べやすくします。", "A 1 mm grid sticker for marking lens eye points and processing positions. It makes position comparison easy while attached.", "用于标记镜片视点和加工位置的1mm方格贴纸，粘贴后便于比较位置。", "렌즈 아이포인트와 가공 위치를 표시하는 1mm 모눈 스티커입니다. 붙인 상태로 위치를 비교하기 쉽습니다."),
            t("レンズの位置決め", "lens positioning", "镜片定位", "렌즈 위치 결정"),
            t("アイポイントや加工位置を確認しやすい", "makes eye points and processing positions easy to check", "便于确认视点和加工位置", "아이포인트와 가공 위치를 확인하기 쉬움"),
        ),
        "special_250_a": template(
            t("貼付式鼻盛りパッドを浮かないよう固定する専用作業台です。接着中のずれを抑えて安定させます。", "A dedicated work stand that holds adhesive nose-build pads flat. It stabilizes them and reduces shifting during bonding.", "用于固定粘贴式增高鼻托、防止翘起的专用工作台，可减少粘接时的移位。", "부착식 코받침이 뜨지 않도록 고정하는 전용 작업대입니다. 접착 중 움직임을 줄여 안정적으로 고정합니다."),
            t("貼付式鼻盛りパッドの固定", "holding adhesive nose-build pads", "固定粘贴式增高鼻托", "부착식 코받침 고정"),
            t("接着中の浮きやずれを抑えやすい", "helps reduce lifting and shifting during bonding", "便于减少粘接时翘起和移位", "접착 중 들뜸과 움직임을 줄이기 쉬움"),
        ),
        "special_333": template(
            t("レンズ加工時の削りカスを固めるハードナーです。清掃や廃棄をしやすくします。", "A hardener that solidifies lens-processing swarf, making cleanup and disposal easier.", "用于固化镜片加工碎屑的硬化剂，便于清扫和废弃处理。", "렌즈 가공 찌꺼기를 굳히는 하드너입니다. 청소와 폐기를 쉽게 합니다."),
            t("レンズ加工くずの固化", "solidifying lens-processing swarf", "镜片加工碎屑固化", "렌즈 가공 찌꺼기 고형화"),
            t("清掃・廃棄をしやすくする", "makes cleanup and disposal easier", "便于清扫和废弃处理", "청소와 폐기를 쉽게 함"),
        ),
        "special_455": template(
            t("角膜反射光を使い、PDを0.5mm単位でデジタル測定するメーターです。読み取りを素早く安定させます。", "A digital meter that uses corneal reflections to measure PD in 0.5 mm steps, supporting quick and consistent readings.", "利用角膜反射光，以0.5mm为单位数字测量瞳距，可快速稳定读取。", "각막 반사광을 이용해 PD를 0.5mm 단위로 디지털 측정하는 미터입니다. 빠르고 안정적으로 판독할 수 있습니다."),
            t("瞳孔間距離（PD）の測定", "pupillary-distance measurement", "瞳距（PD）测量", "동공간거리(PD) 측정"),
            t("0.5mm単位で素早く読み取りやすい", "supports quick readings in 0.5 mm steps", "便于以0.5mm为单位快速读取", "0.5mm 단위로 빠르게 판독하기 쉬움"),
        ),
    }
)


CATEGORY_TO_TEMPLATE = {
    "nose_pad": "nose_pad",
    "air_pad": "air_pad",
    "antibacterial_pad": "antibacterial_pad",
    "adhesive_fit_pad": "adhesive_fit_pad",
    "cellpita": "adhesive_fit_pad",
    "nose_pad_build": "nose_pad_build",
    "pad_arm": "pad_arm",
    "temple_tip": "temple_tip",
    "temple_sheet_grip": "temple_sheet_grip",
    "shrink_tube": "shrink_tube",
    "screw": "screw",
    "screw_bolt": "screw_bolt",
    "nut": "nut",
    "rimless": "nut",
    "washer": "washer",
    "nylon_rail": "nylon_rail",
    "nylor_string": "nylor_string",
    "nylor_sheet": "nylor_sheet",
    "nylor_burner": "nylor_burner",
    "screwdriver": "screwdriver",
    "screwdriver_handle": "screwdriver_handle",
    "nut_driver": "nut_driver",
    "screw_remover": "screw_remover",
    "drill": "drill",
    "drill_stand": "drill_stand",
    "frame_heater": "frame_heater",
    "cutting_fluid": "cutting_fluid",
    "workbench": "workbench",
    "tweezers": "tweezers",
    "lens_hole_bit": "drill",
    "reamer": "reamer",
    "file_grinding": "file_grinding",
    "finishing_tool": "file_grinding",
    "processing_file": "file_grinding",
    "polish": "polish",
    "polishing": "polish",
    "cleaner": "cleaner",
    "tape": "tape",
    "protective_supply": "tape",
    "adhesive": "adhesive",
    "soldering": "soldering",
    "soldering_supply": "soldering",
    "pliers": "pliers_generic",
    "pliers_klings_adjustment_premium": "pliers_klings_adjustment",
    "pliers_pad_adjustment": "pliers_pad_adjustment",
    "pliers_temple_opening": "pliers_temple_opening",
    "pliers_temple_angle": "pliers_temple_angle",
    "pliers_bridge_angle": "pliers_bridge_angle",
    "pliers_rim_shape": "pliers_rim_shape",
    "pliers_rimless_screw_cutter": "pliers_rimless_screw_cutter",
    "pliers_cutting": "pliers_cutting",
    "pliers_replacement_tip": "pliers_replacement_tip",
    "pliers_protective_cover": "pliers_protective_cover",
    "pliers_lens_size_check": "pliers_lens_size_check",
    "pliers_pad_remover": "pliers_pad_remover",
    "pliers_screw_grip": "pliers_screw_grip",
    "pliers_joint_hold": "pliers_joint_hold",
    "toolset": "toolset",
    "tool_set": "toolset",
    "tool_storage": "tool_storage",
    "measuring_device": "measuring_device",
    "measure": "measuring_device",
    "test_lens": "test_lens",
    "trial_frame": "trial_frame",
    "magnifier": "magnifier",
    "checker": "checker",
    "progressive_mark_light": "checker",
    "progressive_mark_light_part": "checker",
    "reading_glasses": "reading_glasses",
    "clip_on": "clip_on",
    "sunglasses": "sunglasses",
    "sports_band": "sports_band",
    "retainer_band": "anti_slip_retainer",
    "children_frame": "children_frame",
    "pc_glasses": "pc_glasses",
    "temple_cable": "temple_cable",
    "parts_set": "parts_set",
    "glass_code_chain": "glass_code_chain",
    "case": "case",
    "case_bag": "case",
    "pop_display": "pop_display",
    "book_training": "book_training",
    "machine_part": "machine_part",
    "work_supply": "work_supply",
    "battery": "battery",
    "charger": "battery",
    "decorative_part": "decorative_part",
    "color_repair": "color_repair",
    "ink_marker": "ink_marker",
    "brush": "brush",
    "eye_point_chart": "eye_point_chart",
    "near_point_chart": "near_point_chart",
    "visual_acuity_chart": "visual_acuity_chart",
    "color_vision_chart": "color_vision_chart",
    "vision_test_accessory": "vision_test_accessory",
    "hinge_part": "hinge_part",
    "lubricant": "lubricant",
    "processing_chemical": "processing_chemical",
    "optical_machine": "optical_machine",
    "anti_fog": "anti_fog",
    "hearing_accessory": "hearing_accessory",
    "service": "service",
    "parts": "parts",
    "generic_part": "parts",
    "repair_part": "parts",
}

# Legacy classifications are used only as a weak fallback for families that are
# difficult to recognize from a model number or brand name alone. Broad or
# historically noisy categories (parts, measuring_device, toolset, soldering,
# book_training, and similar) are intentionally excluded.
LOW_RISK_LEGACY_FALLBACKS = {
    "magnifier": "magnifier",
    "reading_glasses": "reading_glasses",
    "machine_part": "machine_part",
    "case": "case",
    "sports_band": "sports_band",
    "sunglasses": "sunglasses",
    "pc_glasses": "pc_glasses",
    "cleaner": "cleaner",
    "decorative_part": "decorative_part",
    "glass_code_chain": "glass_code_chain",
}


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, headers, rows):
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def compact(value, limit=None):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit and len(value) > limit:
        return value[: limit - 1] + "…"
    return value


def has_any(text, words):
    return any(w in text for w in words)


CODE_TEMPLATE_OVERRIDES = {
    "1510": "special_1510",
    "194-W17": "special_194_w17",
    "669": "special_669",
    "775": "special_775",
    "1040": "eye_point_chart",
    "1040-S": "eye_point_chart",
    "1040-A": "eye_point_chart",
    "493": "watch_tool",
    "636-B": "lens_template",
    "676": "pliers_axis_adjustment",
    "801N-BK": "sports_band",
    "821": "sanitizing_box",
    "836": "screwdriver",
    "877-2": "coating_supply",
    "980": "tool_grip_aid",
    "994-A": "cleaner",
    "1003": "pliers_protective_cover",
    "1007-Z": "work_supply",
    "1032": "screwdriver",
    "1039": "screwdriver",
    "1041": "cleaner",
    "1050": "frame_coating",
    "1062": "eyewear_frame",
    "2045": "fitting_support_tool",
    "2073-10": "reamer",
    "2267-10": "pin_removal_tool",
    "PS-3": "tool_storage",
    "T-40": "lens_removal_tool",
    "329": "nut_driver",
    "672": "adhesive",
    "750-B": "machine_part",
    "773-528": "hinge_part",
    "773-529": "hinge_part",
    "1052-1": "checker",
    "1721-51": "nut_driver",
    "AP-2-3": "polish",
    "E16042": "magnifier",
    "E160422": "magnifier",
    "E299729270": "anti_slip_retainer",
    "UT-06": "anti_slip_retainer",
    "UT-08": "anti_slip_retainer",
    "423": "near_point_chart",
    "815": "near_point_chart",
    "817": "visual_acuity_chart",
    "961": "color_vision_chart",
    "991": "color_vision_chart",
    "250-A": "special_250_a",
    "333": "special_333",
    "455": "special_455",
    # Yattoko / pliers: keep tool bodies separate from parts and cutters.
    "2": "pliers_modern_bending",
    "3": "pliers_klings_adjustment",
    "190": "pliers_klings_adjustment",
    "662": "pliers_klings_adjustment",
    "651": "pliers_klings_adjustment",
    "858": "pliers_klings_adjustment",
    "395-B": "pliers_pad_adjustment",
    "356": "pliers_pad_adjustment",
    "617": "pliers_pad_adjustment",
    "969": "pliers_pad_adjustment",
    "1006": "pliers_pad_adjustment",
    "5": "pliers_cutting",
    "225": "pliers_cutting",
    "304": "pliers_cutting",
    "156-B": "pliers_cutting",
    "372": "pliers_cutting",
    "1577-10N": "pliers_cutting",
    "174": "pliers_rimless_screw_cutter",
    "386": "pliers_joint_hold",
    "661": "pliers_rimless_screw_cutter",
    "22-B": "pliers_lens_size_check",
    "335-B": "pliers_lens_size_check",
    "20-B": "pliers_joint_hold",
    "193": "pliers_joint_hold",
    "308-B": "pliers_joint_hold",
    "765": "pliers_joint_hold",
    "76-B": "pliers_joint_hold",
    "1551-00": "pliers_joint_hold",
    "614": "pliers_joint_hold",
    "937": "pliers_joint_hold",
    "996": "pliers_joint_hold",
    "40-P": "pliers_temple_opening",
    "642-P": "pliers_temple_opening",
    "25-B": "pliers_bridge_angle",
    "352": "pliers_bridge_angle",
    "642": "pliers_temple_opening",
    "720": "pliers_bridge_angle",
    "613-B": "pliers_bridge_angle",
    "834": "pliers_pad_adjustment",
    # Screw-gripping tweezers and nut/screw removal tools.
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
    "669": "special_669",
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
    # High-risk non-toolset or non-case items.
    "169-MBK": "frame_heater",
    "237": "cutting_fluid",
    "284": "workbench",
    "298": "drill_stand",
    "310": "aftercare_kit",
    "310-1": "aftercare_kit",
    "350": "aftercare_kit",
    "441-A": "case",
    "752-WX": "book_training",
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
    "E1625S": "measuring_device",
    "E1625T": "machine_part",
    "E1630": "measuring_device",
    "E16321": "measuring_device",
    "N40350-M372": "drill",
    "N40360-M103": "drill",
}


def get_merged_text(row, catalog_row, hp_row):
    hp_status = hp_row.get("hp_match_status") or row.get("HP確認ステータス", "")
    hp_text = ""
    if hp_status == "exact":
        hp_text = " ".join(
            [
                hp_row.get("hp_categories", ""),
                hp_row.get("hp_description", ""),
                row.get("HPから確認した情報", ""),
            ]
        )
    elif hp_status == "variant_group":
        # Family-page context is useful for broad product-family classification,
        # but is not treated as exact evidence for variant-specific claims.
        hp_text = " ".join(
            [
                hp_row.get("_family_categories", ""),
                hp_row.get("_family_description", ""),
            ]
        )
    return compact(
        " ".join(
            [
                row.get("品番", ""),
                row.get("商品名_JA", ""),
                row.get("説明カテゴリ", ""),
                catalog_row.get("catalog_usage", ""),
                hp_text,
                catalog_row.get("issue_flags", ""),
            ]
        )
    )


def detect_pliers_template(name, text):
    if has_any(text, ["先プラスティック", "先プラ", "先カバー", "透明カバー丈", "交換用先端", "ヤットコ先"]):
        return "pliers_replacement_tip"
    if has_any(text, ["プロテクトフィルム", "ツールゴムコーティング", "グリップゴムシート"]):
        return "pliers_protective_cover"
    if has_any(text, ["ツーポネジ切り", "ツーポイント用ネジ切り", "ネジ切りカッター", "ネジ切り", "ねじ切り", "ネジの長さ"]):
        return "pliers_rimless_screw_cutter"
    if has_any(name + text, ["ニッパー", "喰い切り", "カッター", "Cutter", "切り"]) and not has_any(
        text, ["レンズリムーバー"]
    ):
        return "pliers_cutting"
    if has_any(text, ["ワンタッチパットはずし", "ワンタッチパッドはずし", "パットはずし", "パッドはずし"]):
        return "pliers_pad_remover"
    if has_any(text, ["レンズサイズ", "歪度計", "リム止めネジの代わり"]):
        return "pliers_lens_size_check"
    if has_any(text, ["箱蝶", "ボックス", "パット調整", "パッド調整", "埋込", "ワンタッチパット", "ワンタッチパッド"]):
        return "pliers_pad_adjustment"
    if has_any(text, ["丁番コマ", "ネジつかみ", "ネジ抜き"]):
        return "pliers_screw_grip"
    if has_any(text, ["智固定", "智の部分", "縦智", "丁番の固定", "テンプル調整時のサポート"]):
        return "pliers_joint_hold"
    if has_any(text, ["クリングス", "パット足を直接", "パッド足を直接"]):
        return "pliers_klings_adjustment"
    if has_any(text, ["テンプル角度", "前傾角", "智のねじれ"]):
        return "pliers_temple_angle"
    if has_any(text, ["テンプル開き", "開き調整"]):
        return "pliers_temple_opening"
    if has_any(text, ["ブリッジ角度", "ブリッジカーブ", "フロントバランス"]):
        return "pliers_bridge_angle"
    if has_any(text, ["モダン曲げ", "モダンを", "先セル曲げ"]):
        return "pliers_modern_bending"
    if has_any(text, ["リム", "ナイロール", "アール修正", "溝堀"]):
        return "pliers_rim_shape"
    return "pliers_generic"


def detect_template_key(row, catalog_row, hp_row, legacy_row=None):
    code = row.get("品番", "").strip()
    if code == "104":
        return "special_104"
    if code == "1053":
        return "special_1053"
    if code == "1054":
        return "special_1054"
    if code in CODE_TEMPLATE_OVERRIDES:
        return CODE_TEMPLATE_OVERRIDES[code]

    name = row.get("商品名_JA", "")
    text = get_merged_text(row, catalog_row, hp_row)
    category = row.get("説明カテゴリ", "").strip()
    legacy_category = (legacy_row or {}).get("説明カテゴリ", "").strip()

    # Direct product-purpose rules. These run before broad category fallbacks so
    # chart, inspection, machine, chemical, and service items cannot collapse to
    # the generic replacement-part summary.
    if has_any(name, ["(加工内容)", "（加工内容）", "(修理内容)", "（修理内容）"]):
        return "service"
    if "Sチャート" in name:
        return "measurement_chart_accessory" if "シリコンシート" in name else "eyewear_measurement_chart"
    if "システムチャート" in name:
        return "visual_acuity_chart" if "本体" in name else "machine_part"
    if has_any(name, ["フロアースタンド", "テーブルスタンド", "スマートリモコン", "レッドグリーンメガネ"]):
        return "machine_part"
    if has_any(name, ["ガード二本足"]):
        return "pad_arm"
    if has_any(name, ["シリコンプッシュロック", "スリムフィット", "ピターム", "セルシ-ル", "セルシール"]):
        return "nose_pad"
    if has_any(name, ["ジュニアケ-ブル", "ジュニアケーブル"]):
        return "temple_cable"
    if has_any(name, ["販売用テンプルカバー"]):
        return "temple_tip"
    if has_any(name, ["SWANSスポーツベルト", "スワンズスポーツベルト"]):
        return "sports_band"
    if has_any(name, ["クラッチグラス"]):
        return "eyelid_support"
    if has_any(name, ["イヤホンマイク"]):
        return "hearing_accessory"
    if has_any(name, ["ハイカーブグラス体験用"]):
        return "high_curve_demo"
    if has_any(name, ["おしゃれ仮枠", "万能トライアル・フレーム", "万能トライアル･フレーム"]):
        return "trial_frame"
    if has_any(name, ["バイフォーカルレンズ", "球面S±", "乱視C±", "プリズムP.", "UNIVISION 単品レンズ"]):
        return "test_lens"
    if has_any(name, ["基礎両眼視", "眼鏡用語辞典", "装用テストの実際", "すぐに役立つ眼鏡学"]):
        return "book_training"
    if has_any(name, ["ウェルネスプロテクト", "キャップ・クリップ・サンシェード"]):
        return "clip_on"
    if has_any(name, ["プリズムビノコンフォート", "スマートルクスデジタル", "イージーポケット", "マックス DETAIL", "マックスディテール", "ライトグリップLED"]):
        return "magnifier"
    if has_any(name, ["双眼鏡", "オペラグラス"]):
        return "binoculars"
    if has_any(name, ["グラスホルダー", "ルーぺ用ストラップ", "ルーペ用ストラップ"]):
        return "glass_code_chain"
    if has_any(name, ["天武チタン", "優眠"]):
        return "eyewear_frame"
    if has_any(name, ["提札", "眼鏡かける君"]):
        return "pop_display"
    if has_any(name, ["型板ストッカー"]):
        return "tool_storage"
    if has_any(name, ["型板(", "型板（"]):
        return "lens_template"
    if has_any(name, ["タッチパネルプリンター"]):
        return "price_tag_printer"
    if has_any(name, ["ハイルック", "メガネクリンビュー", "エアダスター"]):
        return "cleaner"
    if has_any(name, ["フレームコート"]):
        return "frame_coating"
    if has_any(name, ["ツールゴムコーティング", "グリップゴムシート"]):
        return "pliers_protective_cover"
    if has_any(name, ["グリップペースト"]):
        return "tool_grip_aid"
    if has_any(name, ["シリコンコートプライマー", "ナノコート溶剤", "コーティングスポンジ", "シリコン液", "うすめ液のみ"]):
        return "coating_supply"
    if has_any(name, ["オイルスプレー"]):
        return "lubricant"
    if has_any(name, ["ガチドラ", "穴切りドライバ", "ドライバ-", "ドライバー"]):
        return "screwdriver"
    if has_any(name, ["コジ明け", "ウラブタ締め器", "キズ見", "側開器", "万能保持器", "保持器", "バネ棒用工具"]):
        return "watch_tool"
    if has_any(name, ["オヤユビツール"]):
        return "fitting_support_tool"
    if has_any(name, ["ピン抜き"]):
        return "pin_removal_tool"
    if has_any(name, ["レンズリムバー"]):
        return "lens_removal_tool"
    if has_any(name, ["溝堀、セル削り", "溝掘、セル削り", "溝掘セル削り"]):
        return "reamer"
    if re.match(r"^(N\d|NLE|NLEP)", code):
        return "machine_part"
    if has_any(
        name,
        [
            "クリップH",
            "台I",
            "フィルター",
            "ソケットタケノコ",
            "抜き棒",
            "受け台",
            "カシメ",
            "集熱カバー",
            "フロート計",
            "チップ20",
            "チップ21",
            "チップ22",
            "チップ23",
            "チップ24",
            "チップ25",
            "エレメントY",
            "ブースター",
            "メタル爪",
            "スペアニ-ドル",
            "スペアニードル",
            "カードA",
            "ゴムパッキン",
            "ACアダプター",
            "電源トランス",
            "削込カバー",
            "フィルタースポンジ",
            "交換用ビット",
            "バネのみ",
            "丸ベルト",
            "ガイドレイル",
            "マットガラス",
            "取り付け用リング",
            "LEDヘッドライト",
            "LEDワイドライト",
        ],
    ):
        return "machine_part"
    if has_any(name + text, ["E・P(アイポイント)", "E.Pシール", "E・Pシール", "アイポイントチャート"]):
        return "eye_point_chart"
    if has_any(name, ["近点表"]):
        return "near_point_chart"
    if has_any(name, ["色覚検査表", "色覚異常検査表"]):
        return "color_vision_chart"
    if has_any(name, ["視力表", "視標", "ランドルド環", "ランドルト環"]):
        return "visual_acuity_chart"
    if has_any(
        name + text,
        [
            "遮眼子",
            "遮閉器",
            "眼球模型",
            "トアール",
            "ツインレンズ",
            "立体視検査",
            "バタフライテスト",
            "利き目棒",
            "検眼テスト枠",
            "視力検査備品",
            "試験枠アイテム",
        ],
    ):
        return "vision_test_accessory"
    if has_any(name + text, ["PDメーター", "レンズメータ", "軸度計", "眼鏡サシ", "サシ・ゲージ", "カーブ計", "厚み計"]):
        return "measuring_device"
    if has_any(name, ["イヤーチップ", "耳あかガード", "イヤーパートナー", "フェミミ", "補聴器", "集音器"]):
        return "hearing_accessory"
    if has_any(name, ["耳ピタ"]):
        return "anti_slip_retainer"
    if has_any(name, ["リメイクカバー"]):
        return "temple_tip"
    if has_any(name + text, ["くもり止め", "アンチーフォグ", "ANTI-FOG"]):
        return "anti_fog"
    if has_any(name + text, ["メガネオイル", "丁番潤滑", "潤滑油", "潤滑剤"]):
        return "lubricant"
    if has_any(name + text, ["消泡剤", "消臭剤", "消臭スプレー", "ハードナー", "凝固剤", "固マリン", "加工用専用水"]):
        return "processing_chemical"
    if has_any(name, ["ディスペンサー", "ハンドラップ"]):
        return "work_supply"
    if has_any(name, ["加工整理箱", "整理箱用ラック", "バースタンド", "ツールスタンド", "工具台", "ツールバー"]):
        return "tool_storage"
    if has_any(name, ["値札", "プライスタグ", "プライスホルダー", "値札用回転印", "デージーホイール", "接客トレー", "プレゼンテーショントレー"]):
        return "pop_display"
    if has_any(name, ["マルチフクロ", "グラスポーチ"]):
        return "case"
    if has_any(name, ["ステッドラー", "レンズマーカー"]):
        return "ink_marker"
    if has_any(name, ["白化防止プライマー", "穴うめ液", "穴うめパウダー"]):
        return "adhesive"
    if has_any(name, ["緑棒", "青棒", "白棒", "赤棒", "茶棒", "黄棒", "光沢液", "艶出し液"]):
        return "polish"
    if has_any(name, ["耐水ペーパー", "仕上げドレス棒", "粗ドレス棒"]):
        return "file_grinding"
    if has_any(name, ["丁番", "箱足", "Wブッシュ", "Ｗブッシュ", "丁番リング", "カシメW", "チタングス"]):
        return "hinge_part"
    if has_any(name, ["ロングロックW", "ロングロックＷ"]):
        return "screw"
    if has_any(name, ["ナイロンキャップ", "スーパーロックシート"]):
        return "screw_bolt"
    if has_any(name, ["先プラスティック", "先プラスチック", "ヤットコ先端", "交換用先端"]):
        return "pliers_replacement_tip"
    if has_any(name, ["チェンジドライバ-柄", "チェンジドライバー柄", "先のみ"]):
        return "screwdriver_handle"
    if has_any(name, ["レンズ艶出機", "ミニルーター", "自動溝堀機", "自動型取機", "NH手摺機", "バフモーター"]):
        return "optical_machine"
    if (
        re.match(r"^(N|E16)", code)
        and has_any(
            name,
            ["交換用", "用専用", "用電球", "用ハロゲンランプ", "用フィルター", "押え", "アダプター", "カートリッジ", "ヒューズ", "フィーラ", "ワイドカップ", "カスバケット", "交換用ゴム"],
        )
    ):
        return "machine_part"

    # Exact official categories are strong family-level evidence.
    if has_any(text, ["バフモーター用研磨剤", "フレーム磨き"]):
        return "polish"
    if has_any(text, ["消泡剤・消臭剤・ハードナー"]):
        return "processing_chemical"
    if has_any(text, ["アイポイントチャート"]):
        return "eye_point_chart"
    if has_any(text, ["値札・ホルダー関連"]):
        return "pop_display"
    if has_any(text, ["ショップアイテム > 書籍"]):
        return "book_training"
    if has_any(text, ["エッシェンバッハ（ルーペ）", "ルーペ >", "ロービジョン"]):
        return "magnifier"
    if has_any(text, ["レンズチェッカー", "レンズメーター"]):
        return "checker"
    if has_any(text, ["チェンジドライバー"]):
        return "screwdriver_handle"
    if has_any(text, ["バネ丁番関連", "丁番関連"]):
        return "hinge_part"
    if has_any(text, ["加工整理箱・関連備品"]):
        return "tool_storage"
    if has_any(text, ["メガネオイル"]):
        return "lubricant"
    if has_any(text, ["店舗除菌"]):
        return "cleaner"
    if has_any(text, ["ネジゆるみ止め"]):
        return "adhesive"

    if has_any(name, ["のぼり", "POP", "吊下台紙", "ディスプレイ"]):
        return "pop_display"
    if "アフターケア" in name:
        return "aftercare_kit"
    if has_any(name, ["メガロック", "メガネグリップ"]):
        return "anti_slip_retainer"
    if has_any(name, ["ビーバ"]):
        return "children_frame"
    if has_any(name, ["エアーPC", "AIR PC", "PC II度無し"]):
        return "pc_glasses"
    if has_any(name, ["ビコーケーブル", "ジュニアケーブル", "ケーブルFセット"]):
        return "temple_cable"
    if has_any(name, ["鼻盛"]):
        return "nose_pad_build"
    if has_any(name + text, ["セルピタ", "セルシール", "セルモリー", "クビフリー"]):
        return "adhesive_fit_pad"
    if has_any(name + text, ["エアシリコン", "エアーシリコン"]):
        return "air_pad"
    if has_any(name, ["モダン", "先セル"]):
        if has_any(name, ["シートモダン"]):
            return "temple_sheet_grip"
        if has_any(name + text, ["調整ツール", "曲げを補助"]):
            return "temple_tip_bending_support"
        return "temple_tip"
    if has_any(name, ["パット", "パッド"]) and has_any(name + text, ["抗菌パット", "抗菌パッド", "抗菌仕様"]):
        return "antibacterial_pad"
    if has_any(name, ["グースネック", "U型", "Ｕ型", "パット足", "パッド足", "ダキ足", "アイアーム", "ガードアーム"]):
        return "pad_arm"
    if has_any(name, ["パット", "パッド", "箱蝶", "ワンタッチ", "ビルトイン", "巻式"]):
        return "nose_pad"
    if has_any(name, ["シュリンクチューブ"]):
        return "shrink_tube"
    if has_any(name, ["スポーツバンド"]):
        return "sports_band"
    if has_any(name, ["バンド"]) and has_any(name, ["ビーバ", "BEAVER"]):
        return "sports_band"
    if has_any(name, ["滑り止めシール"]) and has_any(name, ["ヤットコ"]):
        return "pliers_protective_cover"
    if has_any(name, ["グラスコード", "グラスチェーン", "チェーン", "コード"]):
        return "glass_code_chain"
    if has_any(name, ["クリップオン"]):
        return "clip_on"
    if has_any(name, ["サングラス"]):
        return "sunglasses"
    if has_any(name, ["ピンセット"]):
        return "tweezers"
    if has_any(name, ["ナット廻し", "ナット回し"]):
        return "nut_driver"
    if has_any(name, ["ネジ抜き", "ねじ抜き", "折込ネジ抜き", "折れ込ネジ抜き"]):
        return "screw_remover"
    if has_any(name, ["ドライバー"]):
        return "screwdriver"
    if has_any(name, ["フレームヒーター"]):
        return "frame_heater"
    if has_any(name, ["カットルーブ", "切削剤"]):
        return "cutting_fluid"
    if has_any(name, ["作業台"]):
        return "workbench"
    if has_any(name, ["ハンドドリルスタンド"]):
        return "drill_stand"
    if has_any(name, ["カラーリペア"]):
        return "color_repair"
    if has_any(name, ["部品セット", "パーツセット"]):
        return "parts_set"
    if has_any(name, ["レンズセット"]):
        if has_any(name, ["カバンのみ", "台のみ", "ケースのみ", "バックのみ"]):
            return "case"
        return "test_lens"
    if has_any(name, ["ナイロールストッパーバーナー"]):
        return "nylor_burner"
    if has_any(name, ["ナイロールシート"]):
        return "nylor_sheet"
    if has_any(name, ["テグス", "フロロカーボン"]):
        return "nylor_string"
    if has_any(name, ["ネジ", "スクリュー", "ダブルロック", "ハイブリッドロック", "OSロック", "OSハイブリッド"]):
        if has_any(name, ["ナット", "ボルト", "ツーポ", "ダブルロック", "OS"]):
            return "screw_bolt"
        return "screw"
    if has_any(name, ["ナット"]):
        return "nut"
    if has_any(name, ["ヤットコ", "ニッパー", "プライヤー"]):
        return detect_pliers_template(name, text)
    if has_any(name, ["メガネブク", "洗浄", "クリーナー", "クロス", "セーム革"]):
        return "cleaner"
    if has_any(name, ["ケース", "バッグ", "袋"]) and not has_any(name, ["スライドケース", "ケース丈"]):
        return "case"
    if has_any(name, ["ワッシャ", "座金"]):
        return "washer"
    if has_any(name, ["ナイロンレール", "溝セル", "プロテクトリング", "溝堀レンズはずし"]):
        return "nylon_rail"
    if has_any(name, ["マンドレール", "フェルト"]):
        return "polish"
    if has_any(name, ["ドリル", "穴明", "穴広げ"]):
        return "drill"
    if has_any(name, ["リーマ"]):
        return "reamer"
    if has_any(name, ["ヤスリ", "砥石", "面取り", "サンドペーパー"]):
        return "file_grinding"
    if has_any(name, ["バフ", "ポリッシャ", "みがき", "磨き", "コンパウンド"]):
        return "polish"
    if has_any(name, ["テープ", "フィルム"]):
        return "tape"
    if has_any(name, ["接着", "アロンタイト", "固着剤"]):
        return "adhesive"
    if has_any(name + text, ["ロウ付", "フラックス", "トーチ", "バーナー", "銀ロウ", "酸化防止"]):
        return "soldering"
    if has_any(name, ["テストレンズ"]):
        return "test_lens"
    if has_any(name, ["試験枠"]):
        return "trial_frame"
    if has_any(name, ["ルーペ", "リネンテスター", "拡大", "ローグラス"]):
        return "magnifier"
    if has_any(name, ["チェッカー", "チェックライト", "検査器", "UVライト", "テスター", "ビームライト"]):
        return "checker"
    if has_any(name, ["リーディング", "近用", "老眼"]):
        return "reading_glasses"
    if has_any(name, ["ヤスリセット"]):
        return "file_grinding"
    if has_any(name, ["リーマ-セット", "リーマーセット"]):
        return "reamer"
    if has_any(name, ["工具セット", "外販工具セット", "技能士試験工具", "基本工具セット"]):
        return "toolset"
    if has_any(name, ["工具台", "ツールスタンド", "ツールバー"]):
        return "tool_storage"
    if has_any(name, ["測定", "ゲージ", "メジャー", "歪度計", "カーブ計", "厚み計"]):
        return "measuring_device"
    if has_any(name, ["書籍", "講座", "フィッティング術", "手順"]):
        return "book_training"
    if has_any(name, ["電池", "充電", "USB"]):
        return "battery"
    if has_any(name, ["インク", "マーカー", "印点"]):
        return "ink_marker"
    if has_any(name, ["天然石", "合成石", "ジュエリー"]):
        return "decorative_part"
    if has_any(name, ["タッチアップ", "カラーリペア", "染色"]):
        return "color_repair"
    if has_any(name, ["ブラシ"]):
        return "brush"

    if has_any(text, ["視力測定 > 視力検査備品", "視力測定 > 試験枠アイテム"]):
        return "vision_test_accessory"
    if has_any(text, ["計測器 > サシ・ゲージ", "計測器 > カーブ計"]):
        return "measuring_device"
    if has_any(text, ["加工 > バフモーター機器", "加工 > タクボ製機器"]):
        return "optical_machine"
    if has_any(text, ["加工 > ルーター・バイス"]):
        return "workbench"
    if has_any(text, ["パーツ > 加工備品・消耗品 > 溝セル関連"]):
        return "nylon_rail"
    if has_any(text, ["販売 > くもり止め", "販売 > クリーナー > くもり止め"]):
        return "anti_fog"
    if has_any(text, ["加工備品・消耗品 > マーカーペン・溶解液関連"]):
        return "ink_marker" if has_any(name, ["ペン", "マーカー", "ステッドラー"]) else "work_supply"
    if has_any(text, ["加工 > フレームヒーター"]):
        return "frame_heater"
    if has_any(text, ["ショップアイテム > 鏡"]):
        return "pop_display"
    if has_any(text, ["加工 > ビット(ドリル)"]):
        return "drill"

    if legacy_category in LOW_RISK_LEGACY_FALLBACKS:
        return LOW_RISK_LEGACY_FALLBACKS[legacy_category]

    if category == "checker":
        if has_any(name, ["ペーパー", "紙", "保持台"]):
            return "work_supply"
    if category == "toolset" and not has_any(name, ["工具セット", "外販工具セット", "技能士試験", "基本工具"]):
        return "parts"
    if category == "book_training" and not has_any(name, ["書籍", "講座", "フィッティング術", "手順"]):
        return "parts"
    if category == "case" and has_any(name, ["ドライバー", "メガネブク", "ナット", "メガネふき"]):
        if "ドライバー" in name:
            return "screwdriver"
        if has_any(name, ["メガネブク", "メガネふき"]):
            return "cleaner"
        if "ナット" in name:
            return "nut"
    return CATEGORY_TO_TEMPLATE.get(category, "parts")


def source_label(row, catalog_row, hp_row):
    sources = []
    hp_status = hp_row.get("hp_match_status") or row.get("HP確認ステータス", "")
    hp_url = hp_row.get("hp_url") or row.get("商品ページURL")
    if hp_status == "exact" and hp_url:
        sources.append(hp_url)
    pages = catalog_row.get("catalog_pages") or row.get("カタログ参照")
    if pages:
        sources.append(pages)
    if CATALOG_PDF_PATH.exists():
        sources.append(f"PDF:{CATALOG_PDF_PATH.name}")
    return " / ".join(dict.fromkeys(sources))


def catalog_info(row, catalog_row):
    generic_phrases = (
        "眼鏡店向け作業・販売補助",
        "眼鏡店の作業や店頭提案を補助する商品です",
        "作業や提案をスムーズにし、店頭対応の幅を広げやすい",
    )

    def grounded(value):
        value = value or ""
        return "" if any(phrase in value for phrase in generic_phrases) else value

    parts = [
        catalog_row.get("catalog_pages") or row.get("カタログ参照", ""),
        grounded(catalog_row.get("catalog_usage", "")),
        grounded(catalog_row.get("catalog_features", "")),
        catalog_row.get("catalog_size_material", ""),
        row.get("PDF抽出メモ", ""),
    ]
    return compact(" / ".join(p for p in parts if p), 700)


def hp_info(row, hp_row):
    status = hp_row.get("hp_match_status") or row.get("HP確認ステータス", "")
    if status == "exact":
        parts = [
            hp_row.get("hp_product_name", ""),
            hp_row.get("hp_product_code", ""),
            hp_row.get("hp_categories", ""),
            hp_row.get("hp_description", ""),
        ]
        return compact(" / ".join(p for p in parts if p), 700)
    if status:
        return f"HP照合ステータス: {status}。exact未確認のため要約根拠はカタログ優先。"
    return compact(row.get("HPから確認した情報", ""), 700)


def apply_template(row, key, hp_row, catalog_row):
    tpl = TEMPLATES[key]
    for lang, cols in LANG_COLS.items():
        row[cols["summary"]] = tpl["summary"][lang]
        row[cols["customer"]] = tpl["summary"][lang]
        row[cols["usage"]] = tpl["usage"][lang]
        row[cols["benefit"]] = tpl["benefit"][lang]
    row["説明カテゴリ"] = key
    row["説明強化元"] = "programming_agent_rebuild_summaries.py+HP調査CSV+カタログ調査CSV+PDF抽出メモ"
    row["HP確認ステータス"] = hp_row.get("hp_match_status") or row.get("HP確認ステータス", "")
    row["HPから確認した情報"] = hp_info(row, hp_row)
    row["カタログから確認した情報"] = catalog_info(row, catalog_row)
    row["要約品質メモ"] = "全件再構築: HP exactは強い根拠、その他はカタログ抽出メモと商品名ルールを優先。"
    if hp_row.get("hp_match_status", "") == "exact" and hp_row.get("hp_url", "") and row.get("品番") != "194-W17":
        row["商品ページURL"] = hp_row["hp_url"]

    if row.get("品番") == "104":
        row["商品ページURL"] = "https://www.san-nishimura.co.jp/product/item/%E3%83%A4%E3%83%83%E3%83%88%E3%82%B3104/"
        row["HP確認ステータス"] = "exact"
        row["HPから確認した情報"] = (
            "公式HP: 平ヤットコ 先細・先曲がり。主にクリングス調整用。"
            "主な使用用途はクリングスの微調整。先端が緩やかにカーブし、狭い隙間でも正確につかめる。"
        )
        row["カタログから確認した情報"] = (
            "印刷カタログP.122: No.104 ヤットコ、挟み面=平、先曲、クリングス調整用として掲載。"
        )
        row["要約品質メモ"] = "重要品番の個別修正。ブリッジ角度調整ではなくクリングス微調整として扱う。"
    elif row.get("品番") == "1053":
        row["入数"] = ""
        row["HP確認ステータス"] = "exact"
        row["HPから確認した情報"] = (
            "公式HP: 調整時のカラー剥げ・傷を防止できるプッシュロックパッド専用ヤットコ。"
            "金具を面で挟み、薄く細い先端で狭い場所にも入りやすい。"
        )
        row["カタログから確認した情報"] = (
            "印刷カタログP.126: No.1053 ヤットコ、パット調整、プッシュロックパッド調整用途として掲載。"
            "旧入数「2本」は周辺テキスト誤抽出として表示しない。"
        )
        row["要約品質メモ"] = "重要品番の個別修正。工具本体のため入数「2本」は表示しない。"
    elif row.get("品番") == "1054":
        row["入数"] = ""
        row["HP確認ステータス"] = "exact"
        row["HPから確認した情報"] = (
            "公式HP調査済み: 2本ダキ足パッド専用の調整ヤットコ。"
            "取付金具とパッドを包み込んで保持し、抱き込み部分の緩みを防ぎながら調整。"
        )
        row["カタログから確認した情報"] = (
            "印刷カタログP.126: No.1054 ヤットコ、2本ダキ足パッド調整用途として掲載。"
            "商品用途名の「2本ダキ足」を入数と誤認しない。"
        )
        row["要約品質メモ"] = "重要品番の個別修正。工具本体のため入数「2本」は表示しない。"
    elif row.get("品番") == "1510":
        row["HP確認ステータス"] = "mismatch"
        row["HPから確認した情報"] = "公式HPのNo.379パッド外しページは品番不一致のため不採用。"
        row["カタログから確認した情報"] = "印刷カタログP.144: No.1510 ヤットコ。紙面写真と注記でレンズ止めリム曲がり調整を確認。"
        row["要約品質メモ"] = "紙面P.144を目視確認。ワンタッチパッド外しやテンプル丁番修正の周辺情報は不採用。"
    elif row.get("品番") == "194-W17":
        row["HP確認ステータス"] = "mismatch"
        row["商品ページURL"] = "https://www.san-nishimura.co.jp/product/item/?key_word=194-W17"
        row["HPから確認した情報"] = "公式HPは同一品番を削込ダイヤモンド砥石として掲載し、現行紙面・商品画像と不一致のため要確認。"
        row["カタログから確認した情報"] = "印刷カタログP.208: No.194-W17 ネジ頭切り、軸径2.3mm。ネジ頭にマイナス溝を作る工具。"
        row["要約品質メモ"] = "2025-2027紙面と商品画像を優先。公式HPとの品番・名称衝突を監査事項として保持。"

    if row.get("品番") in {"828-B-36", "828-B-38", "828-P-36", "828-P-38"}:
        row["入数"] = ""
        row["要約品質メモ"] = (
            row.get("要約品質メモ", "")
            + " ビーバ品番の36/38はサイズ表記のため、入数として表示しない。"
        ).strip()


def validate_rebuild(rows):
    by_code = {row.get("品番", ""): row for row in rows}
    expected_categories = {
        "104": "special_104",
        "1040": "eye_point_chart",
        "1040-S": "eye_point_chart",
        "1040-A": "eye_point_chart",
        "352": "pliers_bridge_angle",
        "642": "pliers_temple_opening",
        "642-P": "pliers_temple_opening",
        "1053": "special_1053",
        "1054": "special_1054",
    }
    errors = []
    for code, expected in expected_categories.items():
        actual = by_code.get(code, {}).get("説明カテゴリ", "")
        if actual != expected:
            errors.append(f"{code}: expected category {expected}, got {actual or '<missing>'}")
    forbidden_phrases = (
        "眼鏡店の作業や店頭提案を補助する商品です",
        "眼鏡フレームや関連器具の交換・補修に使うパーツです",
    )
    for row in rows:
        code = row.get("品番", "")
        summary = row.get("一言要約_JA", "")
        if any(phrase in summary for phrase in forbidden_phrases):
            errors.append(f"{code}: forbidden generic summary remains")
        for col in ("一言要約_JA", "一言要約_EN", "一言要約_ZH", "一言要約_KO"):
            if not row.get(col, "").strip():
                errors.append(f"{code}: missing {col}")
    for code in ("1053", "1054"):
        if by_code.get(code, {}).get("入数", "").strip():
            errors.append(f"{code}: tool body must not display pack quantity")
    if "ブリッジ" in by_code.get("642", {}).get("一言要約_JA", ""):
        errors.append("642: bridge-adjustment text remains")
    if errors:
        preview = "\n".join(errors[:30])
        raise RuntimeError(f"Rebuild QA failed ({len(errors)} issues):\n{preview}")


def main():
    rows = read_rows(MASTER_PATH)
    headers = list(rows[0].keys())
    eye_point_names = {
        "1040": {
            "商品名_JA": "E・P(アイポイント)シール10枚入",
            "商品名_EN": "E.P. (Eye Point) sticker, 10 sheets",
            "商品名_ZH": "E・P（视点）贴纸，10张",
            "商品名_KO": "E·P(아이포인트) 스티커 10매",
        },
        "1040-S": {
            "商品名_JA": "E・P(アイポイント)シール50枚",
            "商品名_EN": "E.P. (Eye Point) sticker, 50 sheets",
            "商品名_ZH": "E・P（视点）贴纸，50张",
            "商品名_KO": "E·P(아이포인트) 스티커 50매",
        },
        "1040-A": {
            "商品名_JA": "E・P(アイポイント)シール100枚",
            "商品名_EN": "E.P. (Eye Point) sticker, 100 sheets",
            "商品名_ZH": "E・P（视点）贴纸，100张",
            "商品名_KO": "E·P(아이포인트) 스티커 100매",
        },
    }
    for row in rows:
        if row.get("品番") in eye_point_names:
            row.update(eye_point_names[row["品番"]])
        if row.get("品番") == "642":
            row["カタログ参照"] = "カタログP.136,170"
    legacy_rows = (
        {r["品番"]: r for r in read_rows(LEGACY_MASTER_PATH)}
        if LEGACY_MASTER_PATH.exists()
        else {}
    )
    catalog_source_rows = read_rows(CATALOG_PATH)
    catalog_rows = {r["品番"]: r for r in catalog_source_rows}
    hp_source_rows = read_rows(HP_PATH)
    hp_source_map = {r["品番"]: r for r in hp_source_rows}
    hp_104 = hp_source_map.get("104")
    if hp_104:
        hp_104.update(
            {
                "hp_match_status": "exact",
                "hp_url": "https://www.san-nishimura.co.jp/product/item/%E3%83%A4%E3%83%83%E3%83%88%E3%82%B3104/",
                "hp_product_name": "平ヤットコ 先細・先曲がり",
                "hp_product_code": "104",
                "hp_categories": "工具 > ヤットコ(クリングス調整)",
                "hp_description": "主にクリングス調整用。主な使用用途はクリングスの微調整。先端が緩やかにカーブし、狭い隙間でも正確につかみやすい。",
                "hp_evidence": "公式商品ページで品番104・用途・先端形状を確認。旧No.352参照は破棄。",
                "notes": "v0.14 critical fix: exact confirmed",
            }
        )
    hp_642 = hp_source_map.get("642")
    if hp_642:
        hp_642.update(
            {
                "hp_match_status": "exact",
                "hp_url": "https://www.san-nishimura.co.jp/product/item/%E3%83%A4%E3%83%83%E3%83%88%E3%82%B3642/",
                "hp_product_name": "ヤットコ",
                "hp_product_code": "642",
                "hp_categories": "工具 > ヤットコ(テンプル開き)",
                "hp_description": "テンプル開き調整用のヤットコ。テンプルの開き幅を整える。",
                "hp_evidence": "公式商品ページで品番642とテンプル開き調整用途を確認。旧No.352参照は破棄。",
                "notes": "v0.17 critical fix: exact confirmed; wrong No.352 match removed",
            }
        )
    hp_194 = hp_source_map.get("194-W17")
    if hp_194 and "catalog_hp_name_conflict" not in hp_194.get("notes", ""):
        hp_194["notes"] = (hp_194.get("notes", "") + "; catalog_hp_name_conflict: printed catalog P.208 and local image show screw-head cutter").strip("; ")
    catalog_642 = catalog_rows.get("642")
    if catalog_642:
        catalog_642.update(
            {
                "catalog_pages": "カタログP.136,170",
                "catalog_info": "ヤットコ / テンプル開き幅調整 / テンプル開閉の調整に使用",
                "catalog_usage": "テンプル開き幅調整",
                "catalog_features": "左右のテンプル開き具合を整え、掛け具合を合わせやすい",
                "issue_flags": "printed_pages_normalized|wrong_tool_role_from_no352_corrected|adjacent_product_context_mixed|catalog_primary_page_136",
            }
        )
    for eye_point_code in ("1040", "1040-S", "1040-A"):
        catalog_1040 = catalog_rows.get(eye_point_code)
        if not catalog_1040:
            continue
        catalog_1040.update(
            {
                "catalog_pages": "カタログP.175",
                "catalog_info": "E.Pシール / 眼鏡に直接貼るシール式チャート / E.P・PD確認",
                "catalog_usage": "アイポイント・PD確認",
                "catalog_features": "手書き線を省き、E.P確認の効率・精度・標準化に役立つ",
                "issue_flags": "printed_pages_normalized|summary_overgeneralized_corrected|exact_catalog_purpose_adopted",
            }
        )
    # Inherit only broad family context from an exact page to rows that the HP
    # audit explicitly marked as a variant group on the same URL.
    hp_rows = {code: dict(source) for code, source in hp_source_map.items()}
    exact_by_url = {}
    for source in hp_source_rows:
        if source.get("hp_match_status") == "exact" and source.get("hp_url"):
            exact_by_url[source["hp_url"]] = source
    for hp_row in hp_rows.values():
        if hp_row.get("hp_match_status") != "variant_group":
            continue
        family = exact_by_url.get(hp_row.get("hp_url", ""))
        if family:
            hp_row["_family_categories"] = family.get("hp_categories", "")
            hp_row["_family_description"] = family.get("hp_description", "")
    evidence_rows = []
    audit_rows = []
    counts = Counter()

    for row in rows:
        code = row.get("品番", "")
        catalog_row = catalog_rows.get(code, {})
        hp_row = hp_rows.get(code, {})
        old_summary = row.get("一言要約_JA", "")
        old_category = row.get("説明カテゴリ", "")
        key = detect_template_key(row, catalog_row, hp_row, legacy_rows.get(code, {}))
        if key not in TEMPLATES:
            key = "parts"

        apply_template(row, key, hp_row, catalog_row)
        counts[key] += 1

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
            }
        )
        audit_rows.append(
            {
                "品番": code,
                "商品名_JA": row.get("商品名_JA", ""),
                "old_category": old_category,
                "new_category": key,
                "hp_match_status": row.get("HP確認ステータス", ""),
                "catalog_pages": catalog_row.get("catalog_pages") or row.get("カタログ参照", ""),
                "old_summary_ja": old_summary,
                "new_summary_ja": row.get("一言要約_JA", ""),
                "source": source_label(row, catalog_row, hp_row),
                "quality_note": row.get("要約品質メモ", ""),
            }
        )

    validate_rebuild(rows)
    master_written = MASTER_PATH
    try:
        write_rows(MASTER_PATH, headers, rows)
    except PermissionError:
        write_rows(FALLBACK_MASTER_PATH, headers, rows)
        master_written = FALLBACK_MASTER_PATH
    write_rows(HP_PATH, list(hp_source_rows[0].keys()), hp_source_rows)
    write_rows(CATALOG_PATH, list(catalog_source_rows[0].keys()), catalog_source_rows)
    write_rows(EVIDENCE_PATH, list(evidence_rows[0].keys()), evidence_rows)
    write_rows(AUDIT_PATH, list(audit_rows[0].keys()), audit_rows)

    print(f"rows={len(rows)}")
    print(f"catalog_rows={len(catalog_rows)} hp_rows={len(hp_rows)}")
    print(f"catalog_pdf_exists={CATALOG_PDF_PATH.exists()}")
    print(f"master_written={master_written}")
    for key, count in counts.most_common():
        print(f"{key}\t{count}")


if __name__ == "__main__":
    main()
