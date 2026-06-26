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
