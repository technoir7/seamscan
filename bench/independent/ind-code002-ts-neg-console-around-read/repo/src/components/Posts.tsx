import { useEffect, useState } from "react";
import { supabase } from "../supabase";

export function Posts() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await supabase.from("posts").select("*");
        setPosts(data ?? []);
      } catch (err) {
        console.error("Failed to load posts", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  return loading ? <p>Loading</p> : <ul>{posts.map((p) => <li key={p.id}>{p.title}</li>)}</ul>;
}
