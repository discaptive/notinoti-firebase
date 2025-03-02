from firebase_functions import https_fn, scheduler_fn, firestore_fn
from firebase_functions.firestore_fn import Event, Change, DocumentSnapshot

from firebase_admin import initialize_app, firestore, credentials, messaging
from google.cloud.firestore_v1 import FieldFilter

from features.food import fetch_latest_foods
from features.notice import fetch_popular_notices, fetch_rss_notices

from datetime import datetime, timedelta
import pytz

cred = credentials.Certificate("./service-account.json")
initialize_app(cred)

db = firestore.client()

KST = pytz.timezone("Asia/Seoul")


# Run once a day at midnight, to set new-foods.
@scheduler_fn.on_schedule(
    schedule="1 0 * * *",
    timezone=scheduler_fn.Timezone("Asia/Seoul"),
    region="asia-northeast3",
)
def update_new_foods(event: scheduler_fn.ScheduledEvent) -> None:
    foods = fetch_latest_foods()
    collection_ref = db.collection("new-foods")
    batch = db.batch()

    docs = collection_ref.get()
    for doc in docs:
        batch.delete(doc.reference)

    for food in foods:
        new_food_ref = collection_ref.document()
        batch.set(new_food_ref, food)

    batch.commit()


# Run once a day at midnight, to set popular-notices.
@scheduler_fn.on_schedule(
    schedule="1 0 * * *",
    timezone=scheduler_fn.Timezone("Asia/Seoul"),
    region="asia-northeast3",
)
def update_popular_notices(event: scheduler_fn.ScheduledEvent) -> None:
    notices = fetch_popular_notices(5)
    collection_ref = db.collection("popular-notices")
    batch = db.batch()

    docs = collection_ref.get()
    for doc in docs:
        batch.delete(doc.reference)

    for notice in notices:
        new_notice_ref = collection_ref.document()
        batch.set(new_notice_ref, notice)

    batch.commit()


# Run every hour, to set new-notices.
@scheduler_fn.on_schedule(
    schedule="0 * * * *",
    timezone=scheduler_fn.Timezone("Asia/Seoul"),
    region="asia-northeast3",
)
def update_new_notices(event: scheduler_fn.ScheduledEvent) -> None:
    collection_ref = db.collection("new-notices")
    docs = collection_ref.order_by("pubDate", direction="DESCENDING").get()

    existing = [doc.to_dict() for doc in docs]

    if not existing:
        latest_existing_date = datetime.now(KST) - timedelta(days=7)
    else:
        latest_existing_date = datetime.fromtimestamp(
            existing[0]["pubDate"].timestamp()
        )

    page = 1
    notices = []
    while True:
        fetched = fetch_rss_notices(page)
        if not fetched:
            break

        notices.extend(fetched)
        notices.sort(
            key=lambda x: datetime.fromtimestamp(x["pubDate"].timestamp()), reverse=True
        )

        if (
            datetime.fromtimestamp(notices[-1]["pubDate"].timestamp())
            <= latest_existing_date
        ):
            break

        page += 1

    filtered_notices = [
        notice
        for notice in notices
        if datetime.fromtimestamp(notice["pubDate"].timestamp()) > latest_existing_date
    ]

    if not filtered_notices:
        return

    batch = db.batch()
    start_notices_update()

    for doc in docs:
        batch.delete(doc.reference)

    for filtered_notice in filtered_notices:
        new_notice_ref = collection_ref.document()
        batch.set(new_notice_ref, filtered_notice)

    batch.commit()
    end_notices_update()


# Detect when new-notices collection updates
@firestore_fn.on_document_written(
    document="settings/processing-notices", region="asia-northeast3"
)
def on_new_notices_updated(event: Event[Change[DocumentSnapshot]]) -> None:
    if event.data.after and event.data.after.get("status") == "processing":
        notices = db.collection("new-notices").get()
        keywords = db.collection("keywords").get()

        for notice in notices:
            notice_doc = notice.to_dict()
            title: str = notice_doc.get("title")
            description: str = notice_doc.get("description")

            content = " ".join([title, description])

            for keyword in keywords:
                keyword_doc = keyword.to_dict()
                keyword_raw = keyword_doc.get("keyword")
                subscribers: list[str] = keyword_doc.get("subscribers")

                if keyword_raw in content:
                    send_fcm_notification(
                        title="새로운 공지사항이 도착했어요!",
                        body=description,
                        contents=notice_doc,
                        tokens=subscribers,
                    )

    elif event.data.before and event.data.after is None:
        print("new-notices update completed.")


