from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.graphics.barcode import qr
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SCREEN_DIR = ROOT / "manual-assets" / "screens"
SCENE_DIR = ROOT / "manual-assets" / "scenes"
OUT_PDF = ROOT / "output" / "pdf"
OUT_IMG = ROOT / "output" / "manual"

PAGE_W = 2480
PAGE_H = 3508
LANDSCAPE_W = 3508
LANDSCAPE_H = 2480

NAVY = "#10243e"
INK = "#172033"
MUTED = "#667085"
LINE = "#d8e0ea"
BG = "#f3f6fa"
PALE_BLUE = "#eff6ff"
BLUE = "#2563eb"
GREEN = "#07845f"
PALE_GREEN = "#e9fbf4"
ORANGE = "#c2410c"
PALE_ORANGE = "#fff7ed"
RED = "#b42318"
WHITE = "#ffffff"

FONT_KO = Path("C:/Windows/Fonts/malgun.ttf")
FONT_KO_B = Path("C:/Windows/Fonts/malgunbd.ttf")
FONT_JA = Path("C:/Windows/Fonts/BIZ-UDGothicR.ttc")
FONT_JA_B = Path("C:/Windows/Fonts/BIZ-UDGothicB.ttc")


def font(size: int, *, bold: bool = False, ko: bool = False) -> ImageFont.FreeTypeFont:
    path = (FONT_KO_B if bold else FONT_KO) if ko else (FONT_JA_B if bold else FONT_JA)
    return ImageFont.truetype(str(path), size=size)


