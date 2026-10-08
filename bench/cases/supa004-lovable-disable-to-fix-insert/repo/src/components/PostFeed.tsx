import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export const PostFeed = () => {
  const { data: posts = [] } = useQuery({
    queryKey: ["posts"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("posts")
        .select("id, title, content")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data;
    },
  });

  return (
    <div className="space-y-4">
      {posts.map((p) => (
        <article key={p.id}>
          <h2>{p.title}</h2>
          <p>{p.content}</p>
        </article>
      ))}
    </div>
  );
};
