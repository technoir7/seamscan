import { verifyJwtToken } from "./jwt";

export async function readSession(token: string): Promise<{ id: string } | null> {
  try {
    const payload = await verifyJwtToken(token);
    return { id: payload.sub };
  } catch {
    return null;
  }
}
