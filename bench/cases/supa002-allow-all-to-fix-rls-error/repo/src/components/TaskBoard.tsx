import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function TaskBoard() {
  const [tasks, setTasks] = useState<{ id: string; title: string; status: string }[]>([]);

  useEffect(() => {
    supabase
      .from("tasks")
      .select("id, title, status")
      .then(({ data }) => setTasks(data ?? []));
  }, []);

  return (
    <section className="grid grid-cols-3 gap-4">
      {tasks.map((t) => (
        <article key={t.id}>{t.title}</article>
      ))}
    </section>
  );
}
