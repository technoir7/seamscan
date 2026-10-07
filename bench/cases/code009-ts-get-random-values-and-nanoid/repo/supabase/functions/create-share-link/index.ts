import { nanoid } from "npm:nanoid@5";

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  const { docId } = await req.json();
  const shareToken = toHex(crypto.getRandomValues(new Uint8Array(24)));
  const inviteToken = nanoid(32);
  return Response.json({ url: `/share/${docId}?t=${shareToken}`, inviteToken });
});
