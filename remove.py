# Notionに追加したのが結構前のやつは削除する。
import json
import requests
import os
import re
import time
import datetime

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["API_KEY"]
DATABASE_ID = os.environ["DATABASE_ID"]
NOTION_URL_DB = os.environ["NOTION_URL_DB"]

PATCH_API_ENDPOINT = "https://api.notion.com/v1/pages/"

def main():
    # この日付より前のメモを消すことにする。
    today = datetime.date.today()
    two_month_ago = today - datetime.timedelta(days=60)
    delete_limit_date = str(two_month_ago)

    delete_limit_date = "2023-03-26"

    # まずは条件に合致する（この場合は古い情報）要素だけをNotionのDBから抜き出す。

    # ヘッダー。これは固定
    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    # 抜き出す情報のフィルターをかける
    payload = {
        "filter": {
            "and": [
                {
                    "property": "作成日時",
                    "date": {
                        "before": delete_limit_date
                    }
                },
                {
                    "property": "追ってる",
                    "checkbox": {
                        "equals": False
                    }
                }
            ]
        }
    }

    response = requests.request(
        'POST', url=NOTION_URL_DB, json=payload, headers=headers)

    # これで作成日が古すぎる項目のページIDを取得できる。
    result = re.findall(r'"page","id":"(.*?)"', response.text)

    # NotionAPIで、ページを削除するJSON
    payload_del = {
        "archived": True
    }

    for page_id in result:
        time.sleep(0.5)
        notion_url_page = PATCH_API_ENDPOINT + page_id
        response = requests.request(
            'PATCH', url=notion_url_page, json=payload_del, headers=headers)