# Detect when users collection updates
@firestore_fn.on_document_updated(document="users/{docId}", region="asia-northeast3")
def on_users_keywords_updated(event: Event[Change[DocumentSnapshot]]) -> None:
    before_document = event.data.before
    if not before_document:
        return

    before = before_document.to_dict()
    after = event.data.after.to_dict()

    if not before or not after or before.get("keywords") == after.get("keywords"):
        return

    device_token = after.get("deviceToken", None)

    new_keywords = set(after.get("keywords", []))
    old_keywords = set(before.get("keywords", []))

    added_keywords = new_keywords - old_keywords
    removed_keywords = old_keywords - new_keywords

    batch = db.batch()

    if not device_token:
        print(f"User has no device token. Skipping sync.")
        return

    for keyword in added_keywords:
        keyword_docs = (
            db.collection("keywords")
            .where(filter=FieldFilter("keyword", "==", keyword))
            .get()
        )

        if len(keyword_docs) == 0:
            batch.set(
                db.collection("keywords").document(),
                {
                    "keyword": keyword,
                    "subscribers": [device_token],
                },
            )
            continue

        keyword_ref = db.collection("keywords").document(keyword_docs[0].id)
        keyword_data = keyword_docs[0].to_dict()
        subscribers = set(keyword_data.get("subscribers", []))
        subscribers.add(device_token)

        batch.update(keyword_ref, {"subscribers": list(subscribers)})

    for keyword in removed_keywords:
        keyword_docs = (
            db.collection("keywords")
            .where(filter=FieldFilter("keyword", "==", keyword))
            .get()
        )

        if len(keyword_docs) == 0:
            continue

        keyword_ref = db.collection("keywords").document(keyword_docs[0].id)
        keyword_data = keyword_docs[0].to_dict()
        subscribers = set(keyword_data.get("subscribers", []))

        if device_token in subscribers:
            subscribers.remove(device_token)
            batch.update(keyword_ref, {"subscribers": list(subscribers)})

    batch.commit()


def start_notices_update():
    db.collection("settings").document("processing-notices").set(
        {"status": "processing"}
    )


def end_notices_update():
    db.collection("settings").document("processing-notices").delete()


def send_fcm_notification(
    title: str,
    body: str,
    contents: dict,
    tokens: list[str] | None = None,
    n_type: str = "",
):
    if tokens is None:
        tokens = []
        docs = (
            db.collection("users")
            .where(filter=FieldFilter("notifications", "array_contains", n_type))
            .get()
        )

        for doc in docs:
            tokens.append(doc.get("deviceToken"))

    message = messaging.MulticastMessage(
        data=contents,
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )

    messaging.send_each_for_multicast(multicast_message=message)


@https_fn.on_request(region="asia-northeast3")
def send_push_notification(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response(status=405)

    body = req.get_json()

    send_fcm_notification(
        title=body["title"],
        body=body["body"],
        contents=body["contents"],
        n_type=body["n_type"],
    )

    return https_fn.Response(status=200)


# Run every month on first day midnight(AM 2:00), to clear inactive accounts keywords.
@scheduler_fn.on_schedule(
    schedule="0 2 1 * *",
    timezone=scheduler_fn.Timezone("Asia/Seoul"),
    region="asia-northeast3",
)
def clear_inactive_accounts_keywords(event: scheduler_fn.ScheduledEvent) -> None:
    inactive_date = datetime.now(KST) - timedelta(weeks=24)
    docs = (
        db.collection("users")
        .where(filter=FieldFilter("lastActive", "<", inactive_date))
        .get()
    )

    batch = db.batch()
    for doc in docs:
        user_ref = doc.reference
        batch.update(user_ref, {"keywords": []})

    batch.commit()
