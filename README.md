# Firebase for Hansung University `notinoti` App

This Firebase project provides cloud functions for managing food menu updates, university notices, push notifications, and user keyword subscriptions. The functions utilize Firebase Firestore, Firebase Cloud Messaging (FCM), and Firebase Scheduler to automate data updates and notifications.

## Features

### 1. Scheduled Data Updates
- **New Foods (`update_new_foods`)**
  - Fetches the latest food menu and updates the `new-foods` collection daily at midnight.
- **Popular Notices (`update_popular_notices`)**
  - Fetches the top 5 most popular notices and updates the `popular-notices` collection daily at midnight.
- **New Notices (`update_new_notices`)**
  - Fetches new notices from an RSS feed every hour and updates the `new-notices` collection.
- **Clear Inactive User Keywords (`clear_inactive_accounts_keywords`)**
  - Clears keywords of users inactive for 24 weeks, running on the first day of each month at 2 AM.

### 2. Firestore Triggers
- **Detecting New Notices (`on_new_notices_updated`)**
  - Listens for changes in the `settings/processing_flag` document.
  - Sends push notifications to users subscribed to relevant keywords.
- **User Keyword Updates (`on_users_keywords_updated`)**
  - Detects when users update their keyword subscriptions.
  - Adds or removes device tokens from the corresponding keyword document in Firestore.

### 3. Push Notifications
- **`send_push_notification` HTTP Endpoint**
  - Allows sending push notifications via an HTTP POST request.

## Deployment
To deploy these functions, ensure you have Firebase CLI installed and configured. Then, run:

```sh
firebase deploy --only functions
```

## Environment Setup
1. Set `functions` directory as a root folder.
2. Place your Firebase service account JSON file as `service-account.json` in the project root.
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Ensure Firestore database rules are properly configured to allow function access.

## API Usage
### Sending Push Notifications
**Endpoint:** `POST /send_push_notification`

**Request Body:**
```json
{
  "title": "New Notice Available!",
  "body": "Check out the latest university notice.",
  "contents": { "id": "notice123", "title": "Exam Schedule Updated" },
  "n_type": "announcement"
}
```

## Notes
- Ensure Firestore indexes are created for efficient querying.
- The timezone is set to `Asia/Seoul` for all scheduled functions.
- Firestore `processing_flag` is used to track batch updates and prevent redundant processing.

---
This project automates university-related updates and notifications using Firebase Cloud Functions.

To see the full data model of Cloud Firestore: [MODEL.md](MODEL.md) 