def text_size(draw: ImageDraw.ImageDraw, value: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), value, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_chars(draw: ImageDraw.ImageDraw, value: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in str(value).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            probe = current + char
            if current and text_size(draw, probe, fnt)[0] > max_width:
                lines.append(current.rstrip())
                current = char.lstrip()
            else:
                current = probe
        if current:
            lines.append(current.rstrip())
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_gap: int = 12,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_chars(draw, value, fnt, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    line_height = text_size(draw, "한国Ag", fnt)[1] + line_gap
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_height
    return y


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def crop(path: Path, box: tuple[int, int, int, int]) -> Image.Image:
    return Image.open(path).convert("RGB").crop(box)


def fit_image(source: Image.Image, size: tuple[int, int], *, cover: bool = False) -> Image.Image:
    if cover:
        return ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
    result = Image.new("RGB", size, WHITE)
    copy = source.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    result.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return result


def paste_rounded(page: Image.Image, source: Image.Image, box: tuple[int, int, int, int], radius: int = 36, border: int = 6, border_color: str = NAVY, cover: bool = True) -> None:
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    fitted = fit_image(source, (width - border * 2, height - border * 2), cover=cover)
    mask = Image.new("L", fitted.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fitted.width, fitted.height), radius=max(1, radius - border), fill=255)
    frame = Image.new("RGB", (width, height), border_color)
    frame.paste(fitted, (border, border), mask)
    frame_mask = Image.new("L", frame.size, 0)
    ImageDraw.Draw(frame_mask).rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
    page.paste(frame, (x1, y1), frame_mask)


def paste_logo(page: Image.Image, box: tuple[int, int, int, int]) -> None:
    logo = Image.open(ROOT / "assets" / "sun_nishimura_logo.jpg").convert("RGB")
    logo = fit_image(logo, (box[2] - box[0], box[3] - box[1]))
    page.paste(logo, (box[0], box[1]))


def draw_step_badge(draw: ImageDraw.ImageDraw, center: tuple[int, int], number: int, *, ko: bool = False) -> None:
    x, y = center
    draw.ellipse((x - 58, y - 58, x + 58, y + 58), fill=NAVY)
    label = str(number)
    fnt = font(70, bold=True, ko=ko)
    tw, th = text_size(draw, label, fnt)
    draw.text((x - tw / 2, y - th / 2 - 8), label, font=fnt, fill=WHITE)


def draw_arrow(draw: ImageDraw.ImageDraw, y: int) -> None:
    x = PAGE_W // 2
    draw.polygon([(x - 40, y - 16), (x, y + 24), (x + 40, y - 16), (x + 24, y - 16), (x, y + 7), (x - 24, y - 16)], fill=NAVY)


def qr_matrix(value: str) -> list[list[bool]]:
    widget = qr.QrCodeWidget(value)
    widget.qr.make()
    return [[bool(cell) for cell in row] for row in widget.qr.modules]


def draw_qr(draw: ImageDraw.ImageDraw, value: str, box: tuple[int, int, int, int]) -> None:
    matrix = qr_matrix(value)
    count = len(matrix)
    x1, y1, x2, y2 = box
    side = min(x2 - x1, y2 - y1)
    quiet = 4
    cell = side / (count + quiet * 2)
    draw.rectangle((x1, y1, x1 + side, y1 + side), fill=WHITE)
    for row, cells in enumerate(matrix):
        for col, value_on in enumerate(cells):
            if value_on:
                left = x1 + (col + quiet) * cell
                top = y1 + (row + quiet) * cell
                draw.rectangle((left, top, left + cell + 0.5, top + cell + 0.5), fill="#000000")


def make_customer_final_visual() -> Image.Image:
    top = crop(SCREEN_DIR / "customer_04_receipt_full.png", (150, 10, 1110, 325))
    bottom = crop(SCREEN_DIR / "customer_04_number_full.png", (690, 545, 1090, 690))
    image = Image.new("RGB", (980, 500), WHITE)
    draw = ImageDraw.Draw(image)
    image.paste(fit_image(top, (940, 300), cover=True), (20, 15))
    rounded_rect(draw, (490, 330, 950, 480), 24, PALE_BLUE, BLUE, 4)
    image.paste(fit_image(bottom, (430, 120), cover=True), (505, 345))
    draw.line((430, 285, 510, 345), fill=BLUE, width=6)
    return image


def make_customer_manual() -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, PAGE_W, 24), fill=NAVY)
    paste_logo(page, (1940, 65, 2330, 185))

    draw.text((120, 88), "한국 전시회 주문 도구 간단 가이드", font=font(104, bold=True, ko=True), fill=NAVY)
    draw.text((122, 225), "스마트폰으로 4단계 - 접수 번호가 나오면 직원에게 보여 주세요", font=font(42, bold=True, ko=True), fill=INK)
    draw.line((120, 300, 2360, 300), fill=LINE, width=4)

    product = crop(SCREEN_DIR / "customer_01_product_full.png", (5, 64, 470, 416))
    cart = crop(SCREEN_DIR / "customer_02_cart_full.png", (870, 250, 1245, 675))
    info = crop(SCREEN_DIR / "customer_03_info_full.png", (265, 38, 990, 675))
    final = make_customer_final_visual()

    steps = [
        (product, "품번을 입력하고 ‘추가’", "주문할 상품의 품번 또는 상품명을 검색한 뒤, 상품 카드의 ‘추가’ 버튼을 눌러 주세요.", "상품 사진과 가격을 확인하면 더 안전합니다."),
        (cart, "수량 확인 후 ‘주문 절차로’", "장바구니에서 수량을 확인합니다. − / ＋ 로 수량을 바꾼 뒤 초록색 ‘주문 절차로’를 눌러 주세요.", "필요한 상품을 모두 넣은 뒤 진행하세요."),
        (info, "고객 정보 입력", "회사명, 이름, 전화번호를 입력합니다. 배송지 주소와 명함 사진은 선택 사항입니다.", "입력 후 아래의 ‘접수 번호 발급’을 누르세요."),
        (final, "접수 번호를 직원에게 보여주기", "‘접수 완료 · 직원 확인 대기’가 나오면 접수 완료입니다. 화면의 접수 번호를 가까운 직원에게 보여 주세요.", "직원이 주문 확정하기 전에는 ‘주문 내용 수정’으로 고칠 수 있습니다."),
    ]

    row_top = 340
    row_height = 605
    for idx, (visual, title, body, note) in enumerate(steps, start=1):
        y = row_top + (idx - 1) * row_height
        rounded_rect(draw, (90, y, 2390, y + 555), 38, "#fbfcfe", LINE, 4)
        paste_rounded(page, visual, (125, y + 35, 1050, y + 520), radius=42, border=10, cover=False)
        draw_step_badge(draw, (1175, y + 92), idx, ko=True)
        draw.text((1260, y + 40), title, font=font(57, bold=True, ko=True), fill=NAVY)
        end_y = draw_wrapped(draw, (1260, y + 135), body, font(35, ko=True), INK, 1035, line_gap=20)
        draw.line((1260, end_y + 10, 2265, end_y + 10), fill="#8fb5ea", width=4)
        draw.text((1260, end_y + 38), "TIP", font=font(25, bold=True, ko=True), fill=BLUE)
        draw_wrapped(draw, (1330, end_y + 33), note, font(29, ko=True), MUTED, 930, line_gap=14, max_lines=3)
        if idx < 4:
            draw_arrow(draw, y + 580)

    footer_y = 2785
    rounded_rect(draw, (90, footer_y, 1440, 3370), 38, PALE_BLUE, "#9cc3ff", 4)
    draw.text((135, footer_y + 45), "주문 확인서 이미지 저장", font=font(42, bold=True, ko=True), fill=NAVY)
    draw_wrapped(
        draw,
        (135, footer_y + 125),
        "이미지를 길게 누른 후 ‘사진에 저장’ 또는 ‘이미지 저장’을 선택하세요. 길게 누르기 메뉴가 나오지 않을 때만 아래쪽 화살표 또는 공유 버튼을 사용합니다.",
        font(30, ko=True),
        INK,
        1220,
        line_gap=18,
    )
    rounded_rect(draw, (135, footer_y + 350, 1395, footer_y + 515), 26, PALE_GREEN, "#7ad9b7", 3)
    draw.text((175, footer_y + 385), "접수 번호가 보이면 주문이 저장되었습니다", font=font(34, bold=True, ko=True), fill=GREEN)

    rounded_rect(draw, (1490, footer_y, 2390, 3370), 38, WHITE, BLUE, 5)
    draw.text((1535, footer_y + 45), "주문 도구 열기", font=font(45, bold=True, ko=True), fill=NAVY)
    draw.text((1535, footer_y + 115), "QR 코드를 스마트폰으로 읽어 주세요", font=font(27, ko=True), fill=INK)
    draw_qr(draw, "https://masuda8105-prog.github.io/tenjikai.korea2/", (1885, footer_y + 150, 2265, footer_y + 530))
    draw.text((1535, footer_y + 525), "현장에서 바로 주문할 수 있습니다", font=font(27, bold=True, ko=True), fill=BLUE)

    draw.text((PAGE_W // 2, 3440), "※ 화면 예시는 샘플입니다. 실제 상품과 금액은 선택 내용에 따라 달라집니다.", font=font(24, ko=True), fill=MUTED, anchor="mm")
    return page


def make_customer_final_visual_ja() -> Image.Image:
    top = crop(SCREEN_DIR / "customer_ja_04_receipt_full.png", (150, 10, 1110, 325))
    bottom = crop(SCREEN_DIR / "customer_ja_04_number_full.png", (690, 545, 1090, 690))
    image = Image.new("RGB", (980, 500), WHITE)
    draw = ImageDraw.Draw(image)
    image.paste(fit_image(top, (940, 300), cover=True), (20, 15))
    rounded_rect(draw, (490, 330, 950, 480), 24, PALE_BLUE, BLUE, 4)
    image.paste(fit_image(bottom, (430, 120), cover=True), (505, 345))
    draw.line((430, 285, 510, 345), fill=BLUE, width=6)
    return image


def make_customer_manual_ja() -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, PAGE_W, 24), fill=NAVY)
    paste_logo(page, (1940, 65, 2330, 185))

    draw.text((120, 88), "韓国展示会 注文ツール かんたんガイド", font=font(88, bold=True), fill=NAVY)
    draw.text((122, 225), "スマートフォンで4ステップ ― 受付番号が出たらスタッフへお見せください", font=font(36, bold=True), fill=INK)
    draw.line((120, 300, 2360, 300), fill=LINE, width=4)

    product = crop(SCREEN_DIR / "customer_ja_01_product_full.png", (5, 64, 470, 416))
    cart = crop(SCREEN_DIR / "customer_ja_02_cart_full.png", (870, 250, 1245, 675))
    info = crop(SCREEN_DIR / "customer_ja_03_info_full.png", (265, 38, 990, 675))
    final = make_customer_final_visual_ja()

    steps = [
        (product, "品番を入力して「追加」", "注文したい商品の品番または商品名を検索し、商品カードの「追加」を押します。", "商品画像と価格を確認すると安心です。"),
        (cart, "数量を確認して「注文手続きへ」", "カートで数量を確認します。− / ＋ で数量を変更し、緑色の「注文手続きへ」を押します。", "必要な商品をすべて追加してから進みます。"),
        (info, "お客様情報を入力", "会社名・氏名・電話番号を入力します。発送先住所と名刺写真は任意です。", "入力後、下の「受付番号を発行」を押します。"),
        (final, "受付番号をスタッフへ見せる", "「受付済み・スタッフ確認待ち」と表示されたら受付完了です。受付番号を近くのスタッフへお見せください。", "スタッフが注文確定するまでは「注文内容を修正」から変更できます。"),
    ]

    row_top = 340
    row_height = 605
    for idx, (visual, title, body, note) in enumerate(steps, start=1):
        y = row_top + (idx - 1) * row_height
        rounded_rect(draw, (90, y, 2390, y + 555), 38, "#fbfcfe", LINE, 4)
        paste_rounded(page, visual, (125, y + 35, 1050, y + 520), radius=42, border=10, cover=False)
        draw_step_badge(draw, (1175, y + 92), idx)
        draw.text((1260, y + 40), title, font=font(49, bold=True), fill=NAVY)
        end_y = draw_wrapped(draw, (1260, y + 135), body, font(32), INK, 1035, line_gap=20)
        draw.line((1260, end_y + 10, 2265, end_y + 10), fill="#8fb5ea", width=4)
        draw.text((1260, end_y + 38), "ポイント", font=font(23, bold=True), fill=BLUE)
        draw_wrapped(draw, (1400, end_y + 33), note, font(27), MUTED, 860, line_gap=14, max_lines=3)
        if idx < 4:
            draw_arrow(draw, y + 580)

    footer_y = 2785
    rounded_rect(draw, (90, footer_y, 1440, 3370), 38, PALE_BLUE, "#9cc3ff", 4)
    draw.text((135, footer_y + 45), "お客様控えを保存", font=font(42, bold=True), fill=NAVY)
    draw_wrapped(
        draw,
        (135, footer_y + 125),
        "控え画像を長押しし、「写真に保存」または「画像を保存」を選びます。長押しメニューが出ない場合だけ、下向き矢印または共有ボタンを使います。",
        font(29),
        INK,
        1220,
        line_gap=18,
    )
    rounded_rect(draw, (135, footer_y + 350, 1395, footer_y + 515), 26, PALE_GREEN, "#7ad9b7", 3)
    draw.text((175, footer_y + 385), "受付番号が表示されれば注文は保存済みです", font=font(32, bold=True), fill=GREEN)

    rounded_rect(draw, (1490, footer_y, 2390, 3370), 38, WHITE, BLUE, 5)
    draw.text((1535, footer_y + 45), "注文ツールを開く", font=font(43, bold=True), fill=NAVY)
    draw.text((1535, footer_y + 115), "QRコードをスマートフォンで読み取ってください", font=font(25), fill=INK)
    draw_qr(draw, "https://masuda8105-prog.github.io/tenjikai.korea2/", (1885, footer_y + 150, 2265, footer_y + 530))
    draw.text((1535, footer_y + 525), "会場ですぐに注文できます", font=font(27, bold=True), fill=BLUE)

    draw.text((PAGE_W // 2, 3440), "※ 画面はサンプルです。実際の商品・金額は選択内容により変わります。", font=font(24), fill=MUTED, anchor="mm")
    return page


def mock_staff_dashboard() -> Image.Image:
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 82), fill=NAVY)
    draw.text((34, 23), "SAN NISHIMURA  韓国展示会 注文管理", font=font(28, bold=True), fill=WHITE)
    draw.text((1350, 24), "● 最新情報  メニュー", font=font(20, bold=True), fill="#d8e4f2")

    draw.text((40, 112), "注文対応", font=font(34, bold=True), fill=INK)
    draw.text((40, 158), "基本は「確認待ち」と「確認中」を操作します", font=font(20), fill=MUTED)
    rounded_rect(draw, (40, 205, 760, 290), 20, NAVY)
    draw.text((70, 225), "未着手の注文", font=font(16), fill="#cbd5e1")
    draw.text((70, 250), "① 確認待ち", font=font(25, bold=True), fill=WHITE)
    draw.ellipse((680, 225, 735, 280), fill=WHITE)
    draw.text((707, 252), "2", font=font(24, bold=True), fill=NAVY, anchor="mm")
    rounded_rect(draw, (780, 205, 1500, 290), 20, WHITE, LINE, 3)
    draw.text((810, 225), "対応中の注文", font=font(16), fill=MUTED)
    draw.text((810, 250), "② 確認中", font=font(25, bold=True), fill=INK)
    draw.ellipse((1420, 225, 1475, 280), fill="#eef2f7")
    draw.text((1447, 252), "1", font=font(24, bold=True), fill=INK, anchor="mm")

    rounded_rect(draw, (40, 320, 760, 615), 24, "#f8fafc", LINE, 3)
    draw.text((70, 345), "① 確認待ち", font=font(26, bold=True), fill=INK)
    rounded_rect(draw, (70, 405, 730, 570), 20, WHITE, LINE, 3)
    draw.rectangle((70, 405, 80, 570), fill="#dc2626")
    draw.text((105, 430), "K260804-001", font=font(24, bold=True), fill=INK)
    rounded_rect(draw, (560, 425, 690, 468), 20, "#fee2e2")
    draw.text((625, 446), "確認待ち", font=font(17, bold=True), fill="#991b1b", anchor="mm")
    draw.text((105, 485), "サンプル眼鏡店　金様", font=font(24, bold=True), fill=INK)
    draw.text((105, 530), "11:30  ·  2点  ·  KRW 166,600", font=font(18), fill=MUTED)

    rounded_rect(draw, (780, 320, 1500, 615), 24, "#f8fafc", LINE, 3)
    draw.text((810, 345), "② 確認中", font=font(26, bold=True), fill=INK)
    rounded_rect(draw, (810, 405, 1470, 570), 20, WHITE, LINE, 3)
    draw.rectangle((810, 405, 820, 570), fill=ORANGE)
    draw.text((845, 430), "K260804-002", font=font(24, bold=True), fill=INK)
    rounded_rect(draw, (1300, 425, 1435, 468), 20, "#ffedd5")
    draw.text((1367, 446), "確認中", font=font(17, bold=True), fill="#9a3412", anchor="mm")
    draw.text((845, 485), "テストオプティカル　李様", font=font(24, bold=True), fill=INK)
    draw.text((845, 530), "担当：増田  ·  1点  ·  KRW 83,300", font=font(18), fill=MUTED)

    rounded_rect(draw, (40, 650, 1500, 850), 24, WHITE, LINE, 3)
    draw.text((70, 680), "注文確定分", font=font(27, bold=True), fill=INK)
    rounded_rect(draw, (1120, 670, 1460, 735), 18, GREEN)
    draw.text((1290, 702), "確定注文をまとめて送る", font=font(20, bold=True), fill=WHITE, anchor="mm")
    draw.line((70, 755, 1460, 755), fill=LINE, width=3)
    draw.text((90, 780), "11:20", font=font(19), fill=MUTED)
    draw.text((260, 780), "ABC眼鏡店", font=font(19, bold=True), fill=INK)
    draw.text((650, 780), "増田", font=font(19), fill=INK)
    draw.text((970, 780), "K260804-003", font=font(19, bold=True), fill=INK)
    return image


