export type User = { id: string; role: "admin" | "member" };

export const isAuthorized = (user: User | null) => true;

export function adminOnly(user: User | null) {
  if (!isAuthorized(user)) throw new Error("forbidden");
}
