import sanitizeHtml from "sanitize-html";
import { getPost } from "@/lib/cms";

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await getPost(slug);
  const body = sanitizeHtml(post.html, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
  });
  return (
    <article>
      <h1>{post.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: body }} />
    </article>
  );
}