def mock_staff_detail() -> Image.Image:
    image = Image.new("RGB", (1600, 980), "#475569")
    draw = ImageDraw.Draw(image)
    rounded_rect(draw, (70, 45, 1530, 935), 28, WHITE)
    draw.text((110, 80), "注文詳細  K260804-001", font=font(32, bold=True), fill=INK)
    rounded_rect(draw, (1390, 70, 1485, 120), 15, WHITE, LINE, 3)
    draw.text((1437, 95), "閉じる", font=font(17, bold=True), fill=INK, anchor="mm")
    draw.line((70, 145, 1530, 145), fill=LINE, width=3)

    rounded_rect(draw, (110, 180, 700, 745), 22, WHITE, LINE, 3)
    draw.text((140, 205), "お客様情報", font=font(25, bold=True), fill=INK)
    labels = [("会社名", "サンプル眼鏡店"), ("氏名", "金 民洙"), ("電話番号", "010-1234-5678"), ("発送先住所", "Seoul, Korea")]
    y = 265
    for label, value in labels:
        rounded_rect(draw, (140, y, 670, y + 78), 14, "#f8fafc")
        draw.text((160, y + 10), label, font=font(15, bold=True), fill=MUTED)
        draw.text((160, y + 36), value, font=font(20, bold=True), fill=INK)
        y += 92
    draw.text((140, 640), "名刺", font=font(20, bold=True), fill=INK)
    rounded_rect(draw, (230, 630, 590, 715), 12, PALE_BLUE, "#9cc3ff", 2)
    draw.text((410, 672), "名刺画像をここで確認", font=font(19, bold=True), fill=BLUE, anchor="mm")

    rounded_rect(draw, (730, 180, 1490, 745), 22, WHITE, LINE, 3)
    draw.text((760, 205), "注文明細", font=font(25, bold=True), fill=INK)
    draw.rectangle((760, 260, 1460, 315), fill="#f1f5f9")
    draw.text((785, 275), "商品", font=font(17, bold=True), fill=MUTED)
    draw.text((1130, 275), "数量", font=font(17, bold=True), fill=MUTED)
    draw.text((1340, 275), "金額", font=font(17, bold=True), fill=MUTED)
    product_path = ROOT / "product-images" / "1053_1.jpg"
    if product_path.exists():
        product = fit_image(Image.open(product_path).convert("RGB"), (110, 110))
        image.paste(product, (780, 345))
    draw.text((915, 355), "1053", font=font(24, bold=True), fill=INK)
    draw.text((915, 397), "プッシュロックパッド調整プライヤー", font=font(18), fill=INK)
    rounded_rect(draw, (1100, 355, 1160, 420), 12, "#eef2f7")
    draw.text((1130, 387), "−", font=font(25, bold=True), fill=INK, anchor="mm")
    rounded_rect(draw, (1170, 355, 1245, 420), 12, WHITE, LINE, 2)
    draw.text((1207, 387), "2", font=font(23, bold=True), fill=INK, anchor="mm")
    rounded_rect(draw, (1255, 355, 1315, 420), 12, "#eef2f7")
    draw.text((1285, 387), "+", font=font(25, bold=True), fill=INK, anchor="mm")
    draw.text((1330, 375), "KRW 166,600", font=font(18, bold=True), fill=INK)
    draw.line((760, 490, 1460, 490), fill=LINE, width=3)
    draw.text((1140, 525), "合計", font=font(23, bold=True), fill=INK)
    draw.text((1300, 525), "KRW 166,600", font=font(21, bold=True), fill=INK)
    rounded_rect(draw, (1160, 625, 1460, 690), 16, NAVY)
    draw.text((1310, 658), "変更を保存", font=font(21, bold=True), fill=WHITE, anchor="mm")

    draw.line((70, 780, 1530, 780), fill=LINE, width=3)
    rounded_rect(draw, (110, 815, 370, 885), 18, PALE_ORANGE, "#fdba74", 3)
    draw.text((240, 850), "確認を始める", font=font(22, bold=True), fill=ORANGE, anchor="mm")
    rounded_rect(draw, (390, 815, 650, 885), 18, "#dcfce7", "#86efac", 3)
    draw.text((520, 850), "注文確定", font=font(22, bold=True), fill="#166534", anchor="mm")
    rounded_rect(draw, (1020, 825, 1200, 875), 15, "#f8fafc", LINE, 2)
    draw.text((1110, 850), "お客様用QR", font=font(17, bold=True), fill=MUTED, anchor="mm")
    rounded_rect(draw, (1220, 825, 1375, 875), 15, "#f8fafc", LINE, 2)
    draw.text((1297, 850), "注文書", font=font(17, bold=True), fill=MUTED, anchor="mm")
    rounded_rect(draw, (1395, 825, 1490, 875), 15, "#fff1f0", "#fda29b", 2)
    draw.text((1442, 850), "削除", font=font(17, bold=True), fill=RED, anchor="mm")
    return image


