export function hasSelect(tokens: string[]): boolean {
  for (const token of tokens) {
    if (token === "SELECT") return true;
  }
  return false;
}
