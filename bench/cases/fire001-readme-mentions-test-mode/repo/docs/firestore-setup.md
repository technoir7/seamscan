# Firestore rules

Never ship `allow read, write: if true;` — the rules in `firestore.rules` scope every
habit to the signed-in user who created it.
