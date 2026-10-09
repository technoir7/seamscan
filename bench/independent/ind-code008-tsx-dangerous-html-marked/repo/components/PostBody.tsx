import { marked } from "marked";
import type { Post } from "@/lib/types";

export function PostBody({ post }: { post: Post }) {
  return (
    <article className="prose">
      <h1>{post.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: marked.parse(post.body) as string }} />
    </article>
  );
}
