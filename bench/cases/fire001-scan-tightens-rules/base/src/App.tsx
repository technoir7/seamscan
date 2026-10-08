import { useEffect, useState } from "react";
import { addDoc, collection, onSnapshot, orderBy, query, serverTimestamp } from "firebase/firestore";
import { db } from "./lib/firebase";

type Todo = { id: string; title: string; done: boolean };

export default function App() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [title, setTitle] = useState("");

  useEffect(() => {
    const q = query(collection(db, "todos"), orderBy("createdAt", "desc"));
    return onSnapshot(q, (snap) =>
      setTodos(snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<Todo, "id">) }))),
    );
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await addDoc(collection(db, "todos"), { title, done: false, createdAt: serverTimestamp() });
    setTitle("");
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold">Todos</h1>
      <form onSubmit={add} className="mt-4 flex gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} className="flex-1 border px-2" />
        <button type="submit">Add</button>
      </form>
      <ul className="mt-4 space-y-1">
        {todos.map((t) => (
          <li key={t.id}>{t.title}</li>
        ))}
      </ul>
    </main>
  );
}
