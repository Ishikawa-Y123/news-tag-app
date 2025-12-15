# news-tag-app

ニュースカテゴリ自動付与アプリ
📘 プロジェクト概要

このプロジェクトは、Python でニュースサイトの RSS を取得し、
Google Gemini API を使ってニュース記事に自動でカテゴリタグ（「政治」「経済」「スポーツ」「IT」「AI」）を付ける Web アプリです。

生成したニュース＋タグ情報を all_topics.json に保存し、
index.html から読み込んで Vue.js で表示・カテゴリ絞り込みができるようになっています。

🧩 機能一覧

複数ニュースサイト（Yahooニュース・NHKニュース・Business Journal）から最新ニュースを取得

各記事（タイトル＋説明文）を Gemini API に投げてカテゴリタグを自動判定

自動付与されるカテゴリ：

政治

経済

スポーツ

IT

AI

ニュース一覧を JSON ファイル（all_topics.json）として保存

Web 画面で以下が可能

ニュース一覧の表示（最低 10 件以上）

プルダウンでカテゴリを選択して絞り込み表示
（「すべて」「政治」「経済」「スポーツ」「IT」「AI」）

🔁 カテゴリ変更〜画面表示までのロジック
1. Python でニュース＋タグを準備

rss.py を実行すると、news_sources に定義した 3 つの RSS からニュースを取得します。

get_topics() 関数で、各 RSS から以下情報を取り出します。

title（タイトル）

link（記事への URL）

description（説明文／リード文）

pub_date（公開日時）

それぞれの記事について、tag_topic() を呼び出してカテゴリタグを決定します。

tag_topic() の中で、タイトル＋説明文を 1つの文字列 content にまとめる
→ Gemini API に送る

system prompt で
「内容に関係しそうなカテゴリをすべて付ける」「空配列にしない」
と強めに指示しているので、複数カテゴリが付きやすくなっています。

すべての記事に tags が付き終わったら、
全記事を all_topics.json に書き出します。

2. Web（Vue.js）側の動き

index.html の中で、Vue インスタンスが次のように動きます。

画面ロード時（mounted() フック）に fetch('all_topics.json') を実行し、
JSON 内のニュース一覧を articles 配列に読み込みます。

画面上部の <select> 要素（プルダウン）で選ばれた値を selectedCategory にバインドしています。

<select id="category" v-model="selectedCategory">
  <option v-for="cat in categories" :key="cat" :value="cat">
    {{ cat }}
  </option>
</select>


filteredArticles という computed プロパティで絞り込みを実現しています。

filteredArticles() {
  // 「すべて」のときは全件
  if (this.selectedCategory === 'すべて') {
    return this.articles;
  }
  // 記事の tags に選択中カテゴリが含まれるものだけ表示
  return this.articles.filter(article =>
    Array.isArray(article.tags) &&
    article.tags.includes(this.selectedCategory)
  );
}


テンプレート側では filteredArticles を v-for で回して、
タイトル・説明・タグを画面に表示しています。

プルダウンでカテゴリを変えるたびに、
selectedCategory → filteredArticles が再計算 → 表示される記事が切り替わる、
という流れになっています。

🧱 ファイル構成

リポジトリの主な構成は次の通りです。

.
├─ rss.py          # ニュース取得 + タグ付けスクリプト（Python）
├─ all_topics.json # 取得したニュース一覧 + 自動付与タグ（生成物）
├─ index.html      # ニュースを表示するフロントエンド（Vue.js）
├─ index.css       # ニュース一覧画面のスタイル
└─ README.md       # この説明ファイル

🔧 動作環境

Python 3.x

ライブラリ

google-genai

requests

フロントエンド

素の HTML / CSS / JavaScript

Vue.js 2.x（CDN で読み込み）

🚀 セットアップ手順
1. リポジトリをクローン
git clone <このリポジトリのURL>
cd <クローンしたフォルダ>


※授業用フォルダの場合は、先生から指定されたパスに合わせてください。

2. Python ライブラリのインストール
pip install google-genai requests


※仮想環境を使う場合は、事前に venv をアクティベートしてください。

3. Gemini API キーの設定
PowerShell の場合
$env:GEMINI_API_KEY = "あなたのGemini APIキー"


このキーは 絶対に GitHub に公開しない こと。

rss.py では、環境変数からキーを読み込むようにしています：

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY が環境変数に設定されていません")
client = genai.Client(api_key=api_key)

4. ニュース＋タグの JSON を生成
python rss.py


正常に動けば、このフォルダ内に all_topics.json が作成されます。

実行中、API制限などでエラーが出た場合は、
コンソールに「API呼び出し中にエラーが発生しました: ...」と表示されます。

5. Web サイトの起動
Python の簡易サーバを使う場合
python -m http.server 8000


その後、ブラウザで

http://localhost:8000


にアクセスします。

VSCode の「Go Live」を使う場合

index.html を開く

VSCode の右下「Go Live」をクリック

ブラウザが自動で起動してページが表示されます

⚠️ レート制限とエラーについて

Gemini 無料枠には 1分あたりのリクエスト回数制限 があります。

多くの記事に一気にタグ付けすると、

429 RESOURCE_EXHAUSTED

503 UNAVAILABLE
などのエラーが出ることがあります。

対策として、rss.py 内で 1件ごとのタグ付けの間に time.sleep() を入れて、
リクエスト間隔をあけるようにしています。

それでもエラーが出た場合は、

しばらく時間をおいてから python rss.py をやり直す

もしくは取得する記事数（例: [:10] → [:5]）を一時的に減らして試す
といった運用で対応します。

✅ 動作確認のポイント

all_topics.json に

title

link

description

pub_date

tags（配列：例 ["政治", "経済"]）
が入っていること。

Webページで

初期状態で 10件以上のニュースが表示されること

カテゴリプルダウンを変更すると、表示が切り替わること

記事ごとにタグが表示されていること
