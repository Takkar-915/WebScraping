# NotionのAPIキーやデータベースIDはローカルだけに載せる。

import requests
from bs4 import BeautifulSoup
import time
import json
import datetime
import os
import re

import booklist
import remove

from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

API_KEY = os.environ["API_KEY"]
DATABASE_ID = os.environ["DATABASE_ID"]
NOTION_URL_DB = os.environ["NOTION_URL_DB"]


class label:
    def __init__(self, title_name, date_caractor, tag_name):
        self.title = title_name
        self.date = date_caractor
        self.tag = tag_name

# デバッグ用の関数。引数に文字列を指定するとTestsディレクトリ（ローカルのみ）内にファイルを作成。

def debug_file(s):
    path = 'Tests/output.txt'
    with open(path, mode='w') as f:
        f.write(s)

# 引数はint

def set_date(sale_day):
    dt_now = datetime.datetime.now()
    date = ""
    today = dt_now.day

    sale_day_str = str(sale_day)

    # ISO形式（2023-03-22など）の一文字ずつをリストに格納
    d_today = list(str(datetime.date.today()))
    if today < sale_day:
        d_today[8], d_today[9] = sale_day_str[0], sale_day_str[1]
        date = "".join(d_today)
    else:
        if dt_now.month == 12:
            next_year = str(dt_now.year + 1)
            date = next_year + "-01-" + sale_day_str
        else:
            next_month = ""
            if dt_now.month < 9:
                next_month = "0" + str(dt_now.month + 1)
            else:
                next_month = str(dt_now.month + 1)
            d_today[5], d_today[6] = next_month[0], next_month[1]
            d_today[8], d_today[9] = sale_day_str[0], sale_day_str[1]
            date = "".join(d_today)

    return date


# 現在のデータベースに含まれるページ情報を取得して文字列を返す。
def get_current(url):

    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    params = {"page_size": 100}

    response = requests.request('POST', url=url, headers=headers)
    # 最初100個のレスポンスを文字列として格納する。この後、ループで追加していく。
    response_text = response.text

    if response.ok:
        search_response_obj = response.json()
        pages_and_databases = search_response_obj.get("results")

        while search_response_obj.get("has_more"):
            params["start_cursor"] = search_response_obj.get("next_cursor")

            response = requests.post(url, json=params, headers=headers)
            response_text += response.text
            if response.ok:
                search_response_obj = response.json()
                pages_and_databases.extend(search_response_obj.get("results"))

    return response_text

# 指定された引数を元にNotionに追加する。


def add_notion(title, tag, date):
    notion_url = 'https://api.notion.com/v1/pages'

    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    payload = {
        "parent": {
            "database_id": DATABASE_ID
        },
        "properties": {
            "名前": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ],
            },
            "レーベル": {
                "multi_select": [
                    {
                        "name": tag
                    }
                ],
            },
            "発売日": {
                "date": {
                    "start": date
                }
            },
        }
    }

    response = requests.post(notion_url, json=payload, headers=headers)


def add_notion_checkbox(title, tag, date):
    notion_url = 'https://api.notion.com/v1/pages'

    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY
    }

    payload = {
        "parent": {
            "database_id": DATABASE_ID
        },
        "properties": {
            "名前": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ],
            },
            "レーベル": {
                "multi_select": [
                    {
                        "name": tag
                    }
                ],
            },
            "発売日": {
                "date": {
                    "start": date
                }
            },
            "追ってる": {
                "checkbox": True
            },
        }
    }

    response = requests.post(notion_url, json=payload, headers=headers)

# スクレイピングの部分


def dengeki(all_list):
    # 電撃文庫の今月と来月発売の作品タイトルと発売日を抜粋
    # タイトルと発売日を順番に表示するにはループを使う。elmsは配列だから、それで回す。
    url = "https://dengekibunko.jp/product/newrelease-bunko.html"

    # リクエストの前には必ずsleepを入れる。
    time.sleep(5)
    r = requests.get(url)

    soup = BeautifulSoup(r.content, "html.parser")

    elms = soup.select(".p-books-media__title > a")
    tag = "電撃"

    # dateをISO8601に合わせる。まずは発売日の文字列をfind_allしてくる。
    date_elms = soup.find_all("td", text=re.compile("日発売"))
    date_iso_list = []
    for elm in date_elms:
        d = elm.text
        d_list = list(d)
        if d_list[6] == "月":
            d_list.insert(5, "0")
        if d_list[9] == "日":
            d_list.insert(8, "0")

        d = ''.join(d_list)

        d = d.replace("年", "-")
        d = d.replace("月", "-")
        d = d.replace("日発売", "")

        date_iso_list.append(d)

    # スマホ用とPC用で、要素が重複。インデックスが奇数のものを削除。
    del date_iso_list[1::2]

    # 各作品のタイトルと発売日とレーベルを変数とするインスタンスのリストを生成。
    for i in range(len(elms)):
        cl = label(elms[i].text, date_iso_list[i], tag)
        all_list.append(cl)

    return all_list


def mf(all_list):
    url = "https://mfbunkoj.jp/product/new-release.html"

    time.sleep(5)
    r = requests.get(url)

    soup = BeautifulSoup(r.content, "html.parser")

    elms = soup.select(".detail > h2 > a")
    tag = "MF"

    date_elms = soup.find_all("p", text=re.compile("発売日"))
    date_iso_list = []
    for elm in date_elms:
        d = elm.text
        d_list = list(d)
        if d_list[10] == "月":
            d_list.insert(9, "0")
        if d_list[13] == "日":
            d_list.insert(12, "0")

        d = ''.join(d_list)

        d = d.replace("発売日：", "")
        d = d.replace("年", "-")
        d = d.replace("月", "-")
        d = d.replace("日", "")

        date_iso_list.append(d)

    for i in range(len(elms)):
        cl = label(elms[i].text, date_iso_list[i], tag)
        all_list.append(cl)

    return all_list


