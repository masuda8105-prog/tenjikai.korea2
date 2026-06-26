# Sannishimura Exhibition Order - Multilingual QR Receipt

展示会場で、代理店スタッフが商品を検索し、画像・説明・価格を見せながら仮注文を作成し、QRコードで注文控えを渡すための静的Webアプリです。

## 今回の追加内容

- 商品マスターCSVの自動読み込み
- 日本語 / 英語 / 韓国語 / 中国語の言語切替
- 商品画像表示
- 商品詳細モーダル
- 商品説明の表示
- QR控えPDFにも商品説明を表示
- 価格ありPDF / 価格なしPDF切替
- メール・電話番号・LINEを聞かない設計

## ファイル構成

```text
index.html
product_master_multilingual.csv
sample_products.csv
images/products/
AGENTS.md
README.md
```

## 使い方

1. `index.html` をブラウザで開きます。
2. `product_master_multilingual.csv` が同じフォルダにあれば自動で読み込まれます。
3. 商品画像を入れる場合は `images/products/品番.jpg` で保存します。
4. アプリ上部の表示言語を切り替えると、商品名・説明・画面文言が切り替わります。
5. 商品をカートに追加し、`QR控えを作成` を押すとQRコードが表示されます。
6. お客様がQRを読み込むと、注文控えページを開いてPDF保存できます。

## CSV列名

現在のCSVは以下の列に対応しています。

```text
品番
商品名_JA
一言要約_JA
商品名_EN
一言要約_EN
商品名_ZH
一言要約_ZH
商品名_KO
一言要約_KO
卸価格
カタログ参照
要約タイプ
PDF抽出メモ
```

画像を表示したい場合は、CSVに以下のどちらかを追加すると確実です。

```text
画像ファイル名
画像URL
```

例：

```csv
品番,商品名_JA,一言要約_JA,商品名_EN,一言要約_EN,商品名_ZH,一言要約_ZH,商品名_KO,一言要約_KO,卸価格,画像ファイル名
1053,埋込・ワンタッチ兼用ヤットコ,特殊な鼻パッドを安全に調整できます。,Pliers for push-in nose pads,Helps adjust special nose pad parts safely.,插入式鼻托用钳,用于安全调整特殊鼻托部件。,삽입식 코패드용 플라이어,특수 코패드 부품을 안전하게 조정할 수 있습니다.,120000,1053.jpg
```

CSVに画像列がない場合でも、アプリは自動で以下の画像を探します。

```text
images/products/<品番>.jpg
```

例：

```text
images/products/1053.jpg
images/products/0756-01.jpg
images/products/141-503.jpg
```

## GitHub Pagesに反映する方法

既存の `refactored-fortnight` リポジトリに以下をアップロードしてください。

```text
index.html
product_master_multilingual.csv
images/products/ 商品画像一式
```

`index.html` と `product_master_multilingual.csv` は同じ階層に置いてください。

## 重要な注意点

この試作版は完全静的版です。QRコードの中に注文データを入れているため、サーバーなしで動きます。

ただし本番運用では、注文点数が多い場合や安全性を高めたい場合、以下の方式がおすすめです。

```text
QRコード = ランダムな短い控えURL
注文データ = サーバー側に保存
有効期限 = 7日〜30日
```

今回の版は、展示会場で「操作感」「言語切替」「商品画像と説明の見え方」「QR控えの流れ」を確認するための実用試作です。


## v0.3 商品画像ZIP対応

`product-images.zip` を展開して、`product-images/` フォルダを同梱しました。画像ファイルは主に `品番_1.jpg` 形式です。

- 画像枚数: 2,753枚
- 商品マスターCSVと品番一致: 2719件
- CSVには `画像ファイル名` 列を追加済み
- 画像の自動探索順: `product-images/品番_1.jpg` → `product-images/品番.jpg` → `images/products/品番_1.jpg` → `images/products/品番.jpg`

GitHub Pagesへ反映するときは、以下を同じ階層に置いてください。

```text
index.html
product_master_multilingual.csv
product-images/
```

## v0.4 UI/Search Update

