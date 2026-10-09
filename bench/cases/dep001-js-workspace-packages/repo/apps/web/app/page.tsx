import { Button } from "@acme/ui/button";
import { db } from "@acme/db";

export default async function Home() {
  const posts = await db.post.findMany();
  return <Button>{posts.length} posts</Button>;
}
