const KEYWORDS = new Set(["SELECT", "FROM", "WHERE", "JOIN"]);

export function highlight(sql: string): string {
  const tokens = sql.split(/(\s+)/);
  const out: string[] = [];
  for (const token of tokens) {
    if (token === "SELECT" || token === "WHERE") {
      out.push(`<b>${token}</b>`);
    } else if (KEYWORDS.has(token.toUpperCase())) {
      out.push(`<i>${token}</i>`);
    } else {
      out.push(token);
    }
  }
  return out.join("");
}
