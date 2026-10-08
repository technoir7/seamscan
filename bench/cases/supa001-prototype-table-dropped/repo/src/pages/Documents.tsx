import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export default function Documents() {
  const [docs, setDocs] = useState<{ id: string; title: string }[]>([]);

  useEffect(() => {
    supabase
      .from("documents")
      .select("id, title")
      .then(({ data }) => setDocs(data ?? []));
  }, []);

  return (
    <ul>
      {docs.map((d) => (
        <li key={d.id}>{d.title}</li>
      ))}
    </ul>
  );
}