def mock_batch_dialog() -> Image.Image:
    image = Image.new("RGB", (1600, 1100), "#475569")
    draw = ImageDraw.Draw(image)
    rounded_rect(draw, (115, 45, 1485, 1055), 30, WHITE)
    draw.text((160, 85), "代理店へまとめて送る", font=font(34, bold=True), fill=INK)
    draw.text((160, 140), "PDFを保存 → メールへ添付して送信 → 送付済みにする", font=font(21, bold=True), fill=ORANGE)
    summary = [("対象日", "2026-08-04"), ("送信対象", "2件"), ("合計数量", "42点"), ("合計金額", "KRW 1,571,300")]
    x = 160
    for label, value in summary:
        rounded_rect(draw, (x, 205, x + 290, 305), 16, "#f8fafc")
        draw.text((x + 20, 225), label, font=font(15, bold=True), fill=MUTED)
        draw.text((x + 20, 258), value, font=font(19, bold=True), fill=INK)
        x += 310

    blocks = [
        (365, "① 注文PDFを作成", "注文PDFを作成・保存", NAVY, "印刷画面で『PDFに保存』を選びます。"),
        (555, "② メールを作成", "メール本文を開く", WHITE, "保存したPDFをメールへ添付して送信します。"),
        (745, "③ 送信後に完了登録", "代理店送付済みにする", "#dcfce7", "メール送信が終わってから押します。"),
    ]
    for y, title, button, color, note in blocks:
        draw.text((165, y), title, font=font(25, bold=True), fill=INK)
        outline = LINE if color == WHITE else None
        rounded_rect(draw, (165, y + 50, 650, y + 125), 17, color, outline, 3)
        button_fill = INK if color == WHITE else ("#166534" if color == "#dcfce7" else WHITE)
        draw.text((407, y + 87), button, font=font(20, bold=True), fill=button_fill, anchor="mm")
        draw_wrapped(draw, (700, y + 55), note, font(19), MUTED, 680, line_gap=10, max_lines=2)
    draw.text((165, 955), "□ PDFを保存しました　　□ PDFをメールへ添付して送信しました", font=font(20, bold=True), fill=INK)
    return image


