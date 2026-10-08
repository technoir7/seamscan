# Habit tracker

A tiny habit tracker built with Vite, React and Firebase.

## Setup

1. Create a Firebase project and enable Firestore.
2. When the console asks, **don't** pick test mode. Test mode deploys:

   ```
   match /{document=**} {
     allow read, write: if request.time < timestamp.date(2026, 11, 7);
   }
   ```

   which leaves the database open to anyone for 30 days.
3. Deploy our rules instead: `firebase deploy --only firestore:rules`.
