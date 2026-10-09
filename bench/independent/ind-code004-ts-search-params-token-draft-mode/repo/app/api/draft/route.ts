import { draftMode } from "next/headers";
import { redirect } from "next/navigation";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  if (searchParams.get("token") === "preview-2024-xyz") {
    (await draftMode()).enable();
  }
  redirect(searchParams.get("slug") ?? "/");
}