def gagaga(all_list):
    url = "https://gagagabunko.jp/release/index.html"

    time.sleep(5)
    r = requests.get(url)

    soup = BeautifulSoup(r.content, "html.parser")

    elms = soup.select(".content > #title > h3")
    tag = "ガガガ"
    date = set_date(18)

    for i in range(len(elms)):
        cl = label(elms[i].text, date, tag)
        all_list.append(cl)
    return all_list


def fantasia(all_list):
    url = "https://fantasiabunko.jp/product/"

    time.sleep(5)
    r = requests.get(url)

    soup = BeautifulSoup(r.content, "html.parser")

    elms = soup.select(".detail > .head > h3 > a")
    tag = "ファンタジア"

    date_elms = soup.find_all("p", text=re.compile("発売日"))
    date_iso_list = []
    for elm in date_elms:
        d = elm.text
        d_list = list(d)
        if d_list[10] == "月":
            d_list.insert(9, "0")
        if d_list[13] == "日":
            d_list.insert(12, "0")

        d = ''.join(d_list)

        d = d.replace("発売日：", "")
        d = d.replace("年", "-")
        d = d.replace("月", "-")
        d = d.replace("日", "")

        date_iso_list.append(d)

    for i in range(len(elms)):
        cl = label(elms[i].text, date_iso_list[i], tag)
        all_list.append(cl)

    return all_list


def ga(all_list):
    url1 = "https://ga.sbcr.jp/release/month_current/"
    url2 = "https://ga.sbcr.jp/release/month_next/"

    time.sleep(5)
    r1 = requests.get(url1)
    time.sleep(5)
    r2 = requests.get(url2)

    soup1 = BeautifulSoup(r1.content, "html.parser")
    soup2 = BeautifulSoup(r2.content, "html.parser")

    elms1 = soup1.select(
        ".newBook_gaBunko_wrap .title_area > .title > a > span")
    elms2 = soup2.select(
        ".newBook_gaBunko_wrap .title_area > .title > a > span")

    del elms1[1::2]
    del elms2[1::2]

    date1 = list(str(datetime.date.today()))
    date1[-2], date1[-1] = "1", "5"
    date1 = "".join(date1)

    d_today = list(str(datetime.date.today()))
    date2 = ""
    dt_now = datetime.datetime.now()
    if dt_now.month == 12:
        next_year = str(dt_now.year + 1)
        date2 = next_year + "-01-" + "15"
    else:
        next_month = ""
        if dt_now.month < 9:
            next_month = "0" + str(dt_now.month + 1)
        else:
            next_month = str(dt_now.month + 1)
        d_today[5], d_today[6] = next_month[0], next_month[1]
        d_today[8], d_today[9] = "1", "5"
        date2 = "".join(d_today)

    tag = "GA"

    for i in range(len(elms1)):
        cl1 = label(elms1[i].text, date1, tag)
        all_list.append(cl1)
    for i in range(len(elms2)):
        cl2 = label(elms2[i].text, date2, tag)
        all_list.append(cl2)

    return all_list


def sneaker(all_list):
    dt_now = datetime.datetime.now()
    today = str(datetime.date.today())
    year = str(dt_now.year)
    next_month = "01"
    if dt_now.month == 12:
        year = str(dt_now.year + 1)

    else:
        if dt_now.month < 9:
            next_month = "0" + str(dt_now.month + 1)
        else:
            next_month = str(dt_now.month + 1)

    url1 = "https://sneakerbunko.jp/product/" + today[0:4] + "/" + today[5:7]
    url2 = "https://sneakerbunko.jp/product/" + year + "/" + next_month

    time.sleep(5)
    r1 = requests.get(url1)
    time.sleep(5)
    r2 = requests.get(url2)

    soup1 = BeautifulSoup(r1.content, "html.parser")
    soup2 = BeautifulSoup(r2.content, "html.parser")

    elms1 = soup1.select(".c-thumbnail-book__title > a")
    elms2 = soup2.select(".c-thumbnail-book__title > a")

    # 今月の発売日
    date1 = list(today)
    date1[-2], date1[-1] = "0", "1"
    date1 = "".join(date1)

    # 来月の発売日
    date2 = year + "-" + next_month + "-" + "01"

    tag = "スニーカー"

    for i in range(len(elms1)):
        cl1 = label(elms1[i].text, date1, tag)
        all_list.append(cl1)
    for i in range(len(elms2)):
        cl2 = label(elms2[i].text, date2, tag)
        all_list.append(cl2)

    return all_list


def main():
    all_list = []
    all_list = dengeki(all_list)
    all_list = mf(all_list)
    all_list = gagaga(all_list)
    all_list = fantasia(all_list)
    all_list = ga(all_list)
    all_list = sneaker(all_list)
    
    # 現在のデータベースの状況を取得。タイトルなども取得できる。
    current_db = get_current(NOTION_URL_DB)

    for i in range(len(all_list)):
        # 重複の除外
        if all_list[i].title in current_db:
            continue
        else:
            check_flag = 0
            for book in booklist.l:
                if book in all_list[i].title:
                    time.sleep(0.5)
                    add_notion_checkbox(
                        all_list[i].title, all_list[i].tag, all_list[i].date)
                    check_flag = 1
                    break

            if check_flag == 0:
                time.sleep(0.5)
                add_notion(all_list[i].title,
                           all_list[i].tag, all_list[i].date)


if __name__ == "__main__":
    remove.main()
    time.sleep(5)
    main()
