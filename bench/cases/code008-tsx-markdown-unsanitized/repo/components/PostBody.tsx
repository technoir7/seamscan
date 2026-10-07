import { marked } from "marked";

type Post = { title: string; body: string };

export function PostBody({ post }: { post: Post }) {
  const html = marked.parse(post.body) as string;
  return (
    <article className="prose lg:prose-xl">
      <h1>{post.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
