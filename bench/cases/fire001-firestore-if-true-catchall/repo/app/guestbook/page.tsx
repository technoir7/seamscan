"use client";

import { useEffect, useState } from "react";
import { addDoc, collection, getDocs, limit, orderBy, query } from "firebase/firestore";
import { db } from "@/lib/firebase";

type Entry = { id: string; name: string; message: string };

export default function GuestbookPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const snap = await getDocs(query(collection(db, "guestbook"), orderBy("createdAt", "desc"), limit(50)));
    setEntries(snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Entry, "id">) })));
  }

  useEffect(() => {
    load();
  }, []);

  async function sign(e: React.FormEvent) {
    e.preventDefault();
    await addDoc(collection(db, "guestbook"), { name, message, createdAt: Date.now() });
    setMessage("");
    await load();
  }

  return (
    <section className="space-y-4">
      <form onSubmit={sign} className="flex flex-col gap-2">
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <textarea placeholder="Say hi" value={message} onChange={(e) => setMessage(e.target.value)} />
        <button type="submit">Sign the guestbook</button>
      </form>
      {entries.map((entry) => (
        <article key={entry.id}>
          <strong>{entry.name}</strong>
          <p>{entry.message}</p>
        </article>
      ))}
    </section>
  );
}
