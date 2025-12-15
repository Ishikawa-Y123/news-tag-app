import os
import time
import datetime as dt
import json
import requests
import xml.etree.ElementTree as ET

from google import genai
from google.genai import types

# ==== Gemini クライアントを1回だけ作る ====
# 事前に PowerShell などで:
   $env:GEMINI_API_KEY = "ここに本物のキー"
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY が環境変数に設定されていません")

client = genai.Client(api_key=api_key)


# ==============================
# ニュース取得
# ==============================
def get_topics(rss_url):
    topics = []
    res = requests.get(rss_url)
    res.raise_for_status()

    root = ET.fromstring(res.text)

    # RSS により構造が違う可能性があるので .//item の方が安全
    for item in root.findall(".//item"):
        title = "" if item.find("title") is None else (item.find("title").text or "")
        link = "" if item.find("link") is None else (item.find("link").text or "")
        description = (
            ""
            if item.find("description") is None
            else (item.find("description").text or "")
        )
        pub_date_raw = (
            ""
            if item.find("pubDate") is None
            else (item.find("pubDate").text or "")
        )

        # 日付はパースできなくても落ちないようにする
        if pub_date_raw:
            try:
                if "+" in pub_date_raw:
                    pub_date = dt.datetime.strptime(
                        pub_date_raw, "%a, %d %b %Y %H:%M:%S %z"
                    )
                else:
                    pub_date = dt.datetime.strptime(
                        pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z"
                    )
                pub_date_iso = pub_date.isoformat()
            except ValueError:
                pub_date_iso = pub_date_raw
        else:
            pub_date_iso = ""

        topic = {
            "title": title,
            "link": link,
            "description": description,
            "pub_date": pub_date_iso,
        }
        topics.append(topic)

    return topics


# ==============================
# Gemini とのやりとり
# ==============================
def chat(request_prompt):
    content_string = request_prompt["messages"][0]["content"]

    config = types.GenerateContentConfig(
        system_instruction=[request_prompt["context"]],
        max_output_tokens=request_prompt["maxOutputTokens"],
        temperature=request_prompt["temperature"],
        top_p=request_prompt["topP"],
        response_mime_type="application/json",  # JSONで返してもらう
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[content_string],
            config=config,
        )
        return {"candidates": [{"text": response.text}]}
    except Exception as e:
        print(f"API呼び出し中にエラーが発生しました: {e}")
        return None


def generate_request_prompt(prompt, content, tmp, p):
    """Gemini に渡すリクエストの共通フォーマット"""
    request_prompt = {
        "context": prompt,
        "maxOutputTokens": 1024,
        "messages": [
            {
                "author": "user",
                "content": content,
            }
        ],
        "temperature": tmp,
        "topP": p,
    }
    return request_prompt


# ==============================
# タグ付け
# ==============================
def tag_topic(content):
    system_prompt = """
        # 命令
        あなたはニュース記事にカテゴリタグを付けるアシスタントです。
        入力されるニュース記事の文章に関連するカテゴリを、
        次の5つの中から「当てはまりそうなものをすべて」選んで出力してください。

        ["政治", "経済", "スポーツ", "IT", "AI"]

        # 重要なルール
        - ニュースの内容に少しでも関係しそうなカテゴリは、すべて含めてください。
        - 迷った場合は「付ける」側に寄せてください。（＝複数タグになりやすくしてよい）
        - 必ず1つ以上のカテゴリを返してください。空配列 [] は使ってはいけません。
        - 関係が強い順に並べてください。（例: ["政治", "経済"] のように重要なものを先頭に）

        # 制約条件
        - 次の5つ以外の文字列は絶対に出力しないこと。
          ["政治", "経済", "スポーツ", "IT", "AI"]
        - 出力は JSON 配列「だけ」にすること。
        - 説明文やコメント、日本語の文章は一切書かないこと。

        # 出力例
        ["政治", "経済"]
    """

    request_prompt = generate_request_prompt(system_prompt, content, 0, 1)
    chat_res = chat(request_prompt)
    if chat_res is None:
        return []

    res_str = chat_res["candidates"][0]["text"].strip()

    # ```json ... ``` で返ってくる可能性に備えてお掃除
    if res_str.startswith("```"):
        res_str = res_str.strip("`")
        res_str = res_str.replace("json", "", 1).strip()

    try:
        res_list = json.loads(res_str)
    except json.JSONDecodeError:
        print("JSONとしてパースできませんでした:", res_str)
        return []

    return res_list


# ==============================
# メイン処理部分
# ==============================
news_sources = [
    {
        "category": "総合",
        "rss": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    },
    {
        "category": "NHK",
        "rss": "https://www.nhk.or.jp/rss/news/cat0.xml",
    },
    {
        "category": "ビジネス",
        "rss": "https://biz-journal.jp/index.xml",
    },
]

all_topics = []
for src in news_sources:
    # ここで何件取るか調整（課題の条件を満たすなら 10 件でOK）
    topics = get_topics(src["rss"])[:10]
    for t in topics:
        t["category"] = src["category"]
    all_topics += topics

# タグ付け（レート制限対策で少し待ちながら）
for idx, topic in enumerate(all_topics):
    if idx > 0:
        # 1件ごとに 15 秒休憩（無料枠 1分あたり5回以下を意識）
        time.sleep(15)

    content = topic["title"] + " " + topic["description"]
    topic["tags"] = tag_topic(content)
    print(f"[{idx+1}/{len(all_topics)}] タグ付け完了: {topic['title']}")

# JSON に保存
with open("all_topics.json", "w", encoding="utf-8") as f:
    json.dump(all_topics, f, indent=4, ensure_ascii=False)

print("all_topics.json を更新しました。")

