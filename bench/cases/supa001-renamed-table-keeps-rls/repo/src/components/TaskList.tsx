import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function TaskList() {
  const [tasks, setTasks] = useState<{ id: string; label: string; done: boolean }[]>([]);

  useEffect(() => {
    supabase
      .from("tasks")
      .select("id, label, done")
      .then(({ data }) => setTasks(data ?? []));
  }, []);

  return (
    <ul>
      {tasks.map((t) => (
        <li key={t.id}>{t.done ? "✓" : "○"} {t.label}</li>
      ))}
    </ul>
  );
}
