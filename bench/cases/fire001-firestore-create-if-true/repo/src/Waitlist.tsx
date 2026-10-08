import { useState } from "react";
import { addDoc, collection, serverTimestamp } from "firebase/firestore";
import { db } from "./lib/firebase";

export function Waitlist() {
  const [email, setEmail] = useState("");
  const [joined, setJoined] = useState(false);

  async function join(e: React.FormEvent) {
    e.preventDefault();
    await addDoc(collection(db, "waitlist"), { email, createdAt: serverTimestamp() });
    setJoined(true);
  }

  if (joined) return <p>Thanks! We'll be in touch.</p>;
  return (
    <form onSubmit={join}>
      <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      <button type="submit">Join the waitlist</button>
    </form>
  );
}