- Header simplified to total amount only, with a compact language selector.
- Removed visible product count from search area.
- Keypad changed to a smaller 3-column phone-style layout.
- Product search now prioritizes exact code matches, then prefix matches, partial code matches, and keyword matches.
- Search results show match badges: 完全一致 / 前方一致 / 部分一致 / キーワード.


## v0.6 更新内容

- パーツ商品の「入数」表示に対応しました。
- CSVに `入数` / `入り数` / `内容量` / `袋入数` / `包装入数` / `販売単位` / `注文単位` / `pack_qty` / `pieces_per_pack` などの列がある場合、自動で読み込みます。
- 商品一覧、商品詳細、カート、QR控えPDF、履歴CSVに入数が表示されます。
- `20` のように数字だけ入れた場合、表示言語に合わせて `20個入` / `20 pcs/pack` / `20개입` / `20个/包` と整形します。
- `1袋20個` や `20 pcs` のように文字入りで入力した場合は、そのまま表示します。

### 推奨CSV列

```csv
品番,商品名_JA,一言要約_JA,商品名_EN,一言要約_EN,商品名_ZH,一言要約_ZH,商品名_KO,一言要約_KO,卸価格,入数,画像ファイル名
141-503,シリコン鼻パッド 最柔タイプ,やわらかく鼻あたりを軽減しやすいシリコンパッドです。,Extra soft silicone nose pads,Soft silicone nose pads that help reduce pressure on the nose.,超软硅胶鼻托,柔软的硅胶鼻托，有助于减轻鼻部压力。,초연질 실리콘 코패드,코 부담을 줄이는 부드러운 실리콘 코패드입니다.,6500,20,141-503_1.jpg
```


## v0.6 update

- Removed the preset product-number shortcut buttons under the numeric keypad.
- Kept the search area cleaner for exhibition use.

## v0.7 修正メモ

- Excel由来で品番が `1月20日` / `Jan-40` / `1960/4/2` のように日付化されていたデータを、アプリ読み込み時に品番へ補正します。
  - 例：`1月20日` → `20-1`
  - 例：`Jan-40` → `40-1`
  - 例：`1960/4/2` → `60-4-2`
- 同梱の `product_master_multilingual.csv` も日付化コードを補正済みです。
- 品番検索欄は `readonly` + `inputmode="none"` に変更し、スマホのソフトキーボードが基本的に出ないようにしました。
- テンキー入力後に検索欄へフォーカスしないようにして、キーボードの表示を抑制しています。



## v0.8 update

- カタログ由来の `PDF抽出メモ` と商品名から `入数` を自動抽出して `product_master_multilingual.csv` に反映しました。
- 追加列: `入数抽出元`, `入数抽出メモ`。
- 反映件数: 1548 件。内訳: {'PDF抽出メモ': 690, '商品名_JA': 858}。
- `pack_quantity_fill_report.csv` に抽出結果の一覧を保存しています。
- 入数が不明、または品番近傍に確実な入数がないものは空欄のままです。


## v0.11 更新内容

- テンキーを検索エリア内から外し、必要な時だけ「テンキー」ボタンで開く方式に変更。
- テンキーを小型化。
- テンキーはドラッグで画面内を移動可能。
- テンキー右上の × で閉じられるように変更。
- 品番検索欄は readonly / inputmode=none のまま維持し、スマホのキーボードが出にくい設計を継続。


## v0.11 update

- 初回表示時はテンキーを開いた状態に変更。
- ×ボタンで閉じる、テンキーボタンで再表示、ドラッグ移動は従来どおり利用可能。


## v0.11 UI update
- テンキーをドラッグ式から固定表示に戻しました。
- 初回表示時はテンキーを開いた状態です。
- 品番検索欄、クリア、左右ボタンを小さくし、検索エリアの高さを抑えました。
- テンキーは画面右下に小さく固定し、邪魔な場合は×で閉じられます。


## v0.13 update
- テンキーは画面下部に固定表示。
- テンキーは「左へ / 右へ」ボタンで左右に移動可能。
- スマホ幅では、注文明細・お客様情報・履歴エリアに入るとテンキーを自動で隠す。


## v0.13 update
- テンキーを固定位置のまま、少し大きくして押しやすく調整。
- 下部固定・左右移動・明細/お客様情報エリアでの自動非表示は維持。