def make_capability_overview() -> Image.Image:
    page = Image.new("RGB", (LANDSCAPE_W, LANDSCAPE_H), WHITE)
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, LANDSCAPE_W, 22), fill=NAVY)
    paste_logo(page, (2940, 50, 3390, 180))
    draw.text((90, 62), "韓国展示会 注文ツールでできること", font=font(76, bold=True), fill=NAVY)
    draw.text((94, 176), "お客様の受付から、スタッフ確認、その日の注文PDF送付までをひとつにつなぎます", font=font(32, bold=True), fill=INK)
    draw.line((90, 250, 3418, 250), fill=LINE, width=4)

    scene = Image.open(SCENE_DIR / "exhibition_order_workflow_triptych.png").convert("RGB")
    thirds = [
        scene.crop((0, 0, scene.width // 3, scene.height)),
        scene.crop((scene.width // 3, 0, scene.width * 2 // 3, scene.height)),
        scene.crop((scene.width * 2 // 3, 0, scene.width, scene.height)),
    ]
    customer_ui = crop(SCREEN_DIR / "customer_ja_04_receipt_full.png", (115, 8, 1115, 430))
    staff_ui = mock_staff_detail()
    batch_ui = mock_batch_dialog()

    columns = [
        {
            "x": 70,
            "number": 1,
            "title": "お客様",
            "lead": "スマホで価格確認から受付まで",
            "accent": BLUE,
            "pale": PALE_BLUE,
            "ui": customer_ui,
            "ui_box": (615, 750, 1120, 1195),
            "bullets": [
                "商品の価格を確認",
                "注文する場合は「受付番号を発行」",
                "受付番号をスタッフへ提示",
                "お客様控えを画像で保存",
            ],
            "outcome": "受付番号が出たら受付完了。注文確定前なら内容を修正できます。",
        },
        {
            "x": 1213,
            "number": 2,
            "title": "スタッフ",
            "lead": "お客様と一緒に内容確認・注文確定",
            "accent": ORANGE,
            "pale": PALE_ORANGE,
            "ui": staff_ui,
            "ui_box": (1755, 750, 2263, 1195),
            "bullets": [
                "専用サイトで受付番号を確認",
                "「確認を始める」を押す",
                "お客様と商品・数量・情報を確認",
                "必要なら修正して「注文確定」",
            ],
            "outcome": "受付番号から該当注文へ。お客様と同じ最新内容を確認できます。",
        },
        {
            "x": 2356,
            "number": 3,
            "title": "展示会終了後",
            "lead": "その日の確定注文をまとめて送付",
            "accent": GREEN,
            "pale": PALE_GREEN,
            "ui": batch_ui,
            "ui_box": (2898, 750, 3405, 1195),
            "bullets": [
                "対象日を選び、注文確定分を表示",
                "その日の注文をまとめてPDF化",
                "PDFをメールへ添付",
                "孫さんへメール送付",
            ],
            "outcome": "日付別にまとめるため、複数日の展示会でも注文が混ざりません。",
        },
    ]

    col_width = 1082
    scene_top = 300
    scene_bottom = 1240
    text_top = 1285
    text_bottom = 2135
    for index, data in enumerate(columns):
        x = data["x"]
        scene_panel = thirds[index]
        paste_rounded(page, scene_panel, (x, scene_top, x + col_width, scene_bottom), radius=34, border=7, border_color=data["accent"], cover=True)

        overlay = Image.new("RGBA", (col_width - 14, 185), (16, 36, 62, 220))
        overlay_mask = Image.new("L", overlay.size, 0)
        ImageDraw.Draw(overlay_mask).rounded_rectangle((0, 0, overlay.width, overlay.height), radius=28, fill=255)
        page.paste(overlay.convert("RGB"), (x + 7, scene_top + 7), overlay_mask)
        draw.ellipse((x + 35, scene_top + 35, x + 137, scene_top + 137), fill=data["accent"])
        draw.text((x + 86, scene_top + 86), str(data["number"]), font=font(48, bold=True), fill=WHITE, anchor="mm")
        draw.text((x + 165, scene_top + 34), data["title"], font=font(44, bold=True), fill=WHITE)
        draw.text((x + 165, scene_top + 100), data["lead"], font=font(25, bold=True), fill="#e7eef8")

        paste_rounded(page, data["ui"], data["ui_box"], radius=24, border=8, border_color=WHITE, cover=False)

        rounded_rect(draw, (x, text_top, x + col_width, text_bottom), 34, data["pale"], data["accent"], 4)
        draw.text((x + 45, text_top + 45), f"{data['number']}. {data['title']}の流れ", font=font(38, bold=True), fill=data["accent"])
        y = text_top + 135
        for bullet_index, bullet in enumerate(data["bullets"], start=1):
            draw.ellipse((x + 48, y + 3, x + 103, y + 58), fill=WHITE, outline=data["accent"], width=3)
            draw.text((x + 75, y + 30), str(bullet_index), font=font(23, bold=True), fill=data["accent"], anchor="mm")
            y = draw_wrapped(draw, (x + 125, y), bullet, font(29, bold=True), INK, col_width - 175, line_gap=12, max_lines=2) + 32
        rounded_rect(draw, (x + 42, text_bottom - 205, x + col_width - 42, text_bottom - 45), 24, WHITE, data["accent"], 3)
        draw.text((x + 75, text_bottom - 175), "安心ポイント", font=font(23, bold=True), fill=data["accent"])
        draw_wrapped(draw, (x + 75, text_bottom - 125), data["outcome"], font(25, bold=True), INK, col_width - 150, line_gap=10, max_lines=2)

    rounded_rect(draw, (70, 2185, 3438, 2395), 34, NAVY)
    flow_labels = ["お客様受付", "スタッフ確認", "注文確定", "日付別PDF", "メール送付"]
    flow_x = 145
    for index, label in enumerate(flow_labels):
        rounded_rect(draw, (flow_x, 2233, flow_x + 500, 2345), 25, WHITE)
        draw.text((flow_x + 250, 2289), label, font=font(29, bold=True), fill=NAVY, anchor="mm")
        if index < len(flow_labels) - 1:
            draw.polygon([(flow_x + 535, 2262), (flow_x + 590, 2289), (flow_x + 535, 2316)], fill="#8fb5ea")
        flow_x += 650

    draw.text((LANDSCAPE_W // 2, 2440), "受付番号は変わらず、スタッフはいつでも最新の注文内容を確認できます。　※ 掲載画面・人物は利用イメージです。", font=font(22), fill=MUTED, anchor="mm")
    return page


def draw_header(page: Image.Image, title: str, subtitle: str, page_label: str) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, PAGE_W, 24), fill=NAVY)
    paste_logo(page, (1940, 65, 2330, 185))
    draw.text((120, 82), title, font=font(78, bold=True), fill=NAVY)
    draw.text((122, 195), subtitle, font=font(34, bold=True), fill=INK)
    draw.text((2325, 230), page_label, font=font(24, bold=True), fill=MUTED, anchor="ra")
    draw.line((120, 280, 2360, 280), fill=LINE, width=4)
    return draw


def numbered_text(draw: ImageDraw.ImageDraw, x: int, y: int, number: int, title: str, body: str, width: int) -> int:
    draw.ellipse((x, y, x + 68, y + 68), fill=NAVY)
    draw.text((x + 34, y + 34), str(number), font=font(34, bold=True), fill=WHITE, anchor="mm")
    draw.text((x + 92, y - 2), title, font=font(35, bold=True), fill=NAVY)
    return draw_wrapped(draw, (x + 92, y + 52), body, font(30), INK, width - 92, line_gap=16)


def make_staff_manual_page1() -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
    draw = draw_header(page, "韓国展示会 スタッフ簡易マニュアル", "基本操作：確認待ち → 確認中 → 注文確定", "1 / 2")

    rounded_rect(draw, (100, 325, 2380, 535), 34, PALE_BLUE, "#9cc3ff", 4)
    draw.text((145, 365), "まず覚えるのは2画面だけ", font=font(42, bold=True), fill=NAVY)
    draw.text((145, 435), "① 確認待ちの注文を開く　　② 内容を確認して注文確定", font=font(35, bold=True), fill=INK)

    login = crop(SCREEN_DIR / "staff_00_login_full.png", (380, 85, 900, 625))
    paste_rounded(page, login, (110, 600, 790, 1160), radius=38, border=8)
    draw.text((835, 620), "開場前：スタッフログイン", font=font(42, bold=True), fill=NAVY)
    draw_wrapped(draw, (835, 700), "登録済みのメールアドレスとパスワードでログインします。右上に自分の名前が表示されれば準備完了です。", font(30), INK, 1450, line_gap=20)
    rounded_rect(draw, (835, 905, 2260, 1100), 28, PALE_GREEN, "#7ad9b7", 3)
    draw.text((880, 945), "開場前テスト", font=font(30, bold=True), fill=GREEN)
    draw.text((880, 1005), "テスト注文を1件送り、10秒以内に表示されることを確認", font=font(27, bold=True), fill=INK)

    dashboard = mock_staff_dashboard()
    paste_rounded(page, dashboard, (110, 1240, 1540, 2050), radius=34, border=8)
    numbered_text(draw, 1600, 1270, 1, "確認待ちを開く", "お客様の受付番号・会社名を確認し、注文カードをタップします。基本は『確認待ち』と『確認中』だけを見れば大丈夫です。", 700)
    numbered_text(draw, 1600, 1595, 2, "確認を始める", "注文詳細の『確認を始める』を押すと『確認中』へ移ります。編集中は自動更新で入力内容が消えません。", 700)
    rounded_rect(draw, (1600, 1900, 2290, 2015), 22, PALE_ORANGE, "#fdba74", 3)
    draw.text((1945, 1957), "基本操作はこの2列だけ", font=font(29, bold=True), fill=ORANGE, anchor="mm")

    detail = mock_staff_detail()
    paste_rounded(page, detail, (110, 2160, 1540, 3040), radius=34, border=8)
    numbered_text(draw, 1600, 2200, 3, "内容を確認・必要なら修正", "会社名・氏名・電話番号・発送先・名刺・品番・数量・金額を確認します。修正した場合は先に『変更を保存』を押します。", 700)
    numbered_text(draw, 1600, 2580, 4, "注文確定", "確認が終わったら緑色の『注文確定』を押します。注文は画面下の『注文確定分』へ移り、いつでも確認できます。", 700)

    rounded_rect(draw, (110, 3130, 2370, 3385), 34, "#fff8e8", "#f5c451", 4)
    draw.text((155, 3170), "重要", font=font(32, bold=True), fill=ORANGE)
    draw.text((300, 3170), "修正後は『変更を保存』→『注文確定』の順", font=font(34, bold=True), fill=INK)
    draw.text((300, 3240), "QRを渡す場合も、保存後に『お客様用QR』を表示してください。", font=font(28), fill=INK)
    draw.text((PAGE_W - 120, 3445), "SAN NISHIMURA  Korea Exhibition Staff Guide", font=font(20), fill=MUTED, anchor="ra")
    return page


def make_staff_manual_page2() -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
    draw = draw_header(page, "韓国展示会 スタッフ簡易マニュアル", "注文確定分を日付ごとにまとめて代理店へ送る", "2 / 2")

    rounded_rect(draw, (100, 330, 2380, 590), 34, PALE_GREEN, "#7ad9b7", 4)
    draw.text((145, 370), "一括送付の順番", font=font(42, bold=True), fill=GREEN)
    draw.text((145, 450), "対象日を選ぶ → PDF保存 → メール添付・送信 → 送付済みにする", font=font(34, bold=True), fill=INK)

    batch = mock_batch_dialog()
    paste_rounded(page, batch, (110, 670, 1500, 1640), radius=34, border=8)
    numbered_text(draw, 1570, 720, 1, "対象日を選ぶ", "展示会が複数日にまたがる場合は、送る日付を必ず1日選びます。『確定注文をまとめて送る』を押します。", 760)
    numbered_text(draw, 1570, 1040, 2, "PDFを保存", "『注文PDFを作成・保存』を押し、印刷画面の送信先で『PDFに保存』を選びます。", 760)
    numbered_text(draw, 1570, 1330, 3, "メール送信後に完了", "メール本文を開き、PDFを添付して送信します。送信が終わってから『代理店送付済みにする』を押します。", 760)

    draw.text((110, 1770), "現場でよく使う補助操作", font=font(48, bold=True), fill=NAVY)
    cards = [
        (110, "QRを読み取ったとき", "ログイン後、該当注文が直接開きます。修正後もQRは変わらず、常に最新データを表示します。", BLUE, PALE_BLUE),
        (870, "注文を削除するとき", "『削除履歴へ』を使い、理由を選択します。データは消えず、削除履歴から復元できます。", RED, "#fff1f0"),
        (1630, "送付済み注文を修正", "修正理由を入力して保存すると『修正版・再送待ち』になります。次回の一括送付に含めます。", ORANGE, PALE_ORANGE),
    ]
    for x, title, body, accent, fill in cards:
        rounded_rect(draw, (x, 1850, x + 700, 2310), 30, fill, accent, 4)
        draw.rectangle((x, 1850, x + 18, 2310), fill=accent)
        draw.text((x + 48, 1900), title, font=font(31, bold=True), fill=accent)
        draw_wrapped(draw, (x + 48, 1980), body, font(25), INK, 600, line_gap=18)

    draw.text((110, 2425), "困ったとき", font=font(48, bold=True), fill=NAVY)
    trouble = [
        ("10秒ごとの自動更新", "Realtimeが切れていますが運用できます。必要なら『最新情報に更新』を押します。"),
        ("入力中に新着注文が来た", "編集中の内容は保持されます。焦らず、現在の注文を保存してから次へ進みます。"),
        ("別スタッフが先に更新", "競合メッセージが出たら、最新内容を読み込み直して再確認します。"),
        ("メール送信前", "先に『代理店送付済みにする』を押さないでください。"),
    ]
    y = 2520
    for title, body in trouble:
        rounded_rect(draw, (110, y, 2370, y + 150), 22, "#f8fafc", LINE, 2)
        draw.text((155, y + 32), title, font=font(28, bold=True), fill=INK)
        draw_wrapped(draw, (650, y + 30), body, font(24), MUTED, 1640, line_gap=12, max_lines=2)
        y += 175

    rounded_rect(draw, (110, 3240, 2370, 3385), 28, NAVY)
    draw.text((PAGE_W // 2, 3310), "迷ったら：注文カードを閉じず、近くの担当者へ確認してください", font=font(31, bold=True), fill=WHITE, anchor="mm")
    draw.text((PAGE_W - 120, 3445), "SAN NISHIMURA  Korea Exhibition Staff Guide", font=font(20), fill=MUTED, anchor="ra")
    return page


def write_pdf(pages: Iterable[Image.Image], path: Path, *, page_size: tuple[float, float] = A4) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = ROOT / "tmp" / "pdfs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=page_size)
    page_w, page_h = page_size
    temp_paths: list[Path] = []
    try:
        for index, page in enumerate(pages, start=1):
            temp = temp_dir / f"{path.stem}_page_{index}.png"
            page.save(temp, quality=95)
            temp_paths.append(temp)
            pdf.drawImage(str(temp), 0, 0, width=page_w, height=page_h, preserveAspectRatio=True, mask="auto")
            pdf.showPage()
        pdf.save()
    finally:
        for temp in temp_paths:
            temp.unlink(missing_ok=True)


def write_pdf_or_keep_open_file(pages: Iterable[Image.Image], path: Path, *, page_size: tuple[float, float] = A4) -> None:
    try:
        write_pdf(pages, path, page_size=page_size)
    except PermissionError:
        if not path.exists():
            raise
        print(f"WARNING: PDF is open and was kept unchanged: {path}")


def main() -> None:
    required = [
        SCREEN_DIR / "customer_01_product_full.png",
        SCREEN_DIR / "customer_02_cart_full.png",
        SCREEN_DIR / "customer_03_info_full.png",
        SCREEN_DIR / "customer_04_receipt_full.png",
        SCREEN_DIR / "customer_04_number_full.png",
        SCREEN_DIR / "customer_ja_01_product_full.png",
        SCREEN_DIR / "customer_ja_02_cart_full.png",
        SCREEN_DIR / "customer_ja_03_info_full.png",
        SCREEN_DIR / "customer_ja_04_receipt_full.png",
        SCREEN_DIR / "customer_ja_04_number_full.png",
        SCREEN_DIR / "staff_00_login_full.png",
        SCENE_DIR / "exhibition_order_workflow_triptych.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing manual screen capture(s):\n" + "\n".join(missing))

    OUT_PDF.mkdir(parents=True, exist_ok=True)
    OUT_IMG.mkdir(parents=True, exist_ok=True)

    customer = make_customer_manual()
    customer_ja = make_customer_manual_ja()
    staff_pages = [make_staff_manual_page1(), make_staff_manual_page2()]
    capability = make_capability_overview()

    customer_png = OUT_IMG / "韓国展示会_お客様用かんたんガイド_KO.png"
    customer_pdf = OUT_PDF / "韓国展示会_お客様用かんたんガイド_KO.pdf"
    customer.save(customer_png, optimize=True)
    write_pdf_or_keep_open_file([customer], customer_pdf)

    customer_ja_png = OUT_IMG / "韓国展示会_お客様用かんたんガイド_JA.png"
    customer_ja_pdf = OUT_PDF / "韓国展示会_お客様用かんたんガイド_JA.pdf"
    customer_ja.save(customer_ja_png, optimize=True)
    write_pdf_or_keep_open_file([customer_ja], customer_ja_pdf)

    staff_pngs = []
    for index, page in enumerate(staff_pages, start=1):
        staff_png = OUT_IMG / f"韓国展示会_スタッフ簡易マニュアル_{index}.png"
        page.save(staff_png, optimize=True)
        staff_pngs.append(staff_png)
    staff_pdf = OUT_PDF / "韓国展示会_スタッフ簡易マニュアル.pdf"
    write_pdf_or_keep_open_file(staff_pages, staff_pdf)

    capability_png = OUT_IMG / "韓国展示会_注文ツールでできること.png"
    capability_pdf = OUT_PDF / "韓国展示会_注文ツールでできること.pdf"
    capability.save(capability_png, optimize=True)
    write_pdf_or_keep_open_file([capability], capability_pdf, page_size=landscape(A4))

    print(customer_pdf)
    print(customer_png)
    print(customer_ja_pdf)
    print(customer_ja_png)
    print(staff_pdf)
    for path in staff_pngs:
        print(path)
    print(capability_pdf)
    print(capability_png)


if __name__ == "__main__":
    main()
