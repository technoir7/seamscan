import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function Projects() {
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    supabase
      .from("projects")
      .select("id, name")
      .then(({ data }) => setProjects(data ?? []));
  }, []);

  return (
    <ul>
      {projects.map((p) => (
        <li key={p.id}>{p.name}</li>
      ))}
    </ul>
  );
}
