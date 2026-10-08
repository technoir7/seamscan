"use client";

import { addDoc, collection, onSnapshot, query, where } from "firebase/firestore";
import { useEffect, useState } from "react";
import { auth, db } from "@/lib/firebase";

type Note = { id: string; body: string };

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [body, setBody] = useState("");
  const uid = auth.currentUser?.uid;

  useEffect(() => {
    if (!uid) return;
    const q = query(collection(db, "notes"), where("uid", "==", uid));
    return onSnapshot(q, (snap) => setNotes(snap.docs.map((d) => ({ id: d.id, body: d.data().body }))));
  }, [uid]);

  async function save() {
    if (!uid || !body) return;
    await addDoc(collection(db, "notes"), { uid, body });
    setBody("");
  }

  return (
    <div>
      <textarea value={body} onChange={(e) => setBody(e.target.value)} />
      <button onClick={save}>Save</button>
      <ul>
        {notes.map((n) => (
          <li key={n.id}>{n.body}</li>
        ))}
      </ul>
    </div>
  );
}
