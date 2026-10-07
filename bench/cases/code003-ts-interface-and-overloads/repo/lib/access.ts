export interface SignatureVerifier {
  verify(payload: string, signature: string): boolean;
}

export type PermissionCheck = (userId: string, resource: string) => Promise<boolean>;

export function checkAccess(userId: string, docId: string): Promise<boolean>;
export function checkAccess(userId: string, docIds: string[]): Promise<boolean[]>;
export async function checkAccess(userId: string, docs: string | string[]) {
  const ids = Array.isArray(docs) ? docs : [docs];
  const res = await fetch(`/api/access?user=${userId}&docs=${ids.join(",")}`);
  const allowed: boolean[] = await res.json();
  return Array.isArray(docs) ? allowed : allowed[0];
}
