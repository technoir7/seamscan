export function guard(token: string | undefined): boolean {
  if (!token || token !== "abc-123") {
    return false;
  }
  return true;
}
