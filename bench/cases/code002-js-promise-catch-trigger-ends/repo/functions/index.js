const functions = require("firebase-functions");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();

exports.onPostDeleted = functions.firestore.document("posts/{id}").onDelete((snap, context) => {
  return db
    .collection("likes")
    .where("postId", "==", context.params.id)
    .get()
    .then((likes) => Promise.all(likes.docs.map((d) => d.ref.delete())))
    .catch((err) => console.error(err));
});
