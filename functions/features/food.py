import re
from datetime import datetime, timedelta
import pytz

from lxml import html
import requests

from features.utils import clean_string

KST = pytz.timezone("Asia/Seoul")


def fetch_latest_foods() -> list:
    today = datetime.now(KST)

    monday = today - timedelta(days=today.weekday())
    last_monday = monday - timedelta(days=7)

    monday = monday.strftime("%Y.%m.%d")
    last_monday = last_monday.strftime("%Y.%m.%d")

    this_week = fetch_weekday_foods(monday)
    last_week = fetch_weekday_foods(last_monday)

    this_week_list = []
    this_week_seen_names = set()

    for day in this_week.values():
        if day:
            for item in day:
                if item["name"] not in this_week_seen_names:
                    this_week_seen_names.add(item["name"])
                    this_week_list.append(item)

    last_week_list = []
    last_week_seen_names = set()

    for day in last_week.values():
        if day:
            for item in day:
                if item["name"] not in last_week_seen_names:
                    last_week_seen_names.add(item["name"])
                    last_week_list.append(item)

    new_menus = [
        item for item in this_week_list if item["name"] not in last_week_seen_names
    ]

    return new_menus


def fetch_weekday_foods(monday: str) -> dict:
    result = {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": [],
    }
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    response = requests.post(
        "https://www.hansung.ac.kr/diet/hansung/2/view.do",
        {"monday": monday},
    )

    tree = html.fromstring(response.content)
    foods = tree.xpath("//div[@class='table_1 table_m']//tbody/tr")

    for index, food in enumerate(foods):
        c_food = food.xpath("./td[2]")[0]
        day = days[(index // 2) % 7]

        is_none = c_food.get("colspan")

        if is_none:
            result[day] = None
            continue

        raw_data = clean_string(
            html.tostring(c_food, encoding="unicode", method="html")
        )
        raw_data = re.sub(r"^<td>|</td>$", "", raw_data)

        lines = [line.strip() for line in raw_data.split("<br>") if line.strip()]

        # 덮밥류&비빔밥 코너
        if index % 2 == 0:
            main_category = "덮밥류&비빔밥"

            for line in lines:
                if line == "볶음밥&amp;오므라이스&amp;돈까스":
                    main_category = "볶음밥&오므라이스&돈까스"
                    continue

                match = re.search(r"(.+?)(ⓣ)?\s+([\d,]+)", line)

                if match:
                    name, togo, price = match.groups()
                    price = int(price.replace(",", ""))  # 쉼표 제거 후 정수 변환
                    result[day].append(
                        {
                            "name": name.strip(),
                            "price": price,
                            "togo": bool(togo),
                            "type": main_category,
                        }
                    )

        # 면류&찌개&김밥 코너
        if index % 2 == 1:
            main_category = "면류&찌개&김밥"

            for line in lines:
                match = re.search(r"(.+?)(ⓣ)?\s+([\d,]+)", line)
                if match:
                    name, togo, price = match.groups()
                    price = int(price.replace(",", ""))  # 쉼표 제거 후 정수 변환
                    result[day].append(
                        {
                            "name": name.strip(),
                            "price": price,
                            "togo": bool(togo),
                            "type": main_category,
                        }
                    )

    return result


def compare_menus(last_week, this_week):
    diff = {}
    for day, items in last_week.items():
        if day in this_week:
            last_week_items = {item["name"]: item for item in items}
            this_week_items = {item["name"]: item for item in this_week[day]}

            diff[day] = {
                "last_week": [
                    item for item in items if item["name"] not in this_week_items
                ],
                "this_week": [
                    item
                    for item in this_week[day]
                    if item["name"] not in last_week_items
                ],
            }

    return diff
