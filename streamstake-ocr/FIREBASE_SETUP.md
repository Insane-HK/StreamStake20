# Firebase Service Account Setup

The configuration you provided is for a **Frontend/Web App** (Client SDK), but this Python OCR tool acts as a **Backend Server** (Admin SDK).

To give it permission to write to the database, you need a **Service Account Private Key**.

## How to Get It

1.  Go to the **[Firebase Console](https://console.firebase.google.com/)**.
2.  Open your project (`streamstack-8d985`).
3.  Click the ⚙️ **Settings (Gear Icon)** -> **Project settings**.
4.  Go to the **Service accounts** tab.
5.  Click **Generate new private key**.
6.  This will download a `.json` file.

## Configuration

Open the downloaded JSON file. It will look like this:
```json
{
  "type": "service_account",
  "project_id": "streamstack-8d985",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEv...",
  "client_email": "firebase-adminsdk-xxxxx@streamstack-8d985.iam.gserviceaccount.com",
  ...
}
```

Copy the values into your `.env` file:

```env
FIREBASE_PROJECT_ID=streamstack-8d985
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@streamstack-8d985.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEv..."
FIREBASE_DATABASE_URL=https://streamstack-8d985-default-rtdb.firebaseio.com
```

> **Note:** For the `FIREBASE_PRIVATE_KEY`, copy the *entire* string including `\n` characters. Wrap it in double quotes in the `.env` file.
