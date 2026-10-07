import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";

export default async function AdminPostsPage() {
  const posts = await prisma.post.findMany({ orderBy: { createdAt: "desc" } });

  async function deletePost(formData: FormData) {
    "use server";
    const id = String(formData.get("id"));
    await prisma.post.delete({ where: { id } });
    revalidatePath("/admin/posts");
  }

  return (
    <ul className="divide-y">
      {posts.map((post) => (
        <li key={post.id} className="flex items-center justify-between py-2">
          <span>{post.title}</span>
          <form action={deletePost}>
            <input type="hidden" name="id" value={post.id} />
            <button type="submit" className="text-red-600">
              Delete
            </button>
          </form>
        </li>
      ))}
    </ul>
  );
}
