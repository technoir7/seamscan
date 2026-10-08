import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function Post() {
  const { id } = useParams();
  const [post, setPost] = useState<{ title: string; body: string } | null>(null);
  const [comments, setComments] = useState<{ id: string; body: string }[]>([]);

  useEffect(() => {
    supabase.from("posts").select("title, body").eq("id", id).single()
      .then(({ data }) => setPost(data));
    supabase.from("Comments").select("id, body").eq("post_id", id)
      .then(({ data }) => setComments(data ?? []));
  }, [id]);

  if (!post) return null;
  return (
    <article>
      <h1>{post.title}</h1>
      <p>{post.body}</p>
      {comments.map((c) => <p key={c.id}>{c.body}</p>)}
    </article>
  );
}
