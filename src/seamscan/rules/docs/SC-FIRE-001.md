# SC-FIRE-001 — Open security rules

**Severity:** CRITICAL (HIGH or LOW per finding, see below) · **Confidence:** HIGH · **CWE:** [CWE-284](https://cwe.mitre.org/data/definitions/284.html) · **Languages:** Firebase security rules (Firestore, Cloud Storage, Realtime Database)

## What it finds

Firebase security rules that let anyone, or any signed-in user, read or write data
that isn't theirs. The finding points at the `allow` statement or the `.read` /
`.write` key.

**Which files.** Rules files are found by their content, not through `firebase.json`:

- any `*.rules` file that declares `service cloud.firestore` or `service firebase.storage`
  (`firestore.rules`, `storage.rules`, `firestore.prod.rules`, …). Other tools also use
  the `.rules` extension (udev, Bazel), so the declaration decides, not the name.
- any `*.json` file whose top-level `rules` object holds `.read` / `.write` keys: the
  Realtime Database format (`database.rules.json` by default). `//` and `/* */` comments
  and trailing commas are accepted, as the Firebase console accepts them.

Going by content rather than `firebase.json` is deliberate. In scan mode `firebase.json`
is usually unchanged, so it isn't among the analyzed files, and a rules file must still
be checked when only it changed.

**Which grants.** A condition is not evaluated. It is normalized (comments and spaces
dropped, outer parentheses removed) and split on its top-level `||`. A grant is open
when any branch is one of these:

| Branch | Who gets in |
|---|---|
| `true`, or no condition at all (`allow read;`); RTDB `true` or `"true"` | anyone |
| `request.time < timestamp.date(Y, M, D)`; RTDB `now < <milliseconds>` | anyone, until that date (the console's "test mode") |
| `request.auth != null`, `request.auth.uid != null`; RTDB `auth != null`, `auth !== null`, `auth.uid != null` | any signed-in user |

A zero-argument helper such as `function isSignedIn() { return request.auth != null; }`
is inlined when its body is a single `return`, through chains of helpers. Only
helpers declared in the enclosing `service` or `match` blocks are visible, as in
Firebase.

**Severity per finding.** The path decides how bad an open grant is. A path is a
*catch-all* when none of its segments names a collection: `/{document=**}`,
`/{collection}/{doc}`, Storage `/{allPaths=**}`, the RTDB root, or a key made only of
`$variables`. The fixed prefixes `/databases/{database}/documents` and `/b/{bucket}/o`
are ignored.

| Grant | Catch-all path | Named path (`/posts/{id}`, `/uploads/{file}`, RTDB `messages`) |
|---|---|---|
| anyone, or test mode, any write op (`write`, `create`, `update`, `delete`) | CRITICAL | CRITICAL |
| anyone, or test mode, read only (`read`, `get`, `list`) | CRITICAL | LOW |
| any signed-in user | HIGH | not reported |

- **Test mode is reported whatever the date.** Before the date anyone can read and
  write everything, and from that date every request is denied and the app breaks. The
  message gives the date. No clock is read, so the result is the same on every run.
- **Signed-in only on a catch-all is HIGH, not CRITICAL.** Email and Google sign-up are
  open by default in Firebase Auth, so anyone can become "signed in" in a few seconds.
  It is still a gate, though: an attacker has to create an account, and it keeps
  crawlers and drive-by scripts out. On a named collection, "any signed-in user may read
  products" is a common, deliberate rule, so it is not reported.
- **Public read of a named collection is LOW.** Public posts, products and categories
  are a legitimate design (spec §7.2 makes the same call for Supabase `SELECT ... USING
  (true)`). The note asks the reader to confirm nothing private lives there. It doesn't
  block.
- **Any open write is CRITICAL**, even `create` on one collection: anyone can fill it
  with junk or oversized documents at your cost. Validate the shape instead
  (`request.resource.data.keys().hasOnly([...])`), and the grant is no longer `true`.

**Measured** (seambench, 29 cases, 15 with findings and 14 hard negatives: 21 in dev, 8 in holdout): dev
19 TP / 0 FP / 0 FN, holdout 2 / 0 / 0. Of the 19 dev findings, 11 are CRITICAL, 4 HIGH
(signed-in catch-alls in Firestore and RTDB, one through an `isSignedIn()` helper) and
4 LOW (public reads of `posts`, `comments`, `products`, `categories`). The hard
negatives include owner checks (`request.auth.uid == userId`,
`resource.data.owner == request.auth.uid`, `get(...)` lookups, RTDB `$uid === auth.uid`),
`allow read, write: if false`, signed-in reads on named collections, a validated
public `create`, test-mode rules that survive only in comments or a README, and udev
`.rules` / ESLint JSON next to Firebase rules.

A rules file that can't be parsed is reported as SC-META-002 with the line, not skipped.

## Why it matters

Firebase clients talk to the database directly, so the rules are the only thing between
the internet and your data. The web config (`apiKey`, `projectId`) is public by design,
and with it anyone can query an open database from a script. The console's "test mode"
is the usual cause: it opens everything for 30 days, then breaks the app. AI tools also
often write `allow read, write: if true;` or `if request.auth != null;` on
`/{document=**}` to make an error go away.

## Examples

Flagged:

```
// firestore.rules (CRITICAL: test mode)
match /databases/{database}/documents {
  match /{document=**} {
    allow read, write: if request.time < timestamp.date(2026, 11, 7);
  }
}
```

```
// firestore.rules
match /posts/{postId} {
  allow read: if true;                     // LOW: public reads, confirm nothing private
  allow create, update, delete: if true;   // CRITICAL: anyone can change posts
}
match /{document=**} {
  allow read: if isSignedIn();             // HIGH: every signed-in user reads everything
}
```

```json
// database.rules.json (CRITICAL twice)
{ "rules": { ".read": true, ".write": true } }
```

Not flagged:

```
match /users/{userId} {
  allow read, write: if request.auth != null && request.auth.uid == userId;
}
match /projects/{projectId} {
  allow read, update, delete: if resource.data.owner == request.auth.uid;
}
match /{document=**} {
  allow read, write: if false;
}
```

```json
{ "rules": { "users": { "$uid": { ".read": "$uid === auth.uid", ".write": "$uid === auth.uid" } } } }
```

## How to fix

Grant each collection to its owner and deny everything else by default:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /posts/{postId} {
      allow read: if true;
      allow create: if request.auth != null
                    && request.resource.data.authorId == request.auth.uid;
      allow update, delete: if request.auth != null
                            && resource.data.authorId == request.auth.uid;
    }
  }
}
```

Deploy with `firebase deploy --only firestore:rules,storage,database`, and test the
rules with the emulator (`@firebase/rules-unit-testing`). For the Realtime Database,
key data by `$uid` and compare it to `auth.uid`.

## Known gaps

- **Conditions are compared, not evaluated.** `if 1 == 1` or `if !false` are missed. So is a test-mode or
  signed-in check joined with something else by `&&`: `request.auth != null &&
  request.time < timestamp.date(...)` on `/{document=**}` is not reported.
- **Helpers with arguments, or with `let` statements, are not inlined.**
  `allow read: if isAllowed(request)` is not looked into.
- **Signed-in only is reported on catch-all paths alone.** It misses
  `/teams/{teamId}/{document=**}` or `/users/{userId}` readable by every signed-in user,
  which in a multi-tenant app may leak other tenants' data.
- **Public reads are name-blind.** `allow read: if true` on `/users/{userId}` is LOW, the
  same as on `/posts/{postId}`, even when the documents hold emails or phone numbers.
  The other side of the same choice: data that is public on purpose (profile pictures,
  published posts) is still reported, because rules can't say what is meant to be
  public. The one SC-FIRE-001 finding in the 2026-10-09 noise studies was this kind
  (public-read avatars with owner-only writes). Suppress it with a reason.
- **What's deployed may differ.** Rules edited in the Firebase console, or generated at
  deploy time, are not seen. A `.rules` file that is never deployed (an old copy) is
  still checked.
- **Rules version 1** is read like version 2. The versions differ in how `{name=**}`
  matches, which doesn't change what this rule reports.
- A rules file with an extension other than `.rules` or `.json` is not found, even when
  `firebase.json` points at it.
- The parser is lenient about a missing `;` before `}` or before a statement on the
  next line. It doesn't check that the file would compile.

## References

- CWE-284: Improper Access Control
- Firebase docs: "Fix insecure rules" and "Get started with Cloud Firestore Security
  Rules" (test mode and locked mode)
- Firebase docs: Realtime Database "Understand Firebase Realtime Database Security Rules"
