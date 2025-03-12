import math
from datetime import datetime, timedelta
import pytz

from lxml import html, etree
import requests

from features.utils import clean_string

KST = pytz.timezone("Asia/Seoul")


def fetch_popular_notices(count: int):
    page = 1
    notices = []

    today = datetime.now(KST)
    thirty_days_ago = today - timedelta(days=30)

    while True:
        items = fetch_notices(page, False)
        if not items:
            break

        notices.extend(items)

        if items[-1]["createdAt"].replace(tzinfo=KST) < thirty_days_ago:
            break

        page += 1

    for notice in notices:
        days_since_posted = (today - notice["createdAt"].replace(tzinfo=KST)).days
        decay_factor = math.exp(-0.1 * days_since_posted)
        notice["score"] = notice["hits"] * decay_factor

    notices.sort(key=lambda x: x["score"], reverse=True)

    return notices[:count]


def fetch_notices(page: int, fixed_includes: bool, search: str = "") -> list:
    response = requests.post(
        "https://hansung.ac.kr/bbs/hansung/143/artclList.do",
        {"page": page, "srchWrd": search},
    )

    result = []

    tree = html.fromstring(response.content)
    notices = tree.xpath("//div/table[@class='board-table horizon1']/tbody/tr")

    for notice in notices:
        is_fixed = True if notice.get("class").strip() == "notice" else False

        if not fixed_includes and is_fixed:
            continue

        title = clean_string(
            notice.xpath("./td[@class='td-subject']//strong//text()")[0]
        )
        author = clean_string(notice.xpath("./td[@class='td-write']//text()")[0])
        created_at = datetime.strptime(
            clean_string(notice.xpath("./td[@class='td-date']//text()")[0]), "%Y.%m.%d"
        )
        hits = int(clean_string(notice.xpath("./td[@class='td-access']//text()")[0]))
        link = notice.xpath("./td[@class='td-subject']/a/@href")[0]

        result.append(
            {
                "title": title,
                "author": author,
                "hits": hits,
                "link": link,
                "createdAt": created_at,
                "isFixed": is_fixed,
            }
        )

    return result


def fetch_rss_notices(page: int) -> list:
    response = requests.get(
        "https://hansung.ac.kr/bbs/hansung/143/rssList.do",
        {"row": 20, "page": page},
    )

    result = []

    tree = etree.fromstring(response.content)

    notices = tree.xpath("//item")

    for notice in notices:
        title = clean_string(notice.xpath("./title/text()")[0])
        description = clean_string(notice.xpath("./description/text()")[0])
        link = clean_string(notice.xpath("./link/text()")[0])
        pub_date = KST.localize(
            datetime.strptime(
                clean_string(notice.xpath("./pubDate/text()")[0]),
                "%Y-%m-%d %H:%M:%S.%f",
            )
        )

        result.append(
            {
                "title": title,
                "description": description,
                "link": link,
                "pubDate": pub_date,
            }
        )

    return result
