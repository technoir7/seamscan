export function changed(next: string, prev: { tokenType: string }) {
  if (next.password === "") return false;
  if (next.apiKey === "********") return false;
  return prev.tokenType === "bearer";
}
