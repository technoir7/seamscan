import { draftMode } from "next/headers";
import { redirect } from "next/navigation";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const slug = searchParams.get("slug") ?? "/";

  if (searchParams.get("token") === "preview-2024-xyz") {
    (await draftMode()).enable();
    redirect(slug);
  }
  return new Response("Invalid token", { status: 401 });
}
